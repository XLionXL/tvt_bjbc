# coding:utf-8
import datetime
import platform
import re
import socket
import subprocess
import threading
import time
import traceback


class DebugUDPSender():
    def __init__(self, local_port=18000, remote_ip="255.255.255.255"):
        self.class_name="DebugUDPSender"
        self.local_port = local_port
        self.udpPort_isOpen = False
        self.udp_socket=None
        self.timeout_s = 5
        self.remote_ip = remote_ip
        self.remote_ip_subnet255 = ""
        self.remote_port = 30000    # 修改为固定端口 20220716 zzl
        self.latest_data_stamp = time.time()
        self.udp_open()
        self.debug_callback=None
        self.out_ip=None
        self.get_out_ip()
        print(f"{datetime.datetime.now()},{self.class_name},init,{self.out_ip}:{self.local_port}>>>"
              f"{self.remote_ip},{self.remote_ip_subnet255}:{self.remote_port}")

    def debug_callback_function(self,data):
        if self.debug_callback is not None:
            self.debug_callback(data)

    def udp_open(self, ):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # SO_REUSEADDR是让端口释放后立即就可以被再次使用。
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # SO_BROADCAST 允许发送广播数据
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.bind(('', self.local_port))
            self.udp_socket.settimeout(self.timeout_s)
            print(datetime.datetime.now(), f"{self.class_name} open udp_socket bind_port={self.local_port}")
            self.udpPort_isOpen = True
            self.latest_data_stamp = time.time()
        except Exception as e:
            print(datetime.datetime.now(), f"{self.class_name} udp_open error {self.local_port} ", __file__, e)
            self.udpPort_isOpen = False

    def udp_close(self):
        if self.udpPort_isOpen:
            self.udp_socket.close()
            self.udpPort_isOpen = False
            print(datetime.datetime.now(), f"{self.class_name} udp_close bind_port={self.local_port}")

    def udp_send(self, send_data):
        data_str=f"{datetime.datetime.now()},{send_data},out_ip={self.out_ip}\n"
        # 20230626 60米一体机没有内部网络
        if "armv7l" in platform.platform().lower():
            pass
        else:
            for remote_ip in [self.remote_ip, self.remote_ip_subnet255, "192.168.8.255"]:
                try:
                    self.udp_socket.sendto(data_str.encode('utf-8'), (remote_ip, self.remote_port))
                except:
                    print(f"{datetime.datetime.now()} udp_send error remote_ip={remote_ip},{traceback.format_exc()}")

    def _run_receive(self):
        dataBuffer = bytes()
        while True:
            if not self.udpPort_isOpen or time.time() - self.latest_data_stamp >= self.timeout_s * 20:
                if self.udpPort_isOpen:
                    self.udp_close()
                self.udp_open()
            if self.udpPort_isOpen:
                start = time.time()
                try:
                    recv = self.udp_socket.recvfrom(1404)
                except:
                    continue
                # print(datetime.datetime.now(),"rece data=",recv)
                end = time.time()
                # print(f"radar duration: {end - start} fps: {1 / (end - start)}")
                data, ip_port = recv
                dataBuffer = dataBuffer + data
                frameIndex, frameLength, frameData = self.decoder.check_headtail_crc(dataBuffer)
                # 解码一帧
                if frameLength > 0:
                    # if self.bind_port in [15000,17000,20000]:
                    #     target_list = self.decoder.decode(frameData)
                    # else:
                    #     target_list = self.decoder.unpack_data(frameData)
                    target_list = self.decoder.decode(frameData)
                    if target_list != None:
                        # print(target_list)
                        if self.radar_data_handler is not None:
                            self.radar_data_handler(target_list)
                        self.latest_data_stamp = time.time()
                # dataBuffer更新
                if frameLength > 0:
                    dataBuffer = dataBuffer[frameIndex + frameLength:]

    def start(self):
        # 运行数据接收线程
        self.thread = threading.Thread(target=self._run_receive, daemon=True,name= "x4")
        self.thread.start()
        print(datetime.datetime.now(), f"{self.class_name} thread start,port={self.local_port}")

    def get_out_ip(self, connect_ip='8.8.8.8', ip_change_callback=None):
        try:
            ip= self.get_out_ip_by_ifconfig()
            if ip is None:
                ip = self.get_out_ip_by_connection(connect_ip)
            if self.out_ip != ip and ip is not None:
                print(f"{self.class_name} connect_ip={connect_ip} get_out_ip={ip}")
                self.out_ip=ip
                # self.remote_port = int(ip.split(".")[-1]) + 18000
                print(f"{self.class_name} remote_ip_port={self.remote_ip}:{self.remote_port}")
                self.get_subnet255_ip(self.out_ip)
                print(f"{self.class_name} remote_ip_subnet255={self.remote_ip_subnet255}:{self.remote_port}")
                if ip_change_callback is not None:
                    ip_change_callback()
            return ip
        except:
            return None

    def get_subnet255_ip(self, local_ip_string: str = "192.168.8.200"):
        # 根据local_ip_string生成子网广播地址，例如"192.168.8.200">>>"192.168.8.255"
        sub_list=local_ip_string.split(".")
        sub_list[-1]="255"
        remote_ip_subnet255=".".join(sub_list)
        self.remote_ip_subnet255 = remote_ip_subnet255

    def get_out_ip_by_connection(self, connect_ip='8.8.8.8'):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((connect_ip, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def is_ip_string(self, string="192.168.8.aa"):
        # 匹配 0.0.0.0-255.255.255.255的表达式书写方法
        pattern = re.compile(r'(([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.){3}([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])')
        result = re.match(pattern, string)
        if result is None:
            return False
        elif len(result.string) > 0:
            return True
        else:
            return False

    def get_out_ip_by_ifconfig(self, ):
        if "Windows" not in platform.platform():
            cmd = "ifconfig|grep inet |grep -v inet6 |grep -v 127.0.0.1|grep -v 192.168.8.200"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            time.sleep(0.3)
            text_line_list = p.stdout.readlines()
            #  inet 10.8.2.143  netmask 255.255.255.0  broadcast 10.8.2.255
            # print(f"get_out_ip_by_ifconfig text_line_list={text_line_list}")
            for index in range(len(text_line_list)):
                text_raw = str(text_line_list[index], encoding='utf-8')
                text = re.split('[ :]', string=text_raw)
                text = [x.strip() for x in text if ('255' not in x and len(x) >= 7)]
                ip_list = [x.strip() for x in text if self.is_ip_string(x)]
                # print(f"get_out_ip_by_ifconfig text={text}")
                if len(ip_list) > 0:
                    break
            p.kill()
            if len(ip_list) > 0:
                if self.out_ip != ip_list[0]:
                    print(f"get_out_ip_ifconfig ip_list={ip_list},self.out_ip={self.out_ip}")
                return ip_list[0]
            else:
                return None
        else:
            return None


def test_for_udp_send255(remote_ip_list=["255.255.255.255"]):
    for index in range(60 * 20):
        for remote_ip in remote_ip_list:
            udp_sender = DebugUDPSender(18000, remote_ip=remote_ip)
            udp_sender.udp_send(f">>>>>>{remote_ip},{index}")
            udp_sender.udp_close()
        time.sleep(1)


def test_diff_connectIP():
    remote_ip_list = ["10.8.4.186", "10.8.2.186", "10.8.4.255", "255.255.255.255", "192.168.1.255", ]
    for remote_ip in remote_ip_list[3:4]:
        udp_sender = DebugUDPSender(18000, remote_ip=remote_ip)
        udp_sender.udp_send(f">>>>>>{remote_ip}>>>>>>test1")
        udp_sender.get_out_ip(connect_ip='8.8.8.8')
        # udp_sender.get_local_ip()
        udp_sender.udp_send(f">>>>>>{remote_ip}>>>>>>test2")
        udp_sender.udp_close()
        time.sleep(1)


if __name__=="__main__":
    # test_diff_connectIP()

    test_for_udp_send255(["255.255.255.255", "192.168.8.224", "192.168.8.255"])
