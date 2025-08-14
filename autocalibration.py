# -*- coding: utf-8 -*-

import numpy as np

from xypMatplotLibDebug import matFigure, matPlot, matLegend, matPause, matClf
from xypOpencvDebug import cvVideoCapture, cvResize, cvRectangle, cvPutText, cvImshow, cvWaitKey

'''debug库'''

from tool import LOG_ANALYSE_TOOL
import os
class CLIB_LOG(LOG_ANALYSE_TOOL):
    def __init__(self):
        super().__init__()

    def analyseLog(self,path):
        # 解析日志内容
        '''
        :param path: 日志位置
        :return:返回数据格式为[[timeStamp0,[obj0,obj1...]],...]
        '''
        f = open(path, "r")
        camera0BoxData = []
        camera1BoxData = []
        camera0DtoData = []
        camera1DtoData = []
        radarData = []
        while 1:
            line = f.readline()
            if line == "":
                break
            if "- DEBUG: " in line:
                info = line.split("- DEBUG: ")[1]
                if info.startswith("input_camera"):
                    # {'camerastatus': [{'nearcameraocclude': '-1', 'farcameraocclude': '-1', 'deflection': '-1', 'nighttrainlight': '-1'}],
                    #  'list': [{'id': 0,'timestamp': 1689209775964,'data': []},
                    #      {'id': 1,
                    #      'timestamp': 1689209775964,xywh,x,y
                    #      'data': [{'confidence': 0.15997236960000003, 'class': 0, 'bbox': (91, 388, 67, 56),
                    #               'dto': [9998, -1.744194979673268, 59.89857587748896, 0, 0], 'in_area': 1},
                    #               {'confidence': 0.308260739, 'class': 0, 'bbox': (107, 245, 48, 87),
                    #               'dto': [9998, -2.8025877437997573, 99.39500267049597, 0, 0], 'in_area': 0}]}],
                    #  'stamp': 1689209775.9692466}
                    # 字典键值 'camerastatus'相机状态, 'list'[{相机id, 时间戳, 目标数据:[{置信度，类别，框信息，dto信息，in_area}] }], 'stamp':时间戳
                    infoDict = eval(info.strip()[12:])
                    for i in infoDict["list"]:
                        if i["id"] == 0:
                            camera0BoxData.append( [infoDict["stamp"],  np.asarray([j["bbox"] for j in i["data"]])])
                            camera0DtoData.append( [infoDict["stamp"], np.asarray([j["dto"][1:3] for j in i["data"]])])
                        if i["id"] == 1:
                            camera1BoxData.append( [infoDict["stamp"],  np.asarray([j["bbox"]  for j in i["data"]])*self.farToNearImageCof]) # 1280 * 720 转化分辨率到 800 * 450
                            camera1DtoData.append( [infoDict["stamp"],  np.asarray([j["dto"][1:3] for j in i["data"]])])
                elif info.startswith("input_radar"):
                    # input_radar[1689649199.9447095, 8312, 1.311, 72.31]
                    info = eval(info.strip()[11:])  # [time,objId0,x0,y0,objId1,x1,y1...]
                    # radarData.append([info[0], np.asarray([info[i + 1:i + 3] for i in range(len(info))[1::3]])])
                    radarData.append([info[0], np.asarray([i[1:3] for i in info[1]])])

        f.close()
        logData = {
             "radarData":    radarData,
        "camera0BoxData":camera0BoxData,
        "camera0DtoData":camera0DtoData,
        "camera1BoxData":camera1BoxData,
        "camera1DtoData":camera1DtoData
        }
        return logData
    def cleanLog(self,logData, camera=0):
        # 每个数据都是[time,[]]
        if camera ==0:
            worldRange = self.nearCamWorldRangeXY
            imageRange = self.nearCamImageRangeXY
            radarData     = logData["radarData"]
            cameraBoxData = logData["camera0BoxData"]
            cameraDtoData = logData["camera0DtoData"]
        else:
            worldRange = self.farCamWorldRangeXY
            imageRange = np.array(self.farCamImageRangeXY)* self.farToNearImageCof
            radarData = logData["radarData"]
            cameraBoxData = logData["camera1BoxData"]
            cameraDtoData = logData["camera1DtoData"]
        # 数据根据时间对齐
        if len(radarData) > 0 and len(cameraBoxData) > 0:
            data = self.subAlignByTime(radarData, cameraBoxData, cameraDtoData)
            # data = self.addAlignByTime(radarData, cameraBoxData, cameraDtoData)
            if len(data) == 0:
                return None
        else:
            return None
        # 暂时过滤掉出现多个目标的数据
        index=np.array([True  if len(i[1]) == 1 and len(i[2]) == 1 else False for i in data])
        if (index == False).all():
            return None
        data=data[index]

        # 提取用于计算的数据
        radarXY = np.array([i[1][0] for i in data]).reshape(-1, 2)
        boxBottomXY = np.array([[i[2][0][0] + 0.5 * i[2][0][2], i[2][0][1] + i[2][0][3]] for i in data]).reshape(-1, 2)
        boxDtoXY = np.array([i[3][0] for i in data]).reshape(-1, 2)
        boxW = np.array([i[2][0][2] for i in data])
        boxH = np.array([i[2][0][3] for i in data])


        matFigure(0)
        matPlot(range(len(radarXY)), -radarXY[:, 1], c="r", label="radarXY多目标过滤后")
        matPlot(range(len(boxBottomXY)), boxBottomXY[:, 1], c="b", label="boxBottomXY多目标过滤后")
        matPlot(range(len(boxDtoXY)), boxDtoXY[:, 1], c="g", label="boxDtoXY多目标过滤后")
        matLegend()

        # 异常值过滤
        mask1 =self.removeOutlierByThreshold(radarXY,worldRange)
        mask2 =self.removeOutlierByThreshold(boxBottomXY,imageRange)
        mask3 =self.removeOutlierByThreshold(boxDtoXY,worldRange)
        mask4 = boxH > boxW*2 # 高大于2倍宽
        index = mask1 & mask2 & mask3 & mask4
        if (index == False).all():
            return None
        radarXY =  radarXY[index]
        boxBottomXY = boxBottomXY[index]
        boxDtoXY= boxDtoXY[index]
        data = data[index]
        boxW = boxW[index]
        boxH = boxH[index]

        matFigure(1)
        matPlot(range(len(radarXY)), -radarXY[:, 1], c="r", label="radarXY异常值过滤后")
        matPlot(range(len(boxBottomXY)), boxBottomXY[:, 1], c="b", label="boxBottomXY异常值过滤后")
        matPlot(range(len(boxDtoXY)), boxDtoXY[:, 1], c="g", label="boxDtoXY异常值过滤后")
        matLegend()

        # 离群点过滤
        k = 3
        index = np.arange(len(radarXY))  # 元素索引
        for i in range(k):  # 认为跳跃点至少出现k次才能算是稳定的
            if len(index) < 3:
                return None
            radarDiff = np.abs(radarXY[index][1:] - radarXY[index][:-1])  # 后面元素减前面元素计算距离
            radarDiff = radarDiff[1:] + radarDiff[:-1]  # 每个元素前后差距相加
            mask1 = self.removeOutlierByGaussian(radarDiff[:, 0], 1)
            mask2 = self.removeOutlierByGaussian(radarDiff[:, 1], 1)
            boxBottomDiff = np.abs(boxBottomXY[index][1:] - boxBottomXY[index][:-1])  # 后面元素减前面元素计算距离
            boxBottomDiff = boxBottomDiff[1:] + boxBottomDiff[:-1]  # 每个元素前后差距相加
            mask3 = self.removeOutlierByGaussian(boxBottomDiff[:, 0], 1)
            mask4 = self.removeOutlierByGaussian(boxBottomDiff[:, 1], 1)
            mask5 = self.removeOutlierByGaussian(boxH[index][1:-1], 1)
            mask6 = self.removeOutlierByGaussian(boxW[index][1:-1], 1)
            indexSon = mask1 & mask2 & mask3 & mask4 & mask5 & mask6
            if (indexSon == False).all():
                return None
            index = index[1:-1][indexSon]

        radarXY = radarXY[index]
        boxBottomXY = boxBottomXY[index]
        boxDtoXY = boxDtoXY[index]
        data = data[index]
        boxW = boxW[index]
        boxH = boxH[index]

        matFigure(2)
        matPlot(range(len(radarXY)), -radarXY[:, 1], c="r", label="radarXY高斯过滤后")
        matPlot(range(len(boxBottomXY)), boxBottomXY[:, 1], c="b", label="boxBottomXY高斯过滤后")
        matPlot(range(len(boxDtoXY)), boxDtoXY[:, 1], c="g", label="boxDtoXY高斯过滤后")
        matLegend()

        cleanData = {
            "radarXY": radarXY,
            "imageXY": boxBottomXY,
            "imageDtoXY": boxDtoXY,
        }
        if False: # debug
            displayVideoWithBox("./testData/0.mp4",data)
        return cleanData
    def updateLogInfo(self,logPath,camera):
        files = os.walk(logPath)
        logPathList = []
        for i in files:
            currentFolderDirs, sonFolderNames, sonFileNames = i
            for sfn in sonFileNames:
                if os.path.splitext(sfn)[1] == ".log" or ".log." in sfn:
                    logPathList.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
        logPathList = sorted(logPathList, key=lambda x: os.path.getmtime(x))  # 按修改顺序排序

        radarXY =[]
        imageXY =[]
        imageDtoXY =[]
        for logPath in logPathList[2:]:
            logData = self.analyseLog(logPath)
            cleanData = self.cleanLog(logData, camera)
            if cleanData is not None:
                if len(radarXY) == 0:
                    radarXY = cleanData["radarXY"]
                    imageXY = cleanData["imageXY"]
                    imageDtoXY = cleanData["imageDtoXY"]
                else:
                    radarXY = np.concatenate([radarXY,  cleanData["radarXY"]], axis=0)
                    imageXY = np.concatenate([imageXY,  cleanData["imageXY"]], axis=0)
                    imageDtoXY = np.concatenate([imageDtoXY,  cleanData["imageDtoXY"]], axis=0)
            else:
                continue
            if len(radarXY) > 50:  # 给定一个数据最大阈值
                break
        if len(radarXY) < 10:  # 给定一个数据最少阈值
            # raise ValueError("可用数据不够")
            return None
        if len(radarXY) > 50:  # 给定一个数据最大阈值
            dataStep = len(radarXY) // 50
        else:
            dataStep = 1
        data = np.stack([radarXY[::dataStep], imageXY[::dataStep]], axis=1)
        return data
