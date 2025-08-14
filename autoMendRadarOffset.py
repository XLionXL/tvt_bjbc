import numpy as np
# import cv2 as cv
import os
import sys 
import pandas as pd
import pickle as pk

from tool import LOG_ANALYSE_TOOL
# from pylab import mpl
# import matplotlib.pyplot as plt
# mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # matpotlib显示中文字体
# np.set_pyPrintoptions(suppress=True)
# 这是拟合点的，现在先顶上,复制于b，当前打算改进日志数据相关函数
from xypMatplotLibDebug import *
from xypOpencvDebug import *
from xypPrintDebug import xypPrint


class MODEL_CLASS():
    def __init__(self):
        # 模型参数
        self.angle = None

    def __model(self, sampleData):
        # 旋转
        rotationMatrix = np.array([[np.cos(self.angle), -np.sin(self.angle)],
                                   [np.sin(self.angle), np.cos(self.angle)]])
        radarRotationData = rotationMatrix.dot(sampleData[:, 0].T).T
        # 计算内积
        radarX, radarY, imageX, imageY = radarRotationData[:, 0], radarRotationData[:, 1], sampleData[:, 1, 0], sampleData[:, 1,1]
        imageX = 0.0 * imageX  # 这里的误差在于图像上的夹角不代表真实的夹角，要使该方法成立，我们假设采样的数据都是位于图像竖直中线上
        # 内积
        dotProduct = radarX * imageX + radarY * imageY
        # 模长
        radarLength = np.sqrt(radarX ** 2 + radarY ** 2)
        imageLength = np.sqrt(imageX ** 2 + imageY ** 2)
        # 夹角
        angles = np.abs(np.arccos(dotProduct / (radarLength * imageLength)))
        return angles

    def removeOutlierByGaussian(self,data, d=1):
        dataAvg = np.mean(data, axis=0)
        dataStd = np.std(data, axis=0)
        mask = (np.abs(data - dataAvg) <= d * dataStd)
        return mask

    def calModelArgs(self,sampleData): # 计算模型参数
        # sampleData格式[dataNum,2->[radar,image],2->[x,y]]
        radarX,radarY,imageX,imageY = sampleData[:,0,0],sampleData[:,0,1],sampleData[:,1,0],sampleData[:,1,1]
        imageX = 0.0*imageX # 这里的误差在于图像上的夹角不代表真实的夹角，要使该方法成立，我们假设采样的数据都是位于图像竖直中线上
        # 内积
        dotProduct = radarX * imageX + radarY * imageY
        # 模长
        radarLength = np.sqrt(radarX ** 2 + radarY ** 2)
        imageLength = np.sqrt(imageX ** 2 + imageY ** 2)
        # 夹角
        angels = np.arccos(dotProduct / (radarLength * imageLength))
        angels= angels[self.removeOutlierByGaussian(angels)] # 去除异常点
        self.angle = np.mean(angels)
        return self.__model


class MEND_LOG(LOG_ANALYSE_TOOL):
    def __init__(self):
        super().__init__()
        self.nearCamWorldRangeXY= ((-20, 20),(0, 70)) # ((minX,maxX),(minY,maxY)),单位m
        self.farCamWorldRangeXY= ((-20, 20), (100, 250))
        # 有效范围
        self.nearCamImageRangeXY = ((-20,20), (-1,self.nearCamImageShape[1]))  # ((minX,maxX),(minY,maxY)),单位px
        self.farCamImageRangeXY =  ((-20,20), (-1,self.nearCamImageShape[1]))  # ((minX,maxX),(minY,maxY)),单位px


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

    def cleanLog(self, logData, camera=1):
        # 每个数据都是[time,[]]
        if camera == 0:
            worldRange = self.nearCamWorldRangeXY
            imageRange = self.nearCamImageRangeXY
            radarData = logData["radarData"]
            cameraBoxData = logData["camera0BoxData"]
            cameraDtoData = logData["camera0DtoData"]
        else:
            worldRange = self.farCamWorldRangeXY
            imageRange = self.nearCamImageRangeXY # 数据在分析的时候已经转了
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
        index = np.array([True if len(i[1]) == 1 and len(i[2]) == 1 else False for i in data])
        if (index == False).all():
            return None
        data = data[index]

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
        mask1 = self.removeOutlierByThreshold(radarXY, worldRange)
        mask2 = self.removeOutlierByThreshold(boxBottomXY, imageRange)
        mask3 = self.removeOutlierByThreshold(boxDtoXY, worldRange)
        mask4 = boxH > boxW * 2  # 高大于2倍宽
        index = mask1 &  mask3 & mask4
        if (index == False).all():
            return None
        radarXY = radarXY[index]
        boxBottomXY = boxBottomXY[index]
        boxDtoXY = boxDtoXY[index]
        data = data[index]
        boxW = boxW[index]
        boxH = boxH[index]

        # 以图像底部，中线为原点的坐标
        if camera == 0:
            boxBottomXY[:, 0] = boxBottomXY[:, 0] - self.nearCamImageShape[0] // 2
            boxBottomXY[:, 1] = self.nearCamImageShape[1] - boxBottomXY[:, 1]
        elif camera == 1:
            boxBottomXY[:, 0] = boxBottomXY[:, 0] - self.farCamImageShape[0] // 2
            boxBottomXY[:, 1] = self.farCamImageShape[1] - boxBottomXY[:, 1]

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
        if False:  # debug
            displayVideoWithBox("./testData/0.mp4", data)
        return cleanData

    def updateLogInfo(self, logPath, camera):
        files = os.walk(logPath)
        logPathList = []
        for i in files:
            currentFolderDirs, sonFolderNames, sonFileNames = i
            for sfn in sonFileNames:
                if os.path.splitext(sfn)[1] == ".log" or ".log." in sfn:
                    logPathList.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
        logPathList = sorted(logPathList, key=lambda x: os.path.getmtime(x))  # 按修改顺序排序

        radarXY = []
        imageXY = []
        imageDtoXY = []
        for logPath in logPathList:
            logData = self.analyseLog(logPath)
            cleanData = self.cleanLog(logData, camera)


            if cleanData is not None:

                if len(radarXY) == 0:
                    radarXY = cleanData["radarXY"]
                    imageXY = cleanData["imageXY"]
                    imageDtoXY = cleanData["imageDtoXY"]
                else:
                    radarXY = np.concatenate([radarXY, cleanData["radarXY"]], axis=0)
                    imageXY = np.concatenate([imageXY, cleanData["imageXY"]], axis=0)
                    imageDtoXY = np.concatenate([imageDtoXY, cleanData["imageDtoXY"]], axis=0)
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
    radarData = [[i[0], i[1][0]] for i in data]
    cameraData = [[i[0], i[2][0]] for i in data]
    offsetTime = -226  # 越小，时间整体前移，例如框跟不上人时调小
    # 时间变成基于base时间的相对值后整体移动offsetTime
    # offsetTime用于和视频时间对上，因为数据是第n秒开始接收的，但视频可能n-5秒就开始播放了
    radarBaseTime = radarData[0][0]
    cameraBaseTime = cameraData[0][0]
    cameraData = [[offsetTime + i[0] - cameraBaseTime, i[1]] for i in cameraData]
    radarData = [[offsetTime + i[0] - radarBaseTime, i[1]] for i in radarData]
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
                x, y, w, h = np.array(data[minIdx, 2], dtype=np.int64)
                frame = cvRectangle(frame, (x, y), (x + w, y + h), color=[255, 255, 0])
                frame = cvPutText(frame, str(data[minIdx, 1][1]) + " m", (x, y), cv.FONT_HERSHEY_COMPLEX, 2.0,
                                  (100, 200, 200), 5)
            cvImshow("f", frame)
            cvWaitKey(1)

        else:
            num += 1
            if num > 50:
                break



