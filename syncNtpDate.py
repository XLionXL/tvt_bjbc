import Camera_Http_940
import json
import ntplib
import os
import platform
import requests
import sched
import subprocess
import threading
import time
import traceback
import urllib.request
# from xml.etree.ElementTree import ElementTree
import xml.etree.ElementTree as ET
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
        self.sudo_password = sudo_password
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
        self.max_time_offset = 2.5
        
        self.change_time = True

        url = f'http://{far_camera_IP}/System/Time'
        #username = 'admin'
        #password = 'Admin123'
        p = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        p.add_password(None, url, username, password)
        handler = urllib.request.HTTPBasicAuthHandler(p)
        self.opener = urllib.request.build_opener(handler)
        self.httpdigestauth = HTTPDigestAuth(self.username, self.password)
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.ntp_server_url = ntp_server_url
        # self.ntp_server_url = '192.168.1.200'

        self.Camera_940 = Camera_Http_940.Camera_Http_940(near_camera_IP=near_camera_IP, far_camera_IP=far_camera_IP,
                                                          username=username, password=password)
        self.using_camera_class = "0" # 0:默认 zy:自研 940:940 hk:hk
        self.edge_infer_rtsp = EDGE_DETECT()

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

    def getNearCameraTime(self, ):

        """
        tm_year,tm_mon,tm_mday,tm_hour,tm_min,
                              tm_sec,tm_wday,tm_yday,tm_isdst)
        """
        try:
            url = f'http://{self.near_camera_IP}/digest/frmDeviceTimeCtrl'
            body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
            # print(body)
            response = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth, timeout=2)
            print(f"getNearCameraTime response={response.text}")
            # {"Result":0,"Data":{"Time":[2023,1,9,13,58,28]}}
            response_json = json.loads(response.text)
            if "Time" in response_json["Data"].keys():
                time_list=response_json["Data"]["Time"]
                if len(time_list)>=6:
                    camera_Time_str=f"{time_list[0]}{time_list[1]:02d}{time_list[2]:02d}T{time_list[3]:02d}{time_list[4]:02d}{time_list[5]:02d}"
                    print(f"getNearCameraTime get_time={camera_Time_str}")
                    return camera_Time_str
        except Exception as e:
            traceback.print_exc()
            print(f"getNearCameraTime error={e}")
        # 异常则返回nano时间
        camera_Time_str = time.strftime("%Y%m%dT%H%M%S")
        return camera_Time_str

    def setNearCameraTime(self, new_dateTime):
       
        """
        tm_year,tm_mon,tm_mday,tm_hour,tm_min,
                              tm_sec,tm_wday,tm_yday,tm_isdst)
        """
        try:
            url = f'http://{self.near_camera_IP}/digest/frmDeviceTimeCtrl'
            body = {"Type": 1, "Dev": 1, "Ch": 1, "Data": {"Time": [new_dateTime.tm_year,new_dateTime.tm_mon,new_dateTime.tm_mday,new_dateTime.tm_hour,new_dateTime.tm_min,new_dateTime.tm_sec]}}
            # print(body)
            self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)
            print(f'setNearCameraTime set_time_successfully {time.strftime("%Y%m%dT%H%M%S",new_dateTime)}')
        except :
            traceback.print_exc()
            print("near_camera set_time_error...")

    def get_camera_far_DateTime(self):
        try:
            urllib.request.install_opener(self.opener)
            xml = '''
            <?xml version="1.0" encoding="utf-8"?>
            <Time>
                <DateTimeFormat>YYYYMMDDWhhmmss</DateTimeFormat>
                <TimeFormat>24hour</TimeFormat>
                <SystemTime>{}</SystemTime>
            </Time>
            '''
            req = urllib.request.Request(url=f'http://{self.far_camera_IP}/System/Time', data=xml.encode('utf-8'),
                                         method='GET')
            req_result_xml_raw = urllib.request.urlopen(req, timeout=2).read()
            # print(f'camera_far_getDateTime req :{req}')
            # print(f'camera_far_getDateTime page :{req_result_xml_raw}')
            req_result_xml_str = req_result_xml_raw.decode('utf8')
            # 查找xml中的SystemTime字段值
            root_ =ET.fromstring(req_result_xml_str)
            camera_far_SystemTime_str = root_.find('SystemTime').text
            print(f"camera_far_SystemTime_str get_time={camera_far_SystemTime_str}")
            return camera_far_SystemTime_str

        except Exception as e:
            # 获取远焦相机时间失败，则返回nano当前时间
            print(f"camera_far_getDateTime error:{e}")
            return time.strftime('%Y%m%dT%H%M%S')

    def setFarCameraTime(self, ntp_timeStruct):
        try:
            date_str = f"{ntp_timeStruct.tm_year:04d}{ntp_timeStruct.tm_mon:02d}{ntp_timeStruct.tm_mday:02d}"
            time_str = f"{ntp_timeStruct.tm_hour:02d}{ntp_timeStruct.tm_min:02d}{ntp_timeStruct.tm_sec:02d}"
            ntp_server_datetime_str=f"{date_str}T{time_str}"
            self.xml = '''
                <?xml version="1.0" encoding="utf-8"?>
                <Time>
                <DateTimeFormat>
                YYYYMMDDWhhmmss
                </DateTimeFormat>
                <TimeFormat>24hour</TimeFormat>
                <SystemTime>{dateTime}</SystemTime></Time>
                    '''.format(dateTime=f"{ntp_server_datetime_str}")
            urllib.request.install_opener(self.opener)
            req = urllib.request.Request(url=f'http://{self.far_camera_IP}/System/Time', data=self.xml.encode('utf-8'),
                                         method='PUT')
            page = urllib.request.urlopen(req).read()
            print(f'setFarCameraTime set_time_successfully {ntp_server_datetime_str}')
        except:
            print("far_camera set_time_error...")

    def getNtpTime_old(self, ntp_server_url):
        # ntp_client = ntplib.NTPClient()
        try:
            ntp_stats = self.ntp_client.request(ntp_server_url)
            if "Windows" not in platform.platform():
                time.tzset()
            return ntp_stats.tx_time
        except Exception as e:
            # traceback.print_exc()
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            return time.time()

    def getNtpTime(self, ntp_server_url):
        ntp_stats = self.ntp_client.request(ntp_server_url)
        if "Windows" not in platform.platform():
            time.tzset()
        return ntp_stats.tx_time

    def setNanoTime(self, now_timeStruct):
        """
        :param new_time:
        :param new_date
        """
        try:
            # os.system('time {}'.format(new_time))
            # os.system('date {}'.format(new_date))
            date_str=f"{now_timeStruct.tm_year:04d}-{now_timeStruct.tm_mon:02d}-{now_timeStruct.tm_mday:02d}"
            time_str=f"{now_timeStruct.tm_hour:02d}:{now_timeStruct.tm_min:02d}:{now_timeStruct.tm_sec:02d}"
            command = 'sudo date -s "{} {}"'.format(date_str, time_str)
            os.system('echo %s|sudo -S %s' % (self.sudo_password, command))
        except Exception as e:
            print(f"setNanoTime error={e}")

    def syncTime_zy(self, ntp_server_url):
        try:
            # 从 ntp_server_url 获取当前时间，计算差值，如果差值较大则设置时间
            print("ntp service ip addr: ", ntp_server_url)
            ntp_server_datetime_float = self.getNtpTime_old(ntp_server_url) #返回了time.time()
            ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
            ntp_server_datetime_str =time.strftime("%Y%m%dT%H%M%S",ntp_server_datetime_timeStruct)
            # 计算ntp时间和nano时间 差值，单位为s
            offset_s_ntp_nano = ntp_server_datetime_float - time.time()
            # 如果nano时间和ntp offset_s大于self.max_time_offset则更新nano时间、远焦相机时间、近焦相机时间
            if abs(offset_s_ntp_nano) > self.max_time_offset:
                self.setNanoTime(ntp_server_datetime_timeStruct)
        except:
            traceback.print_exc()
            ntp_server_datetime_float = time.time()
            print("syncTime error...")

        try:
            # 远焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_farCamera = self.get_camera_far_DateTime()
            timeFloat_farCamera = time.mktime(time.strptime(timeStr_farCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_farCamera = timeFloat_farCamera - time.time()
            if abs(offset_s_ntp_farCamera) > self.max_time_offset:
                self.setFarCameraTime(time.localtime())
            # 近焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_nearCamera = self.getNearCameraTime()
            timeFloat_nearCamera = time.mktime(time.strptime(timeStr_nearCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_nearCamera = timeFloat_nearCamera - time.time()
            if abs(offset_s_ntp_nearCamera) > self.max_time_offset:
                self.setNearCameraTime(time.localtime())
            # 调试打印信息
            print(f"syncTime getTime_ntp={ntp_server_datetime_str} getTime_farCamera={timeStr_farCamera},getTime_nearCamera={timeStr_nearCamera}")
            print(f"syncTime offset_s_ntp_nano={offset_s_ntp_nano},"
                  f"offset_s_ntp_farCamera={offset_s_ntp_farCamera},offset_s_ntp_nearCamera={offset_s_ntp_nearCamera}")

            #     # set far_camera time
            #     ntp_server_datetime_timeStruct = time.localtime()
            #     self.setFarCameraTime(ntp_server_datetime_timeStruct)
            #     # set near_camera time
            #     ntp_server_datetime_timeStruct = time.localtime()
            #     self.setNearCameraTime(ntp_server_datetime_timeStruct)
            # else:
        except Exception as e:
            traceback.print_exc()
            print("syncTime error...")
        time.sleep(30)

    def syncTime_940(self, ntp_server_url):
        try:
            # 从 ntp_server_url 获取当前时间，计算差值，如果差值较大则设置时间
            print("ntp service ip addr: ", ntp_server_url)
            ntp_server_datetime_float = self.getNtpTime(ntp_server_url) #返回了time.time()
            # 计算ntp时间和nano时间 差值，单位为s
            offset_s_ntp_nano = ntp_server_datetime_float - time.time()
            ntp_server_datetime_timeStruct = time.localtime(ntp_server_datetime_float)
            ntp_server_datetime_str =time.strftime("%Y%m%dT%H%M%S",ntp_server_datetime_timeStruct)
            # 如果nano时间和ntp offset_s大于self.max_time_offset则更新nano时间、远焦相机时间、近焦相机时间
            if abs(offset_s_ntp_nano) > self.max_time_offset:
                self.setNanoTime(ntp_server_datetime_timeStruct)
        except Exception as e:
            # ntp_server_datetime_float = time.time()
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
            if self.using_camera_class == "940":
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
                self.Camera_940.set_far_DeviceTime()

            # 近焦相机时间获取，计算差值，如果差值较大则设置时间
            timeStr_nearCamera = self.Camera_940.get_near_DeviceTimeX()
            timeFloat_nearCamera = time.mktime(time.strptime(timeStr_nearCamera, "%Y%m%dT%H%M%S"))
            offset_s_ntp_nearCamera = timeFloat_nearCamera - time.time()
            if abs(offset_s_ntp_nearCamera) > self.max_time_offset:
                print(datetime.now().strftime("%Y-%m-%d/%H:%M:%S"))
                print(time.strftime("%Y-%m-%d/%H:%M:%S", time.localtime()))
                self.Camera_940.set_near_DeviceTime()

            # 调试打印信息
            print(f"syncTime getTime_ntp={ntp_server_datetime_str} getTime_farCamera={timeStr_farCamera},getTime_nearCamera={timeStr_nearCamera}")
            print(f"syncTime offset_s_ntp_nano={offset_s_ntp_nano},"
                  f"offset_s_ntp_farCamera={offset_s_ntp_farCamera},offset_s_ntp_nearCamera={offset_s_ntp_nearCamera}")
        except Exception as e:
            print("***************************************")
            print(f"getNtpTime error={e},ntp_server_url={ntp_server_url}")
            print("***************************************")
        time.sleep(30)

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

    def syncTime(self,):
        print(f"{datetime.now()},syncTime start")

        # 从xml文件获取ntp url,如果失败则使用'time.nist.gov'
        ntp_server_url = self.get_ntp_url_from_xml()

        ''' 
        通过流地址判断是否是相机类型
        self.using_camera_class = "zy" 使用自研相机
        self.using_camera_class = "940" 使用940相机
        '''
        if self.using_camera_class == "0":
            self.cemera_class_judge()
            print(f"using_camera_class:{self.using_camera_class}")

        if self.using_camera_class == "zy":
            self.syncTime_zy(ntp_server_url)
        elif self.using_camera_class == "940":
            self.syncTime_940(ntp_server_url)

        self.schedule.enter(0, 0, self.syncTime)
        print(f"{datetime.now()},syncTime exit")

    def get_ntp_url_from_xml(self):
        # 从xml文件获取ntp url,如果失败则使用'time.nist.gov'
        ntp_server_url = 'time.nist.gov'    # 默认ntp_server_url
        try:
            tree_ = ET.parse("/usr/bin/zipx/zj-general-constant.xml")
            root_ = tree_.getroot()
            # print('root-text', root_.text)
            key_value_ = root_.find('ntp_s')
            # print(key_value_.text)
            if len(key_value_.text) > 1 and len(key_value_.text) < 16:
                ntp_server_url = key_value_.text
        except:
            print("xml read error!")
        return ntp_server_url

    def runTask(self):
        self.schedule.enter(0, 0, self.syncTime)
        self.schedule.run()


if __name__ == '__main__':
    # tree_ = ET.parse("/usr/bin/zipx/zj-general-constant.xml")
    # root_ = tree_.getroot()
    # #print('root-text', root_.text)
    # key_value_ = root_.find('ntp_s')
    #print(key_value_.text)
    #print(len(key_value_.text))

    ntp = SyncNtpDate(near_camera_IP='192.168.8.12', far_camera_IP='192.168.8.11')
    # ntp.get_camera_far_DateTime()
    # ntp.getNearCameraTime()
    # nano_start_time=time.localtime()
    # time.sleep(3)
    # ntp.setFarCameraTime(nano_start_time)
    # ntp.setNearCameraTime(nano_start_time)
    try:
        threads = threading.Thread(target=ntp.runTask,name="x11")
        # threads.setDaemon(True)
        threads.start()
    except:
        print("Error: can not create NTP thread...")

