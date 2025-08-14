import argparse
import datetime
import os
import platform
import sys
import time

from DebugUDPSender import DebugUDPSender
from comm_crc16 import crc16_Modbus
from comm_decoder_radar import Decoder_Radar
from comm_radar_driver_shibian import RadarDriver_COM, RadarDriver_UDP


class RadarUpgrade():
    def __init__(self, comm, decoder):
        # self.head = b'\xAA\xAA\x55\x55'
        self.head = decoder.frame_bytes.head
        self.head_str = decoder.frame_bytes.head.hex().upper()
        # self.tail = b'\x55\x55\xAA\xAA'
        self.tail = decoder.frame_bytes.tail
        print(f"RadarUpgrade init head={self.head.hex()},tail={self.tail.hex()}")
        self.comm=comm
        self.fileLength_byte=1
        self.myprint=None
        self.crc16_modbus=crc16_Modbus()

    def Get_FilePath_FileName_FileExt(self, filename):
        filepath, tempfilename = os.path.split(filename)
        shotname, extension = os.path.splitext(tempfilename)
        return filepath, shotname, extension

    def readout_data(self):
        time_start = time.time()
        # for time.time() - time_start <= 2:
        try:
            bytes_received = self.comm.comm_read()
        except:
            pass

    def checkACK(self, ack_index, timeout_s=10):
        if "AAAA5555" in self.head_str:
            frame_id_length = b'\x00\xF1\x00\x00\x00\x04'
        else:
            frame_id_length = b'\x00\xF1\x00\x04'
        bytes_ackIndex = int(ack_index).to_bytes(length=4, byteorder='big', signed=False)
        bytes_crc16 = self.crc16_modbus.crc16(frame_id_length + bytes_ackIndex)
        # bytes_F1_1_ACK_MSG = self.head + frame_id_length + bytes_ackIndex + bytes_crc16 + self.tail
        bytes_F1_1_ACK_MSG = self.head + frame_id_length + bytes_ackIndex
        # print("wait for ",''.join('{:02X}'.format(x) for x in bytes_F1_1_ACK_MSG))
        time_start = time.time()
        data_buffer = b''
        equal = False
        while time.time() - time_start <= timeout_s:
            try:
                bytes_received = self.comm.comm_read()
                if len(bytes_received)>0:
                    bytes_received_hexString = ''.join('{:02X}'.format(x) for x in bytes_received)
                    print(datetime.datetime.now(), "Recv Bytes=" + bytes_received_hexString, ) #20230726 临时调试改动，全部打印
                data_buffer = data_buffer + bytes_received
                if bytes_F1_1_ACK_MSG in data_buffer :
                    print(datetime.datetime.now(), "ACK Bytes=" + bytes_received_hexString, flush=True)
                    return True
            except:
                time.sleep(0.002)
                continue
            time.sleep(0.002)
        if not equal:
            print("\t F1_1:ACK_MSG error")
            time.sleep(1)
            # self.comm.comm_close()
            # sys.exit(0)
        return equal

    def generateF0Frame(self, filePath):
        file_stream = open(filePath, 'rb')
        byte_cnt = 0
        while True:
            data = file_stream.read(10240)
            byte_cnt += len(data)
            if str(data) == "b''":
                break
        print(f"bin file size={byte_cnt/1000} k bytes")
        self.fileLength_byte=byte_cnt
        file_stream.close()
        data_length = int(byte_cnt).to_bytes(length=4, byteorder='big', signed=False)
        if "AAAA5555" in self.head_str:
            frame_id_length = b'\x00\xF0\x00\x00\x00\x04'
            frame_crc16 = self.crc16_modbus.crc16(frame_id_length + data_length)
        else:
            frame_id_length = b'\x00\xF0\x00\x04'
            frame_crc16 = self.crc16_modbus.crc16(self.head + frame_id_length + data_length)

        frame_F0 = self.head + frame_id_length + data_length + frame_crc16 + self.tail
        return frame_F0

    def generateF2DataFrame(self, data):
        frameId = b'\x00\xF2'
        length = len(data)
        if "AAAA5555" in self.head_str:
            frameLength = int(length).to_bytes(length=4, byteorder='big', signed=False)
            frameCRC = self.crc16_modbus.crc16(frameId + frameLength + data)
        else:
            frameLength = int(length).to_bytes(length=2, byteorder='big', signed=False)
            frameCRC = self.crc16_modbus.crc16(self.head + frameId + frameLength + data)
        return self.head + frameId + frameLength + data + frameCRC + self.tail

    def generateF3Frame(self, ):
        frameId = b'\x00\xF3'
        if "AAAA5555" in self.head_str:
            frameLength = b'\x00\x00\x00\x04'
            frameData = b'\x00\x00\x00\x00'
            frameCRC = self.crc16_modbus.crc16(frameId + frameLength + frameData)
        else:
            frameLength = b'\x00\x04'
            frameData = b'\x00\x00\x00\x00'
            frameCRC = self.crc16_modbus.crc16(self.head + frameId + frameLength + frameData)
        return self.head + frameId + frameLength + frameData + frameCRC + self.tail

    def generateGetEdition(self):
        frameId = b'\x00\xFF'
        frameLength = b'\x00\x00\x00\x04'
        frameData = b'\x00\x00\x00\x00'
        frameCRC = self.crc16_modbus.crc16(frameId + frameLength + frameData)
        return self.head + frameId + frameLength + frameData + frameCRC + self.tail

    def send_frame_and_checkACK(self, frame_data, ackCnt=1, ack_timeout_s=10, retryNumber=3,ackNumber=1):
        self.readout_data()
        if "AAAA5555" in self.head_str:
            frameType = frame_data[4:6]
        else:
            frameType = frame_data[2:4]
        frameType_string = "".join(['{:02X}'.format(x) for x in frameType])
        frame_data_str = "".join(['{:02X}'.format(x) for x in frame_data])
        for tryCnt in range(retryNumber):
            if ackCnt % 5 == 0 or True:
                print(datetime.datetime.now(), f"send {frameType_string}, process={ackCnt}/{ackNumber:.1f},length={len(frame_data)}bytes,",end=" ", flush=True)
            # print(f"frame_data_str={frame_data_str}")
            if self.myprint is not None:
                if "00F2" in frameType_string:
                    self.myprint(f" send {frameType_string},process={ackCnt}/{ackNumber:.1f}.")
                else:
                    self.myprint(f" send {frameType_string},process={ackCnt}/{ackNumber:.1f},{frame_data_str}")
            self.comm.comm_send(frame_data)
            if self.checkACK(ackCnt, ack_timeout_s):
                return True

        return False

    def send_file_frame_check_ack(self, filePath):
        count = 0
        ackCnt = 1
        file_stream = open(filePath, 'rb')
        if "AAAA5555" in self.head_str:
            data_length_byte = 128
        else:
            data_length_byte = 66
        ackNumber = self.fileLength_byte / data_length_byte
        while True:
            # for i in range(3):
            data = file_stream.read(data_length_byte)
            if str(data) != "b''":
                count += len(data)
                data_frame = self.generateF2DataFrame(data)
                if ackCnt<=5:
                    print(f"send_file_frame_check_ack ackCnt={ackCnt} data={data_frame.hex().upper()}")
                if not self.send_frame_and_checkACK(data_frame, ackCnt, ackNumber=ackNumber, retryNumber=3):
                    return False
                ackCnt += 1
            else:
                break
            time.sleep(0.04)
        file_stream.close()
        return True


    def upgrade_file(self,filePath,user_confirm_path=True):

        # 用户确认文件路径
        print("bin filepath for upgrade:" + filePath)
        if user_confirm_path:
            confirm = input('filepath correct?(y/n):')
            if confirm in "nN":
                print("program will exit")
                time.sleep(8)
                return False
            elif confirm in "yY":
                pass
            else:
                print("program exit")
                return False


        # 确认filePath存在，否则提示并退出程序
        if not os.path.exists(filePath):
            print(f"can‘t find {filePath}:")
            print("program will exit")
            time.sleep(8)
            return False

        # 发送开始命令F0
        start = time.time()
        bytes_F0_upgradeCmd = self.generateF0Frame(filePath)
        print(f"bytes_F0_upgradeCmd={bytes_F0_upgradeCmd.hex()}")
        if not self.send_frame_and_checkACK(bytes_F0_upgradeCmd, 1, retryNumber=6):
            return False
        time.sleep(0.1)
        # 发送数据文件中的数据
        if not self.send_file_frame_check_ack(filePath):
            return False
        time.sleep(0.1)
        # 发送F3帧
        print()
        F3Frame = self.generateF3Frame()
        if not self.send_frame_and_checkACK(F3Frame, 1, retryNumber=3):
            return False
        end = time.time()
        print(f'\rupgrade time={round(end - start, 2)}s')
        if self.myprint is not None:
            self.myprint(f'\rupgrade time={round(end - start, 2)}s')
        return True


