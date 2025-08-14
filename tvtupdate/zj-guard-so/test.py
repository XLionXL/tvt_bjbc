import ctypes
import os.path
from ctypes import *
import json
import time

def savealarmpicture(save_alarm_pic):
    # save_alarm_pic:
    # 1 save far img
    # 2 save near img
    # 3 save far && near img
    savealarmpic = ctypes.CDLL('./client.so')
    savealarmpic.start(save_alarm_pic)

def new_test(save_alarm_pic, i):
    savealarmpic = ctypes.CDLL('./client.so')
    #str_res = "./ssd/alarmpic/alarmFrame/20230232_192308_alarm_frame.jpg"
    str_res = "./20230232_192308_alarm_frame_" + str(i) + ".jpg"
    #str_res = "/ssd/alarmpic/video/20230232_192208_alarm_frame.mp4"
    print(f"str_res : {str_res}")
    str_r = bytes(str_res, 'utf-8')
    p1 = c_char_p(str_r)

    bbox_list = [[-2, -2, 1, 1]]  # xywh
    bbox_list_str = json.dumps(bbox_list).replace(" ","")
    bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
    p2 = c_char_p(bbox_list_str_1)
    savealarmpic.start(save_alarm_pic, p1, p2)

def new_test2(save_alarm_pic, i, timestamp):
    savealarmpic = ctypes.CDLL('./client.so')
    #str_res = "./ssd/alarmpic/alarmFrame/20230232_192308_alarm_frame.jpg"
    str_res = "/ssd/alarmpic/alarmframe/20230232_192308_alarm_frame_" + str(i) + ".jpg"
    #str_res = "/ssd/alarmpic/video/20230232_192208_alarm_frame.mp4"
    print(f"str_res : {str_res}")
    str_r = bytes(str_res, 'utf-8')
    p1 = c_char_p(str_r)

    bbox_list = [[-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1] ,[-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1], [-2, -2, 1, 1]]  # xywh
    bbox_list_str = json.dumps(bbox_list).replace(" ","")
    bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
    p2 = c_char_p(bbox_list_str_1)

    # add timestamp str
    timestamp_ = c_long(timestamp)
    # send a message
    savealarmpic.start_new(save_alarm_pic, p1, p2, timestamp_)

def test_message_hz():
    test = ctypes.CDLL('./client.so')
    str_ch01 = "rtsp://admin:Admi1n23@192.168.1.199:5542/ch01.h264"
    str_ch02 = "rtsp://admin:Admi1n23@19"
    int_ch01_status = 1
    int_ch02_status = 0
    int_ch01_model = 0
    int_ch02_model = 1

    p1 = c_char_p(bytes(str_ch01, 'utf-8'))
    p2 = c_char_p(bytes(str_ch02, 'utf-8'))
    # run
    test.message_hz(p1, int_ch01_model, int_ch01_status, p2, int_ch02_model, int_ch02_status)


if __name__ == "__main__":
    #savealarmpicture(1)
    # for i in range(100):
    #     new_test(1, i)

    new_test2(1, 1, 1689228293519)



