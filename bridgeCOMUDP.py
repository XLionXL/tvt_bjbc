# coding:utf-8
import argparse
import datetime
import os
import platform
import serial
import socket
import threading
import time


class BridgeCOMUDP:
    def __init__(self, comPort="/dev/ttyTHS2", local_UDP_port=("10.8.4.30", 8888), remoteUDP=("10.8.4.108", 18888)):
        self.className = "BridgeCOMUDP"
        self.portName = comPort
        self.timeout_s = 60
        self.latest_data_stamp = time.time()
        self.local_UDP_port = local_UDP_port
        self.remoteUDP = remoteUDP
        self.udpPort_isOpen = False
        self.sudo_password="TDDPc5kc4WnYcy"
        self.serial_open()
        self.udp_open()

    def udp_open(self, ):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.bind(('', self.local_UDP_port))
            self.udp_socket.settimeout(0.01)
            self.udpPort_isOpen = True
            self.latest_data_stamp = time.time()
        except Exception as e:
            self.udpPort_isOpen = False

    def udp_send(self, data_bytes):
        self.udp_socket.sendto(data_bytes, self.remoteUDP)

    def serial_open(self):
        if "Windows" not in platform.platform():
            os.system(f"echo '{self.sudo_password}' | sudo -S chmod 777 {self.portName}")
        try:
            self.serial_radar = serial.Serial(
                port=self.portName,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout_s,
            )
            # 判断是否打开成功
            if (self.serial_radar.is_open):
                self.serial_isOpen = True
                self.latest_data_stamp = time.time()
        except Exception as e:
            self.serial_isOpen = False

    def serial_send(self, data):
        self.serial_radar.write(data)

    def bridge_task(self):
        while True:
            try:
                if self.serial_radar.in_waiting > 0:
                    data_bytes_from_serial = self.serial_radar.read_all()
                    if len(data_bytes_from_serial) > 0:
                        self.udp_send(data_bytes_from_serial)
                data_bytes_from_udp, ip = self.udp_socket.recvfrom(1404)
                if len(data_bytes_from_udp) > 0:
                    self.serial_send(data_bytes_from_udp)
            except socket.timeout as e:
                continue
            except:
                print(f"{self.className},error={e}", )
            time.sleep(0.002)

    def thread_start(self, is_daemon=True):
        # 运行数据接收线程
        self.thread_bridge = threading.Thread(target=self.bridge_task, daemon=is_daemon,name="thread_start")
        self.thread_bridge.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bridgeCOM_UDP")
    parser.add_argument('-c', '--com', type=str, default="/dev/ttyTHS2", help="bridge source com ,default=/dev/ttyTHS2")
    parser.add_argument('-i', '--des_ip', type=str, default="192.168.1.197", help="bridge des udp ip ,default=192.168.1.197")
    parser.add_argument('-p', '--des_port', type=int, default=15000, help="bridge des udp port ,default=15000")
    args = parser.parse_args()
    if "Windows" in platform.platform():
        test_bridge = BridgeCOMUDP("COM2", local_UDP_port=20000, remoteUDP=(args.des_ip, args.des_port))
        test_bridge.thread_start(False)
    else:
        test_bridge = BridgeCOMUDP("/dev/ttyTHS1", local_UDP_port=20000, remoteUDP=(args.des_ip, args.des_port))
        test_bridge2 = BridgeCOMUDP("/dev/ttyTHS2", local_UDP_port=20000, remoteUDP=(args.des_ip, args.des_port + 1))
        test_bridge.thread_start(False)
        test_bridge2.thread_start(False)
