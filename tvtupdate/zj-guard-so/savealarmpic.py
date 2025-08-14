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
    # /ssd/alarmpic/ 下有两个文件夹
    # 一个farcamera_alarmpic放远焦报警图片，一个 nearcamera_alarmpic 放近焦图片
    for folder_path in ["/ssd/alarmpic/farcamera_alarmpic", "/ssd/alarmpic/nearcamera_alarmpic"]:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    savealarmpic = ctypes.CDLL('./client.so')
    savealarmpic.start(save_alarm_pic)

def new_test(save_alarm_pic, i):
    savealarmpic = ctypes.CDLL('/usr/bin/zipx/zj-guard-so/libclient.so')
    #str_res = "./ssd/alarmpic/alarmFrame/20230232_192308_alarm_frame.jpg"
    str_res = "/ssd/alarmpic/alarmFrame/20230232_192308_alarm_frame_" + str(i) + ".jpg"
    #str_res = "/ssd/alarmpic/video/20230232_192208_alarm_frame.mp4"
    print(f"str_res : {str_res}")
    str_r = bytes(str_res, 'utf-8')
    p1 = c_char_p(str_r)

    bbox_list = [[-2, -2, 1, 1]]  # xywh
    bbox_list_str = json.dumps(bbox_list).replace(" ","")
    bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
    p2 = c_char_p(bbox_list_str_1)
    savealarmpic.start(save_alarm_pic, p1, p2)
    
    #savealarmpic.start(save_alarm_pic, p1)
    #print(p.value)

if __name__ == "__main__":
    for i in range(0, 5):
        new_test(2, i)
        time.sleep(1)
