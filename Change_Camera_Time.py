import Camera_Http_940
import json
import ntplib
# from xml.etree.ElementTree import ElementTree
import platform
import requests
import sched
import subprocess
import time
import traceback
import urllib.request
from datetime import datetime
from requests.auth import HTTPDigestAuth


class EDGE_DETECT():
    def __init__(self, init_value=-562536):
        # 562536 取奇怪值，使得第一次判定为is_edge为True
        self.lastValue = init_value
        self.last_edge_timestamp = time.time()
        self.last_rising_timestamp = time.time()
        self.last_falling_timestamp = time.time()

    def is_Edge(self, value):
        is_edge=True if value!=self.lastValue else False
        if is_edge:
            self.last_edge_timestamp = time.time()
        if value and not self.lastValue:
            self.last_rising_timestamp = time.time()
        if self.lastValue and not value:
            self.last_falling_timestamp = time.time()

        self.lastValue = value
        return is_edge

class SyncNtpDate(object):
    # tvt自研近焦、远焦相机的时间同步设置。
    def __init__(self, near_camera_IP="192.168.8.12", far_camera_IP="192.168.8.11", ntp_server_url='time.nist.gov',
                                 username="admin", password='Admin123', sudo_password="TDDPc5kc4WnYcy"):
        self.near_camera_IP = near_camera_IP
        self.far_camera_IP = far_camera_IP
        self.username = username
        self.password = password
        self.sudo_password=sudo_password
        self.ntp_client = ntplib.NTPClient()
        self.headers = {
                'Accept': '*/*',
                'Content-Type': "application/json",
                "CV-SESSION-ID": '0',
                "Referer": f'http://{near_camera_IP}/',
                "Accept-Language": 'zh-CN',
                "Accept-Encoding": "gzip",
                "User-Agent": 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                "Host": '192.168.1.200',
                "Content-Length": '35',
                'Connection': 'Keep-Alive',
                'Cache-Control': 'no-cache',
                }
        url = f'http://{far_camera_IP}/System/Time'
        p = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        p.add_password(None, url, username, password)
        handler = urllib.request.HTTPBasicAuthHandler(p)
        self.opener = urllib.request.build_opener(handler)
        self.httpdigestauth = HTTPDigestAuth(self.username, self.password)
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.ntp_server_url = ntp_server_url


        self.edge_infer_rtsp = EDGE_DETECT()
        self.Camera_940 = Camera_Http_940.Camera_Http_940(near_camera_IP=near_camera_IP, far_camera_IP=far_camera_IP,
                                                          username=username, password=password)
        self.using_camera_class = "0"  # 0:默认 zy:自研 940:940 hk:hk

    def setCameraDateTime(self, new_dateTime):
        url = f'http://{self.near_camera_IP}/digest/frmDeviceTimeCtrl'
        body = {"Type": 1, "Dev": 1, "Ch": 1, "Data": {"Time": [new_dateTime.tm_year,new_dateTime.tm_mon,new_dateTime.tm_mday,new_dateTime.tm_hour,new_dateTime.tm_min,new_dateTime.tm_sec]}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def farCameraTimeData(self, fmtData):
        self.xml = '''
            <?xml version="1.0" encoding="utf-8"?>
            <Time>
            <DateTimeFormat>
            YYYYMMDDWhhmmss
            </DateTimeFormat>
            <TimeFormat>24hour</TimeFormat>
            <SystemTime>{dateTime}</SystemTime></Time>
            '''.format(dateTime=fmtData)

    def get_rtsp_from_ps_infer_main(self, cmd="ps -aux|grep infer_main|grep rtsp", filterKey='rtsp', ):
        """
        在shell中通过ps命令获得当前系统中的推理流地址
        :param cmd:显示推理进程的ps命令
        :param filterKey:用于过滤的字符串
        :return:
        """
        rtsp_list = []
        if "Windows" not in platform.platform():
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            time.sleep(0.5)
            line_list=p.stdout.readlines()
            for index, line_byte in enumerate(line_list):
                text = str(line_byte, encoding='utf-8').split()
                # print(text)
                rtsp_list = [x.strip() for x in text if (filterKey in x and len(x)>20)]
                # print(rtsp_list)
                if len(rtsp_list)>0:
                    break
            p.kill()
            if self.edge_infer_rtsp.is_Edge(rtsp_list):
                print(f"{datetime.now()},get_rtsp_from_ps_infer_main, rtsp={rtsp_list}")

            if len(rtsp_list) > 0:
                # rtsp_list.reverse()
                return rtsp_list
            else:
                print(f"error in get_url_from_ps_infer_main line_list={line_list}")
                return []
        else:
            # return ["rtsp://admin:Admin123@10.8.4.31", "rtsp://admin:Admin123@10.8.4.32"]
            # return ["rtsp://admin:Admin123@192.168.1.12/ch01.264", "rtsp://admin:Admin123@192.168.1.11/live/0/MAIN"]
            return ["rtsp://admin:Admin123@192.168.8.12/Streaming/Channels/101", "rtsp://admin:Admin123@192.168.8.11/Streaming/Channels/101"]
            # return ["D:\\2022-03-02 18-56-43.mp4", "D:\\2022-03-02 18-49-03.mp4"]

    def cemera_class_judge(self,):
        check_cycle = 3
        for index in range(int(600 / check_cycle)):
            camera_rtsp = self.get_rtsp_from_ps_infer_main()
            if len(camera_rtsp) > 0:
                if "Streaming/Channels" in str(camera_rtsp):
                    self.using_camera_class = "hk"
                elif "/ch01.264" in str(camera_rtsp):
                    self.using_camera_class = "zy"
                elif "/live/0/MAIN" in str(camera_rtsp):
                    self.using_camera_class = "zy"
                elif ":8554/0" in str(camera_rtsp):
                    self.using_camera_class = "940"
                else:
                    print(f"{datetime.now()}, camera rtsp url is error. please check.")
                break
            else:
                print(f"{datetime.now()}, no infer in ps,index={index},wait {check_cycle}s and recheck")
                time.sleep(check_cycle)
        return

    def syncTime_zy(self,):
        ntp_server_datetime = time.localtime()
        self.farCameraTimeData(time.strftime('%Y%m%dT%H%M%S'))

        # set near_camera time
        try:
            self.setCameraDateTime(ntp_server_datetime)
            print("near_camera set time success.")
        except:
            print("near_camera set time error...")

        # set far_camera time
        try:
            urllib.request.install_opener(self.opener)
            req = urllib.request.Request(url=f'http://{self.far_camera_IP}/System/Time', data=self.xml.encode('utf-8'), method='PUT')
            page = urllib.request.urlopen(req).read()
            print("far_camera set time success.")
            # print(ntp_server_url)
        except:
            print("far_camera set time error...")

    def syncTime_940(self,):
        # update 940 near camera time
        try:
            self.Camera_940.set_near_DeviceTime()
        except:
            traceback.print_exc()

        # update 940 far camera time
        try:
            self.Camera_940.set_far_DeviceTime()
        except:
            traceback.print_exc()

    def syncTime(self, ):
        self.cemera_class_judge()
        if self.using_camera_class == "zy":
            self.syncTime_zy()
        elif self.using_camera_class == "940":
            self.syncTime_940()


if __name__ == '__main__':
    ntp = SyncNtpDate(near_camera_IP = '192.168.8.12', far_camera_IP = '192.168.8.11')
    ntp.syncTime()



