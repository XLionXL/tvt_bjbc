import sys
import time
import datetime
import traceback
import numpy as np
import threading
import copy

from xypTcp import Server
class VirtualInput():
    def __init__(self,path=r"/ssd/xyp/2024-05-24 16-21.log",handleRadarData=None,handleCameraData=None):
        self.server = Server(ip='0.0.0.0', port=8095)
        self.path = path
        self.nowTime = time.time()
        self.handleRadarData=handleRadarData
        self.handleCameraData =handleCameraData
        self.flash = False
        self.timeZone=None
        threading.Thread(target=self.serverListen).start()
        threading.Thread(target=self.dataInit).start()
    def serverListen(self):
        while True:
            if len(self.server.recv):
                self.timeZone =self.server.recv.pop(0)# ('2024-05-27 21:09:14', '2024-05-28 21:09:14')
                self.flash=True
            time.sleep(1)

    def dataInit(self):
        while True:
            print(self.timeZone)
            self.radarData, self.cameraData = self.createData()
            # time.sleep(213123)
            # timeZone = ('2024-05-24 16:32:27', '2024-05-24 16:32:54')
            # if isinstance( self.path, list):
            #     self.radarData, self.cameraData=[],[]
            #     for path in self.path:
            #         radarData,   cameraData= self.analyseXypLog(path,  self.timeZone)
            #         self.radarData.extend(radarData)
            #         self.cameraData.extend(cameraData)
            #
            # else:
            #     self.radarData,self.cameraData = self.analyseXypLog(   self.path, self.timeZone)
            # 数据起始时间
            if len(self.radarData) and len(self.cameraData):
                radarDataStartTime = self.radarData[0][0]
                cameraDataStartTime = self.cameraData[0][0]
                # 用于同步雷达和框的时间
                if radarDataStartTime > cameraDataStartTime:
                    self.radarDataWaitTime = radarDataStartTime - cameraDataStartTime
                    self.cameraDataWaitTime = 0
                else:
                    self.radarDataWaitTime = 0
                    self.cameraDataWaitTime = cameraDataStartTime - radarDataStartTime

                a=threading.Thread(target=self.pushRadarData)
                b=threading.Thread(target=self.pushCameraData)
                a.start()
                b.start()
                a.join()
                b.join()
                self.flash = False


    def pushCameraData(self):
        time.sleep(self.cameraDataWaitTime)
        dataStartTime = self.cameraData[0][0]  # 数据起始时间
        startNowTime = time.time()  # 当前真实起始时间
        for data in self.cameraData:

            dataTime, objs = data
            # 当前帧过去的时间 dataTime - timeStamp[0]
            # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
            waitTime = dataTime - dataStartTime  # 需要等待的时常
            while True:
                if self.flash:
                    break
                pastTime = time.time() - startNowTime
                if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
                    # [{'id': 1, 'timestamp': 0.5, 'data': [{'confidence': 0.721973121, 'class': 0, 'bbox': [501, 253, 22, 42]}, {'confidence': 0.768391371, 'class': 0, 'bbox': [501, 253, 22, 42]}]}]
                    # [{'id': 1, 'timestamp': 0.5, 'data': [{'confidence': 0.768391371, 'class': 0, 'bbox': [501, 253, 22, 42]}, {'confidence': 0.768391371, 'class': 0, 'bbox': [501, 253, 22, 42]}]}]
                    self.handleCameraData(objs, time.time())
                    break
                else:
                    time.sleep(0.2 * (waitTime - pastTime))
            if self.flash:
                break
    def pushRadarData(self,):
        time.sleep(self.radarDataWaitTime)
        dataStartTime = self.radarData[0][0]  # 数据起始时间
        startNowTime = time.time()  # 当前真实起始时间
        self.nowTime=datetime.datetime.fromtimestamp(dataStartTime)
        for data in self.radarData:
            dataTime, objs = data
            # 当前帧过去的时间 dataTime - timeStamp[0]
            # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
            waitTime = dataTime - dataStartTime  # 需要等待的时常
            while True:
                if self.flash:
                    break
                pastTime = time.time() - startNowTime
                if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
                    self.nowTime =datetime.datetime.fromtimestamp(dataTime)
                    self.handleRadarData(objs, time.time())
                    break
                else:
                    time.sleep(0.2*(waitTime-pastTime))
            if self.flash:
                break
    def analyseXypLog(self,path, timeZone=None):
        # 解析日志内容
        '''
        :param path: 日志位置
        :return:返回数据格式为[[timeStamp0,[obj0,obj1...]],...]
        '''
        with open(path, "r",encoding='utf-8') as f:
            radarData = []
            radarStr = "radar data&"
            cameraData = []
            cameraStr= "camera data&"
            if timeZone is not None:
                t0 = datetime.datetime.strptime(timeZone[0], "%Y-%m-%d %H:%M:%S").timestamp()
                t1 = datetime.datetime.strptime(timeZone[1], "%Y-%m-%d %H:%M:%S").timestamp()
            while 1:
                line = f.readline()
                if line == "" or (not line.endswith("\n")):  # \n是为了确定是完整的日志行
                    break
                if "- DEBUG: " in line:
                    frameTime ,info = line.split(" - DEBUG: ")
                    frameTime = datetime.datetime.strptime(frameTime, "%Y-%m-%d %H:%M:%S,%f").timestamp() # 时间戳
                    if timeZone is not None and  (not (t0<frameTime < t1)):
                        continue
                    elif info.startswith(radarStr):
                        info = eval((info.strip()[len(radarStr):]))
                        radarData.append([frameTime, info])

                    elif info.startswith(cameraStr):
                        info = eval((info.strip()[len(cameraStr):]))
                        cameraData.append([frameTime, info])
            return radarData,cameraData

    def estimateImageToRadar(self,points, ):
        h = 3.85
        vp = [1, 23]
        resolution = (800, 450)
        per = 0.00017453292519943294
        # vp =[1,120]
        # resolution =(800,450)
        # per = 0.00026179938779914946
        points = np.array(points)
        objDim = points.ndim
        if objDim == 1:
            points = [points]

        cvtObjs = []
        for obj in points:
            if len(obj) == 2:
                objX, objY = obj
            else:
                objX, objY = obj[0] + obj[2] / 2, obj[1] + obj[3]
            _, vpY = vp
            angle = 0.5 * np.pi - per * (objY - vpY)  # 射线与杆的夹角
            temp = np.tan(angle)
            y = h * temp  # 雷达上的y，注意不是射线的长
            # 目前假设：图像垂直中线约为雷达零点，垂直与水平每像数视场角近似相同
            angle = per * (objX - resolution[0] / 2)  # 射线与杆的夹角
            x = y * np.tan(angle)  # 得用y计算，不同的距离夹角一样但y不同
            cvtObjs.append((x, y))
        if objDim == 1:
            return cvtObjs[0]
        else:
            return cvtObjs

    def convertResolution(self,data, inputResolution=(1280, 720), outputResolution=(800, 450), mode="xywh"):
        # data [n,2->(x,y)] xy or [n,2->(x,y,w,h)] xywh
        # inputResolution x,y
        # outputResolution x,y
        data = np.array(data, dtype=np.float64)

        coefX = outputResolution[0] / inputResolution[0]
        coefY = outputResolution[1] / inputResolution[1]

        if coefX == coefY:  # 如果比例缩放相同，如(800,800) --> (400,400)
            offsetX = 0
            offsetY = 0
        # [383.75, 141.25, 45.0, 136.25]
        else:  # 如果比例缩放不相同，如(1000,800) --> (500,200) 2：4
            # 确定哪边是裁剪边，即非裁剪边缩放为对应大小后，裁剪边应有盈余
            # 例如 inputResolution[1] * coefX > inputResolution[1] * coefY
            # 按x轴缩放后，大于本来的inputResolution[1] * coefY，即 coefX > coefY时 Y为裁剪边
            if coefX > coefY:
                coefY = coefX
                offsetX = 0
                offsetY = (outputResolution[1] - inputResolution[1] * coefY) / 2
            else:
                coefX = coefY
                offsetX = (outputResolution[0] - inputResolution[0] * coefX) / 2
                offsetY = 0
        if mode == "xy":
            if len(data.shape) == 1:
                data[:2] = data[:2] * [coefX, coefY]
            else:
                data[:, :2] = data[:, :2] * [coefX, coefY]
        elif mode == "xywh":
            if len(data.shape) == 1:
                data[:4] = data[:4] * [coefX, coefY, coefX, coefY]
            else:
                data[:, :4] = data[:, :4] * [coefX, coefY, coefX, coefY]

        if len(data.shape) == 1:
            data[:2] = data[:2] + [offsetX, offsetY]
        else:
            data[:, :2] = data[:, :2] + [offsetX, offsetY]
        return data
    def iConvertResolution(self,data, inputResolution=(1280, 720), outputResolution=(800, 450), mode="xywh"):
        # iConvertResolution为convertResolution函数的反函数，因为可能是有裁剪的缩放，故需要求原来值时，应用该函数
        '''
        xxx = convertResolution(yyy,(1000,800),(500,200))
        则yyy = iConvertResolution(xxx,(500,200),(1000,800))
        '''

        # data [n,2->(x,y)] xy or [n,2->(x,y,w,h)] xywh
        # inputResolution x,y
        # outputResolution x,y
        data = np.array(data, dtype=np.float64)

        coefX = outputResolution[0] / inputResolution[0]
        coefY = outputResolution[1] / inputResolution[1]

        if coefX == coefY:  # 如果比例缩放相同，如(800,800) --> (400,400)
            offsetX = 0
            offsetY = 0
        # [383.75, 141.25, 45.0, 136.25]
        else:  # 如果比例缩放不相同，如(1000,800) --> (500,200) 2：4
            if coefX < coefY:
                coefY = coefX
                offsetX = 0
                offsetY = (outputResolution[1] - inputResolution[1] * coefY) / 2
            else:
                coefX = coefY
                offsetX = (outputResolution[0] - inputResolution[0] * coefX) / 2
                offsetY = 0
        if mode == "xy":
            if len(data.shape) == 1:
                data[:2] = data[:2] * [coefX, coefY]
            else:
                data[:, :2] = data[:, :2] * [coefX, coefY]
        elif mode == "xywh":
            if len(data.shape) == 1:
                data[:4] = data[:4] * [coefX, coefY, coefX, coefY]
            else:
                data[:, :4] = data[:, :4] * [coefX, coefY, coefX, coefY]

        if len(data.shape) == 1:
            data[:2] = data[:2] + [offsetX, offsetY]
        else:
            data[:, :2] = data[:, :2] + [offsetX, offsetY]
        return data

    def createData(self):

        cameraObj0 = [{'confidence': 0.768391371, 'class': 0, 'bbox':  self.iConvertResolution([i+np.random.randint(-10, 10), 309+np.random.randint(-5, 5), 42, 77], inputResolution=(800, 450),
                                      outputResolution=(640, 640)).tolist()} for i in range (50, 800,300)] # 10s的数据100*0.1
        cameraObj1 = [{'confidence': 0.768391371, 'class': 0, 'bbox':  self.iConvertResolution([i+np.random.randint(-10, 10), 255+np.random.randint(-5, 5), 13, 39], inputResolution=(800, 450),
                                      outputResolution=(640, 640)).tolist()} for i in range (50, 800,300)] # 10s的数据100*0.1
        cameraObj2 = [{'confidence': 0.768391371, 'class': 0, 'bbox': self.iConvertResolution([i, 110, 26, 56], inputResolution=(800, 450),
                                      outputResolution=(640, 640)).tolist()} for i in range (0, 800,8)] # 10s的数据100*0.1



        cameraObjList =[cameraObj0, cameraObj1]
        # cameraObjList =[cameraObj2]

        cameraData =[]
        for cameraObj in cameraObjList:
            for idx,  obj in enumerate(cameraObj,1):
                if idx > len(cameraData):
                    cameraData.append([idx*0.1,[{'id': 1, 'timestamp':idx*0.5,'data': [obj]}]] )
                else:
                    cameraData[idx-1][1][0]["data"].append(obj)

        # cameraData=[{'id': 1, 'timestamp': 1716450188620,
        #          'data': [{'confidence': 0.768391371, 'class': 0, 'bbox': [180, 268, 29, 70]},
        #                   {'confidence': 0.699077189, 'class': 0, 'bbox': [199, 309, 42, 75]},
        #                   {'confidence': 0.690569699, 'class': 0, 'bbox': [273, 208, 17, 33]},
        #                   {'confidence': 0.636456966, 'class': 0, 'bbox': [395, 144, 22, 61]},
        #                   {'confidence': 0.634115398, 'class': 0, 'bbox': [207, 255, 13, 39]},
        #                   {'confidence': 0.593315482, 'class': 0, 'bbox': [292, 206, 14, 28]},
        #                   {'confidence': 0.553813815, 'class': 0, 'bbox': [447, 201, 27, 61]},
        #                   {'confidence': 0.401201725, 'class': 0, 'bbox': [497, 465, 10, 11]},
        #                   {'confidence': 0.333124518, 'class': 0, 'bbox': [280, 206, 18, 32]},
        #                   {'confidence': 0.322763592, 'class': 0, 'bbox': [262, 269, 13, 24]},
        #                   {'confidence': 0.321454346, 'class': 0, 'bbox': [403, 143, 8, 9]}]}]

        # estimateImageToRadar

        # print(cameraData)
        # radarData =[[7977, -1.3, 203.4, 0.0, 0.58, 16, 0, 0], [7963, 0.6, 66.9, 0.0, -0.47, 4806, 0, 0]]
        radarData = []
        for i in  cameraData:
            timeStamp,camObj = i
            radarObj = []
            for idx,  obj in enumerate(camObj[0]["data"]):
                box = self.convertResolution(obj['bbox'], inputResolution=(640, 640),
                                           outputResolution=(800, 450)).tolist()
                radarPoint = self.estimateImageToRadar(box)
                radarObj.append([idx, radarPoint[0],radarPoint[1]-5,0.0, 0.58, 16, 0, 0]) # -10防止投影回去后一模一样
            # radarObj.append([3,np.random.randint(-3,3),np.random.randint(60, 200),  0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            # radarObj.append([4,np.random.randint(-3,3),np.random.randint(60, 200),  0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            # radarObj.append([5,np.random.randint(-3,3),np.random.randint(60, 200),  0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            # radarObj.append([3,  np.random.randint(60, 200),np.random.randint(-3, 3),0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            # radarObj.append([4,  np.random.randint(60, 200),np.random.randint(-3, 3),0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            # radarObj.append([5,  np.random.randint(60, 200),np.random.randint(-3, 3),0.0, 0.58, 16, 0, 0])  # -10防止投影回去后一模一样
            radarData.append([timeStamp,radarObj])
        # print(radarData)
        return radarData,cameraData

