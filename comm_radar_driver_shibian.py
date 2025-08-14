# laser
import datetime
import platform
import serial
import socket
import sys
import threading
import time
import traceback
from abc import abstractmethod

import common_FireTimer
from comm_decoder_radar import Decoder_Radar, Radar_Frame_Code
from common_FireTimer import FireTimer
from common_hysteresis_threshold import EDGE_DETECT

sys.path.append("")


class CommDriver():
    time_start = time.time()
    print_time = 30

    def __init__(self, radar_decoder, get_edition=True):
        self.print_cnt = 0
        self.className="CommDriver"
        self.running=True
        self.latest_target_list = []
        self.latest_data_stamp = time.time()
        self.latest_open_stamp = time.time()
        self.consumer_thread = None
        self.thread = None
        self.comm_isOpen = False
        self.decoder = radar_decoder
        self.get_edition = get_edition
        self.get_edition_firer = common_FireTimer.FireTimer_withCounter_InSpan(-1, -1)
        self.comm_handle=None
        self.radar_address =None
        self.is_train_by_radar_edge = EDGE_DETECT(False)
        self.timeout_for_reconnect = 70
        self.is_print_rx_bytes = False

    def get_radar_mcu_edition(self):
        """
        通过命令获取雷达版本信息
        :return:
        """
        edition = None
        self.comm_open_if_need()
        time.sleep(0.2)
        for index in range(10):
            # 1.读空数据
            for read_index in range(30):
                self.comm_read()
            # 2.发送命令
            time.sleep(0.2)
            edition = self.send_edition_cmd_check_ack()
            if edition is not None:
                break
        return edition

    def send_edition_cmd_check_ack(self):
        """
        发送获取版本信息命令，并接收版本信息，
        :return:
        """
        # print(f"{datetime.datetime.now()},{self.className},send_edition_cmd_check_ack comm_send() ")
        if self.decoder is not None and self.decoder.edition_str is not None:
            print(f"send_edition_cmd_check_ack, edition={self.decoder.edition_str}")
            return self.decoder.edition_str
        frame_get_edition = self.decoder.get_radar_edition_cmd()
        self.comm_send(frame_get_edition, showDataHex=True)
        self.comm_send(frame_get_edition, showDataHex=True)
        self.comm_send(frame_get_edition, showDataHex=True)
        # 3.等待雷达应答，并解码
        # 500*0.01s=5s
        wait_time = 3
        delay_time = 0.01
        for index in range(int(wait_time / delay_time)):
            time.sleep(delay_time)
            self.comm_read_to_buffer()
            frameIndex, frameTailIndex, frameData = self.decoder.check_headtail_crc()
            if frameData is not None:
                print(f"{datetime.datetime.now()},send_edition_cmd_check_ack RxFrame={self.decoder.format_bytes_to_str(frameData)}")
                decode_result = self.decoder.decode(frameData)
                if decode_result is not None and decode_result.code == Radar_Frame_Code.radar_edition:
                    self.decoder.edition_str =decode_result.value
                    print(f"send_edition_cmd_check_ack, edition={self.decoder.edition_str}")
                    break
            if self.decoder.edition_str is not None:
                print(f"send_edition_cmd_check_ack, edition={self.decoder.edition_str}")
                return self.decoder.edition_str
        return self.decoder.edition_str

    def set_radar_defence_area(self, area_point_list=[(-5, 0), (-5, 250), (5, 250), (5, 0)]):
        self.is_print_rx_bytes = True
        frame_radar_defence_area = self.decoder.set_defence_area(area_point_list)
        # 如果是非法的防区数据，则使用默认防区数据
        if len(frame_radar_defence_area)<30:
            print(f"set_radar_defence_area error area_point_list={area_point_list}")
            frame_radar_defence_area = self.decoder.set_defence_area([(-5, 0), (-5, 250), (5, 250), (5, 0)])
        for index in range(2):
            self.comm_send(frame_radar_defence_area, showDataHex=True)
            time.sleep(0.1)
            frame_get_defence_area_bytes = self.decoder.get_radar_obj_area()
            self.comm_send(frame_get_defence_area_bytes, showDataHex=True)
            time.sleep(0.1)
        # self.is_print_rx_bytes = False

    def listen_radar_objArea_update_callback(self, radar_objArea_update_callback):
        self.decoder.radar_obj_area_save_callback = radar_objArea_update_callback
        print(f"{datetime.datetime.now()} CommDriver listen_radar_objArea_update_callback set_callback and comm_send")
        self.comm_send(self.decoder.get_radar_obj_area(), True)
        self.comm_send(self.decoder.get_radar_obj_area(), True)
        self.comm_send(self.decoder.get_radar_obj_area(), True)
        time.sleep(0.6)
        print(f"{datetime.datetime.now()} CommDriver listen_radar_objArea_update_callback obj_area={self.decoder.obj_area}")
        self.comm_send(self.decoder.get_radar_alarm_area_all(), True)
        self.comm_send(self.decoder.get_radar_alarm_area_all(), True)
        self.comm_send(self.decoder.get_radar_alarm_area_all(), True)
        time.sleep(0.6)
        print(f"{datetime.datetime.now()} CommDriver listen_radar_objArea_update_callback alarm_area_all={self.decoder.alarm_area_all}")

    def comm_open_if_need(self, timeout_for_reconnect=70):
        """
        在需要的时候打开通信端口
        :param timeout_for_reconnect:没有数据，重开端口的超时时间，单位为s
        :param timeout_for_reopen:没有数据，重开端口的超时时间，单位为s
        :return:
        """
        #是否需要关闭
        timeout_from_last_data = (time.time() - self.latest_data_stamp) > self.timeout_for_reconnect
        if (self.comm_handle is not None and self.comm_isOpen) and timeout_from_last_data:
            print(f"{datetime.datetime.now()},CommDriver comm_open_if_need, timeout_from_last_data={self.timeout_for_reconnect}")
            self.comm_close()
            self.comm_handle=None
            self.latest_data_stamp=time.time()
        if self.comm_handle is None:
            self.comm_open()
            # print(f"{self.className},comm_open_if_need,")
            time.sleep(0.005)
            if self.decoder is not None:
                self.comm_send(self.decoder.get_radar_edition_cmd(), showDataHex=True)

    @abstractmethod
    def comm_open(self):
        pass

    @abstractmethod
    def comm_send(self, data_bytes, showDataHex=False):
        pass

    @abstractmethod
    def comm_close(self):
        pass

    def comm_read_to_buffer(self):
        if isinstance(self.comm_handle, socket.socket):
            if self.comm_isOpen and self.comm_handle is not None:
                try:
                    data, ip_port = self.comm_handle.recvfrom(4096)
                    # print(f"{datetime.datetime.now()} comm_read_to_buffer {data.hex().upper()}")
                    self.decoder.append_data_to_buffer(data)
                except socket.timeout:
                    pass
                except:
                    pass
        elif isinstance(self.comm_handle, serial.Serial):
            # print(f"{self.comm_handle }  comm_isOpen={self.comm_isOpen}  inWaiting={self.comm_handle.inWaiting()}")
            if self.comm_handle is not None and self.comm_isOpen and self.comm_handle.inWaiting() > 0:
                try:
                    data_bytes = self.comm_handle.read_all()
                    self.decoder.append_data_to_buffer(data_bytes)
                except:
                    # print(f"{datetime.datetime.now()} comm_read_to_buffer {traceback.format_exc()}")
                    pass

    @abstractmethod
    def comm_read(self):
        pass

    def _run_receive(self):
        """
        通信线程任务函数，包含端口打开和重打开，读取数据，解码数据等
        :return:
        """
        timer_for_radar_objs=time.time()
        print(f"{datetime.datetime.now()} CommDriver _run_receive start")
        while self.running:
            try:
                self.comm_open_if_need()
                if not self.comm_transfer_data():
                    self.comm_read_to_buffer()
                    if len(self.decoder.dataBuffer_bytes) >= 8:
                        frameIndex, frameTailIndex, frameData = self.decoder.check_headtail_crc()
                        if frameTailIndex < 0:
                            time.sleep(0.05)
                        # 解码一帧
                        if frameData is not None:
                            self.latest_data_stamp = time.time()
                            result = self.decoder.decode(frameData)
                            # print(f"result={result}")

                            # 仅供收发调试，打印数据帧
                            if self.print_cnt <= 20:
                                print(f"{datetime.datetime.now()},{self.comm_handle} _run_receive {self.print_cnt}/20 {frameData.hex()}")
                                self.print_cnt+=1

                            # 如果还没有读到版本号，则持续发送读版本号的命令
                            if self.get_edition and self.decoder.edition_str is None and self.get_edition_firer.isFireTime(4):
                                frame_get_edition = self.decoder.get_radar_edition_cmd()
                                self.comm_send(frame_get_edition, showDataHex=True)
                                self.comm_send(frame_get_edition, showDataHex=True)
                                self.comm_send(frame_get_edition, showDataHex=True)

                        # 确保发送虚拟目标
                        # if time.time() - timer_for_radar_objs > 0.4 and self.decoder.radar_data_handler is not None:
                        #     self.decoder.radar_data_handler([])
                        #     timer_for_radar_objs = time.time()

            except :
                print(datetime.datetime.now(), "CommDriver", "".join([f"{byte:02X}" for byte in self.decoder.dataBuffer_bytes]))
                print(f"{datetime.datetime.now()},_run_receive, error={traceback.format_exc()}")
        print(f"{datetime.datetime.now()} CommDriver _run_receive exit")

    @abstractmethod
    def comm_transfer_data(self, ):
        pass

    def start(self, daemon=True,name=''):
        """
        开始通信主线程
        :param daemon:是否为守护进程。
        :return:
        """
        self.running=True
        if self.thread is None:
            # 运行数据接收线程
            self.thread = threading.Thread(target=self._run_receive, daemon=daemon,name=name)
            self.thread.start()

    def exit(self):
        self.running=False
        time.sleep(1)
        if self.thread is not None:
            self.thread.join()
        self.thread=None
        print(f"{datetime.datetime.now()},{self.className},exit")


