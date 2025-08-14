# -*- coding: gbk -*-
import datetime
import json
import requests
import time
from requests.auth import HTTPDigestAuth

from common_hysteresis_threshold import EDGE_DETECT


class Camera_Http_EnZhi():
    def __init__(self, ip="192.168.1.161", username="admin", password='123456'):
        self.class_name="Camera_Http_EnZhi"
        self.ip = ip
        self.username = username
        self.password = password
        self.headers = {
            'Accept': '*/*',
            'Content-Type': "application/json",
            "CV-SESSION-ID": '0',
            "Referer": f'http://{ip}/',
            "Accept-Language": 'zh-CN',
            "Accept-Encoding": "gzip",
            "User-Agent": 'Mozilla/5.0',
            "Host": '192.168.1.161',
            "Content-Length": '35',
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
        }
        self.body = {
            "Type": 0,
            "Dev": 1,
            "Ch": 1,
            "Data": {}
        }
        self.httpdigestauth = HTTPDigestAuth(self.username, self.password)
        self.resp = None
        self.frmVideoParaEx=None
        self.isTrainInView_last = -1    #-1可以保证第一次调用,参见controlIcrbyTrainstatus函数
        self.isTrainInView_edge = EDGE_DETECT()
        self.has_login=False

    def login(self, ):
        """
        http登录操作
        :return:
        """
        try:
            url = f'http://{self.ip}/digest/frmUserLogin'
            body = {
                "Type": 0,
                "Dev": 1,
                "Ch": 1,
                "Data": {}
            }
            self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)
            self.has_login=True
        except:
            self.has_login=False
        # print(datetime.datetime.now(), "user login resp.text=", self.resp.text)

    def get_frmVideoEffect(self, ):
        """
        获取图像效果配置
        """
        url = f'http://{self.ip}/digest/frmVideoEffect'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def update_frmVideoParaEx(self, Type=0):
        """
        获取视频参数配置
        "Type": 0-获取全天配置  2-获取白天配置  3-获取黑夜配置
        """
        url = f'http://{self.ip}/digest/frmVideoParaEx'
        body = {"Type": Type, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

        # 如果读取成功
        if "IcrLightMode" in self.resp.text:
            # print(datetime.datetime.now(), f"{self.class_name},update_frmVideoParaEx resp.text={self.resp.text}")
            frmVideoParaEx = json.loads(self.resp.text)["Data"]
            self.frmVideoParaEx = frmVideoParaEx
            return True
        else:
            return False

    def set_frmVideoParaEx(self, Type=1, IcrLightMode=None, IcrLightAue=None):
        """
        设置红外灯板工作模式和亮度
        :param Type:1-设置全天配置  4-设置白天配置  5-设置黑夜配置
        :param IcrLightMode:Int型,红外灯板状态,0-关闭,1-手动,2-自动
        :param IcrLightAue:Int型,红外灯板亮度,范围0-100
        :return:
        """
        url = f'http://{self.ip}/digest/frmVideoParaEx'
        type_map_dict = {1: 0, 4: 2, 5: 3}

        # 获得相机当前参数
        if Type in type_map_dict:
            type_of_get = type_map_dict[Type]
        else:
            print(f"Type 配置错误={Type}: 1-设置全天配置  4-设置白天配置  5-设置黑夜配置")
        index=0
        while not self.update_frmVideoParaEx(type_of_get):
            index+=1
            time.sleep(3)
            if index>100:
                return False
        # 比较相机参数和需要设置的参数，如果相同则返回
        if IcrLightMode==self.frmVideoParaEx["IcrLightMode"] and IcrLightAue==self.frmVideoParaEx["IcrLightAue"]:
            return True

        # 需要设置的新参数
        if IcrLightMode is not None and isinstance(IcrLightMode, int):
            self.frmVideoParaEx["IcrLightMode"] = IcrLightMode
        elif IcrLightMode is None:
            pass
        else:
            print(f"IcrLightMode error={IcrLightMode}: Int,0-close,1-man,2-auto")

        if IcrLightAue is not None and isinstance(IcrLightAue, int) and (0 <= IcrLightAue and IcrLightAue <= 100):
            self.frmVideoParaEx["IcrLightAue"] = IcrLightAue
        elif IcrLightAue is None:
            pass
        else:
            print(f"IcrLightAue error={IcrLightAue}: Int,0-100")

        # 设置红外灯板参数
        if isinstance(self.frmVideoParaEx, dict) and "IcrLightMode" in self.frmVideoParaEx:
            body = {"Type": Type, "Dev": 1, "Ch": 1, "Data": self.frmVideoParaEx}
            self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)
            # print(datetime.datetime.now(), f"设置红外灯板工作模式={IcrLightMode}和亮度={IcrLightAue}", " resp.text=", self.resp.text)
            if 'Operation Ok' in self.resp.text:
                return True
            else:
                print(datetime.datetime.now(), f"set_frmVideoParaEx error")

        return False

    def controlIcrbyTrainstatus(self, isTrainInView):
        """
        根据是否有火车决定恩智相机红外是否开启icr
        :param isTrainInView:
        :return:
        """
        try:
            if not self.has_login:
                self.login()
                self.update_frmVideoParaEx(0)
            rst = False
            if self.has_login and self.isTrainInView_edge.is_Edge(isTrainInView):
                # 如果有火车则关闭icr
                if isTrainInView:
                    rst = self.set_frmVideoParaEx(1, 0, 0)  #有火车，0关闭
                # 如果有火车则设置icr自动模式
                else:
                    rst = self.set_frmVideoParaEx(1, 2, 100)    #无火车，2自动, 红外灯板亮度100
        except:
            self.has_login = False

    def get_frmDevicePara(self):
        """
        获取恩智相机设备信息
        """
        url = f'http://{self.ip}/digest/frmDevicePara'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def get_frmImageType(self):
        """
        获取场景抓拍配置
        """
        url = f'http://{self.ip}/digest/frmImageType'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def get_frmGetRtspUrl(self):
        """
        获取场景抓拍配置
        """
        url = f'http://{self.ip}/digest/frmGetRtspUrl'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def set_DeviceTime(self, time_now=datetime.datetime.now()):
        """
        设置恩智相机的时间
        :param time_now: 当前时刻
        :return:
        """
        url = f'http://{self.ip}/digest/frmDeviceTimeCtrl'
        body = {
            "Type": 1,
            "Dev": 1,
            "Ch": 1,
            "Data": {
                "Time": [time_now.year, time_now.month, time_now.day, time_now.hour, time_now.minute, time_now.second]
            }
        }
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def set_FTPSetting(self, FServer="", FUserName="kk", FPassword="123456", FServerDir=""):
        """
        设置恩智相机的FTP信息
        :return:
        """
        url = f'http://{self.ip}/digest/frmFTPSetting'
        body = {
            "Type": 1,
            "Dev": 1,
            "Ch": 1,
            "Data": {
                "FLinkMode": 0,
                "FPort": 21,
                "FServer": FServer,
                "FUserName": FUserName,
                "FPasswordB64": "MTIzNDU2",
                "FPassword": FPassword,
                "FServerDir": FServerDir
            }
        }
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

if __name__ == "__main__":
    camera_nz = Camera_Http_EnZhi("192.168.8.12", "admin", 'Admin123')
    # camera_nz.login()
    # camera_nz.set_frmVideoParaEx(1, 2, 0)
    # camera_nz.get_frmDevicePara()
    # camera_nz.get_frmGetRtspUrl()
    # camera_nz.set_DeviceTime()
    for index in range(0, 1):
        camera_nz.controlIcrbyTrainstatus(False)
        time.sleep(3)
        camera_nz.controlIcrbyTrainstatus(True)
        time.sleep(3)
    camera_nz.controlIcrbyTrainstatus(False)