'''debug'''
def displayVideoWithBox(videoPath, data):
    radarData = [[i[0],i[1][0]] for i in data]
    cameraData = [[i[0],i[2][0]] for i in data]
    offsetTime = -226  # 越小，时间整体前移，例如框跟不上人时调小
    # 时间变成基于base时间的相对值后整体移动offsetTime
    # offsetTime用于和视频时间对上，因为数据是第n秒开始接收的，但视频可能n-5秒就开始播放了
    radarBaseTime = radarData[0][0]
    cameraBaseTime = cameraData[0][0]
    cameraData = [[offsetTime + i[0] - cameraBaseTime, i[1]] for i in cameraData]
    radarData =  [[offsetTime + i[0] - radarBaseTime, i[1]] for i in radarData]
    data = LOG_ANALYSE_TOOL.subAlignByTime(radarData, cameraData)
    num = 0  # 用于计数多长时间没有帧被读取了，超过则认为视频读取完了
    timeSum = 0  # 计算视频当前播放时长
    unitTime = 1.0 / 15.0  # 视频帧率是15
    cap = cvVideoCapture(videoPath)
    radarTrack = []
    while cap is not None:
        ref, frame = cap.read()
        timeSum += unitTime  # 视频的时间帧
        if ref:
            num = 0
            frame = cvResize(frame, (800, 450))  # 图片大小
            disTime = np.abs(data[:, 0] - timeSum)
            minIdx = np.argmin(disTime)
            if disTime[minIdx] < unitTime:  # 最小且差距不超过1/15秒，数据帧率中最快的是1/15，即不能跳帧匹配
                radarTrack.append(data[minIdx, 1])
                drawRadarTrack = np.array(radarTrack).reshape(-1, 2)
                matPlot(drawRadarTrack[:, 0], drawRadarTrack[:, 1])
                matPause(0.0000001)
                matClf()
                x, y, w, h = np.array(data[minIdx, 2],dtype=np.int64)
                frame = cvRectangle(frame, (x, y), (x + w, y + h), color=[255, 255, 0])
                frame = cvPutText(frame, str(data[minIdx, 1][1]) + " m", (x, y), cv.FONT_HERSHEY_COMPLEX, 2.0,
                                   (100, 200, 200), 5)
            cvImshow("f", frame)
            cvWaitKey(1)

        else:
            num += 1
            if num > 50:
                break