class RadarDriver_COM(CommDriver):
    def __init__(self, portName="/dev/ttyTHS2", password="king", radar_decoder=None, get_edition=True):
        super().__init__(radar_decoder, get_edition=get_edition)
        self.className="RadarDriver_COM"
        self.comm_handle: serial.Serial = None
        self.portName = portName
        self.timeout_s = 1
        self.frame_count = 0
        self.password=password
        self.transfer_handle = TRANSFER_SERIAL_UDP(('127.0.0.1', 18203))
        self.comm_open_error_callback = None

    def comm_open(self):
        """
        打开串口
        :return:
        """
        try:
            self.comm_handle = serial.Serial(
                port=self.portName,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout_s,
            )
            time.sleep(1)
            # 判断是否打开成功
            if self.comm_handle is not None and self.comm_handle.is_open:
                self.comm_isOpen = True
                print(datetime.datetime.now(), f"RadarDriver_COM comm_open {self.portName},get_edition={self.get_edition}")
                self.latest_open_stamp = time.time()

        except Exception as e:
            print(datetime.datetime.now(), f"RadarDriver_COM comm_open error {self.portName}",  e)
            if self.comm_open_error_callback is not None:
                time.sleep(1)
                print(datetime.datetime.now(), f"RadarDriver_COM comm_open_error_callback {self.portName}")
                self.comm_open_error_callback(self.portName)
            self.comm_isOpen = False
            time.sleep(1)

    def listen_comm_open_error_callback(self, callback):
        print(f"{datetime.datetime.now()},listen_comm_open_error_callback, {callback}")
        self.comm_open_error_callback = callback

    def comm_send(self, data_bytes, showDataHex=False):
        """
        发送串口数据
        :param data_bytes:需要发送的16进制byte数据
        :param showDataHex:是否打印16进制数据信息
        :return:
        """
        if self.comm_handle is not None:
            self.comm_handle.write(data_bytes)
            if showDataHex:
                data_bytes_str="".join([f"{x:02X}" for x in data_bytes])
                print(f"{datetime.datetime.now()},RadarDriver_COM comm_send,{self.portName} ={data_bytes_str}")

    def comm_read(self):
        """
        有数据读就读数据
        :return:
        """
        try:
            if self.comm_handle is not None and self.comm_isOpen and self.comm_handle.in_waiting>0:
                data_bytes = self.comm_handle.read_all()
                return data_bytes
            else:
                return b''
        except Exception as e:
            print(f"RadarDriver_COM,comm_read error,{e}")
            time.sleep(0.5)
            # self.comm_close()
            return b''

    def comm_close(self):
        """
        关闭通信端口
        :return:
        """
        if self.comm_isOpen:
            self.comm_handle.close()
        self.comm_isOpen = False
        self.comm_handle = None
        print(datetime.datetime.now(), f"RadarDriver_COM comm_close port={self.portName}")

    def comm_transfer_data(self, ):
        self.transfer_handle.transfer_serial_udp(self.comm_handle)
        if self.transfer_handle.is_transfer_mode:
            # 更新数据时间戳，避免未收到雷达数据重启雷达
            self.latest_data_stamp = time.time()
        return self.transfer_handle.is_transfer_mode


