import cv2 as cv
import numpy as np
import pickle
import socket
import struct
import threading
import time
import traceback
import json
import matplotlib.pyplot as plt
import numpy as np
from xypTool.common import xypFileTool
from scipy.optimize import curve_fit
from xypTool.common import xypRemoteTool

pushImageCode= lambda rstp:f'''
import cv2 as cv
import pickle
import socket
import struct
import threading
import time
import traceback


class PushStream():
    def __init__(self,ip='0.0.0.0',port=8091,mode=0):
        # 创建Socket连接
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 取消端口关闭后的等待期,重启程序就不会出现端口被占用的情况
        self.serverSocket.bind((ip, port))
        self.serverSocket.listen(10)
        self.client = {{}}
        self.task=[]
        self.mode=mode # 0传输图片，用cv.imencode快，1几乎为万能模式，但慢
        threading.Thread(target=self.clientHandle).start()
        threading.Thread(target=self.push).start()
        print(f"PushStream {{ip}} {{port}} init done")


    def clientHandle(self):
        while True:
            # 接受客户端连接
            clientConnection, clientAddress = self.serverSocket.accept()
            print(f"new client {{clientAddress}}")
            self.client[clientAddress]=clientConnection

    def push(self,):
        lastClientTime= time.time()
        lastTaskTime = time.time()
        while True:
            try:
                nowTime =time.time()
                if len(self.client):
                    lastClientTime = time.time()
                    if len(self.task):
                        lastTaskTime = time.time()
                        self.task=self.task[-1:]
                        data = self.task.pop(0)
                        if self.mode==0:
                            ret, data = cv.imencode('.jpg', data)
                        else:
                            data = pickle.dumps(data)
                        for address,connection in self.client.items():
                            connection.sendall(struct.pack("<L", len(data)))
                            # 发送数据
                            connection.sendall(data)
                    else:
                        if nowTime - lastTaskTime >2:
                            print("push no task")
                            time.sleep(0.5)
                else:
                    if nowTime - lastClientTime > 2:
                        print("push no client")
                        self.task = []
                        time.sleep(1)
            except socket.error:
                print(f"Client {{address}} has disconnected.")
                self.client.pop(address)
                connection.close()
            except:
                print(f"push error {{ traceback.format_exc()}}")
               

def sendVideo():
    p = PushStream(ip='0.0.0.0', port=8091, mode=0)
    cap = cv.VideoCapture("{rstp}")
    while True:
        try:
            ret, frame = cap.read()
            frame = cv.resize(frame, (1920 // 3, 1080 // 3))
            p.task.append(frame)
        except:
            print(f"sendVideo error {{traceback.format_exc()}}")
if __name__ =="__main__":
    sendVideo()
'''


class xypCalib():
    def __init__(self,vanish=1,vanishArea=0):
        self.ssh = xypRemoteTool.SSH('58.20.230.32', "10080", "tvt", "TDDPc5kc4WnYcy", 3)

        camId =1
        if camId==0:
            rstp = "rtsp://admin:Admin123@192.168.8.12:8554/0"
        else:
            rstp = "rtsp://admin:Admin123@192.168.8.11:8554/0"
        self.killRemoteRunPythonCode = self.ssh.remoteRunPythonCode(pushImageCode(rstp))

        #sq
        time.sleep(3)
        if vanishArea: # 指定灭点适配区域
            self.pullStream = PullStream(ip='0.0.0.0', port=8091)
            SplitArea(camId,self.pullStream)

        if vanish:
            self.pullStream = PullStream(ip='0.0.0.0', port=8091)
            CalibVanish(camId, 2, self.pullStream)