class AUTO_CALIBRATION():
    def __init__(self,  fovV=None, H=None):
        self.imgH = 450  # 图像高度，在数据处理时，1280*720数据已经被换算到800*450下的了
        self.fovV = fovV  # 垂直视场角，弧度
        self.H = H  # 安装位置的高度
        if (self.H is None) and (self.fovV is None):
            raise ValueError("安装高度和垂直视场角必须给出一个")

    def estimateBaseAngleByIteration(self, distance, pixelOffset):  # 计算目标底部在相机看过去的下倾角，即相机光轴同杆子的夹角
        # distance：雷达测量的距离，单位m
        # pixelOffset：像素偏移量
        dataNum = len(distance)
        # Adam参数经调试如下
        baseAngle = np.deg2rad(45)  # 初始化参考角度
        baseAngle_M = 0.0
        baseAngle_V = 0.0
        baseAngle_Rate = 0.1
        baseAngle_Beta1 = 0.9
        baseAngle_Beta2 = 0.999
        baseAngle_Epsilon = 1e-8

        if self.fovV is None:  # 如果fovV没有给出，fovV也作为参数需要求解
            fovV = np.deg2rad(45)  # 初始化垂直视场角
            fovV_M = 0.0
            fovV_V = 0.0
            fovV_Rate = 0.2
            fovV_Beta1 = 0.9
            fovV_Beta2 = 0.999
            fovV_Epsilon = 1e-8
        else:
            fovV = self.fovV
        # 用于提前结束迭代
        lastLoss = None
        thresholdLoss = 1e-4 # 度量单位 1大概是m，1e-2大概是cm
        exitVote = 0
        for epoch in range(2000): # 最大循环2000次
            # 理论上数值精确的话funcSeq中每个函数的值是一样的，为杆子的高度
            # fov收敛稳定一些，所以不用fovV/self.imgH
            loss = 0.0 # 损失函数
            derivativeBA = 0.0 # 损失函数对baseAngle求偏导
            derivativeFV = 0.0 # 损失函数对fovV 求偏导
            if self.H is None:
                for i in range(dataNum - 1):
                    for j in range(i + 1, dataNum):
                        loss = loss + (distance[i] * np.cos(baseAngle + pixelOffset[i] * fovV / self.imgH) -
                                       distance[j] * np.cos(baseAngle + pixelOffset[j] * fovV / self.imgH)) ** 2 # 约束是每个数据求出的H应该相等
                        derivativeBA = derivativeBA + 2 * (
                                    -distance[i] * np.sin(baseAngle + pixelOffset[i] * fovV / self.imgH) +
                                    distance[j] * np.sin(baseAngle + pixelOffset[j] * fovV / self.imgH)) \
                                      * (distance[i] * np.cos(baseAngle + pixelOffset[i] * fovV / self.imgH) -
                                         distance[j] * np.cos(baseAngle + pixelOffset[j] * fovV / self.imgH))
                        if self.fovV is None:
                            derivativeFV = derivativeFV + (distance[i]*np.cos(baseAngle + fovV*pixelOffset[i]/self.imgH) - distance[j]*np.cos(baseAngle + fovV*pixelOffset[j]/self.imgH))*(-2*distance[i]*pixelOffset[i]*np.sin(baseAngle + fovV*pixelOffset[i]/self.imgH)/self.imgH + 2*distance[j]*pixelOffset[j]*np.sin(baseAngle + fovV*pixelOffset[j]/self.imgH)/self.imgH)

            else:
                for i in range(dataNum):
                    loss = loss + (distance[i] * np.cos(baseAngle + pixelOffset[i] * fovV / self.imgH) - self.H) ** 2  # 约束是每个数据求出的H应该等于给定的self.H
                    derivativeBA = derivativeBA + 2 * (distance[i] * np.cos(baseAngle  + pixelOffset[i] * fovV / self.imgH) - self.H) * \
                                  (-distance[i] * np.sin(baseAngle + pixelOffset[i] * fovV / self.imgH))
                    if self.fovV is None:
                        derivativeFV = derivativeFV +(-2*distance[i]*pixelOffset[i]*(distance[i]*np.cos(baseAngle + fovV*pixelOffset[i]/self.imgH) - self.H)*np.sin(baseAngle + fovV*pixelOffset[i]/self.imgH)/self.imgH)

            # Adam优化策略
            baseAngle_M = baseAngle_Beta1 * baseAngle_M + (1.0 - baseAngle_Beta1) * derivativeBA
            baseAngle_V = baseAngle_Beta2 * baseAngle_V + (1.0 - baseAngle_Beta2) * (derivativeBA ** 2)
            mHat = baseAngle_M / (1.0 - np.power(baseAngle_Beta1, epoch + 1))
            vHat = baseAngle_V / (1.0 - np.power(baseAngle_Beta2, epoch + 1))
            baseAngle = baseAngle - (baseAngle_Rate * mHat / (np.sqrt(vHat) + baseAngle_Epsilon))

            if self.fovV is None:
                fovV_M = fovV_Beta1 * fovV_M + (1.0 - fovV_Beta1) * derivativeFV
                fovV_V = fovV_Beta2 * fovV_V + (1.0 - fovV_Beta2) * (derivativeFV ** 2)
                fovVMHat =  fovV_M  / (1.0 - np.power(fovV_Beta1, epoch + 1))
                fovVVHat =  fovV_V  / (1.0 - np.power(fovV_Beta2, epoch + 1))
                fovV = fovV - (fovV_Rate * fovVMHat / (np.sqrt(fovVVHat) + fovV_Epsilon))

            if lastLoss is None:
                lastLoss = loss / dataNum
            else:
                meanLoss = loss / dataNum
                if  lastLoss - meanLoss < thresholdLoss and lastLoss - meanLoss > 0:# 如果误差减少量小于阈值
                    exitVote+=1
                lastLoss = meanLoss
            if exitVote > 10:
                break

        if self.H is not None:  # 给定H求解fov时，用得到的fov估计H，比较估计的H和给定的H，判断是否求解成功
            Hs = []
            for i in range(dataNum):
                Hs.append(distance[i] * np.cos(baseAngle + pixelOffset[i] * fovV / self.imgH))
            Hs = np.array(Hs)
            dataAvg = np.mean(Hs, axis=0)
            dataStd = np.std(Hs, axis=0)
            mask = (np.abs(Hs - dataAvg) <= 1 * dataStd)
            H = np.mean(Hs[mask])
            if abs(H - self.H) > 0.1:  # 求出来的与给定的H相差超过0.1m,认为求解失败
                # return None # 暂时弃用
                return (baseAngle, fovV, self.H)
            else:
                return (baseAngle, fovV, self.H)
        elif self.fovV is not None: # 给定fov求解H时，用得到的H估计fov，比较估计的fov和给定的fov，判断是否求解成功
            Hs = []
            for i in range(dataNum):
                Hs.append(distance[i] * np.cos(baseAngle + pixelOffset[i] * fovV / self.imgH))
            Hs = np.array(Hs)
            dataAvg = np.mean(Hs, axis=0)
            dataStd = np.std(Hs, axis=0)
            mask = (np.abs(Hs - dataAvg) <= 1 * dataStd)
            H = np.mean(Hs[mask])

            fovs = []
            for i in range(0,dataNum):
                if pixelOffset[i] ==0 or distance[i] ==0:
                    pass
                else:
                    fovs.append((np.arccos(H / distance[i]) - baseAngle) * self.imgH / pixelOffset[i])

            fovs = np.array(fovs)
            dataAvg = np.mean(fovs, axis=0)
            dataStd = np.std(fovs, axis=0)
            mask = (np.abs(fovs - dataAvg) <= 1 * dataStd)
            fov = np.mean(fovs[mask])
            if abs(fov - self.fovV) > np.deg2rad(4):  # 求出来的与给定的fov相差超过 x deg,认为求解失败
                # return None # 暂时弃用
                return (baseAngle, self.fovV, H)
            else:
                return (baseAngle, self.fovV, H)


    def run(self, radarXY, imageXY):
        """
        imageXY = array([imageXY0:[x,y],imageXY1...]) ,image中目标的像素xy坐标，单位px
        radarXY = array([radarXY0:[x,y],radarXY1...]) ,radar中目标的真实xy坐标，单位m
        返回值：self.H self.fovV self.centerAngle self.vanishPointY  设备安装高度/m 设备垂直视场角/rad 设备垂直方向与安装杆的夹角/rad 灭点在图像的y值/px
        """
        distance = radarXY[:, 1]  # 雷达y轴距离
        imageBaseY = imageXY[0, 1]  # 将第一个视觉目标的y值作为y轴的参考值
        pixelOffset = imageBaseY - imageXY[:, 1]  # 图像中y值比参考值小，则目标与杆的夹角增大
        # 注意angle的第一个值是参考值，其他值都是与参考值位置的y值偏移量，angle采用弧度制
        data = self.estimateBaseAngleByIteration(distance, pixelOffset)  # 迭代慢，但抗干扰能力强
        if data is None:# 求解失败：
            return None
        else:
            baseAngle, fovV, H = data
        perPixelRad = fovV / self.imgH
        centerAngle = baseAngle - (self.imgH / 2 - imageBaseY) * perPixelRad
        vanishPointY = imageBaseY - (np.pi / 2 - baseAngle) // perPixelRad
        # fovV  垂直视场角，弧度
        # H 安装位置的高度
        # baseAngle 参考点在垂直方向上与杆的夹角，弧度
        # centerAngle 光心在垂直方向上与杆的夹角，弧度
        # vanishPointY 灭点在垂直方向上的像素坐标，px
        # perPixelRad 每个像素点代表的角度，弧度
        return (H,fovV,perPixelRad,vanishPointY,centerAngle)
    
    
    
    
'''自动标定封装函数'''

def calibration(logPath='/ssd/zipx/log/',camera=0, H=None, fovV=None):
    log = CLIB_LOG()
    data = log.updateLogInfo(logPath,camera)
    if data is not None:
        C = AUTO_CALIBRATION(H=H, fovV=fovV)
        return  C.run(data[:,0], data[:,1]) # None or (H, fovV, centerAngle, vanishPointY, perPixelRad)
    else:
        return None
    
if __name__ == "__main__":
   pass