class RadarDriver_UDP(CommDriver):
    def __init__(self, radar_decoder, local_port=17000, get_edition=True, ):
        super().__init__(radar_decoder, get_edition=get_edition)
        self.className="RadarDriver_UDP"
        self.local_port = local_port
        self.timeout_s = 0.025
        self.frame_count = 0
        self.local_ip=None
        self.radar_address = ("192.168.8.100", 20000) if self.decoder.frame_bytes.head == b'\xAA\xAA\x55\x55' else ("192.168.8.100", 15555)
        self.transfer_handle = TRANSFER_UDP_UDP(remoteUDP1=self.radar_address,
                                                remoteUDP2=('10.8.4.129', 19253),
                                                udp2radar_data_local_Address=('', local_port),
                                                udp2radar_cmd_local_Address=('', 15000),
                                                udp_local2_address=('', 18202),
                                                )

    def comm_open(self, ):
        try:
            self.comm_handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.comm_handle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.comm_handle.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.comm_handle.bind(('', self.local_port))
            self.comm_handle.settimeout(self.timeout_s)
            print(datetime.datetime.now(), f"{self.className} open udp_socket bind_port={self.local_port},get_edition={self.get_edition}")
            self.comm_isOpen = True
            self.latest_open_stamp = time.time()

        except Exception as e:
            print(datetime.datetime.now(), f"{self.className} udp_open error {self.local_port} ", __file__, e)
            # self.comm_isOpen = False
            self.comm_close()

    def comm_send(self, data_bytes, showDataHex=False):
        if self.comm_isOpen:
            self.comm_handle.sendto(data_bytes, self.radar_address)
            # print("xyp雷达解码发送", ''.join(['%02X' % b for b in data_bytes]),data_bytes )  # xyp雷达解码接收
            if showDataHex:
                data_bytes_str="".join([f"{x:02X}" for x in data_bytes])
                print(f"{datetime.datetime.now()},{self.className},comm_send{self.local_port}>>{self.radar_address}={data_bytes_str}")
        else:
            print(f"{self.className},comm_send,comm_handle is not open error!")

    def comm_close(self):
        if self.comm_handle is not None:
            self.comm_handle.close()
        print(datetime.datetime.now(), f"{self.className} comm_close local_port={self.local_port}")
        self.comm_handle = None
        self.comm_isOpen = False

    def comm_read(self):
        if self.comm_isOpen:
            try:
                recv = self.comm_handle.recvfrom(4096)
                data, ip_port = recv
                if self.is_print_rx_bytes and data is not None:
                    data_str="".join(['%02X' % b for b in data])
                    print(f"{self.className},{self.local_port},rx={data_str}")
                return data
            except:
                return b''

    def comm_transfer_data(self, ):
        self.transfer_handle.transfer_udp_udp()
        if self.transfer_handle.is_transfer_mode:
            # 更新数据时间戳，避免未收到雷达数据重启雷达
            self.latest_data_stamp = time.time()
        return self.transfer_handle.is_transfer_mode