class CalibVanish():
    def __init__(self, camId, h, pullImage):
        """
        初始化消失点标定类
        
        参数:
        camId (int): 相机ID
        h (float): 设备安装高度
        pullImage (object): 图像获取对象，需包含data属性存储图像数据
        """
        self.h = h  # 设备安装高度
        self.camId = camId
        self.pullImage = pullImage
        self.calibData = {}  # 存储标定数据：区域类型 -> [(图像Y坐标, 雷达Y坐标)]
        self.nowPoint = []  # 当前选中的像素点坐标
        
        # 加载区域掩码配置文件
        with open(f"./config/vanishMask{camId}.json", "rt") as file:
            self.areaDict = json.load(file)
        
        # 开始标定过程
        self.calibVanish()

    def updateImage(self):
        """更新显示图像，叠加掩码区域和当前选中点"""
        # 调整图像大小为800x450
        img = cv.resize(self.pullImage.data, (800, 450))
        
        # 创建透明掩码，用于显示标定区域
        vanishMask = np.zeros_like(img)
        for areaType, areaInfo in self.areaDict.items():
            for area in areaInfo["area"]:
                # 填充多边形区域
                vanishMask = cv.fillPoly(vanishMask, [np.array(area)], [255, 255, 255])
                # 在区域中心添加类型标签
                vanishMask = cv.putText(vanishMask, str(areaType), 
                                       np.mean(area, axis=0).astype(np.int64), 
                                       cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv.LINE_AA)
        
        # 将掩码与原图叠加，透明度各50%
        img = cv.addWeighted(img, 0.5, vanishMask, 0.5, 0.0)
        
        # 如果有选中点，在图像上标记
        if len(self.nowPoint):
            img = cv.circle(img, self.nowPoint, 3, (0, 0, 255), -1)
        
        # 显示图像并等待1ms
        cv.imshow('calibVanish', img)
        cv.waitKey(1)

    def calibVanish(self):
        """执行消失点标定主循环"""
        # 创建窗口并设置为置顶
        cv.namedWindow('calibVanish')
        cv.setWindowProperty("calibVanish", cv.WND_PROP_TOPMOST, 1)
        
        # 设置鼠标回调函数
        cv.setMouseCallback('calibVanish', self.mouseCallback)
        
        # 主循环：持续更新图像，按ESC键退出
        while True:
            try:
                self.updateImage()
                if cv.waitKey(1) == 27:  # 按ESC键退出
                    break
            except:
                print(f"split error {traceback.format_exc()}")

    def mouseCallback(self, event, x, y, flags, param):
        """鼠标事件回调函数，处理不同鼠标操作"""
        if event == cv.EVENT_LBUTTONDOWN:
            # 左键点击：记录当前点并更新图像
            self.nowPoint = [x, y]
            self.updateImage()
            print(f"左键点击坐标为: ({x}, {y})")
            
        elif event == cv.EVENT_RBUTTONDOWN:
            # 右键点击：清除当前点并更新图像
            self.nowPoint = []
            self.updateImage()
            
        elif event == cv.EVENT_MBUTTONDOWN:
            # 中键点击：添加标定数据点
            if not self.nowPoint:
                print("请先左键选择一个点!")
                return
                
            # 输入区域类型和雷达Y坐标
            areaType = int(input(f"请输入区域类型（可选: {list(self.areaDict.keys())}）: "))
            radarY = float(input("请输入对应的雷达Y坐标: "))
            
            # 保存标定数据：区域类型 -> [(图像Y坐标, 雷达Y坐标)]
            if areaType not in self.calibData:
                self.calibData[areaType] = [[self.nowPoint[1], radarY]]
            else:
                self.calibData[areaType].append([self.nowPoint[1], radarY])
            print(f"已添加标定数据: {self.calibData}")
            
        elif event == cv.EVENT_LBUTTONDBLCLK:
            # 左键双击：执行消失点计算和参数拟合
            # 使用预设标定数据（可注释掉，使用手动标定数据）
            # self.calibData = {1: [[384, 55.0], [328, 65.0], [308, 80.0], [294, 93.0], [244, 143.0]]}
            
            best = {}  # 存储最优参数
            
            # 遍历每个区域类型，寻找最优消失点参数
            for areaType, areaData in self.calibData.items():
                minDiff = np.inf  # 初始化最小误差为无穷大
                
                # 遍历所有可能的消失点Y坐标（垂直方向）
                for vpY in range(450):
                    # 遍历不同的视角变化率（0到π/4弧度范围内）
                    for per in np.arange(0, np.pi/4, 0.01*np.pi/4):
                        per = per/450  # 归一化视角变化率
                        diff = 0  # 初始化误差和
                        
                        # 计算当前参数下的误差
                        for data in areaData:
                            objY, radarY = data
                            # 计算射线与杆的夹角（基于消失点和视角变化率）
                            angle = 0.5 * np.pi - per * (objY - vpY)
                            # 计算对应的雷达Y坐标（基于安装高度和夹角）
                            y = self.h * np.tan(angle)
                            # 累加误差（预测值与实际值的绝对差）
                            diff += abs(radarY - y)
                            
                        # 如果当前误差更小，更新最优参数
                        if diff < minDiff:
                            minDiff = diff
                            best[areaType] = {"vpY": vpY, "per": per}
                
                # 使用非线性最小二乘法拟合参数 a 和 b
                x = [d[1] for d in areaData]  # 雷达Y坐标
                y = [d[0] for d in areaData]  # 图像Y坐标
                a, b = self.lambdaFitFunc(x, y)
                best[areaType]["a"] = a
                best[areaType]["b"] = b
            
            # 打印最优参数和标定数据
            print(f"最优参数: {best}")
            print(f"标定数据: {self.calibData}")
            
            # 更新区域配置字典并保存到文件
            for k, v in best.items():
                self.areaDict[str(k)].update(v)
            with open(f"./config/vanishMask{self.camId}.json", "wt") as file:
                json.dump(self.areaDict, file)
                print(f"参数已保存到: ./config/vanishMask{self.camId}.json")

    def fitFunc(self, x, a, b):
        """拟合函数：y = a/x + b，用于建立图像坐标与雷达坐标的关系"""
        return a / x + b

    def lambdaFitFunc(self, x, y):
        """使用scipy.optimize.curve_fit进行参数拟合"""
        try:
            args, _ = curve_fit(self.fitFunc, x, y)
            a, b = args
            if a <= 0:  # 参数a必须为正，否则返回None
                return None, None
            else:
                return a, b
        except:
            return None, None