class RadarUpgrade_Radar_MCU():
    # 封装给web的，radar 和Mcu 升级类
    def __init__(self, com_port_name="/dev/ttyTHS1",
                 filePath=r"/usr/bin/zipx/upgradeTest/RT_Thread1_NoHelloWorld(2).bin",
                 head_type="AAAA5555"):
        self.class_name="RadarUpgrade_Radar_MCU"
        self.com_port_name = com_port_name
        self.filePath = filePath
        # if "armv7l" in platform.platform():
        #     # RV1126平台
        #     self.decoder = Decoder_Radar(head_type="A66A")
        # else:
        #     # nano 平台
        self.decoder = Decoder_Radar(head_type=head_type)

    def upgrade_com(self):
        if isinstance(self.com_port_name, str):
            comm = RadarDriver_COM(self.com_port_name, radar_decoder=self.decoder)
            comm.comm_open()
            print(f"{datetime.datetime.now()},{self.class_name},com_port_name={self.com_port_name}")
            radar_upgrade = RadarUpgrade(comm, self.decoder)
        elif isinstance(self.com_port_name, int):
            comm = RadarDriver_UDP(radar_decoder=self.decoder, local_port=self.com_port_name)
            comm.comm_open()
            # 获得并打印本地ip
            comm.comm_handle.connect(comm.radar_address)
            ip = comm.comm_handle.getsockname()[0]

            print(f"{datetime.datetime.now()},{self.class_name},ip={ip},port_name={self.com_port_name}")
            radar_upgrade = RadarUpgrade(comm,self.decoder)

        # 用于了解升级进度的udp工具
        self.debug_udp_sender = DebugUDPSender(remote_ip="255.255.255.255")
        radar_upgrade.myprint = self.debug_udp_sender.udp_send

        # start upgrade
        comm.get_radar_mcu_edition()
        result=radar_upgrade.upgrade_file(self.filePath, user_confirm_path=False)
        radar_upgrade.comm.comm_close()

        return result


