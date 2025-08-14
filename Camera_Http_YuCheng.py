# -*- coding: gbk -*-
import datetime
import requests
import time
from requests.auth import HTTPBasicAuth

from common_hysteresis_threshold import EDGE_DETECT


class Camera_Http_YuCheng():
    def __init__(self, ip="192.168.1.11", username="admin", password=''):
        self.class_name = "Camera_Http_YuCheng"
        self.ip = ip
        self.username = username
        self.password = password
        self.headers = {
            'Accept': '*/*',
            'Content-Type': "application/x-www-form-urlencoded",
            "If-Modified-Since": "0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f'http://{ip}/main.html',
            "Accept-Language": 'zh-Hans-CN,zh-Hans',
            "Accept-Encoding": "gzip",
            "User-Agent": 'Mozilla/5.0',
            "Host": self.ip,
            "Content-Length": '35',
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
        }
        self.http_auth = HTTPBasicAuth(self.username, self.password)
        self.resp = None
        self.is_train_in_view_edge = EDGE_DETECT()
        self.has_login = False


    def goto_Presets(self, preset_point_int=139):
        """
        ����������Ԥ�õ�����
        :param preset_point_int: ���Ԥ������id
        :return:
        """
        url = f'http://{self.ip}/PTZ/1/Presets/Goto'
        # ��ҳ��Ԥ�õ�ʵ�ʷ�������Ҫ ��ȥ1��������ҳ139��ʵ�ʷ���138
        body = {"Param1": preset_point_int - 1}
        self.resp = requests.put(url, data=body, headers=self.headers, auth=self.http_auth)
        # print(datetime.datetime.now(), f"set to point={preset_point_int} resp.text=", self.resp.text)

    def camera_icr_set(self, is_train_in_view=True):
        """
        �����Ƿ��л𳵾����Ƿ�ر�icr
        :param is_train_in_view:��ǰ�Ƿ��л�
        :return:
        """
        try:
            if self.is_train_in_view_edge.is_Edge(is_train_in_view):
                print(f"{datetime.datetime.now()},{self.class_name},camera_icr_set is_train_in_view={is_train_in_view}")
            if is_train_in_view:
                # ǿ�ƹر�icr�����
                self.goto_Presets(139)
            else:
                # ���Զ�ģʽ��ҹ����icr�����
                self.goto_Presets(138)
            self.has_login = True
        except:
            self.has_login=False


if __name__ == "__main__":
    camera_yc = Camera_Http_YuCheng("192.168.8.11", "admin", 'Admin123')
    for index in range(1):
        camera_yc.camera_icr_set(False)
        time.sleep(10)
        camera_yc.camera_icr_set(True)
        time.sleep(3)