def ransac(data, epochNum=1000, sampleNum=8,threshold=1):
    # data格式[dataNum,2:[radar,image],2:[x,y]]
    # threshold: 在200m的距离摄像头与雷达允许的最大偏差，单位m
    maxOffsetAngle = abs(np.arctan(threshold/200)) # 计算最大偏差角度

    bestModel = None # 保存最佳模型
    bestInliers = None # 保存最佳内点
    nowLoss = np.inf # 记录当前误差
    dataNum = len(data)
    data = np.array(data)
    for i in range(epochNum):

        # 数据采样
        sampleIdx = np.random.choice(dataNum, sampleNum, replace=False)
        sampleData = data[sampleIdx]
        # 创建模型
        modelClass = MODEL_CLASS()
        model = modelClass.calModelArgs(sampleData) # 计算模型参数，返回模型
        loss = model(data)  # 计算误差
        inliersIdx = loss < 5*maxOffsetAngle # 判断内点
        if np.sum(inliersIdx)>=0.8*dataNum or np.sum(inliersIdx)>=10: # 如果内点数量满足要求
            inliersData = data[inliersIdx]
            modelClass = MODEL_CLASS()
            model = modelClass.calModelArgs(inliersData)
            loss = np.mean(model(inliersData))  # 计算误差
            if loss < nowLoss: # 保存最优模型
                nowLoss = loss
                bestModel = modelClass
                bestInliers = inliersData
        # 200米要求误差不超过1m的话，夹角应该小于(np.rad2deg(np.arctan(1/200))=0.2864765102770745度，
        # 或者旋转后y值总差距不能超过maxLoss = 200*cos(0.2864765102770745) = 0.003m
        # 求出的角度不能太离谱
        if bestModel is not None and abs(bestModel.angle) <= maxOffsetAngle and abs(bestModel.angle) <= np.deg2rad(2):
            break
    return bestModel, bestInliers

# 循环日志直到获取到需要的数据



def createOrOpenFileByPath(filePath="config/amendRadarOffsetData.txt"):
    directoryPath = os.path.dirname(filePath)
    if not os.path.exists(directoryPath):
        os.mkdir(directoryPath)
    if not os.path.exists(filePath):
        return None
    else:
        f = open(filePath, "rb")
        data = pk.load(f)
        f.close()
        return data

def amendRadarOffset(logPath='./testData/'):
    savePath="config/amendRadarOffsetData.txt"
    log = MEND_LOG()
    oldData = createOrOpenFileByPath(savePath)
    newData = log.updateLogInfo(logPath, 1) # 默认使用远焦数据
    # data格式[dataNum,2:[radar,image],2:[x,y]]

    if oldData is not None and newData is not None:
        data = np.concatenate([oldData, newData], axis=0)
    elif oldData is not None:
        data = oldData
    elif newData is not None:
        data = newData
    else:
        # raise ValueError("可用数据不够")
        return None

    data = sorted(data, key=lambda x: x[1,0])  # 按图像框x值距离中线的大小排序
    data = data[:200]
    model = None
    inliers = None
    if len(data)>0:
        model, inliers = ransac(data)
    if model is not None:
        xypPrint(np.rad2deg(model.angle))  # 0.5542767075567312
        f = open(savePath, "wb")
        pk.dump(inliers,f)
        f.close()
        return model.angle
    else:
        return None



if __name__ == "__main__":
    xypPrint(np.__version__)
    xypPrint(pd.__version__)

    # amendRadarOffset("testData")
    pass