def upgrade_by_paras():
    global filePath
    parser = argparse.ArgumentParser(description="雷达UDP或者COM连接")
    parser.add_argument('-r', '--radar_ip', type=str, default="192.168.1.204", help="设置雷达ip")
    parser.add_argument('-p', '--radar_port', type=int, default=20000, help="设置雷达端口")
    parser.add_argument('-i', '--local_ip', type=str, default="192.168.1.198", help="设置本地ip，例如192.168.1.200或者COM1等")
    parser.add_argument('-t', '--local_port', type=int, default=15000, help="设置本地端口")
    parser.add_argument('-f', '--filePath', type=str,
                        default="D:\\project\\traffic_monitoring_18xx_SerialOut2.2.2.27.bin", help="设置bin文件路径")
    args = parser.parse_args()
    print("bin filePath=", args.filePath)
    if not os.path.exists(args.filePath):
        print("can't find bin file ,program will exit")
        time.sleep(8)
        sys.exit(0)
    filePath = args.filePath
    # 更新输入参数
    if '.' in args.local_ip:
        address_local = (args.local_ip, args.local_port)
        comm = RadarDriver_UDP(args.local_port)
        comm.comm_open()
        address_radar = (args.radar_ip, args.radar_port)
        print(f"[*] address_local={address_local} ")
        print(f"[*] address_radar={address_radar} ")
        radar_upgrade = RadarUpgrade(comm, address_radar)
        print("udp upgrade start -----------")
    else:
        comm = RadarDriver_COM(args.local_ip)
        comm.comm_open()
        address_radar = (args.radar_ip, args.radar_port)
        print(f"[*] COM={args.local_ip} ")
        radar_upgrade = RadarUpgrade(comm, comm.decoder)
        print("COM upgrade start -----------")
    # 开启socket
    fileFolder, shotname, extension = radar_upgrade.Get_FilePath_FileName_FileExt(filePath)
    retryNumber = 20
    if radar_upgrade.upgrade_file(filePath, user_confirm_path=True):
        print("upgrade finished")
    radar_upgrade.comm.comm_close()
    # time.sleep(60)