class TRANSFER_SERIAL_UDP:
    def __init__(self, remoteUDP, udp_local_address=("127.0.0.1", 18202)):
        self.class_name = "TRANSFER_SERIAL_UDP"
        self.remoteUDP = remoteUDP
        self.is_socket_open=False
        self.udp_socket=None
        self.udp_local_address=udp_local_address
        self.is_transfer_mode = False
        self.transfer_mode_print_fire_timer = FireTimer()

    def transfer_serial_udp(self, serial_handler,):
        if not self.is_transfer_mode:
            return
        if self.transfer_mode_print_fire_timer.isFireTime(10):
            print(f"{datetime.datetime.now()},transfer_serial_udp transfer_mode,")
        try:
            if not self.is_socket_open or self.udp_socket is None:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.bind(self.udp_local_address)  # 为服务器绑定一个固定的地址，ip和端口
                self.udp_socket.settimeout(0.01)
                self.is_socket_open=True
        except Exception as e:
            print(f"{self.class_name},transfer_udp_udp error={e}", )
            self.is_socket_open=False
        self.transfer_serial_udp_read_send(serial_handler, self.udp_socket, self.remoteUDP)
        self.transfer_serial_udp_read_send(self.udp_socket, serial_handler, self.remoteUDP)

    def transfer_serial_udp_read_send(self, handler_for_read, handler_for_send, remote):
        try:
            if isinstance(handler_for_read, serial.Serial):
                # serial>>>UDP
                if handler_for_read.in_waiting > 0:
                    data_bytes_from_serial = handler_for_read.read_all()
                    if len(data_bytes_from_serial) > 0:
                        print(datetime.datetime.now(),
                              f"{self.class_name},{handler_for_read.port}>>>{self.udp_local_address}>>>UDP{remote}",
                              "".join(['%02X' % b for b in data_bytes_from_serial])
                              )
                        handler_for_send.sendto(data_bytes_from_serial, remote)
            elif isinstance(handler_for_read, socket.socket):
                # UDP>>>serial
                data_bytes_from_udp, ip = handler_for_read.recvfrom(1024 * 10)
                if len(data_bytes_from_udp) > 0:
                    print(datetime.datetime.now(),
                          f"{self.class_name},UDP{ip}>>>{self.udp_local_address}>>>{handler_for_send.port}",
                          "".join(['%02X' % b for b in data_bytes_from_udp])
                          )
                    handler_for_send.write(data_bytes_from_udp)
        except socket.timeout as e:
            time.sleep(0.001)
            pass
        except Exception as e:
            traceback.print_exc()
            print(f"{self.class_name},transfer_serial_udp_read_send error={e}", )

    def set_transfer_mode(self, transfer_config):
        # transfer_config = {
        #     "transfer_enable": is_transfer_mode,
        #     "transfer_ip": local_ip,
        #     "transfer_port": 18888,
        # }
        print(f"{datetime.datetime.now()},set_transfer_mode, is_transfer_mode={transfer_config}")
        self.is_transfer_mode=True if transfer_config["transfer_enable"] else False
        self.remoteUDP = (transfer_config["transfer_ip"], transfer_config["transfer_port"])
        return {"transfer_config": transfer_config}


