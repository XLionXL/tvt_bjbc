# -*- coding:utf-8 -*-
import datetime
import time

class IntelCore_status():
    def __init__(self):
        self.temp = 0  # 工控板温度
        self.temp_current = 0  # 温度传感器电流
        self.temp_voltage = 0  # 温度传感器电压
        self.angle = []  # 工控板角度 x,y
        self.angle_current = 0  # 角度传感器电流
        self.angle_voltage = 0  # 角度传感器电压
        self.gps_lnglat = []  # gps经纬度
        self.gps_current = 0  # gps电流
        self.gps_voltage = 0  # gps电压
        self.acousto_optic_current = 0  # 声光报警电流
        self.acousto_optic_voltage = 0  # 声光报警电压
        self.exchange_current = 0  # 交换机电流
        self.exchange_voltage = 0  # 交换价电压
        self.warm_current = 0  # 加热片电流
        self.warm_voltage = 0  # 加热片电压
        self.T_sum_v = 5  # 温湿度电压
        self.nano_sum_v = 5  # nano总电源电压
        self.exchange_sum_v = 3.3  # 交换机总电源电压
        self.intelCore_status = {}
        self.update_status()

    def update_status(self):
        self.intelCore_status = {
            "temp": self.temp,
            "temp_current": self.temp_current,
            "temp_voltage": self.temp_voltage,
            "angle": self.angle,
            "angle_current": self.angle_current,
            "angle_voltage": self.angle_voltage,
            "gps": self.gps_lnglat,
            "gps_current": self.gps_current,
            "gps_voltage": self.gps_voltage,
            "acousto_optic_current": self.acousto_optic_current,
            "acousto_optic_voltage": self.acousto_optic_voltage,
            "exchange_current": self.exchange_current,
            "exchange_voltage": self.exchange_voltage,
            "warm_current": self.warm_current,
            "warm_voltage": self.warm_voltage,
            "T_sum_v": self.T_sum_v,
            "nano_sum_v": self.nano_sum_v,
            "exchange_sum_v": self.exchange_sum_v,
        }


class Nano_status():
    def __init__(self):
        self.class_name = "Nano_status"
        self.temp_alarm = 0  # 温度异常报警,0正常,1报警
        self.temp = 30.0  # 当前温度
        self.temp_high_threshold = 60.0  # 高温报警阈值
        self.temp_low_threshold = -20.0  # 低温报警阈值
        self.voltage_alarm = 0  # 电压异常报警，0正常,1报警
        self.voltage = 5.0  # 当前电压
        self.voltage_high_threshold = round(self.voltage * 1.1, 3)  # 电压过高报警阈值
        self.voltage_low_threshold = round(self.voltage * 0.8, 3)  # 电压过低报警阈值
        self.current_alarm = 0  # 电流异常是否报警，0正常,1报警
        self.current = 2.2  # 当前电流
        self.current_high_threshold = round(self.current * 1.2, 3)  # 电流过大报警阈值
        self.current_low_threshold = 0-self.current_high_threshold  # 电流过低报警阈值
        self.infer_quit_alarm = 0  # 推理停止报警0正常,1停止
        self.infer_timeStamp = 0  # 推理停止报警0正常,1停止
        self.reserved = {}  # 用于扩展后续其他信息
        self.nano_status = {}
        self.update_status()

    def update_status(self):
        if self.voltage >= self.voltage_high_threshold or self.voltage <= self.voltage_low_threshold:
            self.voltage_alarm = 1
        else:
            self.voltage_alarm = 0

        if abs(self.current) >= self.current_high_threshold :
            self.current_alarm = 1
        else:
            self.current_alarm = 0

        self.nano_status = {
            "temp_alarm": self.temp_alarm,  # 温度异常报警,0正常,1报警
            "temp": self.temp,  # 当前温度
            "temp_high_threshold": self.temp_high_threshold,  # 高温报警阈值
            "temp_low_threshold": self.temp_low_threshold,  # 低温报警阈值
            "voltage_alarm": self.voltage_alarm,  # 电压异常报警，0正常,1报警
            "voltage": self.voltage,  # 当前电压
            "voltage_high_threshold": self.voltage_high_threshold,  # 电压过高报警阈值
            "voltage_low_threshold": self.voltage_low_threshold,  # 电压过低报警阈值
            "current_alarm": self.current_alarm,  # 电流异常是否报警，0正常,1报警
            "current": self.current,  # 当前电流
            "current_high_threshold": self.current_high_threshold,  # 电流过大报警阈值
            "current_low_threshold": self.current_low_threshold,  # 电流过低报警阈值
            "infer_quit_alarm": self.infer_quit_alarm,  # 推理停止报警0正常,1停止
            "reserved": {},  # 用于扩展后续其他信息
        }


