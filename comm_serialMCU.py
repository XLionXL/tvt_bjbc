# -*- coding: utf-8 -*-
import datetime
import platform
import struct
import threading
import time
import traceback

from Camera_Link import Camere_Online_Tester
from DebugUDPSender import DebugUDPSender
from comm_decoder_radar import Decoder_Radar, Decode_Result, Radar_Frame_Code
from comm_nano_heartbeat_frame import Component_Status
from comm_radar_driver_shibian import CommDriver, RadarDriver_COM
from common_FireTimer import FireTimer, FireTimer_WithCounter, FireTimer_withCounter_InSpan
from common_hysteresis_threshold import EDGE_DETECT
from common_period_sleep import Period_Sleep
from xypTool.debug import xypLog


class HeartBeat_frame(threading.Thread):
    def __init__(self, mcu, tcp_server=None, radar_driver: CommDriver = None, main_engine=None):
        """
        初始化心跳包模块，
        :param mcu: 需要mcu串口发送命令的comm_send函数
        :param tcp_server:用于发送心跳数据的tcp模块handler
        :param radar_driver:雷达通信模块handler，获得雷达
        :param main_engine:
        """
        threading.Thread.__init__(self)
        self.block_level = 0
        self.component_sta: Component_Status = Component_Status()
        self.power_control_gpio_reset_callback = None
        self.power_control_gpio_set_callback = None
        self.className="sendAllMessage"
        if mcu is not None:
            self.serial_mcu_write_callback = mcu.comm_send
            mcu.decoder.component_status = self.component_sta
        else:
            self.serial_mcu_write_callback = None

        self.tcp_server = tcp_server
        self.radar_driver = radar_driver
        self.main_engine = main_engine
        self.radar_false_alarm_firer = FireTimer()
        self.timer_of_radar_reset = FireTimer()
        self.camera_near_Online_Tester=Camere_Online_Tester(camera_ip="192.168.8.12", camera_port=554, )
        self.camera_remote_Online_Tester=Camere_Online_Tester(camera_ip="192.168.8.11", camera_port=554, )
        self.timer_of_camera_near_power_reset = FireTimer_WithCounter()
        self.timer_of_camera_remote_power_reset = FireTimer_WithCounter()
        self.timer_of_nano_power_reset=FireTimer()
        self.timer_of_infer_restart = FireTimer()
        self.timer_of_tcp_check = FireTimer()
        self.update_camera_rtsp_callback=None
        self.acousto_optic_off_timer=FireTimer()
        self.acousto_optic_on_edge_detect=EDGE_DETECT(False)
        self.always_power_on=0
        self.keep_send = False
        self.alarm_power_on=False
        self.alarm_power_edge=EDGE_DETECT()
        self.remote_call_acousto_optic_power_on_edge=EDGE_DETECT()
        self.remote_call_acousto_optic_power_fire=FireTimer()   # 远程喊话声光报警器电源延时器
        self.period_sleep=Period_Sleep()
        # zipx.s.service 定时重启
        self.zipx_s_service_restart_callback = None
        self.timer_of_zipx_s_service_restart = FireTimer_withCounter_InSpan(-1, -1)

    def listen_power_control_gpio_set(self, callback_set, callback_reset, ):
        if not self.main_engine.main_config.mcu_enable:
            print(f"listen_power_control_gpio_set={callback_set}")
            self.power_control_gpio_set_callback = callback_set
            print(f"listen_power_control_gpio_reset={callback_reset}")
            self.power_control_gpio_reset_callback = callback_reset

    def check_radar_isOk(self, ):
        if self.radar_driver is None:
            print(f"{self.className},check_radar_isOk,self.radar_driver is None")
            return True
        time_now = time.time()
        if time_now - self.radar_driver.latest_data_stamp >= 60:
            self.component_sta.radar_sta.offline_alarm = 1
            time.sleep(1)
            return False
        elif time_now - self.radar_driver.latest_data_stamp < 60 < time_now - self.radar_driver.latest_open_stamp:
            self.component_sta.radar_sta.offline_alarm = 0
        return True

    def set_acousto_optic_power(self, alarm_power):
        self.alarm_power_on = alarm_power
        if self.alarm_power_on:
            self.send_cmd_acousto_optic_on_off_start()


    def send_cmd_acousto_optic_on_off_start(self):
        if not self.keep_send:
            print(f"{datetime.datetime.now()}, send_cmd_acousto_optic_on_off_start restart")            
            self.cmd_thread = threading.Thread(target=self.send_cmd_acousto_optic_power_task, name="send_cmd_acousto_optic_power_task")
            self.cmd_thread.setDaemon(True)
            self.cmd_thread.start()

    def send_cmd_acousto_optic_power_task(self, ):
        print(f"{datetime.datetime.now()}, send_cmd_acousto_optic_power_task start.")
        try:
            self.keep_send = True
            print_firer = FireTimer_withCounter_InSpan(-1, -1)
            alarm_power_on_edge = EDGE_DETECT()
            remote_call_power_on_edge = EDGE_DETECT()
            while self.keep_send:
                # 避免打印数据太多
                is_print = print_firer.isFireTime(4) or \
                           alarm_power_on_edge.is_Edge(self.alarm_power_on) or \
                           remote_call_power_on_edge.is_Edge(self.main_engine.config_manager.remote_call_power_on)
                if is_print:
                    value_str = f"alarm_power_on={self.alarm_power_on} " \
                                f"remote_call_power_on={self.main_engine.config_manager.remote_call_power_on} " \
                                f"always_power_on={self.always_power_on}"
                    print(f"{datetime.datetime.now()},{value_str}")
                acousto_optic_power_on = self.alarm_power_on or self.main_engine.config_manager.remote_call_power_on or self.always_power_on > 0
                if acousto_optic_power_on:
                    # 获得音量配置
                    if self.main_engine is not None:
                        speak_on_off, speak_volume = self.main_engine.get_speak_config_data()
                    else:
                        speak_on_off, speak_volume = 1, 0.8
                    if speak_on_off > 0:
                        # 向mcu发送声光报警器上电命令
                        data_bytes_on = self.radar_driver.decoder.gen_frame(b'\x00\x10\x00\x00\x00\x04\x00\x00\x00\x01', "little")
                        self.power_control_cmd2mcu(data_bytes_on, print_data=is_print)
                        if self.power_control_gpio_set_callback is not None :
                            self.power_control_gpio_set_callback(f"GPIO_AO", "hi")
                    else:
                        print(f"{datetime.datetime.now()},send_cmd_acousto_optic_power_task,speak_on_off=0")
                        time.sleep(2)
                else:
                    # 向mcu发送声光报警器下电命令后跳出循环，结束本函数
                    data_bytes_off = self.radar_driver.decoder.gen_frame(b'\x00\x10\x00\x00\x00\x04\x00\x00\x00\x00', "little")
                    self.power_control_cmd2mcu(data_bytes_off, True)
                    if self.power_control_gpio_set_callback is not None:
                        self.power_control_gpio_set_callback(f"GPIO_AO", "low")
                    break
                time.sleep(1)     # 控制发送速度，太快会导致关闭时延，太慢中间会掉电
            self.keep_send=False
            print(f"{datetime.datetime.now()},send_cmd_acousto_optic_power_task exit.")
        except Exception as error:
            print(f"send_cmd_acousto_optic_power_task {error}")

    def run(self):
        while True:
            try:
                self.period_sleep.period_sleep(1.5)
                if self.remote_call_acousto_optic_power_fire.isFireTime(2):
                    self.main_engine.config_manager.remote_call_power_on = False
                if self.remote_call_acousto_optic_power_on_edge.is_Edge(self.main_engine.config_manager.remote_call_power_on) and (not self.main_engine.config_manager.remote_call_power_on):
                    print(f"{datetime.datetime.now()},REMOTE_CALL_ACOUSTO_OPTIC off")
                if self.always_power_on:
                    self.send_cmd_acousto_optic_on_off_start()

                # 推理状态检查
                if self.main_engine.main_config.infer_enable:
                    is_infer_on = self.main_engine.nano_infer.is_infer_online()
                    if self.component_sta is not None:
                        self.component_sta.nano_sta.infer_quit_alarm = 0 if is_infer_on else 1
                    if not is_infer_on:
                        # 算力中断
                        print(f"{datetime.datetime.now()} HeartBeat_frame run(), infer offline")
                        if self.timer_of_infer_restart.isFireTime(40) and True:
                            self.main_engine.nano_infer.restart_infer(self.main_engine.user_pw)
                        if self.main_engine is not None:
                            # 通过MCU断电重启Nano
                            if self.timer_of_nano_power_reset.isFireTime(300):
                                data_bytes = self.radar_driver.decoder.gen_frame(b'\x00\x41\x00\x00\x00\x04\x00\x00\x00\x00', "little")
                                infor_str=f"{datetime.datetime.now()},mcu reset because infer offline"
                                print(infor_str)
                                xypLog.xypError(infor_str)
                                self.power_control_cmd2mcu(data_bytes)
                    else:
                        # 算力在线
                        self.timer_of_infer_restart.update_Timer()
                        self.timer_of_nano_power_reset.update_Timer()

                # 雷达状态检查
                if not self.check_radar_isOk():  # 雷达故障
                    print(f"{datetime.datetime.now()} HeartBeat_frame run(), radar offline")
                    # 掉线持续40s，则断电重启
                    if self.timer_of_radar_reset.isFireTime(10):
                        data_bytes = self.radar_driver.decoder.gen_frame(b'\x00\x42\x00\x00\x00\x04\x00\x00\x00\x00', "little")
                        infor_str=f"{datetime.datetime.now()} radar reset because radar offline"
                        print(infor_str)
                        xypLog.xypError(infor_str)
                        self.power_control_cmd2mcu(data_bytes)
                        if self.power_control_gpio_reset_callback is not None:
                            print(f"power_control_gpio_reset_callback")
                            self.power_control_gpio_reset_callback("GPIO_RD")
                            self.power_control_gpio_reset_callback("GPIO_HB") # 20230526 北京比测雷达接的灯板供电口
                            self.radar_driver.comm_close() # 20230901 重启雷达也重启下通信端口，避免因为端口通信故障导致雷达反复重启
                else:
                    self.timer_of_radar_reset.update_Timer()

                # 近焦相机状态检查
                reset_time_s = 300
                if not self.camera_near_Online_Tester.is_Camera_Online():
                    if 5 < time.time() - self.timer_of_camera_near_power_reset.startTime < 10:
                        print(f"{datetime.datetime.now()} camera_near,offline")
                    if time.time() - self.timer_of_camera_near_power_reset.startTime > 90:
                        # 相机上电到ping通大概需要60多秒。ping不通相机达到90秒，则发出报警。
                        self.component_sta.camera_near.rtsp_quit_alarm=1
                        if 90<time.time() - self.timer_of_camera_near_power_reset.startTime < 100:
                            print(f"{datetime.datetime.now()} camera_near,offline rtsp_quit_alarm")
                    if self.timer_of_camera_near_power_reset.isFireTime(reset_time_s):
                        # 重启近焦相机
                        camera_ip_port_str=f"{self.camera_near_Online_Tester.camera_ip}:{self.camera_near_Online_Tester.camera_port}"
                        data_bytes = self.radar_driver.decoder.gen_frame(b'\x00\x40\x00\x00\x00\x05\x00\x00\x00\x00\x00', "big")
                        infor_str = f"{datetime.datetime.now()},camera_near,{camera_ip_port_str} reset because offline {reset_time_s}s"
                        print(infor_str)
                        xypLog.xypError(infor_str)
                        self.power_control_cmd2mcu(data_bytes)
                        if self.power_control_gpio_reset_callback is not None:
                            self.power_control_gpio_reset_callback("GPIO_VC")
                            self.main_engine.camera_driver.comm_close()  # 20230901 重启雷达也重启下通信端口，避免因为端口通信故障导致雷达反复重启
                else:
                    # 相机有连接
                    self.timer_of_camera_near_power_reset.update_Timer()
                    self.timer_of_camera_near_power_reset.reset_fire_cnt()
                    if self.main_engine is not None and time.time() - self.main_engine.camera_driver.latest_data_stamp < 5:
                        self.component_sta.camera_near.rtsp_quit_alarm = 0

                # 远焦相机状态检查
                if self.main_engine.main_config.camera_remote_enable:
                    if not self.camera_remote_Online_Tester.is_Camera_Online():
                        if 5 < time.time() - self.timer_of_camera_remote_power_reset.startTime < 10:
                            print(f"{datetime.datetime.now()} camera_remote,offline")
                        if time.time()-self.timer_of_camera_remote_power_reset.startTime>90:
                            # 相机上电到ping通大概需要60多秒。ping不通相机达到90秒，则发出报警。
                            self.component_sta.camera_remote.rtsp_quit_alarm = 1
                            if 90 < time.time() - self.timer_of_camera_remote_power_reset.startTime < 100:
                                print(f"{datetime.datetime.now()} camera_remote,offline,rtsp_quit_alarm")
                        if self.timer_of_camera_remote_power_reset.isFireTime(reset_time_s):
                            # 重启远焦相机
                            camera_ip_port_str = f"{self.camera_remote_Online_Tester.camera_ip}:{self.camera_remote_Online_Tester.camera_port}"
                            data_bytes = self.radar_driver.decoder.gen_frame(b'\x00\x40\x00\x00\x00\x05\x01\x00\x00\x00\x00', "big")
                            infor_str = f"{datetime.datetime.now()},camera_remote,{camera_ip_port_str} reset because offline {reset_time_s}s"
                            print(infor_str)
                            xypLog.xypError(infor_str)
                            self.power_control_cmd2mcu(data_bytes)
                            if self.power_control_gpio_reset_callback is not None:
                                self.power_control_gpio_reset_callback("GPIO_RC")
                    else:
                        # 相机有连接
                        self.timer_of_camera_remote_power_reset.update_Timer()
                        self.timer_of_camera_remote_power_reset.reset_fire_cnt()
                        if time.time()-self.main_engine.camera_driver.latest_data_stamp<5:
                            self.component_sta.camera_remote.rtsp_quit_alarm = 0

                # tcp状态检查,10s阻塞则restart consumer_thread,30s阻塞则重启tcp侦听,60s阻塞则重启推理服务
                if self.timer_of_tcp_check.isFireTime(1):
                    timeSpan_of_tcp_send = time.time() - self.main_engine.tcp_server.send_ok_timeStamp
                    block_ipPort_list = self.main_engine.tcp_server.get_tcp_recvQ_size_by_netstat()
                    if 5 < timeSpan_of_tcp_send:
                        print(f"{datetime.datetime.now()} tcp_server block timeSpan_of_tcp_send={timeSpan_of_tcp_send},"
                              f"block_ipPort_list={block_ipPort_list},block_level={self.block_level}")
                    elif timeSpan_of_tcp_send < 1:
                        self.block_level = 0
                    if 10 < timeSpan_of_tcp_send < 30 and self.block_level in [0]:
                        print(f"{datetime.datetime.now()} tcp_server block to restart consumer_thread")
                        self.main_engine.tcp_server.close_consumer_thread()
                        self.main_engine.tcp_server.init_consumer_thread()
                        self.block_level = 1
                    elif 30 <= timeSpan_of_tcp_send < 60 and self.block_level in [1]:
                        print(f"{datetime.datetime.now()} tcp_server block to restart tcp server")
                        self.main_engine.tcp_server.close()
                        self.main_engine.tcp_server.run_forever(is_block=False)
                        self.block_level = 2
                    # elif 60 <= timeSpan_of_tcp_send < 120 and self.block_level in [2]:
                    #     print(f"{datetime.datetime.now()} tcp_server block to restart zipx.s.service")
                    #     self.zipx_s_service_restart_callback()
                    #     self.block_level = 0
                    #     time.sleep(10)

                if self.update_camera_rtsp_callback is not None:
                    self.update_camera_rtsp_callback()
                if self.tcp_server is not None:
                    self.tcp_server.send_heartbeat_data(self.component_sta.gen_heartbeat_frame(self.main_engine))
                # 读 false_alarm
                if self.radar_false_alarm_firer.isFireTime(3600*2):
                    # cmd_frame=b'\xAA\xAA\x55\x55\x02\xA2\x00\x00\x00\x04\x00\x00\x00\x00\xC1\x6A\x55\x55\xAA\xAA'
                    if "UDP" in self.main_engine.radar_driver.className and self.main_engine.radar_driver_udp_cmd is not None:
                        cmd_frame = self.main_engine.radar_driver_udp_cmd.decoder.get_radar_false_alarm_cmd()
                        self.main_engine.radar_driver_udp_cmd.comm_send(cmd_frame, True)
                    else:
                        cmd_frame = self.main_engine.radar_driver.decoder.get_radar_false_alarm_cmd()
                        self.main_engine.radar_driver.comm_send(cmd_frame, True)
                    pass
                # # 长期运行后重启zipx_s_service
                # restart_time_s = self.main_engine.main_config.zipx_s_service_restart_time_s
                # if restart_time_s > 0 and self.timer_of_zipx_s_service_restart.isFireTime(restart_time_s):
                #     if self.zipx_s_service_restart_callback is not None:
                #         self.zipx_s_service_restart_callback()
                # monitor_trace 没有运行
                # if time.time() - self.main_engine.trace.timeStamp_start > 30:
                #     infor_str = f"{datetime.datetime.now()},zipx_s_service reset because monitor_trace offline "
                #     print(infor_str)
                #     LOG_system_info(infor_str)
                #     if self.zipx_s_service_restart_callback is not None:
                #         self.zipx_s_service_restart_callback()

            except Exception as error:
                print(f"{datetime.datetime.now()},HeartBeat_frame error={traceback.print_exc()}")

    def handle_remote_call_acousto_optic_power(self,  json_obj):
        """
        {
            "code": 305,
            "msg": "audio_heartbeat",
            "data":{"count":1}
         }
        """
        print(f"{datetime.datetime.now()},REMOTE_CALL_ACOUSTO_OPTIC on, json={json_obj}")
        self.main_engine.config_manager.remote_call_power_on = True
        self.remote_call_acousto_optic_power_fire.update_Timer()
        # 只在喊话开始时候立即执行打开电源命令，不要频繁发送命令给mcu，导致mcu关闭声光报警器延时。
        if int(json_obj["data"]["count"])<=2:
            self.send_cmd_acousto_optic_on_off_start()

    def power_control_cmd2mcu(self, data_bytes, print_data=True):
        data_write_str = "".join(['%02X' % x for x in data_bytes])
        print_for_debug=False
        if self.serial_mcu_write_callback is not None:
            if print_data or print_for_debug:
                infor_str = f"{datetime.datetime.now()},mcu cmd dataBytes={data_write_str}"
                xypLog.xypError(infor_str)
                print(infor_str)
            self.serial_mcu_write_callback(data_bytes)
            self.serial_mcu_write_callback(data_bytes)
            # self.serial_mcu_write_callback(data_bytes)
            # time.sleep(1)
        else:
            print(f"{datetime.datetime.now()},send_mcu_cmd_bytes is None,can't send mcu cmd {data_write_str}")


