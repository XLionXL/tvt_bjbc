# -*- coding:utf-8 -*-

import datetime
import enum
import json
import os
import re
import struct
import time

from comm_crc16 import crc16_Modbus
from common_FileLoadSave import File_Saver_Loader_json


class Radar_Frame_Code(enum.Enum):
    mcu_ack = 0x0010
    mcu_temp = 0x0020
    mcu_angel = 0x0021
    mcu_gps = 0x0022
    mcu_curt = 0x0030
    mcu_volt = 0x0031
    radar_edition = 0x00ff
    radar_edition_A66A = 0x5f01
    train_paras = 0x01a2
    train_status = 0x01a3
    false_alarm_set = 0x02a1
    false_alarm_read = 0x02a2
    set_defense_area_ack = 0x00b0
    read_defense_area_ack = 0x00b1
    set_defense_area_ack_A66A = 0x6401
    read_defense_area_ack_A66A = 0x6402
    read_alarm_area_all_A66A = 0x64b1
    radar_objs = 0x00e1
    radar_objs_A66A = 0x5E01
    radar_heartBeat_A66A = 0x5E11
    cmd_ = 0x0042


class Decode_Result:
    def __init__(self):
        self.code = None
        self.value = None


class Frame_Bytes_AAAA5555():
    def __init__(self):
        self.head = b'\xAA\xAA\x55\x55'
        self.tail = b'\x55\x55\xAA\xAA'
        self.len_head = len(self.head)
        self.edition_response_head = self.head + b'\x00\xFF\x00\x00\x00\x10'
        self.get_edition_data= b'\x00\xFF\x00\x00\x00\x04\x00\x00\x00\x00'
        self.radar_objs = b'\x00\xe1'
        self.get_obj_area_data= b'\x00\xB1\x00\x00\x00\x04\x00\x00\x00\x00'
        self.get_radar_false_alarm_data=b'\x02\xA2\x00\x00\x00\x04\x00\x00\x00\x00'
        self.set_area_code = b'\x00\xB0'


class Frame_Bytes_A66A(Frame_Bytes_AAAA5555):
    def __init__(self):
        super().__init__()
        self.head = b'\xA6\x6A'
        self.tail = b'\xB7\x7B'
        self.len_head = len(self.head)
        self.edition_response_head = self.head + b'\x5F\x01\x00\x10'  # 5F 01 00 00
        self.edition_response_head_18 = self.head + b'\x5F\x01\x00\x18'  # 5F 01 00 00
        self.edition_response_head_1a = self.head + b'\x5F\x01\x00\x1a'  # 5F 01 00 00
        self.get_edition_data = b'\x5F\x01\x00\x00'
        self.radar_objs = b'\x5E\x01'
        self.get_obj_area_data= b'\x64\x02\x00\x00'
        self.set_area_code = b'\x64\x01'
        self.get_alarm_area_all_data = b'\x64\xB1\x00\x01\xFF'