class Radar_status():
    def __init__(self):
        self.class_name = "Radar_status"
        self.temp_alarm = 0  # 温度异常报警,0正常,1报警,
        self.temp = 30.0  # 当前温度
        self.temp_high_threshold = 60.0  # 高温报警阈值
        self.temp_low_threshold = -20.0  # 低温报警阈值
        self.voltage_alarm = 0  # 电压异常报警，0正常,1报警
        self.voltage = 12.0  # 当前电压
        self.voltage_high_threshold = round(self.voltage * 1.1, 3)  # 电压过高报警阈值
        self.voltage_low_threshold = round(self.voltage * 0.8, 3)  # 电压过低报警阈值
        self.current_alarm = 0  # 电流异常是否报警，0正常,1报警
        self.current = 0.7  # 当前电流
        self.current_high_threshold = round(self.current * 1.2, 3)  # 电流过大报警阈值
        self.current_low_threshold = 0 - self.current_high_threshold  # 电流过低报警阈值
        self.occlusion_alarm = 0  # 雷达是否遮挡报警，0正常,1遮挡
        self.offline_alarm = 0  # 雷达是否在线报警，0正常,1掉线
        self.reserved = {}  # 用于扩展后续其他信息
        self.radar_status = {}
        self.update_status()
        self.debug_callback = None

    def debug_callback_function(self, data):
        if self.debug_callback is not None:
            self.debug_callback(data)

    def update_status(self):
        if self.voltage >= self.voltage_high_threshold or self.voltage <= self.voltage_low_threshold:
            self.voltage_alarm = 1
        else:
            self.voltage_alarm = 0

        if abs(self.current) >= self.current_high_threshold :
            self.current_alarm = 1
        else:
            self.current_alarm = 0

        self.radar_status = {
            "temp_alarm": self.temp_alarm,  # 温度异常报警,0正常,1报警
            "temp": self.temp,  # 当前温度
            "temp_high_threshold": self.temp_high_threshold,  # 高温报警阈值
            "temp_low_threshold": self.temp_low_threshold,  # 低温报警阈值
            "voltage_alarm": self.voltage_alarm,  # 电压异常报警，0正常,1报警
            "voltage": self.voltage,  # 当前电压
            "voltage_high_threshold": self.voltage_high_threshold,  # 电压过高报警阈值
            "voltage_low_threshold": self.voltage_low_threshold,  # 电压过低报警阈值
            "current_alarm": self.current_alarm,  # 电流异常是否报警，0正常,1报警
            "current": self.current,  # 当前电流
            "current_high_threshold": self.current_high_threshold,  # 电流过大报警阈值
            "current_low_threshold": self.current_low_threshold,  # 电流过低报警阈值
            "occlusion_alarm": self.occlusion_alarm,  # 雷达是否遮挡报警，0正常,1遮挡
            "offline_alarm": self.offline_alarm,  # 雷达是否在线报警，0正常,1遮挡
            "reserved": {},  # 用于扩展后续其他信息
        }