class SerialMCU(RadarDriver_COM):
    time_start = time.time()
    print_time = 30

    def __init__(self, portName="/dev/ttyTHS1", get_edition=True):
        time.sleep(2)
        super().__init__(portName,get_edition=get_edition)
        self.className = "SerialMCU"
        self.timeout_s = 1
        self.decoder = Decoder_MCU()
        self.is_print_mcu_date=False

    # def _run_receive(self):
    #     while True:
    #         try:
    #             self.comm_open_if_need()
    #             self.comm_read_to_buffer()
    #             if len(self.decoder.dataBuffer_bytes)>=10:
    #                 frameIndex, frameTailIndex, frameData = self.decoder.check_headtail_crc()
    #                 if frameTailIndex<0:
    #                     time.sleep(0.05)
    #                 # 解码一帧
    #                 if frameData is not None:
    #                     self.latest_data_stamp = time.time()
    #                     self.decoder.unpack_mcu_frame(frameData)
    #                     # 仅mcu收发调试，打印mcu数据帧
    #                     time_spend=time.time() - SerialMCU.time_start
    #                     if time_spend < SerialMCU.print_time:
    #                         frame_hex_str="".join(['%02X' % x for x in frameData])
    #                         print(f"{datetime.datetime.now()},SerialMCU _run_receive {time_spend}/{SerialMCU.print_time} MCU_Frame={frame_hex_str}")
    #             # 如果还没有读到版本号，则持续发送读版本号的命令
    #             if self.edition_str is None and self.get_edition_firer.isFireTime(2):
    #                 frame_get_edition = self.decoder.get_radar_edition_cmd()
    #                 self.comm_send(frame_get_edition, showDataHex=True)
    #         except Exception as e:
    #             print(f"{datetime.datetime.now()},error={str(e)}")


