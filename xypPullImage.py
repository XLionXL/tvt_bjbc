import cv2 as cv
import numpy as np
import pickle
import socket
import struct
import threading
import time
import traceback


# 创建Socket连接
class PullStream():
    def __init__(self,ip='10.8.2.14',port=8091,mode=0):
        # 创建Socket连接
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.connect((ip, port))
        self.ip, self.port=ip,port
        self.mode=mode # 0传输图片，用cv.imencode快，1几乎为万能模式，但慢
        self.data=None
        threading.Thread(target=self.pull).start()
        print(f"PullStream {ip} {port} init done")
    def pull(self):
        # 接收图像并显示
        lastRecvTime = time.time()
        while True:
            try:
                nowTime = time.time()
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
                    if  self.mode==0:
                        data=cv.imdecode(np.frombuffer(data, np.uint8), cv.IMREAD_COLOR)
                    else:
                        data=pickle.loads(data)
                    self.data=data
                    if self.port==8091:
                        self.imageHandle(data)
                    else:
                        self.imageHandle2(data)

                else:
                    if nowTime - lastRecvTime>3:
                        raise socket.error
                    elif nowTime - lastRecvTime>2:
                        time.sleep(0.1)
            except socket.error: # 可能是服务器死掉了
                try:
                    self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.serverSocket.connect((self.ip,self.port))
                    print(f"pull socket.error {traceback.format_exc()}")
                except:
                    time.sleep(1)
            except:
                print(f"pull error {traceback.format_exc()}")
                time.sleep(1)

    def imageHandle(self,data):
        self.image=data
        cv.namedWindow("img", cv.WINDOW_NORMAL)
        cv.setWindowProperty("img", cv.WND_PROP_TOPMOST, 1)
        cv.imshow('img', data)
        cv.waitKey(1)
    def getImage(self):
        img = self.data
        return img



    def imageHandle2(self, data):
        self.image = data
        if not hasattr(self, 'xxx'):
            self.xxx=[]
            cv.namedWindow("img", cv.WINDOW_NORMAL)
            cv.setWindowProperty("img", cv.WND_PROP_TOPMOST, 1)

            cv.setMouseCallback('img', self.mouse_callback)
        data =cv.resize(data,(800,450))

        cv.imwrite('./config/c0.jpg', data)
        cv.imshow('img', data)
        cv.waitKey(1)
    def mouse_callback(self,event, x, y, flags, param):
        if event == cv.EVENT_LBUTTONDOWN:
            print("左键点击坐标为: ({}, {})".format(x, y))

        if event == cv.EVENT_RBUTTONDOWN:
            s = float(input("input:"))
            self.xxx.append([x, y,s])
            print(self.xxx)

        if event == cv.EVENT_MBUTTONDOWN:
            minS = 9999999
            best =[]
            # self.xxx=[[404, 375, 12.7], [401, 274, 28.7], [613, 348, 44.7]]
            # self.xxx=[[454, 272, 219.1], [437, 283, 187.2], [455, 307, 141.9], [462, 340, 101.6], [418, 389, 73.2]]
            # self.xxx=[[414, 425, 70.4], [439, 379, 99.4], [476, 341, 148.7], [349, 318, 200.0]]
            # self.xxx=[[381, 412, 22.3], [394, 371, 27.1], [382, 342, 33.9], [392, 321, 40.1], [392, 307, 47.3], [392, 297, 52.7],
            #  [391, 289, 59.1], [391, 281, 65.5]]
            # self.xxx=[[335, 445, 83.1], [351, 426, 88.7], [346, 410, 94.3],[313,385,105.5],[319, 373, 113.5], [321, 361, 119.9], [327, 352, 124.7], [330, 337, 137.4], [332, 324, 148.7], [335, 312, 163.1], [337, 297, 175.9], [327, 291, 187.1], [334, 283, 203.1]]
            # self.xxx=[[339, 193, 200.0], [348, 202, 179.0],[352, 231, 150.3], [349, 230, 121.4], [349, 266, 100.7], [369, 306, 75.1], [360, 426, 65.5]]
            self.xxx = [
                [401, 380, 24.0], [390, 318, 36.8], [391, 281, 51.1]]
            for vp in range(450):
                for per in np.arange(0,np.pi/4,0.01*np.pi/4):
                    per=per/450
                    s = 0
                    h = 3.85
                    resolution = (800,450)
                    for p in self.xxx:
                        obj = np.array(p[:2])
                        dddd = p[-1]
                        cvtObjs = []
                        if len(obj) == 2:
                            objX, objY = obj
                        else:
                            objX, objY = obj[0] + obj[2] / 2, obj[1] + obj[3]
                        vpY = vp
                        angle = 0.5 * np.pi - per * (objY - vpY)  # 射线与杆的夹角
                        temp = np.tan(angle)
                        y = h * temp  # 雷达上的y，注意不是射线的长
                        # 目前假设：图像垂直中线约为雷达零点，垂直与水平每像数视场角近似相同
                        angle = per * (objX - resolution[0] / 2)  # 射线与杆的夹角
                        x = y * np.tan(angle)  # 得用y计算，不同的距离夹角一样但y不同
                        cvtObjs.append((x, y))
                        s+=abs(dddd-y)
                    if s < minS:
                        minS = s
                        best = [vp,per]
            print(best)
            print("sss")
            print(self.xxx)


if __name__ == "__main__":
    # PullStream(ip='10.8.2.14', port=8091, mode=0)
    PullStream(ip='58.20.230.32', port=8093, mode=0)
    # PullStream(ip='192.168.90.41', port=8092, mode=0)
    # PullStream(ip='121.62.22.121', port=47350, mode=0)
# [[335, 445, 83.1], [351, 426, 88.7], [346, 410, 94.3]]
# 左键点击坐标为: (356, 385)
# input:105.5[[339, 193, 200.0], [348, 202, 179.0],[352, 231, 150.3], [349, 230, 121.4], [349, 266, 100.7], [369, 306, 75.1], [360, 426, 65.5]]