class MCU_status():
    def __init__(self):
        self.temp_alarm = 0  # 温度异常报警,0正常,1报警,
        self.temp = 30.0  # 当前温度
        self.temp_high_threshold = 60.0  # 高温报警阈值
        self.temp_low_threshold = -20.0  # 低温报警阈值
        self.voltage_alarm = 0  # 电压异常报警，0正常,1报警
        self.voltage = 12.0  # 当前电压
        self.voltage_high_threshold = round(self.voltage * 1.1, 3)  # 电压过高报警阈值
        self.voltage_low_threshold = round(self.voltage * 0.8, 3)  # 电压过低报警阈值
        self.current_alarm = 0  # 电流异常是否报警，0正常,1报警
        self.current = 2.0  # 当前电流
        self.current_high_threshold = 2.2  # 电流过大报警阈值
        self.current_low_threshold = 0-self.current_high_threshold  # 电流过低报警阈值
        self.reserved = {}  # 用于扩展后续其他信息
        self.mcu_status = {}
        self.update_status()

    def update_status(self):
        self.mcu_status = {
            "temp_alarm": self.temp_alarm,  # 温度异常报警,0正常,1报警
            "temp": self.temp,  # 当前温度
            "temp_high_threshold": self.temp_high_threshold,  # 高温报警阈值
            "temp_low_threshold": self.temp_low_threshold,  # 低温报警阈值
            "voltage_alarm": self.voltage_alarm,  # 电压异常报警，0正常,1报警
            "voltage": self.voltage,  # 当前电压
            "voltage_high_threshold": self.voltage_high_threshold,  # 电压过高报警阈值
            "voltage_low_threshold": self.voltage_low_threshold,  # 电压过低报警阈值
            "current_alarm": self.current_alarm,  # 电流异常是否报警，0正常,1报警
            "current": self.current,  # 当前电流
            "current_high_threshold": self.current_high_threshold,  # 电流过大报警阈值
            "current_low_threshold": self.current_low_threshold,  # 电流过低报警阈值
            "reserved": {},  # 用于扩展后续其他信息
        }
        if self.voltage_alarm or self.current_alarm or self.temp_alarm:
            print(f"update_status {self.mcu_status}")


class Camera_near_status():
    def __init__(self):
        self.temp_alarm = 0  # 温度异常报警,0正常,1报警,
        self.temp = 30.0  # 当前温度
        self.temp_high_threshold = 60.0  # 高温报警阈值
        self.temp_low_threshold = -20.0  # 低温报警阈值
        self.occlusion_alarm = 0  # 是否遮挡，0正常,1遮挡
        self.deflection_alarm = 0  # 摄像头是否偏转，0正常,1偏转
        self.rtsp_quit_alarm = 0  # 视频流停止报警0正常,1停止
        self.reserved = {}  # 用于扩展后续其他信息
        self.camera_status_dict = {}
        self.update_status()

    def update_status(self):
        self.camera_status_dict = {
            "temp_alarm": self.temp_alarm,  # 温度异常报警,0正常,1报警
            "temp": self.temp,  # 当前温度
            "temp_high_threshold": self.temp_high_threshold,  # 高温报警阈值
            "temp_low_threshold": self.temp_low_threshold,  # 低温报警阈值
            "occlusion_alarm": self.occlusion_alarm,  # 是否遮挡，0正常,1遮挡
            "deflection_alarm": self.deflection_alarm,  # 摄像头是否偏转，0正常,1偏转
            "rtsp_quit_alarm": self.rtsp_quit_alarm,  # 视频流停止报警0正常,1停止
            "reserved": self.reserved,  # 用于扩展后续其他信息
        }
        if self.rtsp_quit_alarm or self.occlusion_alarm or self.deflection_alarm or self.temp_alarm:
            print(f"update_status {self.camera_status_dict}")