posX =[]
posY =[]
def cc(data,timeFrame):
    return
    obj = {}
    print(data)
    posX.append(data[1])
    posY.append(data[2])
    for x, y in zip(posX, posY):
        if len(obj) == 0:
            obj[0] = [[x, y]]
        else:
            is0 = True
            for i in list(obj.keys())[::-1]:
                if np.min(np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=1)) < 2:
                    obj[i + 1] = [[x, y]]
                    is0 = False
                    break
            if is0:
                obj[0].append([x, y])

            #     obj[0]

            print(np.array(obj[i]), np.array((x, y)))
            print(np.array(obj[i]) - np.array((x, y)))
            print(np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=1))
            # if np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=0):
        print(obj)

def rr(data,timeFrame):
    return
    obj = {}
    print(data)
    posX.append(data[0][1])
    posY.append(data[0][2])
    for x, y in zip(posX, posY):
        if len(obj) == 0:
            obj[0] = [[x, y]]
        else:
            is0 = True
            for i in list(obj.keys())[::-1]:
                if np.min(np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=1)) < 2:
                    obj[i + 1] = [[x, y]]
                    is0 = False
                    break
            if is0:
                obj[0].append([x, y])

            #     obj[0]

            print(np.array(obj[i]), np.array((x, y)))
            print(np.array(obj[i]) - np.array((x, y)))
            print(np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=1))
            # if np.linalg.norm(np.array(obj[i]) - np.array((x, y)), axis=0):
    print(obj)
if __name__ == "__main__":
    v=VirtualInput([r"C:\Users\admins\Desktop\20240527测试日志\2024-05-27 20-11.log.2024-05-27_20",r"C:\Users\admins\Desktop\20240527测试日志\2024-05-27 20-11.log"],rr,cc,)
    time.sleep(555)
    pass