class TRANSFER_UDP_UDP:
    def __init__(self, remoteUDP1=('192.168.8.100', 20000), remoteUDP2=('10.8.4.129', 18253),
                 udp2radar_data_local_Address=("", 17000), udp2radar_cmd_local_Address=("", 15000),
                 udp_local2_address=("", 18202)):
        self.class_name = "TRANSFER_UDP_UDP"
        self.is_transfer_mode = False
        self.transfer_mode_print_fire_timer = FireTimer()
        self.remoteUDP1_radar = remoteUDP1
        self.remoteUDP2_host = remoteUDP2
        self.is_socket_open = False
        self.udp2radar_data = None
        self.udp2radar_cmd = None
        self.udp2host = None
        self.udp2radar_data_local_Address = udp2radar_data_local_Address
        self.udp2radar_cmd_local_Address = udp2radar_cmd_local_Address
        self.udp2host_local_address = udp_local2_address
        print(f"{datetime.datetime.now()},TRANSFER_UDP_UDP init, "
              f"radar:{self.remoteUDP1_radar}>>>nano:{self.udp2radar_data_local_Address}&{self.udp2radar_cmd_local_Address}"
              f"   nano:{self.udp2host_local_address}>>>Host:{self.remoteUDP2_host}")

    def transfer_udp_udp(self, ):
        if not self.is_transfer_mode:
            return
        if self.transfer_mode_print_fire_timer.isFireTime(10):
            print(f"{datetime.datetime.now()},transfer_udp_udp transfer_mode,")
        try:
            if not self.is_socket_open or self.udp2radar_data is None or self.udp2radar_cmd is None or self.udp2host is None:
                if self.udp2radar_data is None:
                    self.udp2radar_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.udp2radar_data.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # SO_REUSEADDR是让端口释放后立即就可以被再次使用。
                    self.udp2radar_data.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)   # SO_BROADCAST 允许发送广播数据
                    self.udp2radar_data.bind(self.udp2radar_data_local_Address)  # 为服务器绑定一个固定的地址，ip和端口
                    self.udp2radar_data.settimeout(0.01)
                if self.udp2radar_cmd is None:
                    self.udp2radar_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.udp2radar_cmd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # SO_REUSEADDR是让端口释放后立即就可以被再次使用。
                    self.udp2radar_cmd.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)   # SO_BROADCAST 允许发送广播数据
                    self.udp2radar_cmd.bind(self.udp2radar_cmd_local_Address)  # 为服务器绑定一个固定的地址，ip和端口
                    self.udp2radar_cmd.settimeout(0.01)
                if self.udp2host is None:
                    self.udp2host = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.udp2host.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # SO_REUSEADDR是让端口释放后立即就可以被再次使用。
                    self.udp2host.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # SO_BROADCAST 允许发送广播数据
                    self.udp2host.bind(self.udp2host_local_address)  # 为服务器绑定一个固定的地址，ip和端口
                    self.udp2host.settimeout(0.01)
                self.is_socket_open=True
        except Exception as e:
            print(f"{self.class_name},transfer_udp_udp error={e}", )
            self.is_socket_open=False
        self.transfer_udp_udp_read_send(self.udp2radar_data, self.udp2host, self.remoteUDP2_host)
        self.transfer_udp_udp_read_send(self.udp2radar_cmd, self.udp2host, self.remoteUDP2_host)
        self.transfer_udp_udp_read_send(self.udp2host, self.udp2radar_cmd, self.remoteUDP1_radar)

    def transfer_udp_udp_read_send(self, udp_for_read, udp_for_send, remoteUDP):
        try:
            # udp_for_read>>>udp_for_send
            data_bytes_from_udp1, ip = udp_for_read.recvfrom(1024 * 10)
            if len(data_bytes_from_udp1) > 0:
                print(datetime.datetime.now(), f"{self.class_name},UDP{ip}>>>udp{remoteUDP}","".join(['%02X' % b for b in data_bytes_from_udp1]))
                udp_for_send.sendto(data_bytes_from_udp1, remoteUDP)
        except socket.timeout as e:
            time.sleep(0.001)
            pass
        except Exception as e:
            print(f"{udp_for_read, udp_for_send, remoteUDP}")
            traceback.print_exc()
            print(f"{self.class_name},transfer_udp_udp_read_send error={e}", )

    def set_transfer_mode(self, transfer_config):
        # transfer_config = {
        #     "transfer_enable": is_transfer_mode,
        #     "transfer_ip": local_ip,
        #     "transfer_port": 18888,
        # }
        print(f"{datetime.datetime.now()},set_transfer_mode, is_transfer_mode={transfer_config}")
        self.is_transfer_mode = True if transfer_config["transfer_enable"] else False
        self.remoteUDP2_host = (transfer_config["transfer_ip"], transfer_config["transfer_port"])
        return {"transfer_config": transfer_config}