class Component_Status:
    time_start = time.time()
    print_time = 10

    def __init__(self):
        self.nano_sta = Nano_status()
        self.radar_sta = Radar_status()
        self.mcu_sta = MCU_status()
        self.camera_near = Camera_near_status()
        self.camera_remote = Camera_near_status()
        self.intelCore = IntelCore_status()
        self.edition_info = None

    def gen_heartbeat_frame(self, main_engine):
        self.intelCore.update_status()
        self.nano_sta.update_status()
        self.radar_sta.update_status()
        self.mcu_sta.update_status()
        self.camera_near.update_status()
        self.camera_remote.update_status()
        now_time=time.time()
        time_spend=time.time()-Component_Status.time_start
        speak_on_off, speak_volume = main_engine.get_speak_config_data()

        if main_engine.radar_driver.decoder.edition_str is not None:
            radar_edition = main_engine.radar_driver.decoder.edition_str
        elif main_engine.radar_driver_udp_cmd is not None and main_engine.radar_driver_udp_cmd.decoder.edition_str is not None:
            radar_edition = main_engine.radar_driver_udp_cmd.decoder.edition_str
        else:
            radar_edition = "null"

        if main_engine.mcu is not None and main_engine.mcu.decoder.edition_str is not None:
            mcu_edition = main_engine.mcu.decoder.edition_str
        else:
            mcu_edition = "null"

        self.edition_info = {
            "sn": main_engine.config_manager.sn,
            "guard": main_engine.xml_handle.guard_version,
            "radar": radar_edition,
            "mcu": mcu_edition
        }
        reserved = {
            "radar_latest_data_time": round(now_time - main_engine.radar_driver.latest_data_stamp, 3),
            "camera_latest_data_time": round(now_time - main_engine.camera_driver.latest_data_stamp, 3),
            "block_alarm": main_engine.block_alarm_edge.lastValue,
            "block_icr": main_engine.block_icr_edge.lastValue,
            "block_alarm_radar_train": main_engine.radar_driver.is_train_by_radar_edge.lastValue,
            "speak_volume": {'status': speak_on_off, 'volume': speak_volume},
            "edition_info": self.edition_info,
            "nano_time": datetime.datetime.now().strftime("%Y%m%d_%H%M%S.%f"),
            "trace_score": main_engine.trace.scores_string,
        }
        if main_engine.mcu is not None:
            reserved["mcu_latest_data_time"] = round(now_time - main_engine.mcu.latest_data_stamp, 3)
        nano_heartbeat_data_json = {
            "radar": self.radar_sta.radar_status,
            'nano': self.nano_sta.nano_status,
            'camera_near': self.camera_near.camera_status_dict,
            'camera_remote': self.camera_remote.camera_status_dict,
            "intelCore": self.intelCore.intelCore_status,
            'reserved':reserved
        }
        if time_spend < Component_Status.print_time:
            print(f"Component_Status intelCore: {self.intelCore.intelCore_status},"
                  f"nano_heartbeat_data_json={nano_heartbeat_data_json}")
        if main_engine.mcu is not None:
            # print(self.mcu_sta.mcu_status)
            # print(f"debug_1009_mcu Component_Status.gen_heartbeat_frame gen_heartbeat_frame")
            nano_heartbeat_data_json['mcu'] = self.mcu_sta.mcu_status

        nano_heartbeat_frame_json = {
            "code": 302,
            "msg": "nano_heartbeat",
            "data": nano_heartbeat_data_json
        }
        # print(f"nano_heartbeat_frame_json={nano_heartbeat_frame_json}")
        return nano_heartbeat_frame_json

    def camera_status_update(self, camerastatus_dict):
        # 根据从推理端接收的遮挡和偏转报警，更新对应模块状态
        # camerastatus_dict={'nearcameraocclude': 1, 'farcameraocclude': 1, 'deflection': 0}    #调试数据
        # print(f"camera_status_update camerastatus_dict={camerastatus_dict}")
        print_dict = 0
        if "nearcameraocclude" in camerastatus_dict:
            self.camera_near.occlusion_alarm = camerastatus_dict["nearcameraocclude"]
            print_dict += int(camerastatus_dict["nearcameraocclude"])
        if "farcameraocclude" in camerastatus_dict:
            self.camera_remote.occlusion_alarm = camerastatus_dict["farcameraocclude"]
            print_dict += int(camerastatus_dict["farcameraocclude"])
        if "deflection" in camerastatus_dict:
            self.camera_near.deflection_alarm = camerastatus_dict["deflection"]
            self.camera_remote.deflection_alarm = camerastatus_dict["deflection"]
            print_dict += float(camerastatus_dict["deflection"])


if __name__ == "__main__":
    heartbeat = Component_Status()
    print(heartbeat.radar_sta.radar_status)
    print(heartbeat.mcu_sta.mcu_status)
    print(heartbeat.nano_sta.nano_status)
    print(heartbeat.camera_near.camera_status_dict)
    print(heartbeat.camera_remote.camera_status_dict)
    print(heartbeat.gen_heartbeat_frame())
