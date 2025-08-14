from datetime import date, datetime, timedelta
import time
import threading
import os
import ntplib
import sched
import json
import requests
from requests.auth import HTTPDigestAuth
import urllib.request
#from xml.etree.ElementTree import ElementTree
import xml.etree.ElementTree as ET
import platform
import subprocess
import traceback

import Camera_Http_940

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
        print(body)
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)
        print(self.resp)

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
            if len(camera_rtsp) > 1:
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
            elif len(camera_rtsp) == 1:
                if "Streaming/Channels" in str(camera_rtsp):
                    self.using_camera_class = "hk_rv1126"
                elif "/ch01.264" in str(camera_rtsp):
                    self.using_camera_class = "zy_rv1126"
                elif ":8554/0" in str(camera_rtsp):
                    self.using_camera_class = "940_rv1126"
                else:
                    print(f"{datetime.now()}, camera rtsp url is error. please check. len(camera_rtsp)：{len(camera_rtsp)}.")
                break
            else:
                print(f"{datetime.now()}, no infer in ps,index={index},wait {check_cycle}s and recheck")
                time.sleep(check_cycle)
        return

    def syncTime_zy(self):
        ntp_server_datetime = time.localtime()
        # self.farCameraTimeData(time.strftime('%Y%m%dT%H%M%S'))

        # set near_camera time
        try:
            self.setCameraDateTime(ntp_server_datetime)
            print("camera set time success.")
        except:
            print("camera set time error...")

    def syncTime_940(self, ntp_server_url):
        try:
            # 从 ntp_server_url 获取当前时间，计算差值，如果差值较大则设置时间
            print("ntp service ip addr: ", ntp_server_url)
            ntp_server_datetime_float = self.getNtpTime(ntp_server_url) #返回了time.time()
            # 计算ntp时间和nano时间 差值，单位为s
            offset_s_ntp_nano = ntp_server_datetime_float - time.time()
            ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
            ntp_server_datetime_str =time.strftime("%Y%m%dT%H%M%S",ntp_server_datetime_timeStruct)
            print(f"get time from ntp service:{ntp_server_datetime_str}")
            # 如果nano时间和ntp offset_s大于self.max_time_offset则更新nano时间、远焦相机时间、近焦相机时间
            if abs(offset_s_ntp_nano) > self.max_time_offset:
                self.setNanoTime(ntp_server_datetime_timeStruct)
        except Exception as e:
            # ntp_server_datetime_float = time.time()
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
            print("***********Using camera time to update system time.***********")
            try:
                '''
                在ntp服务器失效时，可以通过940相机端的时间来修正NANO时间
                保证nano和相机时间的同步
                '''
                timeStr_farCamera_pre = self.Camera_940.get_far_DeviceTimeX()
                timeStr_nearCamera_pre = self.Camera_940.get_near_DeviceTimeX()

                timeFloat_farCamera_pre = time.mktime(time.strptime(timeStr_farCamera_pre, "%Y%m%dT%H%M%S"))
                timeFloat_nearCamera_pre = time.mktime(time.strptime(timeStr_nearCamera_pre, "%Y%m%dT%H%M%S"))

                timeFloatMean_camera_pre = (timeFloat_farCamera_pre + timeFloat_nearCamera_pre) / 2
                camera_mean_datetime_timeStruct = time.localtime(timeFloatMean_camera_pre)
                # 更新打印信息
                ntp_server_datetime_str = time.strftime("%Y%m%dT%H%M%S", camera_mean_datetime_timeStruct)
                print(f"recevie from cameras time is {ntp_server_datetime_str}")
                offset_s_camera_nano = timeFloatMean_camera_pre - time.time()
                if abs(offset_s_camera_nano) > self.max_time_offset:
                    self.setNanoTime(camera_mean_datetime_timeStruct)

                # 更新打印信息
                offset_s_ntp_nano = offset_s_camera_nano

            except Exception as e1:
                print("***************************************")
                print(f"getNtpTime error={e1}")
                print("***************************************")
                ntp_server_datetime_float = time.time()  # 返回了time.time()
                ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
                ntp_server_datetime_str = time.strftime("%Y%m%dT%H%M%S", ntp_server_datetime_timeStruct)

        try:
            # 远焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_farCamera = self.Camera_940.get_far_DeviceTimeX()
            timeFloat_farCamera = time.mktime(time.strptime(timeStr_farCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_farCamera = timeFloat_farCamera - time.time()
            if abs(offset_s_ntp_farCamera) > self.max_time_offset:
                print(datetime.now().strftime("%Y-%m-%d/%H:%M:%S"))
                print(time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

                # self.Camera_940.set_far_DeviceTime() -> self.Camera_940.set_far_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))
                self.Camera_940.set_far_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

            # 近焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_nearCamera = self.Camera_940.get_near_DeviceTimeX()
            timeFloat_nearCamera = time.mktime(time.strptime(timeStr_nearCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_nearCamera = timeFloat_nearCamera - time.time()
            if abs(offset_s_ntp_nearCamera) > self.max_time_offset:
                print(datetime.now().strftime("%Y-%m-%d/%H:%M:%S"))
                print(time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

                # self.Camera_940.set_near_DeviceTime() -> self.Camera_940.set_near_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))
                self.Camera_940.set_near_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

            # 调试打印信息
            print(f"syncTime getTime_ntp={ntp_server_datetime_str} getTime_farCamera={timeStr_farCamera},getTime_nearCamera={timeStr_nearCamera}")
            print(f"syncTime offset_s_ntp_nano={offset_s_ntp_nano},"
                  f"offset_s_ntp_farCamera={offset_s_ntp_farCamera},offset_s_ntp_nearCamera={offset_s_ntp_nearCamera}")
        except Exception as e:
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
        time.sleep(30)

    def syncTime_940_rv1126(self, ntp_server_url):
        try:
            # 从 ntp_server_url 获取当前时间，计算差值，如果差值较大则设置时间
            print("ntp service ip addr: ", ntp_server_url)
            ntp_server_datetime_float = self.getNtpTime(ntp_server_url) #返回了time.time()
            # 计算ntp时间和nano时间 差值，单位为s
            offset_s_ntp_nano = ntp_server_datetime_float - time.time()
            ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
            ntp_server_datetime_str =time.strftime("%Y%m%dT%H%M%S",ntp_server_datetime_timeStruct)
            print(f"get time from ntp service:{ntp_server_datetime_str}")
            # 如果nano时间和ntp offset_s大于self.max_time_offset则更新nano时间、远焦相机时间、近焦相机时间
            if abs(offset_s_ntp_nano) > self.max_time_offset:
                self.setNanoTime(ntp_server_datetime_timeStruct)
        except Exception as e:
            # ntp_server_datetime_float = time.time()
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
            print("***********Using camera time to update system time.***********")
            try:
                '''
                在ntp服务器失效时，可以通过940相机端的时间来修正NANO时间
                保证nano和相机时间的同步
                '''
                timeStr_nearCamera_pre = self.Camera_940.get_near_DeviceTimeX()
                timeFloat_nearCamera_pre = time.mktime(time.strptime(timeStr_nearCamera_pre, "%Y%m%dT%H%M%S"))
                timeFloatMean_camera_pre = timeFloat_nearCamera_pre
                camera_mean_datetime_timeStruct = time.localtime(timeFloatMean_camera_pre)
                # 更新打印信息
                ntp_server_datetime_str = time.strftime("%Y%m%dT%H%M%S", camera_mean_datetime_timeStruct)
                print(f"recevie from cameras time is {ntp_server_datetime_str}")
                offset_s_camera_nano = timeFloatMean_camera_pre - time.time()
                if abs(offset_s_camera_nano) > self.max_time_offset:
                    self.setNanoTime(camera_mean_datetime_timeStruct)

                # 更新打印信息
                offset_s_ntp_nano = offset_s_camera_nano

            except Exception as e1:
                print("***************************************")
                print(f"getNtpTime error={e1}")
                print("***************************************")
                ntp_server_datetime_float = time.time()  # 返回了time.time()
                ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
                ntp_server_datetime_str = time.strftime("%Y%m%dT%H%M%S", ntp_server_datetime_timeStruct)

        try:
            # 近焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_nearCamera = self.Camera_940.get_near_DeviceTimeX()
            timeFloat_nearCamera = time.mktime(time.strptime(timeStr_nearCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_nearCamera = timeFloat_nearCamera - time.time()
            if abs(offset_s_ntp_nearCamera) > self.max_time_offset:
                print(datetime.now().strftime("%Y-%m-%d/%H:%M:%S"))
                print(time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

                # self.Camera_940.set_near_DeviceTime() -> self.Camera_940.set_near_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))
                self.Camera_940.set_near_DeviceTime(time_str=time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))

            # 调试打印信息
            print(f"syncTime getTime_ntp={ntp_server_datetime_str}, getTime_Camera={timeStr_nearCamera}")
            print(f"syncTime offset_s_ntp_nano={offset_s_ntp_nano},"
                  f"offset_s_ntp_Camera={offset_s_ntp_nearCamera}")
        except Exception as e:
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
        time.sleep(30)

    def syncTime(self, ):
        if "generic" in platform.platform():
            self.using_camera_class = "zy"
        else:
            self.cemera_class_judge()
        if self.using_camera_class == "zy" or self.using_camera_class == "zy_rv1126":
            self.syncTime_zy()
        elif self.using_camera_class == "940":
            self.syncTime_940()

if __name__ == '__main__':
    ntp = SyncNtpDate(near_camera_IP = '192.168.8.12', far_camera_IP = '192.168.8.11')
    ntp.syncTime()