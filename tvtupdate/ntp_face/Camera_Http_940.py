# -*- coding: gbk -*-
import datetime
import json
import time
import traceback

import requests
from requests.auth import HTTPDigestAuth
from bs4 import BeautifulSoup

class Camera_Http_940():
    def __init__(self, near_camera_IP="192.168.1.161", far_camera_IP="192.168.1.161", username="admin", password='Admin123'):
        self.near_camera_IP = near_camera_IP
        self.far_camera_IP = far_camera_IP
        self.username = username
        self.password = password
        self.headers = {
        }
        self.resp = None

    def get_near_DeviceTime(self):
        url = f'http://{self.near_camera_IP}/cgi-bin/devInfo.cgi?action=list&group=TIME'
        self.resp = requests.get(url, auth=(self.username, self.password))
        print(datetime.datetime.now(), "Camera_Http_940 get_near_DeviceTime resp.text=", self.resp.text)

    def get_far_DeviceTime(self):
        url = f'http://{self.far_camera_IP}/cgi-bin/devInfo.cgi?action=list&group=TIME'
        self.resp = requests.get(url, auth=(self.username, self.password))
        print(datetime.datetime.now(), "Camera_Http_940 get_far_DeviceTime resp.text=", self.resp.text)

    def get_near_DeviceTimeX(self):
        try:
            url = f'http://{self.near_camera_IP}/cgi-bin/devInfo.cgi?action=list&group=TIMEX'
            resp = requests.get(url, auth=(self.username, self.password), timeout=2)
            # print(datetime.datetime.now(), "Camera_Http_940 get_near_DeviceTimeX resp.text=", resp.text)
            # print(f"type(self.resp.text):{type(resp.text)}")

            # Ѱ��"root.TIMEX.time"�ֶ�����
            p1 = resp.text.find("root.TIMEX.time")
            # print(f'''self.resp.text.find("root.TIMEX.time"):{self.resp.text.find("root.TIMEX.time")}''')
            p2 = resp.text.find("root.TIMEX.msec")
            # print(f'''self.resp.text.find("root.TIMEX.msec"):{self.resp.text.find("root.TIMEX.msec")}''')
            # print(f'''self.resp.text[p1, p2]:{self.resp.text[p1+16:p2-1]}''')

            p3 = resp.text.find("root.TIMEX.timezone")
            p4 = resp.text.find("root.ERR.no")
            TIMEX_timezone = resp.text[p3 + 20:p4 - 1]


            TIMEX_time = resp.text[p1+16:p2-1]
            TIMEX_time_str = time.strftime("%Y%m%dT%H%M%S", time.localtime(int(TIMEX_time)))
            print(datetime.datetime.now(), "get near camera TIMEX_time_str=", TIMEX_time_str)
            print(datetime.datetime.now(), "get near camera TIMEX_timezone=", TIMEX_timezone)
            return TIMEX_time_str, TIMEX_timezone

        except Exception as e:
            traceback.print_exc()
            print(f"getNearCameraTime error={e}")
        TIMEX_time_str = time.strftime("%Y%m%dT%H%M%S")
        return TIMEX_time_str

    def get_far_DeviceTimeX(self):
        try:
            url = f'http://{self.far_camera_IP}/cgi-bin/devInfo.cgi?action=list&group=TIMEX'
            resp = requests.get(url, auth=(self.username, self.password), timeout=2)
            # print(datetime.datetime.now(), "Camera_Http_940 get_far_DeviceTimeX resp.text=", resp.text)

            # Ѱ��"root.TIMEX.time"�ֶ�����
            p1 = resp.text.find("root.TIMEX.time")
            # print(f'''self.resp.text.find("root.TIMEX.time"):{self.resp.text.find("root.TIMEX.time")}''')
            p2 = resp.text.find("root.TIMEX.msec")
            # print(f'''self.resp.text.find("root.TIMEX.msec"):{self.resp.text.find("root.TIMEX.msec")}''')
            # print(f'''self.resp.text[p1, p2]:{self.resp.text[p1+16:p2-1]}''')

            p3 = resp.text.find("root.TIMEX.timezone")
            p4 = resp.text.find("root.ERR.no")
            TIMEX_timezone = resp.text[p3 + 20:p4 - 1]

            TIMEX_time = resp.text[p1+16:p2-1]
            TIMEX_time_str = time.strftime("%Y%m%dT%H%M%S", time.localtime(int(TIMEX_time)))
            print(datetime.datetime.now(), "get far camera TIMEX_time_str=", TIMEX_time_str)
            print(datetime.datetime.now(), "get far camera TIMEX_timezone=", TIMEX_timezone)
            return TIMEX_time_str, TIMEX_timezone

        except Exception as e:
            traceback.print_exc()
            print(f"getFarCameraTime error={e}")
        TIMEX_time_str = time.strftime("%Y%m%dT%H%M%S")
        return TIMEX_time_str

    def set_near_DeviceTime(self, time_str=datetime.datetime.now().strftime("%Y-%m-%d/%H:%M:%S")):
        try:
            url = f'http://{self.near_camera_IP}/cgi-bin/devInfo.cgi?action=update&group=TIME&TIME.time={time_str}'
            print(f"set_near_DeviceTime time_str:{time_str}")
            self.resp = requests.get(url, auth=(self.username, self.password))
            # print(datetime.datetime.now(), "Camera_Http_940 set_near_DeviceTime resp.text=", self.resp.text)
        except:
            traceback.print_exc()
            print("near_camera set_time_error...")

    def set_far_DeviceTime(self, time_str=datetime.datetime.now().strftime("%Y-%m-%d/%H:%M:%S")):
        try:
            url = f'http://{self.far_camera_IP}/cgi-bin/devInfo.cgi?action=update&group=TIME&TIME.time={time_str}'
            print(f"set_far_DeviceTime time_str:{time_str}")
            self.resp = requests.get(url, auth=(self.username, self.password))
            # print(datetime.datetime.now(), "Camera_Http_940 set_far_DeviceTime resp.text=", self.resp.text)

        except:
            traceback.print_exc()
            print("far_camera set_time_error...")

    def set_near_DeviceTimeX(self, time_str=datetime.datetime.now().strftime("%Y-%m-%d/%H:%M:%S"), timezone=28800):
        try:
            times = time.time()
            url = f'http://{self.near_camera_IP}/cgi-bin/devInfo.cgi?action=update&group=TIMEX&TIMEX.time={times}&TIMEX.timezone={timezone}'
            print(f"set_near_DeviceTime time_str:{time_str}")
            self.resp = requests.get(url, auth=(self.username, self.password))
        except:
            traceback.print_exc()
            print("near_camera set_timeX_error...")

    def set_far_DeviceTimeX(self, time_str=datetime.datetime.now().strftime("%Y-%m-%d/%H:%M:%S"), timezone=28800):
        try:
            times = time.time()
            url = f'http://{self.far_camera_IP}/cgi-bin/devInfo.cgi?action=update&group=TIMEX&TIMEX.time={times}&TIMEX.timezone={timezone}'
            print(f"set_far_DeviceTime time_str:{time_str}")
            self.resp = requests.get(url, auth=(self.username, self.password))
        except:
            traceback.print_exc()
            print("far_camera set_timeX_error...")

    # def set_DeviceTimeX(self, timestamp=time.time(), timezone):
    #     url = f'http://{self.ip}/cgi-bin/devInfo.cgi?action=update&group=TIMEX&TIMEX.time={timestamp}&TIMEX.timezone={timezone}'
    #     self.resp = requests.get(url, auth=(self.username, self.password))
    #     print(datetime.datetime.now(), "Camera_Http_940 set_DeviceTime resp.text=", self.resp.text)

def test_camera_940(camera_ip="192.168.8.12"):
    camera_940 = Camera_Http_940(near_camera_IP=camera_ip, username="admin", password='12345')
    camera_940.get_near_DeviceTime()
    camera_940.get_near_DeviceTimeX()
    camera_940.set_near_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))


if __name__ == "__main__":
    # test_camera_940("192.168.8.11")
    # test_camera_940("192.168.8.12")
    # test_camera_940("10.8.4.224:8001")
    test_camera_940("10.8.4.163")
    print(time.strftime('%z'))

