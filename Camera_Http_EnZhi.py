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
        self.isTrainInView_last = -1    #-1���Ա�֤��һ�ε���,�μ�controlIcrbyTrainstatus����
        self.isTrainInView_edge = EDGE_DETECT()
        self.has_login=False

    def login(self, ):
        """
        http��¼����
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
        ��ȡͼ��Ч������
        """
        url = f'http://{self.ip}/digest/frmVideoEffect'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def update_frmVideoParaEx(self, Type=0):
        """
        ��ȡ��Ƶ��������
        "Type": 0-��ȡȫ������  2-��ȡ��������  3-��ȡ��ҹ����
        """
        url = f'http://{self.ip}/digest/frmVideoParaEx'
        body = {"Type": Type, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

        # �����ȡ�ɹ�
        if "IcrLightMode" in self.resp.text:
            # print(datetime.datetime.now(), f"{self.class_name},update_frmVideoParaEx resp.text={self.resp.text}")
            frmVideoParaEx = json.loads(self.resp.text)["Data"]
            self.frmVideoParaEx = frmVideoParaEx
            return True
        else:
            return False

    def set_frmVideoParaEx(self, Type=1, IcrLightMode=None, IcrLightAue=None):
        """
        ���ú���ư幤��ģʽ������
        :param Type:1-����ȫ������  4-���ð�������  5-���ú�ҹ����
        :param IcrLightMode:Int��,����ư�״̬,0-�ر�,1-�ֶ�,2-�Զ�
        :param IcrLightAue:Int��,����ư�����,��Χ0-100
        :return:
        """
        url = f'http://{self.ip}/digest/frmVideoParaEx'
        type_map_dict = {1: 0, 4: 2, 5: 3}

        # ��������ǰ����
        if Type in type_map_dict:
            type_of_get = type_map_dict[Type]
        else:
            print(f"Type ���ô���={Type}: 1-����ȫ������  4-���ð�������  5-���ú�ҹ����")
        index=0
        while not self.update_frmVideoParaEx(type_of_get):
            index+=1
            time.sleep(3)
            if index>100:
                return False
        # �Ƚ������������Ҫ���õĲ����������ͬ�򷵻�
        if IcrLightMode==self.frmVideoParaEx["IcrLightMode"] and IcrLightAue==self.frmVideoParaEx["IcrLightAue"]:
            return True

        # ��Ҫ���õ��²���
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

        # ���ú���ư����
        if isinstance(self.frmVideoParaEx, dict) and "IcrLightMode" in self.frmVideoParaEx:
            body = {"Type": Type, "Dev": 1, "Ch": 1, "Data": self.frmVideoParaEx}
            self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)
            # print(datetime.datetime.now(), f"���ú���ư幤��ģʽ={IcrLightMode}������={IcrLightAue}", " resp.text=", self.resp.text)
            if 'Operation Ok' in self.resp.text:
                return True
            else:
                print(datetime.datetime.now(), f"set_frmVideoParaEx error")

        return False

    def controlIcrbyTrainstatus(self, isTrainInView):
        """
        �����Ƿ��л𳵾���������������Ƿ���icr
        :param isTrainInView:
        :return:
        """
        try:
            if not self.has_login:
                self.login()
                self.update_frmVideoParaEx(0)
            rst = False
            if self.has_login and self.isTrainInView_edge.is_Edge(isTrainInView):
                # ����л���ر�icr
                if isTrainInView:
                    rst = self.set_frmVideoParaEx(1, 0, 0)  #�л𳵣�0�ر�
                # ����л�������icr�Զ�ģʽ
                else:
                    rst = self.set_frmVideoParaEx(1, 2, 100)    #�޻𳵣�2�Զ�, ����ư�����100
        except:
            self.has_login = False

    def get_frmDevicePara(self):
        """
        ��ȡ��������豸��Ϣ
        """
        url = f'http://{self.ip}/digest/frmDevicePara'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def get_frmImageType(self):
        """
        ��ȡ����ץ������
        """
        url = f'http://{self.ip}/digest/frmImageType'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def get_frmGetRtspUrl(self):
        """
        ��ȡ����ץ������
        """
        url = f'http://{self.ip}/digest/frmGetRtspUrl'
        body = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
        self.resp = requests.post(url, data=json.dumps(body), headers=self.headers, auth=self.httpdigestauth)

    def set_DeviceTime(self, time_now=datetime.datetime.now()):
        """
        ���ö��������ʱ��
        :param time_now: ��ǰʱ��
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
        ���ö��������FTP��Ϣ
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
