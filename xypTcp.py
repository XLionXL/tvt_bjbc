import cv2 as cv
import numpy as np
import time
import pickle
import socket
import struct
import threading
import datetime
import traceback


# 创建Socket连接
class Client():
    def __init__(self,ip='0.0.0.0',port=8094):
        self.task = []
        self.recv = []
        self.ip, self.port=ip,port
        self.connect()
        print(f"Client {ip} {port} init done")
        threading.Thread(target=self.pull).start()
        threading.Thread(target=self.send).start()
    def connect(self):
        # 创建Socket连接
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSocket.connect((self.ip, self.port))
        except Exception as e:
            print(f"{datetime.datetime.now()} exception:{e}\ntraceback:{traceback.format_exc()}")
            time.sleep(1)
    def dataTaskFunc(self,data):
        data =  pickle.dumps(data)
        self.serverSocket.sendall(struct.pack("<L", len(data)))  # 发送数据长度
        self.serverSocket.sendall(data)  # 发送数据
    def dataRecvFunc(self,data):
        data =pickle.loads(data)
        print(data)
        # self.recv.append(data)

    def send(self, ):
        lastSendTime = time.monotonic()
        while True:
            try:
                self.task = self.task[-100:]
                if len(self.task):
                    lastSendTime = time.monotonic()
                    data = self.task.pop(0)
                    self.dataTaskFunc(data)
                else:
                    time.sleep(0.5)
                if time.monotonic() - lastSendTime>5:
                    self.task.append("live")
            except Exception as e:
                print(f"{datetime.datetime.now()} exception:{e}\ntraceback:{traceback.format_exc()}")
                time.sleep(1)
    def pull(self):
        # 接收图像并显示
        lastRecvTime = time.monotonic()
        while True:
            try:
                nowTime = time.monotonic()
                lenInfo = self.serverSocket.recv(struct.calcsize("<L"))
                if lenInfo:
                    lastRecvTime =nowTime
                    # 接收图像数据的长度
                    dataLen = struct.unpack("<L",lenInfo)[0]
                    # 接收图像数据
                    data = b""
                    while len(data) < dataLen:
                        pkg = self.serverSocket.recv(dataLen - len(data))
                        if not pkg:
                            break
                        data += pkg
                    self.dataRecvFunc(data)


                else:
                    if nowTime - lastRecvTime>3:
                        raise socket.error
                    elif nowTime - lastRecvTime>2:
                        time.sleep(0.1)
            except socket.error: # 可能是服务器死掉了
                self.connect()
            except Exception as e:
                print(f"{datetime.datetime.now()} exception:{e}\ntraceback:{traceback.format_exc()}")
                time.sleep(1)




class Server():
    def __init__(self,ip='0.0.0.0',port=8091):
        # 创建Socket连接
        self.task = []
        self.recv = []
        self.client = {}
        self.ip, self.port = ip, port
        self.createServer()
        print(f"Server {ip} {port} init done")
        threading.Thread(target=self.clientHandle).start()
        threading.Thread(target=self.push).start()
    def dataTaskFunc(self,data):
        data=  pickle.dumps(data)
        for address, connection in self.client.items():  # 群发
            connection.sendall(struct.pack("<L", len(data)))  # 发送数据长度
            connection.sendall(data)  # 发送数据
    def dataRecvFunc(self,data):
        data=pickle.loads(data)
        if data != "live":  # 心跳
            print(f"{datetime.datetime.now()} Server {self.ip}:{self.port} recv {data}")
            self.recv.append(data)

    def createServer(self):
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 取消端口关闭后的等待期,重启程序就不会出现端口被占用的情况
            self.serverSocket.bind((self.ip, self.port))
            self.serverSocket.listen(10)
        except Exception as e:
            print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
            time.sleep(1)
    def clientHandle(self):
        while True:
            # 接受客户端连接
            clientConnection, clientAddress = self.serverSocket.accept()
            clientConnection.settimeout(10) # 10s没收到消息就关掉客户端
            print(f"{datetime.datetime.now()} new client {clientAddress}")
            self.client[clientAddress] = clientConnection
            threading.Thread(target=self.clientListen,args=(clientConnection,clientAddress)).start()

    def clientListen(self,client,address):
        try:
            while True:
                lenInfo = client.recv(struct.calcsize("<L"))
                if lenInfo:
                    # 接收图像数据的长度
                    dataLen = struct.unpack("<L", lenInfo)[0]
                    # 接收图像数据
                    data = b""
                    while len(data) < dataLen:
                        pkg = client.recv(dataLen - len(data))
                        if not pkg:
                            break
                        data += pkg
                    self.dataRecvFunc(data)

        except Exception as e:
            self.client.pop(address)
            print(f"{datetime.datetime.now()} exception:{e}\ntraceback:{traceback.format_exc()}")
            time.sleep(1)


    def push(self,):
        while True:
            try:
                self.task=self.task[-100:]
                if len(self.client):
                    if len(self.task):
                        data = self.task.pop(0)
                        self.dataTaskFunc(data)
                    else:
                        time.sleep(0.5)
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"{datetime.datetime.now()} exception:{e}\ntraceback:{traceback.format_exc()}")
                time.sleep(1)
if __name__ == "__main__":
    s=Server(ip='0.0.0.0',     port=8095)
    c=Client(ip='192.168.1.39',    port=8095)
    while 1:
        # c.task.append(1)
        time.sleep(1.1)
    #
    # time.sleep(555)

    # c = Client(ip='10.29.3.32', port=8095)
    # c.task.append(('2024-06-04 13:53:45', '2024-06-04 13:54:20'))

    # Client(ip='10.8.2.14', port=8091, mode=0)
    # Client(ip='10.29.3.32', port=8093, mode=0)
    # Client(ip='192.168.90.41', port=8092, mode=0)
    # Client(ip='121.62.22.121', port=47350, mode=0)
# [[335, 445, 83.1], [351, 426, 88.7], [346, 410, 94.3]]
# 左键点击坐标为: (356, 385)
# input:105.5[[339, 193, 200.0], [348, 202, 179.0],[352, 231, 150.3], [349, 230, 121.4], [349, 266, 100.7], [369, 306, 75.1], [360, 426, 65.5]]