if __name__ == '__main__':
    if "Windows" in platform.platform():
        radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name="COM5",
                                                   filePath=r"D:\FTP\log\20230615\TR.230222_60RadarApp_serial.Release.V1.0.2.2.bin",
                                                   head_type="A66A")
        result = radar_upgrade_com.upgrade_com()
    else:
        parser = argparse.ArgumentParser(description="Radar and MCU upgrade")
        # parser.add_argument('-f', '--filePath', type=str,
        #                     default=r"D:\TVT2022\20220322_mcu_Upgrade\mcu_HelloWorld2.bin",
        #                     help="设置bin文件路径")
        # parser.add_argument('-f', '--filePath', type=str, default=r"D:\TVT2022\20220322_mcu_Upgrade\V11.1.3.0_mcu_256.bin", help="设置bin文件路径")
        parser.add_argument('-f', '--filePath', type=str, default=r"d:\FTP\log\radar2.2.2.64.bin", help="设置bin文件路径")
        # parser.add_argument('-f', '--filePath', type=str, default=r"D:\周界雷达数据\zhoujie_v2.2.2.38\perimeterRadar_18xx_CH395_v2.2.2.38_radar.bin", help="设置bin文件路径")
        args = parser.parse_args()
        print(f"upgrade_radar_mcu bin filePath={args.filePath}")
        file_path = args.filePath

        print(datetime.datetime.now(), f"upgrade start")
        result=False
        file_folder, file_name = os.path.split(file_path)
        radar_upgrade_com=None
        if "Windows" in platform.platform():
            if "mcu" in file_name.lower():
                radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name="COM3", filePath=file_path)
                result = radar_upgrade_com.upgrade_com()
            else:
                radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name=15000, filePath=file_path,)
                result = radar_upgrade_com.upgrade_com()
        else:
            if "mcu" in file_name.lower():
                radar_upgrade_com=RadarUpgrade_Radar_MCU(com_port_name="/dev/ttyTHS1", filePath=file_path)
                result = radar_upgrade_com.upgrade_com()
            else:
                if "serial" in file_name.lower():
                    print(f"platform={platform.platform()}")
                    if "armv7l" in platform.platform():
                        # 60 米雷视一体机 rv1126平台，雷达串口 "/dev/ttyS1"
                        radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name="/dev/ttyS0", filePath=file_path,head_type="A66A")
                        result = radar_upgrade_com.upgrade_com()
                    else:
                        radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name="/dev/ttyTHS2", filePath=file_path,)
                        result=radar_upgrade_com.upgrade_com()
                elif "ch395" in file_name.lower():
                    radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name=15000, filePath=file_path,)
                    result=radar_upgrade_com.upgrade_com()
                else:
                    radar_upgrade_com = RadarUpgrade_Radar_MCU(com_port_name=15000, filePath=file_path,)
                    result=radar_upgrade_com.upgrade_com()

        result_infor_str= f"{datetime.datetime.now()},upgrade finish, result ={result}"
        for index_print in range(2):
            if radar_upgrade_com is not None:
                radar_upgrade_com.debug_udp_sender.udp_send(result_infor_str)
            print(result_infor_str)
            time.sleep(0.2)


