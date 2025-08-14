import datetime
import socket
import time


class Camere_Online_Tester():
    def __init__(self, camera_ip="192.168.8.11", camera_port=554, ):
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.is_online=False
        self.is_Camera_Online()

    def is_Camera_Online(self, ):
        """
        使用socket连接判定相机网线是否在线
        :return:
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.camera_ip, self.camera_port))
            s.shutdown(0)
            self.is_online = True
            return True
        except:
            self.is_online = False
            return False

if __name__ == '__main__':
    cameraLink_11=Camere_Online_Tester("192.168.8.11", camera_port=554,)
    cameraLink_12=Camere_Online_Tester("192.168.8.12", camera_port=554,)
    for index in range(60):
        is_online_11=cameraLink_11.is_Camera_Online()
        is_online_12=cameraLink_12.is_Camera_Online()
        str_11=f"{cameraLink_11.camera_ip}:{cameraLink_11.camera_port} online={is_online_11}"
        str_12=f"{cameraLink_12.camera_ip}:{cameraLink_12.camera_port} online={is_online_12}"
        time.sleep(1)