class Decoder_Radar():
    if __name__ == "__main__":
        config_folder = os.path.join("", "config")
    elif os.path.exists(os.path.join("service", "config")):
        config_folder = os.path.join("service", "config")
    else:
        config_folder = os.path.join(".", "config")
    false_alarm_result_file = File_Saver_Loader_json(os.path.join(config_folder, "radar_false_alarm.json"))

    def __init__(self, head_type="AAAA5555"):
        self.class_name = "Decoder_Radar"
        self.edition_str = None
        self.obj_area = None
        self.alarm_area_all = None
        if "AAAA5555" in head_type:
            self.frame_bytes = Frame_Bytes_AAAA5555()
        else:
            self.frame_bytes = Frame_Bytes_A66A()
        self.crc16_modbus = crc16_Modbus()
        self.dataBuffer_bytes = b''
        self.udp_debug_callback = None
        self.radar_obj_area_save_callback = None
        self.radar_data_handler = None
        self.check_crc = True

    def listen_radar_data_handler(self, handle_radar_data):
        self.radar_data_handler = handle_radar_data

    def debug_callback_function(self, dataString):
        if self.udp_debug_callback is not None:
            self.udp_debug_callback(dataString)

    def format_bytes_to_str(self, bytes):
        return ''.join(['%02X' % b for b in bytes])
    def check_headtail_crc(self):
        """
         check headtail_crc and return index_head, index_tail, frameData
        """
        # 最小长度不够
        if len(self.dataBuffer_bytes) < 6:
            return -1, -1, None
        # 查找头尾位置
        index_head = self.dataBuffer_bytes.find(self.frame_bytes.head)
        len_of_frame = int.from_bytes(self.dataBuffer_bytes[index_head + 4:index_head + 6], "big")
        index_tail = self.dataBuffer_bytes.find(self.frame_bytes.tail, index_head)
        index_head_2 = -1
        # print(f"len_of_frame:{len_of_frame} index_head:{index_head} index_tail:{index_tail} {index_head+6+len_of_frame+2}")

        # 根据len_of_frame查找 frame_tail
        if self.dataBuffer_bytes[index_head+6+len_of_frame+2: index_head+6+len_of_frame+4] == self.frame_bytes.tail:
            # 找到了正确的帧数据
            # print("find end of this frame.")
            index_tail = index_head + 6 + len_of_frame + 2 # 防止出现数据中出现B77B字段数据导致index_tail不对
        elif index_tail < 0:
            # 只有一部分帧数据被接收到
            # print(f"{datetime.datetime.now()} find a part of frame")
            return index_head, index_tail, None
        else:
            # 数据不对的情况
            # print(f"{datetime.datetime.now()} do not find end of this frame.")
            find_end = index_tail
            for i in range(10):
                index_head_2 = self.dataBuffer_bytes.rfind(self.frame_bytes.head, index_head + 1, find_end)
                if index_head_2 < 0 :
                    # 从终止位往前找不到A66A数据时，数据错误
                    test_str = ''.join(['%02X' % b for b in self.dataBuffer_bytes])
                    self.data_buffer_forword(index_tail + self.frame_bytes.len_head)
                    return index_head, index_tail, None
                len_of_frame_2 = int.from_bytes(self.dataBuffer_bytes[index_head_2 + 4:index_head_2 + 6], "big")
                if index_tail == self.dataBuffer_bytes[index_head_2] + 6 + len_of_frame_2 + 2:
                    index_head = index_head_2
                    break
                elif self.dataBuffer_bytes[index_head_2+6+len_of_frame_2+2: index_head_2+6+len_of_frame_2+4] == self.frame_bytes.tail:
                    # print(f"{datetime.datetime.now()} find real data.")
                    index_head = index_head_2
                    index_tail = index_head_2 + 6 + len_of_frame_2 + 2
                else:
                    # print("find next 'A66A' data.")
                    find_end = index_head_2 - 1

        # # 如果不包含头和尾
        # if index_head < 0 or index_tail < 0 or index_head + 2 > index_tail:
        #     return index_head, index_tail, None
        # 如果包含头和尾,并且头尾包含的数据足够
        if self.frame_bytes.head == b'\xAA\xAA\x55\x55':
            crc_body = self.dataBuffer_bytes[index_head + self.frame_bytes.len_head:index_tail - 2]
        else:
            crc_body = self.dataBuffer_bytes[index_head:index_tail - 2]  # A66A decoder的crc计算需要包含head
        crc_2bytes_inFrame = self.dataBuffer_bytes[index_tail - 2:index_tail]
        crc_2bytes = self.crc16_modbus.crc16(crc_body, "big")
        crc_2bytes_little = self.crc16_modbus.crc16(crc_body, "little")
        if not self.check_crc or crc_2bytes == crc_2bytes_inFrame or crc_2bytes_little == crc_2bytes_inFrame or crc_2bytes_inFrame==b'\xBE\xBE':
            # 提取数据，并返回帧开始位置，长度，内容
            frameData = self.dataBuffer_bytes[index_head:index_tail + self.frame_bytes.len_head]
            time_now = datetime.datetime.now()
            decode_frame_str = ''.join(['%02X' % b for b in frameData])
            # print(f"{time_now} decode_frame_str:{decode_frame_str}")
            self.data_buffer_forword(index_tail + self.frame_bytes.len_head)
            return index_head, index_tail, frameData
        else:
            time_now = datetime.datetime.now()
            print(time_now, "CRC Error,Frame=", ''.join(['%02X' % b for b in self.dataBuffer_bytes[index_head:index_tail + self.frame_bytes.len_head]]))
            print(time_now, "crc_2bytes,Frame=", ''.join(['%02X' % b for b in crc_2bytes]), f"crc_2bytes_inFrame=={crc_2bytes_inFrame}")
            return index_head, index_tail, None

    def get_code(self, data_frame):
        frame_code = data_frame[self.frame_bytes.len_head] * 256 + data_frame[self.frame_bytes.len_head + 1]
        try:
            code = Radar_Frame_Code(frame_code)
        except:
            # print(f"{datetime.datetime.now()},{self.class_name} decode,Radar_Frame_Code error {self.format_bytes_to_str(data_frame)}")
            code= None
        return code

    def decode(self, data_frame):
        decode_result = Decode_Result()
        decode_result.code = self.get_code(data_frame)
        # print(f"decode_result.code={decode_result.code}")
        # 雷达目标
        if decode_result.code == Radar_Frame_Code.radar_objs:
            decode_result.value = self.decode_radar_objs(data_frame)
            if self.radar_data_handler is not None:
                self.radar_data_handler(decode_result.value)
                timer_for_radar_objs = time.time()
            # print(f"decode radar_objs={decode_result.value}")
        if decode_result.code == Radar_Frame_Code.radar_objs_A66A:
            decode_result.value = self.decode_radar_objs_A66A(data_frame)# xyp雷达解码
            # xyp雷达a66a输入数据
            if self.radar_data_handler is not None:
                self.radar_data_handler(decode_result.value)
                timer_for_radar_objs = time.time()
        # 雷达心跳包
        if decode_result.code == Radar_Frame_Code.radar_heartBeat_A66A:
            decode_result.value = self.decode_radar_heartBeat_A66A(data_frame)
            # print(f"decode radar_objs={decode_result.value}")
        # 火车检测状态输出
        if decode_result.code == Radar_Frame_Code.train_status:
            if data_frame[10] == 0x01 and data_frame[11] == 0x01:
                # print(f"{datetime.datetime.now()},train by radar={True}")
                decode_result.value=True
            else:
                # print(f"{datetime.datetime.now()},train by radar={False}")
                decode_result.value= False
            # if self.is_train_by_radar_edge.is_Edge(result.value):
        # 雷达版本
        if decode_result.code == Radar_Frame_Code.radar_edition:
            self.update_edition_str(data_frame)
            decode_result.value = self.edition_str
        if decode_result.code == Radar_Frame_Code.radar_edition_A66A:
            self.update_edition_str(data_frame)
            decode_result.value = self.edition_str
        # 虚警列表设置
        if decode_result.code == Radar_Frame_Code.false_alarm_set:
            decode_result.value=self.format_bytes_to_str(data_frame)
        # 虚警列表读取
        if decode_result.code == Radar_Frame_Code.false_alarm_read:
            decode_result.value=self.decode_false_alarm(data_frame)
        # set_defense_area_ack
        if decode_result.code == Radar_Frame_Code.set_defense_area_ack:
            print(f"set_defense_area_ack ={data_frame}")
        if decode_result.code == Radar_Frame_Code.set_defense_area_ack_A66A:
            result_str= "OK" if data_frame[6]==0x01 else "fail"
        # read_defense_area_ack
        if decode_result.code == Radar_Frame_Code.read_defense_area_ack:
            decode_result.value=self.decode_defense_areas(data_frame)
            if self.radar_obj_area_save_callback is not None:
                self.radar_obj_area_save_callback(
                    {"time_stamp": datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
                     "value": decode_result.value}
                )
        if decode_result.code == Radar_Frame_Code.read_defense_area_ack_A66A:
            decode_result.value = self.decode_defense_areas_A66A(data_frame)
            print("defense_area_A66A decode_result.value=", decode_result.value)
            if decode_result.value is not None and len(decode_result.value) > 0:
                self.obj_area = [{"type": 1, "verteces": area} for area in decode_result.value]
            if self.radar_obj_area_save_callback is not None:
                print(f"{datetime.datetime.now()} radar_obj_area_save_callback=", self.obj_area)
                self.radar_obj_area_save_callback(self.obj_area)
        if decode_result.code == Radar_Frame_Code.read_alarm_area_all_A66A:
            decode_result.value = self.decode_alarm_areas_A66A(data_frame)
            if decode_result.value is not None:
                self.alarm_area_all = [{"type": 1, "verteces": area} for area in decode_result.value]
            if self.radar_obj_area_save_callback is not None:
                self.radar_obj_area_save_callback(self.alarm_area_all)
        return decode_result

    def update_edition_str(self, data_frame):
        value = None
        if len(data_frame) == 32:
            print(f"{self.class_name},get_edition,Edition len(frameData)==32", self.format_bytes_to_str(data_frame))
            value = self.decode_edition_frame32(data_frame)
            # 只显示软件版本号 App=2.2.2.60,Alg=1.2.0.3,Hdw=1.3.0.3,Prt=1.0.0.9 >>> 2.2.2.60
            if "App" in value:
                pattern = "\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}"
                ret_group = re.search(pattern, value).group()
                if len(ret_group) > 0:
                    value = f"V{ret_group}"
        elif len(data_frame) == 20:
            value = self.decode_edition_frame20(data_frame)
        elif self.frame_bytes.edition_response_head in data_frame:
            print(f"{self.class_name},get_edition,Edition A66A", self.format_bytes_to_str(data_frame))
            value = self.decode_edition_frame32(data_frame)
        elif self.frame_bytes.edition_response_head_18 in data_frame or self.frame_bytes.edition_response_head_1a in data_frame:
            # App=1.0.1.4,Alg=1.0.2.7,FPGA=0.2.0.4,Prt=1.0.0.2,DNA_H=004ce429,DNA_L=7b3ea85c,Device=0101
            value = self.decode_edition_frame_001A(data_frame)
        if value is not None:
            self.edition_str = value
        return value

    def decode_false_alarm(self, data_frame):
        # 解码虚警帧
        false_alarm_result = {}
        false_alarm_result["list"] = {}
        pointPackage_size = 4  # 4(point_length)*11(num)+16(reserved)
        false_alarm_result["onOff"] = data_frame[10]
        false_alarm_result["length"] = data_frame[11]
        _offset = 12
        for i in range(false_alarm_result["length"]):
            offset = _offset + (i * pointPackage_size)
            location = struct.unpack('h', (data_frame[offset + 0:offset + 2])[::-1])[0]
            score = struct.unpack('h', (data_frame[offset + 2:offset + 4])[::-1])[0] * 0.1
            false_alarm_result["list"][location] = score
        print(f"{datetime.datetime.now()}, decode_false_alarm,{json.dumps(false_alarm_result)}")
        self.false_alarm_result_file.save_to_file(false_alarm_result)
        return false_alarm_result

    def decode_radar_objs(self, data_frame):
        target_list = []
        if data_frame[-6:-4]==b'\xBE\xBE':
            padding = data_frame[4:5]
            tag = data_frame[5:6]
            lens = data_frame[6:10]
            uuid = data_frame[10:22]
            # print(f"decode_radar_objs BEBE frame={self.format_bytes_to_str(data_frame)},tag={tag},lens={lens}")
            target = data_frame[22:302]
            try:
                for i in range(10):
                    offset = i * 28
                    # 有时候防摔雷达输出的数据不够导致解码错误，需要判断长度再解码
                    if len(target) >= offset + 28:
                        ID = struct.unpack('i', target[offset + 0:offset + 4])[0]
                        x = 2 * struct.unpack('f', target[offset + 4:offset + 8])[0]
                        y = struct.unpack('f', target[offset + 8:offset + 12])[0]
                        posZ = struct.unpack('f', target[offset + 12:offset + 16])[0]
                        vx = struct.unpack('f', target[offset + 16:offset + 20])[0]
                        vy = struct.unpack('f', target[offset + 20:offset + 24])[0]
                        confidence = struct.unpack('f', target[offset + 24:offset + 28])[0]
                        dto = [ID, x, y, vx, vy]  # 20221026 [ID, x, y, vx, a]
                        dto = [round(value, 3) for value in dto]
                        if 0 < y <= 250 and max(dto) > 0:
                            # print(f"{ID},x:{x},y:{y},posZ:{posZ},vx:{vx},vy:{vy},confidence:{confidence}")
                            if ID in target_list:
                                # 20230303,zuozhongliang 调试雷达数据中的重复目标
                                data_frame_str="".join([f"{byte:02X}" for byte in data_frame])
                            target_list.append(dto)
                        elif y > 250:
                            pass
                    else:
                        print(f"decode_radar_objs ,{len(target)}<{offset + 28},{self.format_bytes_to_str(data_frame)}")
                        break
                # print(f"{data_frame[-6:-4]} target_list={target_list}")
            except Exception as err:
                print(f"decode_radar_objs {err},{self.format_bytes_to_str(data_frame)}")
        else:
            pointPackage_offset = 10
            pointPackage_size = 60  # 4(point_length)*11(num)+16(reserved)
            num = int((len(data_frame) - pointPackage_offset) / pointPackage_size)
            for i in range(num):
                offset = pointPackage_offset + (i * pointPackage_size)
                ID = struct.unpack('i', (data_frame[offset + 0:offset + 4])[::-1])[0]
                x = struct.unpack('f', (data_frame[offset + 4:offset + 8])[::-1])[0]
                y = struct.unpack('f', (data_frame[offset + 8:offset + 12])[::-1])[0]
                z = struct.unpack('f', (data_frame[offset + 12:offset + 16])[::-1])[0]
                vx = struct.unpack('f', (data_frame[offset + 16:offset + 20])[::-1])[0]
                vy = struct.unpack('f', (data_frame[offset + 20:offset + 24])[::-1])[0]
                vz = struct.unpack('f', (data_frame[offset + 24:offset + 28])[::-1])[0]
                a = struct.unpack('f', (data_frame[offset + 28:offset + 32])[::-1])[0]
                r = struct.unpack('f', (data_frame[offset + 32:offset + 36])[::-1])[0]
                SNR = struct.unpack('f', (data_frame[offset + 36:offset + 40])[::-1])[0]
                en = struct.unpack('f', (data_frame[offset + 40:offset + 44])[::-1])[0]
                # print(f'shibian_radar count: {} data: id={} x={} y={} z={} vx={} vy={} vz={} a={} r={} snr={} power={}'.
                #       format(num, ID, x, y, z, vx, vy, vz, a, r, SNR, en))
                # dto = [ID, x, y, vx, a]
                dto = [ID, x, y, vx, vy]  # 20220621 [ID, x, y, vx, a] >>>[ID, x, y, vx, vy] 用vy过滤火车
                dto = [round(value, 3) for value in dto]
                if 0 < y <= 250:
                    target_list.append(dto)
                elif y > 250:
                    pass
        return target_list

    def decode_radar_objs_A66A(self, data_frame):
        # bytes_str = "".join([f"{byte:02X}" for byte in data_frame])
        # print(bytes_str)
        target_list = []
        pointPackage_offset = 2 + 2 + 2  # 帧头+功能+长度
        pointPackage_size = 13 * 2  # 13个字段，每个字段2字节
        num = int((len(data_frame) - pointPackage_offset) / pointPackage_size)
        for i in range(num):
            offset = pointPackage_offset + (i * pointPackage_size)
            ID = int.from_bytes(data_frame[offset + 0:offset + 2], "big")
            x = struct.unpack('h', (data_frame[offset + 2:offset + 4])[::-1])[0] * 0.1
            y = struct.unpack('h', (data_frame[offset + 4:offset + 6])[::-1])[0] * 0.1
            z = struct.unpack('h', (data_frame[offset + 6:offset + 8])[::-1])[0] * 0.1
            vx = struct.unpack('h', (data_frame[offset + 8:offset + 10])[::-1])[0] * 0.01
            vy = struct.unpack('h', (data_frame[offset + 10:offset + 12])[::-1])[0] * 0.01
            vz = struct.unpack('h', (data_frame[offset + 12:offset + 14])[::-1])[0] * 0.01
            a = struct.unpack('h', (data_frame[offset + 14:offset + 16])[::-1])[0] * 0.1
            b = int.from_bytes(data_frame[offset + 16:offset + 18], "big") * 0.1
            r = struct.unpack('h', (data_frame[offset + 18:offset + 20])[::-1])[0] * 0.1
            snr = int.from_bytes(data_frame[offset + 20:offset + 22], "big")
            en = int.from_bytes(data_frame[offset + 22:offset + 24], "big")
            reversed_data = int.from_bytes(data_frame[offset + 24:offset + 26], "big")
            # print(f'shibian_radar count: {} data: id={} x={} y={} z={} vx={} vy={} vz={} a={} r={} snr={} power={}'.
            #       format(num, ID, x, y, z, vx, vy, vz, a, r, SNR, en))
            # dto = [ID, x, y, vx, a]
            dto = [ID, x, y, vx, vy,snr,en,reversed_data]  # 20220621 [ID, x, y, vx, a] >>>[ID, x, y, vx, vy] 用vy过滤火车
            dto = [round(value, 3) for value in dto]
            if 0 < y <= 800:
                target_list.append(dto)
            elif y > 800:
                pass
        return target_list

    def decode_radar_heartBeat_A66A(self, data_frame):
        data_offset = 2 + 2 + 2  # 帧头+功能+长度
        heartBeat_cnt = struct.unpack('<I', (data_frame[data_offset:data_offset + 4])[::-1])[0]
        temp = int.from_bytes(data_frame[data_offset + 4:data_offset + 6], "big") * 0.1
        return [heartBeat_cnt, temp]

    def decode_defense_areas(self, data_frame):
        # area_str = "AAAA555500B10000002401010000BFDC03E000000000C0F5409841A62521403FAD5541912AEE3FABF1EB00000000D9315555AAAA"
        pointPackage_offset = 10
        area_list = []
        pointPackage_size = 36  # (1+1+2+8*4)*n
        num = int((len(data_frame) - pointPackage_offset) / pointPackage_size)
        for i in range(num):
            offset = pointPackage_offset + (i * pointPackage_size)
            ID = struct.unpack('B', (data_frame[offset + 0:offset + 1]))[0]
            Num = struct.unpack('B', (data_frame[offset + 1:offset + 2]))[0]
            type = struct.unpack('H', (data_frame[offset + 2:offset + 4]))[0]
            x0 = struct.unpack('>f', (data_frame[offset + 4:offset + 8]))[0]
            y0 = struct.unpack('>f', (data_frame[offset + 8:offset + 12]))[0]
            x1 = struct.unpack('>f', (data_frame[offset + 12:offset + 16]))[0]
            y1 = struct.unpack('>f', (data_frame[offset + 16:offset + 20]))[0]
            x2 = struct.unpack('>f', (data_frame[offset + 20:offset + 24]))[0]
            y2 = struct.unpack('>f', (data_frame[offset + 24:offset + 28]))[0]
            x3 = struct.unpack('>f', (data_frame[offset + 28:offset + 32]))[0]
            y3 = struct.unpack('>f', (data_frame[offset + 32:offset + 36]))[0]
            dto = [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
            area_list.append(dto)
        return area_list

    def decode_defense_areas_A66A(self, data_frame):
        # area_str = "A66A640200420004414570A3414570A3C14570A3C14570A300000000000000000000000000000000414570A3C14570A3C14570A3414570A30000000000000000000000000000000018B3B77B"
        pointPackage_offset = 6
        area_list = []
        pointPackage_size = 66  # (2+16*4)
        num = int((len(data_frame) - pointPackage_offset) / pointPackage_size)
        for i in range(num):
            offset = pointPackage_offset + (i * pointPackage_size)
            x_y_pair_num = struct.unpack('>H', (data_frame[offset + 0:offset + 2]))[0]
            dto=[]
            for index in range(x_y_pair_num):
                x = struct.unpack('>f', (data_frame[offset + 2 + index * 4:offset + 6 + index * 4]))[0]
                y = struct.unpack('>f', (data_frame[offset + 2 + 32 + index * 4:offset + 6 + 32 + index * 4]))[0]
                dto.append([x, y])
            area_list.append(dto)
        return area_list

    def decode_alarm_areas_A66A(self, data_frame):
        # area_str = "A66A64B10046000100010005BF8A3D7140A8F5C340051EB8C0947AE1BF8A3D710000000000000000000000004181E1E2435FC3C4435FC3C4416787884181E1E20000000000000000000000009CC5B77B"
        data_offset = 6
        area_list = []
        pointPackage_size = 70  # (2+16*4)
        num = int((len(data_frame) - data_offset) / pointPackage_size)
        for i in range(num):
            area_offset = data_offset + (i * pointPackage_size)
            x_offset = area_offset + 6
            y_offset = area_offset + 6 + 4 * 8
            area_id = struct.unpack('>H', (data_frame[area_offset + 0:area_offset + 2]))[0]
            area_enable = struct.unpack('>H', (data_frame[area_offset + 2:area_offset + 4]))[0]
            if not area_enable:
                continue
            x_y_pair_num = struct.unpack('>H', (data_frame[area_offset + 4:area_offset + 6]))[0]
            dto=[]
            for index_0_8 in range(x_y_pair_num):
                x = struct.unpack('>f', (data_frame[x_offset + index_0_8 * 4:x_offset + 4 + index_0_8 * 4]))[0]
                y = struct.unpack('>f', (data_frame[y_offset + index_0_8 * 4:y_offset + 4 + index_0_8 * 4]))[0]
                dto.append([x, y])
            area_list.append(dto)
        return area_list

    def set_defence_area(self, area_point_list=[(3, 0), (3, 95), (-2.5, 95), (-2, 0)]):
        # 防区设置报文
        # 测试用数据area_point_list = [(3, 0), (3, 95), (-2.5, 95), (-2, 0)]
        # AAAA555500B0000000240101000040400000000000004040000042BE0000C020000042BE0000C000000000000000BB3A5555AAAA

        # area_point_list = [[12.339999198913574, 12.339999198913574], [12.339999198913574, -12.339999198913574],
        #                    [-12.339999198913574, -12.339999198913574], [-12.339999198913574, 12.339999198913574]]
        # A66A640100420004414570A3414570A3C14570A3C14570A300000000000000000000000000000000414570A3C14570A3C14570A3414570A3000000000000000000000000000000000980B77B
        if self.frame_bytes.head==b'\xA6\x6A':
            bytes_length = struct.pack('>H', (2 + 4 * 16))  # 数据长度
            bytes_data_x = b''
            bytes_data_y = b''
            len_area_point_list = len(area_point_list)
            for index in range(8):
                if index<len_area_point_list:
                    x, y = area_point_list[index]
                else:
                    x, y = 0, 0
                bytes_data_x += struct.pack('>f', x)
                bytes_data_y += struct.pack('>f', y)
            bytes_data = struct.pack('>H', len(area_point_list)) + bytes_data_x + bytes_data_y  # 区域点数
        else:
            bytes_length = struct.pack('>I', (1 + 1 + 2 + 4 * 8))  # 数据长度
            bytes_data = b''
            bytes_data += struct.pack('>B', 1)  # 防区id
            bytes_data += struct.pack('>B', 1)  # 防区个数
            bytes_data += struct.pack('>H', 0)  # 防区类型
            for point in area_point_list:
                x, y = point
                bytes_data += struct.pack('>f', x)
                bytes_data += struct.pack('>f', y)
        frame_defence_area = self.gen_frame(self.frame_bytes.set_area_code + bytes_length + bytes_data)
        return frame_defence_area

    def get_radar_obj_area(self, ):
        # 读取目标上报区命令
        frame_defence_area = self.gen_frame(self.frame_bytes.get_obj_area_data)
        return frame_defence_area

    def get_radar_alarm_area_all(self, ):
        if b'\xA6\x6A' == self.frame_bytes.head:
            # 读取所有报警区命令
            frame_defence_area = self.gen_frame(self.frame_bytes.get_alarm_area_all_data)
            return frame_defence_area
        else:
            print(f"get_radar_alarm_area_all error , get_alarm_area_all_data not support in AAAA5555 radar")
            return b''

    def decode_edition(self, data_buffer):
        decode_result = Decode_Result()
        if self.frame_bytes.edition_response_head[:-1] in data_buffer:
            start_index = data_buffer.find(self.frame_bytes.edition_response_head[:-1])
            if start_index >= 0:
                frame_bytes = data_buffer[start_index:]
                # print(f"{datetime.datetime.now()},decode_edition,frame_data={self.format_bytes_to_str(frame_bytes)}")
                index_head, index_tail, frameData = self.check_headtail_crc()
                if frameData is None:
                    return None
                else:
                    decode_result=self.decode(frameData)
        return decode_result.value

    def decode_edition_frame20(self, frameData):
        offset = len(self.frame_bytes.edition_response_head)
        edition_list = ["V", ]
        for v_index in range(len(edition_list)):
            edition = ".".join([str(x) for x in frameData[offset + 0:offset + 4]])
            edition_list[v_index] += edition
            offset += 4
        edition_str = ",".join([str(x) for x in edition_list])
        return edition_str

    def decode_edition_frame32(self, frameData):
        offset = len(self.frame_bytes.edition_response_head)
        edition_list = ["App=", "Alg=", "Hdw=", "Prt=", ]
        for v_index in range(len(edition_list)):
            edition = ".".join([str(x) for x in frameData[offset + 0:offset + 4]])
            edition_list[v_index] += edition
            offset += 4
        edition_str = ",".join([str(x) for x in edition_list])
        return edition_str

    def decode_edition_frame_001A(self, frameData):
        offset = len(self.frame_bytes.edition_response_head)
        edition_list = ["App=", "Alg=", "FPGA=", "Prt=", "DNA_H=", "DNA_L=", "Device="]
        edition_len_list = [4, 4, 4, 4, 4, 4, 2]
        for v_index in range(len(edition_list)):
            if edition_list[v_index] in ["App=", "Alg=", "FPGA=", "Prt=",]:
                edition = ".".join([str(x) for x in frameData[offset + 0:offset + edition_len_list[v_index]]])
            else:
                edition = frameData[offset + 0:offset + edition_len_list[v_index]].hex()
            edition_list[v_index] += edition
            offset += edition_len_list[v_index]
        edition_str = ",".join([str(x) for x in edition_list])
        return edition_str

    def gen_frame(self, data, byteorder="big"):
        if b'\xAA\xAA\x55\x55' in self.frame_bytes.head:
            crc_2bytes = self.crc16_modbus.crc16(data, byteorder)
            frame_bytes = self.frame_bytes.head + data + crc_2bytes + self.frame_bytes.tail
        else:
            crc_2bytes = self.crc16_modbus.crc16(self.frame_bytes.head + data, byteorder)
            frame_bytes = self.frame_bytes.head + data + crc_2bytes + self.frame_bytes.tail
        # print("Decoder_Radar gen_frame frame_bytes=",frame_bytes)
        return frame_bytes

    def get_radar_edition_cmd(self):
        frame_get_edition = self.gen_frame(self.frame_bytes.get_edition_data)
        # frame_get_edition_str = self.format_bytes_to_str(frame_get_edition)
        return frame_get_edition

    def get_radar_false_alarm_cmd(self):
        # get_radar_false_alarm_cmd = AAAA555502A20000000400000000C16A5555AAAA
        frame_get_false_alarm=self.gen_frame(self.frame_bytes.get_radar_false_alarm_data)
        return frame_get_false_alarm

    def data_buffer_forword(self,  forwardIndex):
        """
        把buffer中的数据向前移动，
        :param forwardIndex:向前移动的字节数
        :return:
        """
        # dataBuffer更新
        if forwardIndex > 0:
            self.dataBuffer_bytes = self.dataBuffer_bytes[forwardIndex:]
        if len(self.dataBuffer_bytes) >= 500:
            self.dataBuffer_bytes = self.dataBuffer_bytes[500:]

    def append_data_to_buffer(self, data_bytes):
        if isinstance(data_bytes, bytes) and len(data_bytes) > 0:
            bytes_str = "".join([f"{byte:02X}" for byte in data_bytes])
            self.debug_callback_function(f"{self.class_name} Rx " + bytes_str)
            if self.dataBuffer_bytes is None:
                self.dataBuffer_bytes = data_bytes
            else:
                self.dataBuffer_bytes += data_bytes
        if len(self.dataBuffer_bytes)>=500:
            self.dataBuffer_bytes = data_bytes
            print(f"{self.class_name} self.dataBuffer_bytes reset")

    def test_false_alarm_frame_decoder(self):
        false_alarm_frame_string = "AAAA555502A2000000CA013200220012006F000700E300160079000600440010003D000D0019000C00E6001C001E005B001D001600E4001900EB000600780006005E00050061000500E200110028001B007B00160014001000230009003C001A003B0010003A00050039000500E5001900ED00070042000D00760005007500050074000600E1001600E00019007300060072000500710005007000050077000500EE000D006E0007006D0007006C0007001F0069006B000600690005006800050043001B00E7001B0020001300E8001C00DF001765E75555AAAA"
        false_alarm_frame_list = []
        for index in range(0, len(false_alarm_frame_string), 2):
            false_alarm_frame_list.append(false_alarm_frame_string[index:index + 2])
        false_alarm_frame = bytes([int(x, 16) for x in false_alarm_frame_list])
        self.decode_false_alarm(false_alarm_frame)


if __name__ == "__main__":
    test_decoder = Decoder_Radar(head_type="AAAA5555")
    radar_obj_str = "AAAA555500E100000000BC0D5555AAAA"
    radar_obj_frame = bytes([int(radar_obj_str[index * 2:index * 2 + 2], 16) for index in range(int(0.5 * len(radar_obj_str)))])
    test_decoder.decode(radar_obj_frame)
    frame = test_decoder.gen_frame(b'\x00\xe1\x00\x00\x00\x04\x00\x00\x00\x01')
    test_decoder.decode(test_decoder.frame_bytes.head + b'\x01\xA3\x00\x00\x00\x04\x00\x00\x05\x02\xBE\x64')
    test_decoder.decode_edition(test_decoder.get_radar_edition_cmd())
    test_decoder.decode(test_decoder.frame_bytes.head + b'\x01\xA3\x00\x00\x00\x04\x01\x01\x05\x03\x2F\x98' + test_decoder.frame_bytes.tail)
    test_decoder.check_headtail_crc()
    test_decoder.test_false_alarm_frame_decoder()
    area_set=test_decoder.set_defence_area()
    test_decoder.get_radar_obj_area()

    area_str = "AAAA555500B10000002401010000BFDC03E000000000C0F5409841A62521403FAD5541912AEE3FABF1EB00000000D9315555AAAA"
    area_frame = bytes([int(area_str[index * 2:index * 2 + 2], 16) for index in range(int(0.5 * len(area_str)))])
    test_decoder.decode_defense_areas(area_frame)

    test_decode_A66A = Decoder_Radar(head_type="A66A")

    area_set = test_decode_A66A.set_defence_area()
    alarm_area_all = "A66A64B10046000100010005BF8A3D7140A8F5C340051EB8C0947AE1BF8A3D710000000000000000000000004181E1E2435FC3C4435FC3C4416787884181E1E20000000000000000000000009CC5B77B"
    alarm_area_all = "A66A64B100D2000000010004C1A00000419CCCCD419CCCCDC1A666660000000000000000000000000000000042712D2D4271C3C44200D2D34200D2D300000000000000000000000000000000000100010004C220CCCDBECCCCCDBF19999AC21D999A00000000000000000000000000000000420C0000420C9697409B4B4B4091E1E200000000000000000000000000000000000200010004C12147AE419D70A4419F5C29C11D70A400000000000000000000000000000000430D2D2D430FD2D341F70F0F41F70F0F00000000000000000000000000000000BEBCB77B"

    radar_area_str="A66A640200420004414570A3414570A3C14570A3C14570A300000000000000000000000000000000414570A3C14570A3C14570A3414570A30000000000000000000000000000000018B3B77B"
    radar_area_frame = bytes([int(radar_area_str[index * 2:index * 2 + 2], 16) for index in range(int(0.5 * len(radar_area_str)))])
    test_decode_A66A.decode(radar_area_frame).value

    radar_obj_str = "A66A5E0101040000002B01F200000000000000000032000001F40000000000000001FFCC01F10000FFF6FFF60000FFC4000001F403E803E800000002003C01F00000FFECFFEC00000046000001F407D007D000000003FFBB01EF0000FFE2FFE20000FFB0000001F40BB80BB800000004004E01ED0000FFD8FFD80000005A000001F40FA00FA000000005FFAA01EC0000FFCEFFCE0000FF9C000001F41388138800000006005F01EA0000FFC4FFC40000006E000001F41770177000000007FF9901E90000FFBAFFBA0000FF88000001F41B581B5800000008007001E70000FFB0FFB000000082000001F41F401F4000000009FF8801E50000FFA6FFA60000FF74000001F423282328000005F3B77B"
    radar_obj_frame = bytes([int(radar_obj_str[index * 2:index * 2 + 2], 16) for index in range(int(0.5 * len(radar_obj_str)))])
    print(f"test_decode_A66A.decode radar_obj_frame={test_decode_A66A.decode(radar_obj_frame).value}")

    # radar_edition_str = "A66A5F0100100100000301000105000100010100000406FEB77B"
    radar_edition_str = "A66A5F010018010001010100010301000101010002010034E4297B3EA85C82DBB77B"
    radar_edition_str = "A66A5F01001A01000104010002070002000401000002004CE4297B3EA85C0101550CB77B"
    radar_heartBeat_frame="A66A5E110006000006590269E523B77B"
    radar_heartBeat_frame="A66A5E1100060000065A02691523B77B"