def TRANSFER_SERIAL_UDP_test():
    my_transfer=TRANSFER_SERIAL_UDP(('127.0.0.1', 18203))
    # 串口
    ser = serial.Serial("COM2", 9600, timeout=0.05)
    ser.read_all()
    print(datetime.datetime.now(), f"transfer_test")
    my_transfer.is_transfer_mode=True
    for i in range(10000):
        my_transfer.transfer_serial_udp(ser,)


def TRANSFER_UDP_UDP_test():
    if "Windows" in platform.platform():
        my_transfer = TRANSFER_UDP_UDP(('127.0.0.1', 18200), ('127.0.0.1', 18203))
        print(datetime.datetime.now(), f"transfer_test")
        my_transfer.is_transfer_mode = True
        for i in range(10000):
            my_transfer.transfer_udp_udp()
    else:
        my_transfer = TRANSFER_UDP_UDP(('192.168.8.100', 20000), ('10.8.4.129', 18253),
                                       udp2radar_data_local_Address=('', 17000),
                                       udp2radar_cmd_local_Address=('', 15000),
                                       udp_local2_address=('', 18202),
                                       )
        print(datetime.datetime.now(), f"transfer_test")
        my_transfer.is_transfer_mode = True
        for i in range(10000):
            my_transfer.transfer_udp_udp()


def print_for_test(targetList):
    if isinstance(targetList, bytes):
        data_bytes_str = "".join([f"{x:02X}" for x in targetList])
        print(datetime.datetime.now(),"print_for_test", data_bytes_str)
    else:
        print(datetime.datetime.now(), "print_for_test", targetList)