class Decoder_MCU(Decoder_Radar):
    time_start = time.time()
    print_time = 30

    def __init__(self):
        super().__init__()
        self.debug_callback =None
        self.component_status = None

    def decode(self, data_frame):
        time_spend=time.time()-Decoder_MCU.time_start
        offset = 10
        decode_result = Decode_Result()
        decode_result.code = self.get_code(data_frame)
        if len(data_frame) >= 16:
            self.mcu_timeStamp = time.time()
        if decode_result.code == Radar_Frame_Code.radar_edition:  # 版本
            decode_result.value=self.update_edition_str(data_frame)
        if decode_result.code == Radar_Frame_Code.mcu_temp:  # 温度
            T = struct.unpack('>f', data_frame[offset + 0:offset + 4])[0]
            if self.component_status is not None:
                self.component_status.intelCore.temp = T
            self.debug_callback_function(f"Decoder_MCU Temp:{T}")
        if decode_result.code ==Radar_Frame_Code.mcu_angel:  # 角度
            angle_x = struct.unpack('>f', data_frame[offset + 0:offset + 4])[0]
            angle_y = struct.unpack('>f', data_frame[offset + 4:offset + 8])[0]
            if self.component_status is not None:
                self.component_status.intelCore.angle = [angle_x, angle_y]
            self.debug_callback_function(f"Decoder_MCU angle:angle_x={angle_x},angle_y={angle_y}")
        if decode_result.code ==Radar_Frame_Code.mcu_gps:  # GPS
            index = 0
            longitude = struct.unpack('>f', data_frame[offset + 4 * index:offset + 4 * (index + 1)])[0]
            index = 1
            latitude = struct.unpack('>f', data_frame[offset + 4 * index:offset + 4 * (index + 1)])[0]
            if time_spend < Decoder_MCU.print_time:
                print(f"Decoder_MCU GPS long={longitude},lati={latitude}")
            self.debug_callback_function(f"Decoder_MCU GPS long={longitude},lati={latitude}")
            if self.component_status is not None:
                self.component_status.intelCore.gps_lnglat = [longitude, latitude]
        if decode_result.code == Radar_Frame_Code.mcu_curt:  # 电流
            result = [0] * 10
            for index in range(len(result)):
                value = struct.unpack('>f', data_frame[offset + 4 * index:offset + 4 * (index + 1)])[0]
                result[index] = round(value, 4)
            result_str=",".join([f"{x:.3f}" for x in result])
            self.debug_callback_function(f"Decoder_MCU current:{result_str}")
            if time_spend < Decoder_MCU.print_time:
                print(f"Decoder_MCU current {time_spend}/{SerialMCU.print_time}:{result_str}")
            if self.component_status is not None:
                self.component_status.intelCore.acousto_optic_current = result[0]  # 声光报警
                self.component_status.radar_sta.current = result[1]  # 雷达
                self.component_status.intelCore.warm_current = result[2]  # 加热片
                self.component_status.camera_near.reserved["near_cam_current"] = result[3]  # 近端摄像头
                self.component_status.intelCore.gps_current = result[4]  # GPS
                self.component_status.intelCore.angle_current = result[5]  # 角度传感器
                self.component_status.intelCore.temp_current = result[6]  # 温度传感器
                self.component_status.nano_sta.current = result[7]  # NANO
                self.component_status.intelCore.exchange_current = result[8]  # 交换机
                self.component_status.camera_remote.reserved["remote_cam_current"] = result[9]  # 远端摄像头
        if decode_result.code == Radar_Frame_Code.mcu_volt:  # 电压
            # 1.声光报警器，2.雷达，3.加热片   4.近距离摄像头，5.GPS，6.角度传感器，7.温度传感器，8.NANO，9.交换机，10.远距离摄像头，
            # 11.温湿度等模块总路线，12.NANO总电源，13.交换机总电源
            result = [0] * 13
            for index in range(len(result)):
                value = struct.unpack('>f', data_frame[offset + 4 * index:offset + 4 * (index + 1)])[0]
                result[index] = round(value, 4)

            #for debug
            data_str = "".join(['%02X' % x for x in data_frame])
            self.debug_callback_function(f"Decoder_MCU Frame:{data_str}")
            result_str = ",".join([f"{x:.3f}" for x in result])
            self.debug_callback_function(f"Decoder_MCU voltage:{result_str}")
            if time_spend < Decoder_MCU.print_time:
                print(f"Decoder_MCU voltage {time_spend}/{SerialMCU.print_time}:{result_str}")
            if self.component_status is not None:
                self.component_status.intelCore.acousto_optic_voltage = result[0]  # 声光报警
                self.component_status.radar_sta.voltage = result[1]  # 雷达
                self.component_status.intelCore.warm_voltage = result[2]  # 加热片
                self.component_status.camera_near.reserved["near_cam_voltage"] = result[3]  # 近端摄像头
                self.component_status.intelCore.gps_voltage = result[4]  # GPS
                self.component_status.intelCore.angle_voltage = result[5]  # 角度传感器
                self.component_status.intelCore.temp_voltage = result[6]  # 温度传感器
                self.component_status.nano_sta.voltage = result[7]  # NANO
                self.component_status.intelCore.exchange_voltage = result[8]  # 交换机
                self.component_status.camera_remote.reserved["remote_cam_voltage"] = result[9]  # 远端摄像头
                self.component_status.intelCore.T_sum_v = result[10]  # 温湿度
                self.component_status.intelCore.nano_sum_v = result[11]  # nano总电源
                self.component_status.intelCore.exchange_sum_v = result[12]  # 交换机总电源

        # if self.component_status is not None:
        #     # print(f"debug_1009_mcu Decoder_MCU.unpack_mcu_frame update_status")
        #     self.component_status.intelCore.update_status()
        #     self.component_status.nano_sta.update_status()
        #     self.component_status.radar_sta.update_status()
        #     self.component_status.mcu_sta.update_status()
        #     self.component_status.camera_near.update_status()
        #     self.component_status.camera_remote.update_status()

        return None


if __name__ == '__main__':

    if "Windows" in platform.platform():
        ser = SerialMCU(portName="COM1")  # MCU数据
        # ser.get_radar_mcu_edition()
    else:
        ser = SerialMCU(portName="/dev/ttyTHS1")  # MCU数据
        # ser.get_radar_mcu_edition()
    debuger = DebugUDPSender()
    ser.decoder.debug_callback=print
    ser.udp_debug_callback=print
    # ser.decoder.debug_callback = debuger.udp_send

    ser.start(False)
    time.sleep(20)
    ser.exit()