# 创建Socket连接
class PullStream():
    # def __init__(self,ip='10.8.2.14',port=8091):
    def __init__(self,ip='58.20.230.32',port=8091):
        # 创建Socket连接
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.connect((ip, port))
        self.ip, self.port=ip,port
        self.data=None
        print(f"PullStream {ip} {port} init done")
        threading.Thread(target=self.pull).start()
        while self.data is None:
            time.sleep(0.1)


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
                    data = cv.imdecode(np.frombuffer(data, np.uint8), cv.IMREAD_COLOR)
                    self.data=data
                    # if cv.waitKey(1) == 27:
                    #     cv.destroyWindow("img")
                    #     break
                else:
                    if nowTime - lastRecvTime>5:
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

class SplitArea():
    def __init__(self,camId, pullImage):
        self.areaList = []
        self.camId= camId
        self.area = []
        self.pullImage=pullImage
        self.areaMask = None
        self.split()
    def split(self):
        cv.namedWindow('splitArea',cv.WND_PROP_FULLSCREEN)
        cv.setWindowProperty("splitArea", cv.WND_PROP_TOPMOST, 1)
        cv.setMouseCallback('splitArea', self.drawPoint)
        while True:
            try:
                self.updateImage()
                if  cv.waitKey(1) == 27:  # Press 'Esc' to exit
                    break
            except:
                print(f"split error {traceback.format_exc()}")
                time.sleep(1)

        isSave = int(input("is save ? (0 :save, 1: try again, other: close):"))
        if isSave ==0:
            cv.imwrite(f"./config/vanishMask{self.camId}.jpg",self.areaMask)
            with open(f"./config/vanishMask{self.camId}.json", "wt") as file:
                self.areaDict = {}
                for areaInfo in self.areaList:
                    areaType, area = areaInfo
                    if areaType not in self.areaDict:
                        self.areaDict[areaType]= {"area":[area]}
                    else:
                        self.areaDict[areaType]["area"].append(area)
                json.dump(self.areaDict, file)
            print(f"./config/vanishMask{self.camId}.png save done")
            cv.destroyWindow("splitArea")
        elif isSave==1:
            cv.destroyWindow("splitArea")
            self.areaList = []
            self.area = []
            self.split()
        else:
            cv.destroyWindow("splitArea")

    def drawPoint(self,event, x, y, flags, param):
        if event == cv.EVENT_LBUTTONDOWN:
            n=15
            exist = [[0,0],[799,0],[799,449],[0,449]]
            for i in self.areaList:
                exist = exist+i[1]
            exist=exist+self.area
            diffPos = np.linalg.norm(np.array((x, y))-np.array(exist),axis=1)
            if min(diffPos)<15:
                x,y  = exist[np.argmin(diffPos)]
            if abs(x - 0) < n:
                x = 0
            if abs(x - 799) < n:
                x = 799
            if abs(y - 0) < n:
                y = 0
            if abs(y - 449) < n:
                y = 449
            print("click pos x y:",x,y)
            self.area.append((x, y))
            self.updateImage()
        elif event == cv.EVENT_RBUTTONDOWN: # Right mouse button clicked
            if len(self.area):
                self.area.pop()
                self.updateImage()
            else:
                if len(self.areaList):
                    self.areaList.pop()
                    self.updateImage()
        elif event == cv.EVENT_MBUTTONDOWN: # Right mouse button clicked
            if self.area:
                areaType= int(input("input area type (is int and not 0):"))
                self.areaList.append((areaType,self.area))
                self.area=[]
                self.updateImage()
    # Function to update image with circles
    def updateImage(self):
        img = cv.resize(self.pullImage.data, (800, 450))
        for point in self.area:
            cv.circle(img, point, 3, (0, 0, 255), -1)

        mask = np.zeros_like(img)
        for areaInfo in self.areaList:
            areaType,area=areaInfo
            mask = cv.fillPoly(mask, [np.array(area)], [areaType, areaType, areaType])
        self.areaMask = mask
        # 用于显示
        mask = np.zeros_like(img)
        for areaInfo in self.areaList:
            areaType, area = areaInfo
            mask = cv.fillPoly(mask, [np.array(area)], [255, 255, 255])
            mask = cv.putText(mask, str(areaType), np.mean(area, axis=0).astype(np.int64), cv.FONT_HERSHEY_SIMPLEX, 1,
                              (0, 255, 0), 2, cv.LINE_AA)
        result = cv.addWeighted(img, 0.5, mask, 0.5, 0.0)
        img[mask!=0]=result[mask!=0]
        cv.imshow('splitArea', img)
        cv.waitKey(1)



if __name__ == "__main__":
    a=xypCalib()
    # time.sleep(2)
    # a.killRemoteRunPythonCode()
    # s = SplitArea(1, PullStream(ip='0.0.0.0', port=8091))