def RadarDriver_COM_test(COM="COM2"):
    decoder = Decoder_Radar(head_type="A66A")
    driver = RadarDriver_COM(COM, radar_decoder=decoder)
    # print(f"RadarDriver_COM_test,COM={COM}")
    driver.decoder.listen_radar_data_handler(print_for_test)
    driver.start(False)
    time.sleep(1.5)
    frame = driver.decoder.get_radar_edition_cmd()
    driver.comm_send(frame, True)
    driver.comm_send(frame, True)
    driver.comm_send(frame, True)
    time.sleep(30)
    print(f"edition_str={driver.decoder.edition_str}")
    driver.exit()
    # print("RadarDriver_COM_test exit")


def RadarDriver_UDP_test(local_port=17000):
    decoder=Decoder_Radar()
    driver = RadarDriver_UDP(decoder, local_port=local_port)
    # print(f"RadarDriver_UDP_test,local_port={local_port}")
    driver.decoder.listen_radar_data_handler(print_for_test)
    driver.is_print_rx_bytes = True
    driver.start(False)
    time.sleep(2)
    # 读版本号
    driver.comm_send(driver.decoder.get_radar_edition_cmd(), True)
    time.sleep(1)
    # 读虚警列表 AA AA 55 55 02 A2 00 00 00 04 00 00 00 00 C1 6A 55 55 AA AA
    driver.comm_send(driver.decoder.get_radar_false_alarm_cmd(), True)
    time.sleep(1)
    time.sleep(20)
    print(f"edition_str={driver.decoder.edition_str}")
    driver.exit()
    print("RadarDriver_UDP_test exit")


def udp_test(local_port=17000, head_type="AAAA5555", time_test=30):
    decoder=Decoder_Radar(head_type)
    udp_handler = RadarDriver_UDP(decoder, local_port)
    udp_handler.start("x16")
    udp_handler.is_print_rx_bytes = True
    udp_handler.comm_open()
    time_start = time.time()
    time_send = time.time()
    while time.time() - time_start < time_test:
        # udp_handler.comm_read()
        time.sleep(0.01)
        if time.time()-time_send>2:
            udp_handler.comm_send(udp_handler.decoder.get_radar_edition_cmd(), True)
            udp_handler.comm_send(udp_handler.decoder.get_radar_edition_cmd(), True)
            udp_handler.comm_send(udp_handler.decoder.get_radar_edition_cmd(), True)
            time.sleep(1)
            udp_handler.comm_send(udp_handler.decoder.get_radar_alarm_area_all(), True)
            udp_handler.comm_send(udp_handler.decoder.get_radar_alarm_area_all(), True)
            udp_handler.comm_send(udp_handler.decoder.get_radar_alarm_area_all(), True)
            time.sleep(1)
    udp_handler.running = False
    print(f"local_port={local_port},edition_str={udp_handler.decoder.edition_str}")
    udp_handler.comm_close()
    time.sleep(3)


if __name__ == '__main__':
    # 毫米波雷达和彩色相机的数据融合
    # camera_radar_fusion_test()

    # 雷达UDP驱动测试
    if "Window" in platform.platform():
        # RadarDriver_COM_test("COM1")
        # RadarDriver_COM_test("COM2")
        udp_test(local_port=15555, time_test=10)
        udp_test(local_port=17000, time_test=10)
    elif "debian" in platform.platform().lower() or "armv7l" in platform.platform().lower():
        RadarDriver_COM_test("/dev/ttyS0")
        RadarDriver_COM_test("/dev/ttyS1")
    else:
        # RadarDriver_COM_test("/dev/ttyTHS1")
        # RadarDriver_COM_test("/dev/ttyTHS2")
        # 雷达UDP驱动测试
        time.sleep(3)
        # udp读数据测试
        udp_test(local_port=15555, head_type="A66A", time_test=10)
        udp_test(local_port=17000, head_type="A66A", time_test=10)
        udp_test(local_port=15000, head_type="A66A", time_test=10)
        udp_test(local_port=15555, time_test=10)
        udp_test(local_port=17000, time_test=10)
        udp_test(local_port=15000, time_test=10)


    # 数据转发测试
    # TRANSFER_SERIAL_UDP_test()
    # TRANSFER_UDP_UDP_test()