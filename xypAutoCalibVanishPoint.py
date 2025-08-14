from scipy.optimize import minimize
import math
import pickle as pk
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
# from comm_Polygon import Polygon_zzl
'''debug库'''
import json
import time
import datetime
import multiprocessing
from comm_Polygon import Polygon_zzl

# from xypCommonTool import repeatRunFunc,DynamicCanvas
# aa=DynamicCanvas("aa")
# from xypLogTool import LogAnalyseTool
import re
from numpy import *
import threading
import os
import re
import platform
import numpy as np
import pandas as pd
from collections import OrderedDict

class AdamOptimizer(): # adam优化器
    def __init__(self,x,rate=0.1):
        self.x = x
        self.epoch = 0
        self.m = 0.0
        self.v = 0.0
        self.rate = rate
        self.beta1 = 0.9
        self.beta2 = 0.999
        self.epsilon = 1e-8
    def __call__(self, gradient):
        # gradient:对x求的梯度
        # Adam优化策略
        self.epoch += 1
        self.m = self.beta1 * self.m + (1.0 - self.beta1) * gradient
        self.v = self.beta2 * self.v + (1.0 - self.beta2) * (gradient ** 2)
        mHat = self.m / (1.0 - np.power(self.beta1, self.epoch))
        vHat = self.v / (1.0 - np.power(self.beta2, self.epoch))
        self.x = self.x - ( self.rate * mHat / (np.sqrt(vHat) + self.epsilon))
        return self.x

# 灭点细化
class Refine(): # 简化版，用于处理凸问题
    def __init__(self,  perPixelRad=None, vanishPoint=0):
        self.vanishPoint = vanishPoint  # 灭点的水平位置
        self.vanishAngle = np.pi * 0.5  # 灭点与杆的夹角，杆垂直于地面
        self.perPixelRad = perPixelRad # 每个像素的垂直视场角度,弧度

    def calLoss(self,): # 损失函数
        loss = []
        for group in self.data:
            distance, _, foot = group
            pixelOffset = self.vanishPoint - foot  # 框底与灭点在y轴上的偏差像素值
            baseAng = self.vanishAngle + pixelOffset[0] * self.perPixelRad
            baseDis = distance[0]
            for idx in range(1, len(distance)):
                otherAng = self.vanishAngle + pixelOffset[idx] * self.perPixelRad
                otherDis = distance[idx]
                loss.append((baseDis * np.cos(baseAng) - otherDis * np.cos(otherAng)) ** 2)
        return np.mean(loss)
    def calGradient(self,): # 梯度函数
        grad = 0
        for group in self.data:
            distance, _, foot = group
            baseFoot = self.vanishPoint - foot[0]  # 框底与灭点在y轴上的偏差像素值
            baseDis = distance[0]
            for idx in range(1, len(distance)):
                otherFoot = self.vanishPoint - foot[idx]
                otherDis = distance[idx]
                grad += (baseDis*np.cos(self.perPixelRad*(-baseFoot + self.vanishPoint) + self.vanishAngle) - otherDis*np.cos(self.perPixelRad*(-otherFoot + self.vanishPoint) + self.vanishAngle))*(-2*baseDis*self.perPixelRad*np.sin(self.perPixelRad*(-baseFoot + self.vanishPoint) + self.vanishAngle) + 2*otherDis*self.perPixelRad*np.sin(self.perPixelRad*(-otherFoot + self.vanishPoint) + self.vanishAngle))
        return grad

    def estimateBaseAngleByIteration(self,):  # 梯度下降
        vanishOp = AdamOptimizer(self.vanishPoint) # 灭点优化器
        # 用于提前结束迭代
        lastLoss = None # 上一次误差
        thresholdLoss = 1e-4 # 度量单位: 1大概是m，1e-2大概是cm
        bestModelVote = [] # 用于模型投票
        bestModel = None
        minloss = np.inf

        for epoch in range(20000): # 最大循环2000次
            loss = self.calLoss() # 误差
            grad = self.calGradient() # 梯度
            self.vanishPoint = vanishOp(grad) # 更新
            if lastLoss is None:
                lastLoss = loss
            else:
                if loss < minloss:  # 默认测试集误差最小的是最佳模型
                    minloss = loss
                    bestModel = (self.vanishPoint,loss)
                if len(bestModelVote)==10: # 只统计最近10次损失变化
                    bestModelVote.pop(0)
                bestModelVote.append(loss - lastLoss)
                lastLoss = loss

            bestModelVoteNp = np.array(bestModelVote)
            if np.sum(np.abs(bestModelVoteNp)<thresholdLoss) == 10: # 如果test误差变化量连续10次小于阈值，退出训练
                break
            # 如果测试集只有有一个噪声，但噪声的误差过大，如果某次偶然，让噪声误差很小，足以抵消正常值误差过大，就会得到不好的模型
            if np.sum(bestModelVoteNp>0) == 10:  # 连续10次增加
                break
            elif np.sum(bestModelVoteNp) <=10: # 10次有增有减且总体减少
                bestModel = (self.vanishPoint,loss)
            else:  # 10次有增有减且总体增加
                pass
        self.vanishPoint,loss = bestModel
        loss = np.sqrt(loss) # m**2 -> m
        return (self.vanishPoint, loss)
    def dataInit(self, data):
        dataInit = []
        for group in data:
            radarX, radarY, boxHeadY, boxFootX, boxFootY = group[:, 0], group[:, 1], group[:, 2], group[:, 3], group[:, 4]
            dataInit.append( [radarY,boxHeadY,boxFootY])
        return dataInit
    def run(self, data):
        self.data = self.dataInit(data)
        return self.estimateBaseAngleByIteration()

# ransac 模型拟合
class ModelClass():
    def __init__(self,perPixelRad):
        # 模型参数
        self.vanishPoint = None
        self.perPixelRad =perPixelRad
        self.vanishAngle = np.pi * 0.5
    def __call__(self, data): # 计算误差,内点
        data = self.dataInit(data)
        distance = np.array([], dtype=np.float64)
        boxFoot = np.array([], dtype=np.float64)
        for group in data:
            dis, head, foot = group
            distance = np.concatenate([distance, dis])
            boxFoot = np.concatenate([boxFoot, foot])

        label =   self.footF(distance)
        error1 = self.foot1F(distance)
        error2 = self.foot2F(distance)
        maxV = np.max([label, error1], axis=0)
        minV = np.min([label, error1], axis=0)
        mask1 = (boxFoot <= maxV) & (boxFoot >= minV)
        maxV = np.max([label, error2], axis=0)
        minV = np.min([label, error2], axis=0)
        mask2 = (boxFoot <= maxV) & (boxFoot >= minV)
        mask =  mask1|mask2
        # plt.figure(1)
        # x = np.arange(1, 1000)
        # x = distance
        # idx = np.argsort(x)
        # x = distance[idx]
        # plt.plot(x, self.footF(x), label="Head")
        # plt.plot(x, self.foot1F(x), label="Foot")
        # plt.plot(x, self.foot2F(x), label="Foot")
        # plt.scatter(x, boxFoot[idx], label="(x)")
        # print(np.sum(mask),np.sum(mask1),np.sum(mask2))
        # plt.show()
        mask = mask[0::2] & mask[1::2] # 平面两个点都是内点才是好平面
        return mask




    def getVxFov(self,x, data, v,h):
        data = self.dataInit(data)
        vanishAngle = np.pi * 0.5  # 灭点方向于杆的夹角
        loss = []
        for group in data:
            distance, _, foot = group
            pixelOffset = v  - foot  # 框底与灭点在y轴上的偏差像素值
            baseAng = vanishAngle + pixelOffset[0] * x
            baseDis = distance[0]
            for idx in range(1, len(distance)):
                otherAng = vanishAngle + pixelOffset[idx] * x
                otherDis = distance[idx]
                loss.append(( baseDis * np.cos(baseAng) - h) ** 2)
                loss.append((otherDis * np.cos(otherAng) - h) ** 2)
        return np.mean(loss)


    # def __call__(self, data,t): # 计算误差,内点
    #     self.data = self.dataInit(data)
    #     mask = []
    #     for group in self.data:
    #         distance, _, foot = group
    #         pixelOffset = self.vanishPoint - foot  # 框底与灭点在y轴上的偏差像素值
    #
    #         baseAng = self.vanishAngle + pixelOffset[0] * self.perPixelRad
    #         baseDis = distance[0]
    #
    #         otherAng = self.vanishAngle + pixelOffset[1]* self.perPixelRad
    #         otherDis = distance[1]
    #
    #         angleDiff = abs(baseAng-otherAng) # 夹角
    #         c = np.sqrt(baseDis ** 2 + otherDis ** 2 - 2 * (baseDis * otherDis) * cos(angleDiff)) # 两边距离
    #         loss = abs(baseDis * np.cos(baseAng) - otherDis * np.cos(otherAng)) # 误差
    #         k = abs(np.arcsin(loss / c)) # 平面斜率
    #         if t is None:
    #             mask.append(k < np.deg2rad(0.5)) # 远距离误差用斜率比较好
    #         else:
    #             mask.append(loss < t) # m**2 -> m 近距离误差用m比较好
    #     return np.array(mask,dtype=np.bool_)

    def fitFunc(self, x, a, b): # 拟合函数
        return a / x + b

    def lambdaFitFunc(self,x,y):
        args, _ = curve_fit(self.fitFunc, x, y)
        a,b=args
        if a <= 0:
            return (None,None,None)
        else:
            return (lambda v: a / v + b,a,b)

    def dataInit(self,data):
        dataInit = []
        for group in data:
            radarX, radarY, boxHeadY, boxFootX, boxFootY = group[:, 0], group[:, 1], group[:, 2], group[:, 3], group[:,4]
            dataInit.append([radarY, boxHeadY, boxFootY])
        return dataInit



    def getVanishY(self,):
        distance = np.array([],dtype=np.float64)
        boxHead =  np.array([],dtype=np.float64)
        boxFoot =  np.array([],dtype=np.float64)
        for group in self.data:
            dis,head,foot = group
            distance= np.concatenate([distance,dis])
            boxHead = np.concatenate([boxHead, head])
            boxFoot = np.concatenate([boxFoot, foot])
        try:
            headF, headA, headB = self.lambdaFitFunc( distance, boxHead)
            footF, footA, footB = self.lambdaFitFunc( distance, boxFoot)
            diffF, diffA, diffB = self.lambdaFitFunc( distance, boxFoot-boxHead)
            x = np.arange(1, 1000)
            plt.figure(1)
            plt.plot(x, headA / x + headB,label="Head")
            plt.plot(x, footA / x + footB,label="Foot")
            plt.plot(x, diffA / x + diffB)
            y = 1e-8
            x = diffA * (y - diffB)
            print(diffA, diffB )
            print((headF(x) + footF(x)) / 2)
            plt.legend()
            plt.show()
            # 由于框可能上下抖动，交点并没有做差稳定
            # x=(headA-footA)/(footB-headB)
            if headA is None or footA is None or diffA is None:
                xypDebug("fit fail")
                return None
            self.footF = footF
            # 误差主要来源于角度，雷达测距误差小
            self.foot1F, _, _ = self.lambdaFitFunc(distance, boxFoot + 3)
            self.foot2F, _, _ = self.lambdaFitFunc(distance, boxFoot - 3)

            y = 1e-8
            x = diffA * (y-diffB)

            return  (headF(x) + footF(x))/2
        except Exception as e :
            xypDebug("fit error", e)
            return None
    def createModel(self,data):
        self.data= self.dataInit(data)
        self.vanishPoint = self.getVanishY()




def sampleFunc(data, sampleNum=50):
    minV = np.min(data)
    maxV = np.max(data)
    dataNum = len(data)

    data = np.array(data)
    dataIdx = np.arange(dataNum,dtype=np.int64)


    sample = np.array([])  # 记录采样点
    sampleIdx = np.array([],dtype=np.int64)  # 记录采样点下标
    section = np.linspace(minV, maxV, sampleNum + 1, endpoint=True)    # 最小值到最大值均匀划分区间
    section[-1] += 1e-8  # 加值是为了保证最后区间能将数据最大值能参与采样
    for i in range(sampleNum):
        sampleData = data[(section[i] <= data) & (data < section[i + 1])]
        sampleDataIdx = dataIdx[(section[i] <= data) & (data < section[i + 1])]
        DataNum = len(sampleData)
        if DataNum >=1:  # 区间数据为0
            idx = np.random.choice(sampleDataIdx, 1, replace=False)
            sample = np.concatenate([sample, data[idx]])
            sampleIdx = np.concatenate([sampleIdx, idx])

    # plt.plot(sorted(data),c="r")
    # plt.figure(0)
    # plt.hist(sorted(data), bins=250, color='blue', alpha=0.7)
    # plt.xlim(0,100)
    # plt.ylim(0,20)
    # plt.figure(1)
    # plt.hist(sorted(data[sampleIdx]), bins=250, color='r', alpha=0.7)
    # plt.xlim(0, 100)
    # plt.ylim(0, 20)
    # plt.show()
    return sample, sampleIdx


def ransac(data, camConfig, epochNum=200, sampleNum=8,threshold=1):
    # data = data[data[:, 1] <80]
    dataNum = len(data)
    # 由近到远排序
    data = data[np.argsort(data[:, 1])]
    radarX, radarY, boxHeadY, boxFootX, boxFootY = data[:, 0], data[:, 1], data[:, 2], data[:, 3], data[:, 4]
    maxLenth = 20
    bestModel = None  # 保存最佳模型
    for repeatIdx in range(6):
        # np.random.seed(None)
        xypDebug(f"第{repeatIdx}次运行")

        maxLenth -= 3 # 平面最大长度
        minLenth = 1 # 平面最小长度
        planeGroup = []
        for i in range(dataNum - 1):
            # 平面的两个边缘
            planeEdge0 = i
            planeEdge1 = None
            lastMaxLenth = 0
            for j in range(i + 1, dataNum):
                angleDiff = abs(boxFootY[j] - boxFootY[i]) * camConfig['rad_per_pixel']  # 夹角
                diff = np.sqrt(radarY[i]**2+radarY[j]**2-2*radarY[i]*radarY[j] *np.cos(angleDiff)) # 两点之间距离
                if minLenth < diff and diff < maxLenth and lastMaxLenth<diff:
                    planeEdge1=j
                    lastMaxLenth=diff
                else:
                    pass
            if planeEdge1 is not None:
                planeGroup.append(data[[planeEdge0, planeEdge1]])

        # distance = np.array([], dtype=np.float64)
        # boxHead = np.array([], dtype=np.float64)
        # boxFoot = np.array([], dtype=np.float64)
        # temp= ModelClass(1)
        # for group in planeGroup:
        #     dis, head, foot = temp.dataInit(group)
        #     distance = np.concatenate([distance, dis])
        #     boxHead = np.concatenate([boxHead, head])
        #     boxFoot = np.concatenate([boxFoot, foot])
        # seq=np.argsort(distance)
        # distance = distance[seq]
        # boxHead =boxHead [seq]
        # boxFoot =boxFoot [seq]
        #
        # plt.plot(distance,boxFoot)
        # plt.plot(distance, boxHead)
        # # plt.plot(distance, boxFoot-boxHead)
        # plt.ylim(0, 500)
        # plt.xlim(0, 90)
        # plt.xlabel("radar dis")
        # plt.ylabel("image coord y")
        # plt.pause(0.1)


        # 3
        planeGroup = np.array(planeGroup)
        planeGroupNum = len(planeGroup)

        if planeGroupNum >30:
            planeCenter = np.mean(planeGroup[:, :, 1], axis=1)
            _,idx =  sampleFunc(planeCenter, sampleNum=30)
            planeGroup=planeGroup[idx]
            planeGroupNum = len(planeGroup)


        # planeCenter = np.mean(planeGroup[:,:,1],axis=1)
        # minDis = np.min(planeCenter)
        # maxDis = np.max(planeCenter)
        #
        # planeSampleNum=int((maxDis-minDis)//minLenth) # 每隔最小平面采样一个平面
        # mask=sampleFunc(planeCenter,planeSampleNum)
        # if mask is None:
        #     print("sampleFunc error")
        #     continue
        #
        # else:
        #     mask = mask[1]
        # planeGroup = planeGroup[mask]

        # 比如ransac要让0.8的数据满足条件，但采样数量肯定不能接近0.8，一般是三分之一的数据推测
        # 因为如果采样数接近数据数，采样就没了意义，n个采样要推出3n个内点，且3n个内点要大于ratio的数据
        ratio = 0.8
        thresholdNum = int(round(planeGroupNum*ratio,0))
        sampleNum = int(round(planeGroupNum*ratio/3,0))
        if sampleNum < 3: # 不满足数量，调整平面参数并重运行
            xypDebug(f"平面数据数不足，数据数{planeGroupNum}，阈值{sampleNum}")
            continue
        xypDebug(f"平面数据数:{planeGroupNum}")


        nowLoss = np.inf # 记录当前误差
        breakVote = 0
        inlierNumHistory = [] # 内点数历史记录
        # [47, 64, 69, 79, 80, 82, 88, 99]
        # ghnyhn
        # [2, 18, 47, 67, 69, 71, 75, 76]
        # [9, 21, 36, 64, 67, 67, 83, 87]
        # ghnyhn
        # [13, 44, 45, 53, 62, 77, 91, 91]
        # print(sorted(np.random.choice(100,8)),"ghnyhn")
        # np.random.seed(None)
        # print(sorted(np.random.choice(100, 8)), "ghnyhn")
        for i in range(epochNum):
            modelClass = ModelClass(camConfig['rad_per_pixel'])
            # 数据采样，拟合灭点，对所有平面最佳
            for repeatNum in range(8):
                # 数据随便采, 提高内点阈值就行，如0.8
                sampleIdx = np.random.choice(planeGroupNum, sampleNum, replace=False)
                samplePlane = planeGroup[sampleIdx]
                modelClass.createModel(samplePlane) # 用采样数据计算模型参数
                if modelClass.vanishPoint is not None:
                    break
            if modelClass.vanishPoint is None:
                xypDebug(f"随机采样估计模型失败")
                continue
            # 通过最佳灭点计算灭点适用的平面，这些平面几乎平行
            inlierMask = modelClass(planeGroup) # 计算模型误差与内点
            inlierNum = np.sum(inlierMask)
            inlierNumHistory.append(inlierNum)
            # 虽然采样数据是为了拟合一个反函数，且是真实分布，但是内点数量满足要求必须从整体数量来看，才能选出最合适的灭点
            if inlierNum>=thresholdNum:
                breakVote += 1
                inlierplaneGroup = planeGroup[inlierMask]
                a = Refine(camConfig['rad_per_pixel'], vanishPoint=modelClass.vanishPoint)
                data = a.run(inlierplaneGroup)
                v,loss = data
                if loss <= nowLoss: # 保存最优模型
                    breakVote = 0
                    nowLoss = loss
                    solutions = minimize(modelClass.getVxFov, x0=0.000001, args=(inlierplaneGroup, v, 2.2))
                    bestModel = (v,np.rad2deg(solutions.x*450))
            # breakVote：好的模型不应该反复被替代
            if bestModel is not None and breakVote>20:
                xypDebug(f"第{repeatIdx}次运行模型估计成功，提前结束，迭代数：{i}，最大、最小、平均、阈值内点数：{np.max(inlierNumHistory),np.min(inlierNumHistory), round(np.mean(inlierNumHistory),2),thresholdNum}")
                return bestModel
        xypDebug(f"第{repeatIdx}次运行模型估计失败，最大、最小、平均、阈值内点数：{np.max(inlierNumHistory), np.min(inlierNumHistory), round(np.mean(inlierNumHistory),2),thresholdNum}")

    if bestModel is not None:
        xypDebug(f"模型估计成功，但不是提前结束，值得注意")
        return bestModel
    else:
        xypDebug(f"模型估计失败")
        return None


class ClibLog():
    def __init__(self,logPath, imageDefences,timeArea):
        Polygon_zzl.init_inside_so()
        self.nearCamImageShape = (800, 450)  # (X,Y)
        self.farCamImageShape = (800, 450)  # (X,Y)
        # 数据有效范围
        self.cameraWorldDefence0 = ((-20, 20), (0, 70))  # ((minX,maxX),(minY,maxY)),单位m
        self.cameraWorldDefence1 = ((-20, 20), (70, 250))  # ((minX,maxX),(minY,maxY)),单位m
        # 有效范围
        self.cameraImageDefence0,self.cameraImageDefence1= imageDefences
        self.startTime, self.endTime = timeArea
        self.path = logPath
        if isinstance(self.path, str):
            self.printPath = os.path.basename(self.path)
        else:
            self.printPath = []
            for p in self.path:
                self.printPath.append(os.path.basename(p))


    @staticmethod
    def addAlignByTime(*dataSet, allowSpanTime=1.0 / 8.0, ):  # 通过时间对齐帧，以第一组数据的时间为基准
        # dataSet中每个元素都是是按帧划分的数据，如dataSet[0]格式为：[[time,data],...]
        # allowSpanTime匹配的最小时间差距不超过的秒数，如数据帧率中最快的是1/8秒，就设置为1/8秒，即不能跳帧匹配
        alignData = np.array(dataSet[0], dtype=object)  # [[time,data],...]
        # 兼容pandas==0.22.0
        alignData = pd.DataFrame(OrderedDict([('timestamp', alignData[:, 0]),
                                              ('data', alignData[:, 1])]))  # 兼容写法，要有序序列，否则生成DataFrame
        alignData = alignData.sort_values(by='timestamp')
        for i in range(1, len(dataSet)):  # 循环其他数据
            newData = np.array(dataSet[i], dtype=object)  # [[time,data],...]
            newData = pd.DataFrame(OrderedDict([('timestamp', newData[:, 0]),
                                                ('data', newData[:, 1])]))
            newData = newData.sort_values(by='timestamp')
            alignData = pd.merge_asof(alignData, newData, on='timestamp', direction='nearest',
                                      suffixes=(str(i - 1), str(i)),
                                      tolerance=pd.Timedelta('{} milliseconds'.format(allowSpanTime * 1000)))

        # alignData = alignData.to_numpy()
        alignData = alignData.dropna()  # 删除有nan值的
        alignData = alignData.values  # 兼容写法，获取numpy类型数据
        return alignData

    @staticmethod
    def removeOutlierByGaussian(data, multiple=1):
        if isinstance(data, list):
            data = np.array(data)
        # 针对二维及以下数据的每个属性Attribute进行高斯过滤,获取满足所有高斯multiple倍标准差的数据mask
        # data:一维数据,形状[dataNum],将被广播为[dataNum,AttributeNum=1];二维数据,形状[dataNum,AttributeNum]
        # t:形状[AttributeNum,2->min,max]
        dataShape = data.shape
        if len(dataShape) == 1:
            data = data.reshape(-1, 1)
            dataShape = data.shape
        axis = 1  # 目前开发要求只需针对列进行处理
        attributeNum = dataShape[axis]  # 获取属性数量
        mask = None
        for i in range(attributeNum):
            sliceData = data.take(i, axis)  # 提取axis维度上第i组数据
            dataAvg = np.mean(sliceData)
            dataStd = np.std(sliceData)
            if mask is None:
                mask = (np.abs(sliceData - dataAvg) <= multiple * dataStd)
            else:
                mask &= (np.abs(sliceData - dataAvg) <= multiple * dataStd)
        return mask

    @staticmethod
    def removeOutlierByThreshold(data, t=((-np.inf, np.inf),)):
        # 针对二维及以下数据的每个属性Attribute设置阈值,获取满足所有阈值的数据mask
        # data:一维数据,形状[dataNum],将被广播为[dataNum,AttributeNum=1];二维数据,形状[dataNum,AttributeNum]
        # t:形状[AttributeNum,2->min,max]
        dataShape = data.shape
        if len(dataShape) == 1:
            data = data.reshape(-1, 1)
            dataShape = data.shape
        axis = 1  # 目前开发要求只需针对列进行处理
        attributeNum = dataShape[axis]  # 获取属性数量
        # 如果t是一维序列转为2维序列
        if isinstance(t, (list, np.ndarray, tuple)):
            if isinstance(t[0], (list, np.ndarray, tuple)):  # t已经是二维序列
                pass
            else:
                t = [t]
        if len(t) == 1:  # 如果阈值范围只有一个，复制
            t = [t[0]] * attributeNum
        mask = None
        for i in range(attributeNum):
            sliceData = data.take(i, axis)  # 提取axis维度上第i组数据
            if mask is None:
                mask = (sliceData > t[i][0]) & (sliceData < t[i][1])
            else:
                mask &= (sliceData > t[i][0]) & (sliceData < t[i][1])
        return mask

    @staticmethod
    def subAlignByTime(*args):
        # 每个数据都是[[time,[...]],...]
        alignData = np.array(args[0], dtype=object)
        for i in range(1, len(args)):
            newData = np.array(args[i], dtype=object)
            # 每个数据都是[[time,[...]],...]
            changePosFlag = False  # 如果交换顺序了，返回newData,alignData
            if len(alignData) < len(newData):
                dataQuery, dataValue = alignData, newData
            else:
                changePosFlag = True
                dataQuery, dataValue = newData, alignData

            dataQueryTime = np.array([i[0] for i in dataQuery])
            dataValueTime = np.array([i[0] for i in dataValue])

            dataQueryIndex = []
            dataValueIndex = []
            for qtIdx, qt in enumerate(dataQueryTime):
                disTime = np.abs(dataValueTime - qt)  # 计算差距
                vtIdx = np.argmin(disTime)
                if disTime[vtIdx] < 1.0 / 8.0:  # 最小且差距不超过1/8秒，数据帧率中最快的是1/8，即不能跳帧匹配
                    dataQueryIndex.append(qtIdx)
                    dataValueIndex.append(vtIdx)
            dataQuery = dataQuery[dataQueryIndex]
            dataValue = dataValue[dataValueIndex]
            if changePosFlag:
                data = []
                for i in zip(dataValue, dataQuery):
                    d = i[0].tolist()
                    d.append(i[1][1])
                    data.append(d)
                alignData = np.array(data, dtype=object)
            else:
                data = []
                for i in zip(dataQuery, dataValue):
                    d = i[0].tolist()
                    d.append(i[1][1])
                    data.append(d)
                alignData = np.array(data, dtype=object)
        return alignData


    def analyseLog(self,):
        # 解析日志内容:param path: 日志位置
        camera0BoxData = []
        camera1BoxData = []
        radarData = []
        if isinstance(self.path, str):
            with open(self.path, "r") as f:
                data = f.read()
        else:
            data = ''
            for p in self.path:
                with open(p, "r") as f:
                    data = data + f.read() + "\n"
        # 寻找雷达数据
        radarDataRule = re.compile("input_radar.*]]]\n")
        radarInputData = re.findall(radarDataRule, data)
        radarFrameRule = re.compile(r"[-+]?\d+\.?\d*[eE]?[-+]?\d*")  # 存在科学计数法

        for r in radarInputData:
            radarFrame = re.findall(radarFrameRule, r)  # 获取雷达帧数据
            timeStamp = datetime.datetime.fromtimestamp(float(radarFrame[0]))
            if self.startTime <= timeStamp and timeStamp <= self.endTime:
                radarData.append([timeStamp,
                                  [[float(radarFrame[j + 1]), float(radarFrame[j + 2])] for j in
                                   range(1, len(radarFrame), 5)]])

        # 寻找camera数据
        cameraDataRule = re.compile("input_camera.*, 'stamp': .*\n")
        cameraData = re.findall(cameraDataRule, data)
        cameraBoxRule = re.compile("\([+-]?\d+, [+-]?\d+, [+-]?\d+, [+-]?\d+\)")  # 寻找bbox数据
        for c in cameraData:
            cams = c.split("'id': ")  # 划分相机数据
            delay = 0
            for cc in cams:  # 循环每个相机数据
                if cc[0] == "0":  # 相机id
                    timeStamp = datetime.datetime.fromtimestamp(float(cc.split(", 'stamp': ")[-1][:-2]))-datetime.timedelta(seconds=delay)
                    if self.startTime <= timeStamp and timeStamp <= self.endTime:
                        cameraBoxData = [[float(k) for k in box[1:-1].split(", ")] for box in re.findall(cameraBoxRule, cc)]
                        camera0BoxData.append([timeStamp, cameraBoxData])
                elif cc[0] == "1":
                    timeStamp = datetime.datetime.fromtimestamp(float(cc.split(", 'stamp': ")[-1][:-2]))-datetime.timedelta(seconds=delay)
                    if self.startTime <= timeStamp and timeStamp<= self.endTime:
                        cameraBoxData = [[float(k) for k in box[1:-1].split(", ")] for box in
                                         re.findall(cameraBoxRule, cc)]
                        camera1BoxData.append([timeStamp, cameraBoxData])


        logData = {
            "radarData": radarData,
            "camera0BoxData": camera0BoxData,
            "camera1BoxData": camera1BoxData,
        }
        return logData

    def removeOutlierByInDenfence(self,imageDefence,data):
        mask = []
        for  pos in data:
            inFlag = False
            for area_polygon in imageDefence:
                inFlag =Polygon_zzl.isPointIntersectPoly_by_so(pos, area_polygon.data_list_800_450)
                if inFlag:
                    mask.append(inFlag)
                    break
            if not inFlag:
                mask.append(inFlag)
        return np.array(mask)
    def cleanLog(self, logData, camera=0):
        # 每个数据都是[time,[]]
        if camera == 0:
            imageDefence = self.cameraImageDefence0
            worldRangeX, worldRangeY = self.cameraWorldDefence0
            radarData = logData["radarData"]
            cameraBoxData = logData["camera0BoxData"]
        else:
            imageDefence =  self.cameraImageDefence1
            worldRangeX, worldRangeY = self.cameraWorldDefence1
            radarData = logData["radarData"]
            cameraBoxData = logData["camera1BoxData"]

        thresholdNum = 3  # 每个日志找的是一组数据而不是一个个点
        if len(radarData) > 0 and len(cameraBoxData) > 0:
            xypDebug(f"camera{camera} 初始数据数：{len(radarData)}，文件：{self.printPath}")
            # 数据根据时间对齐
            data = self.addAlignByTime(radarData, cameraBoxData)
            if len(data) < thresholdNum:
                xypDebug(f"camera{camera} 对齐数据数不足，数据数：{len(data)}，阈值：{thresholdNum}，文件：{self.printPath}")
                return None
            xypDebug(f"camera{camera} 对齐数据数：{len(data)}，文件：{self.printPath}")
        else:
            xypDebug(f"camera{camera} 初始数据数不足，数据数：{0}，阈值：{0}，文件：{self.printPath}")
            return None

        # 提取用于计算过滤的数据，只用第一个目标，即同一时刻只用一个目标
        radarX = np.array([i[1][0][0] for i in data])
        radarY = np.array([i[1][0][1] for i in data])
        try:
            boxX = np.array([i[2][0][0] for i in data])
        except:

            pass
        boxY = np.array([i[2][0][1] for i in data])
        boxW = np.array([i[2][0][2] for i in data])
        boxH = np.array([i[2][0][3] for i in data])
        # 人脚位置
        boxFootX = boxX + boxW * 0.5
        boxFootY = boxY + boxH
        times = np.array([i[0] for i in data])
        # times2 = np.array([i[0] for i in data])
        # 异常值过滤
        # 雷达距离明显异常的点
        mask1 = self.removeOutlierByThreshold(radarX, worldRangeX)
        mask2 = self.removeOutlierByThreshold(radarY, worldRangeY)
        # 不在视觉防区的点
        mask5 = self.removeOutlierByInDenfence(imageDefence,np.stack([boxFootX,boxFootY],axis=1))
        # 人像框不完整点
        mask6 = boxH > boxW * 2  # 高大于n倍宽
        mask = mask1 & mask2 & mask5  & mask6
        xypDebug(f"camera{camera} 防区内数据数：{np.sum(mask)}，文件：{self.printPath}")
        if np.sum(mask) < thresholdNum:
            xypDebug(f"camera{camera} 防区内数据数不足，数据数{np.sum(mask)}，阈值{thresholdNum}，文件：{self.printPath}")
            return None

        radarX = radarX[mask]
        radarY = radarY[mask]
        boxW = boxW[mask]
        boxH = boxH[mask]
        boxFootX = boxFootX[mask]
        boxFootY = boxFootY[mask]
        times = times[mask]

        epochNum = 3  # 认为跳跃至少epochNum个点稳定, 不满足该值则属于闪现之类的误报，否则认为是新目标（或被遮挡后重新出现）出现
        indexGood = np.arange(len(times))  # 元素索引
        for i in range(epochNum):
            # 计算速度
            timeDiff = np.array([i.total_seconds() for i in (times[indexGood][1:] - times[indexGood][:-1])])
            radarVelDiffX = (radarX[indexGood][1:] - radarX[indexGood][:-1]) / timeDiff
            radarVelDiffY = (radarY[indexGood][1:] - radarY[indexGood][:-1]) / timeDiff
            vel = np.sqrt(radarVelDiffX **2 + radarVelDiffY**2)
            # 只要纵向移动速度
            # radarVelDiffY = (radarY[indexGood][1:] - radarY[indexGood][:-1]) / timeDiff
            # vel = np.sqrt(radarVelDiffY ** 2)
            mask = (vel <= 3.5) & (vel >= 0.83) # 3 公里到 12公里的时速
            mask = np.concatenate([[mask[0]], mask])  # 不抛弃
            if np.sum(mask) < thresholdNum:
                xypDebug(f"camera{camera} 位置合理数据数不足，数据数：{np.sum(mask)}，阈值：{thresholdNum}，文件：{self.printPath}")
                return None
            else:
                indexGood = indexGood[mask]
        xypDebug(f"camera{camera} 位置合理数据数：{np.sum(mask)}，文件：{self.printPath}")

        radarX = radarX[indexGood]
        radarY = radarY[indexGood]
        boxW = boxW[indexGood]
        boxH = boxH[indexGood]
        boxFootX = boxFootX[indexGood]
        boxFootY = boxFootY[indexGood]
        times = times[indexGood]

        # 后期图像框会按距离排序，所以可能会造成不同升高的生物乱入，所以数据按时间差分组，确保目标不变稳定图像框波动，并改善在高斯滤波中前面值受后面加入的值的影响
        tenSplit = 10 # tenSplits秒一个组
        group = []
        groupIdx = 0
        group.append(groupIdx)
        timeDiff = np.array([i.total_seconds() for i in (times[1:] - times[:-1])])
        for td in timeDiff:
            if td > tenSplit:  # 间隔超过tenSplit秒分一组
                groupIdx += 1
            group.append(groupIdx)
        group = np.array(group)

        # group2 = []
        # groupIdx2 = 0
        # group2.append(groupIdx2)
        # print(times2[0])
        # print(times2[1000])
        # print(times2[-1])
        # print("222222222222222")
        # print(times[0])
        # print(times[-1])
        # timeDiff2 = np.array([i.total_seconds() for i in (times2[1:] - times2[:-1])])
        # for td in timeDiff2:
        #     if td > tenSplit:  # 间隔超过tenSplit秒分一组
        #         groupIdx2 += 1
        #     group2.append(groupIdx2)
        # group2 = np.array(group2)
        # a = plt.figure(0)
        # plt.plot(group2)
        # a=plt.figure(1)
        # plt.plot(group)
        # plt.show()
        minGroupSize = tenSplit # 平均每秒至少1个数据
        gusNum = 3
        indexAll = np.arange(len(radarY))  # 元素索引
        indexGood = []
        littleGroup = np.array([], dtype=np.int64)
        for g in range(groupIdx + 1):
            # print(f"小组{g}: {np.sum(group == g)}")
            index = indexAll[group == g]
            # 可能不是很好的数据，数据紧缺时考虑
            # if len(index) < minGroupSize:
            #     littleGroup=np.concatenate([littleGroup,index])
            #     if len(littleGroup)>=minGroupSize:
            #         index = littleGroup
            #         littleGroup = np.array([],dtype=np.int64)
            if len(index) >= minGroupSize:
                for _ in range(gusNum):  # 认为跳跃点至少出现gusNum次才能算是稳定的,针对不同目标
                    multiple = 3
                    # DiffY[1:] 后面减自己的距离
                    # DiffY[:-1] 自己减前面的距离
                    def getMask(data):
                        # 全部忽略方向
                        # 后面元素减前面元素计算位移
                        diff = np.abs(data[1:] - data[:-1])
                        # 位移波动
                        mask1 = self.removeOutlierByGaussian(np.abs(diff[1:] - diff[:-1]), multiple)
                        # 位移大小
                        mask2 = self.removeOutlierByGaussian(diff[1:] + diff[:-1], multiple)
                        return mask1 & mask2
                    # 目标框位置稳定性
                    mask3 = getMask(boxFootY[index])
                    mask4 = getMask(boxFootX[index])
                    # 目标框大小稳定性
                    mask13 = self.removeOutlierByGaussian(boxH[index][1:-1], multiple)
                    mask14 = self.removeOutlierByGaussian(boxW[index][1:-1], multiple)
                    mask = mask3 & mask4 & mask13 & mask14
                    mask = np.concatenate([[mask[0]], mask, [mask[-1]]])  # 不抛弃
                    if np.sum(mask) < thresholdNum:
                        index = None
                        # print(f"小组{g}: 0")
                        break
                    index = index[mask]
                if index is not None:
                    # print(f"小组{g}: {len(index)}")
                    indexGood.append(index)

        if len(indexGood) == 0:
            xypDebug(f"camera{camera} 分布合理数据数不足，数据数：{0}，阈值：{0}，文件：{self.printPath}")
            return None
        else:
            index = np.concatenate(indexGood)
            xypDebug(f"camera{camera} 分布合理数据数：{len(index)}，文件：{self.printPath}")


        radarX = radarX[index]
        radarY = radarY[index]
        boxFootX = boxFootX[index]
        boxFootY = boxFootY[index]
        boxW = boxW[index]
        boxH = boxH[index]
        boxHeadY = boxFootY - boxH

        if len(radarX) >= thresholdNum:  # 上面的过滤是要找合群的一组数据，而不是几个点
            cleanData = {
                "boxTXB": np.stack([boxHeadY, boxFootX, boxFootY], axis=1),
                "radarXY": np.stack([radarX, radarY], axis=1),
            }
            # timeTool.reckon("cleanDatas7")
            return cleanData
        else:
            return None

        # matShow()
        # if False:  # debug
        #     displayVideoWithBox(data, r"C:\Users\admins\Desktop\guardData\0824\1\0.mp4")
        #     # displayVideoWithBox(data,r"C:\Users\admins\Desktop\guardData\0824\20230824_172149_i23_topLineB.mp4")
        # if len(radarX)>=thresholdNum: # 上面的过滤是要找合群的一组数据，而不是几个点
        #     cleanData = {
        #         "radarXY": np.stack([radarX,radarY],axis=1),
        #         "imageXY": np.stack([boxFootX,boxFootY],axis=1),
        #         "boxHeadY": np.stack([boxHeadX, boxHeadY], axis=1),
        #     }
        #     #timeTool.reckon("cleanDatas7")
        #     return cleanData
        # else:
        #     return None

    @staticmethod
    def sortLogFile(logPath,timeArea):
        files = os.walk(logPath)
        logPathList = []
        for i in files:
            currentFolderDirs, sonFolderNames, sonFileNames = i
            for sfn in sonFileNames:
                if ".log" in sfn:
                    logPathList.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
        logPathList = np.array(logPathList)

        np.random.shuffle(logPathList)
        timeInfo = []
        for p in logPathList:
            logName = os.path.basename(p)
            if ".log." in logName:
                minus,other = logName.split(".log.")
                other = other+minus[-2:]
                logStartTime = datetime.datetime.strptime(other, '%Y-%m-%d_%H%M')
            else:
                logStartTime = datetime.datetime.strptime(logName, 'system_%Y%m%d_%H%M.log')
            logEndTime = logStartTime + datetime.timedelta(hours=1)


            if not (logEndTime < timeArea[0] or timeArea[1] < logStartTime):
                timeInfo.append(logStartTime)

        logNum = len(timeInfo)
        if logNum == 0:
            xypDebug("没有日志在搜索时间范围内")
            return []
        else:
            xypDebug(f"有{logNum}个日志在搜索时间范围内")
            idx = np.argsort(timeInfo)[::-1]
            logPathList = logPathList[idx]
            return logPathList

class MyProcess(multiprocessing.Process):
    def __init__(self, target, processResult, camStop0, camStop1, *args, **kwargs):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self.processResult = processResult
        self.camStop0 = camStop0
        self.camStop1 = camStop1

    def run(self):
        self.processResult.append(self._target(self.camStop0, self.camStop1, *self._args, **self._kwargs))

class MyProcessPool():
    def __init__(self, maxThreadNum):
        if maxThreadNum < 1:
            raise None
        self.maxThreadNum = maxThreadNum
        self.threadWait = []
        self.threadRun = []
        self.runningFlag = False
        # 相机数据
        self.camResult0 = np.zeros((0,5)) # 有形无数据
        self.camResult1 = np.zeros((0,5)) # 有形无数据
        # 进程间相机数据加载完毕标识符
        self.camStop0 = multiprocessing.Value('i', 0)
        self.camStop1 = multiprocessing.Value('i', 0)
        # 进程间相机数据
        self.processResult = multiprocessing.Manager().list()
        self.threadWaitLock = threading.Lock()
        self.resResLock = threading.Lock()

    def managerThread(self):  # 管理线程的等待和运行
        while self.runningFlag:
            start = time.time()
            while len(self.threadRun) < self.maxThreadNum:  # 如果有空位将等待的线程启动
                if len(self.threadWait) > 0:
                    with self.threadWaitLock:
                        t = self.threadWait.pop(0)
                    self.threadRun.append(t)
                    t.start()
                else:
                    break

            # 处理运行完成的线程
            for idx in range(len(self.threadRun) - 1, -1, -1):
                t = self.threadRun[idx]
                if not t.is_alive():
                    # 暂时不用线程
                    if self.runningFlag:  # 结束后还没运行完成的线程的结果不要了
                        self.mergerRes(self.processResult.pop(0))
                    self.threadRun.pop(idx)
            spendTime = time.time() - start
            # 延迟，合理的延时反而可以增加速度
            if spendTime < 0.01:  # 如果上面有一个条件为真，运行时间一般至少要0.01s
                time.sleep(0.01)

    def sampleFunc(self,data, sampleNum=50):
        nowQuota = 1  # 当前区间配额，如果当前区间没有采样到，将配额留个下一区间
        minV = np.mean(data)
        maxV = np.max(data)
        dataIdx = np.arange(len(data),dtype=np.int64)
        sampleAll = np.array([])  # 记录采样点
        sampleAllIdx = np.array([],dtype=np.int64) # 记录采样点下标
        while sampleNum > 0:
            # 最小值到最大值均匀划分区间
            sample = np.array([])  # 记录采样点
            sampleIdx = np.array([],dtype=np.int64)  # 记录采样点下标
            section = np.linspace(minV, maxV, sampleNum + 1, endpoint=True)
            section[-1] += 1e-8  # 加值是为了保证最后区间能将数据最大值能参与采样
            for i in range(sampleNum):
                sampleArea = data[(section[i] <= data) & (data < section[i + 1])]
                sampleAreaIdx = dataIdx[(section[i] <= data) & (data < section[i + 1])]
                areaNum = len(sampleArea)
                if areaNum == 0:  # 区间数据为0
                    nowQuota = 1 #+ nowQuota  # 1 指的是每个区间默认配额为1
                elif areaNum <= nowQuota:  # 区间数据小于等于配额
                    nowQuota = 1# + (nowQuota - areaNum)
                    sample = np.concatenate([sample, sampleArea])
                    sampleIdx = np.concatenate([sampleIdx, sampleAreaIdx])
                else:  # 区间数据大于配额
                    idx = np.random.choice(sampleAreaIdx, nowQuota, replace=False)
                    sample = np.concatenate([sample, data[idx]])
                    sampleIdx = np.concatenate([sampleIdx, idx])
                    nowQuota = 1  # 每个区间默认配额为1
            sampleNum = sampleNum - len(sample)  # 数据不够重新分区采样
            sampleAll = np.concatenate([sampleAll, sample])
            sampleAllIdx = np.concatenate([sampleAllIdx, sampleIdx])
            nowQuota = 1  # 每个区间默认配额为1

        # plt.plot(sorted(data),c="r")
        # plt.figure(0)
        # plt.hist(sorted(data), bins=250, color='blue', alpha=0.7)
        # plt.xlim(0,100)
        # plt.ylim(0,20)
        # plt.figure(1)
        # plt.hist(sorted(data[sampleAllIdx]), bins=250, color='r', alpha=0.7)
        # plt.xlim(0, 100)
        # plt.ylim(0, 20)
        # plt.show()
        return sampleAll, sampleAllIdx
    def mergerRes(self, res):
        with self.resResLock:
            res0, res1 = res
            if res0 is not None:
                temp = np.concatenate([res0["radarXY"], res0["boxTXB"]], axis=1)
                self.camResult0 = np.concatenate([self.camResult0,temp], axis=0)
            if res1 is not None:
                temp = np.concatenate([res1["radarXY"], res1["boxTXB"]], axis=1)
                self.camResult1 = np.concatenate([self.camResult1, temp], axis=0)

    def addTask(self, func, *args, **kwargs):
        if not self.runningFlag:
            self.runningFlag = True
            threading.Thread(target=self.managerThread).start()
        process = MyProcess(func, self.processResult, self.camStop0, self.camStop1, *args, **kwargs)
        with self.threadWaitLock:
            self.threadWait.append(process)

    def shutdown(self):
        self.runningFlag = False
        with self.threadWaitLock:
            self.threadWait = []
        for p in self.threadRun:
            try:
                p.terminate()
            except Exception as e:
                # 还没启动完成就加入self.threadRun了，待定进程启动完成并没有终止方法
                while True:
                    try:
                        p.terminate()
                        break
                    except:
                        time.sleep(0.01)


def processFunc(camStop0, camStop1, *args, **kwargs):
    path = args[0]
    defences = args[1]
    timeArea = args[2]
    log = ClibLog(path,defences,timeArea)
    logInfo = log.analyseLog()
    return [log.cleanLog(logInfo, 0), log.cleanLog(logInfo, 1)]
    # if camStop0.value ==0 and camStop1.value ==0:
    # elif camStop0.value == 0:
    #     return [log.cleanLog(logInfo,0), None]
    # elif camStop1.value == 0:
    #     return [None, log.cleanLog(logInfo,1)]
    # else:
    #     return [None,None]



def solveVanishPoint(data, camConfig):
    return ransac(data,camConfig)

def calibVanishPoint(logPath, cameraConfig, defences, timeArea = None):
    sss = time.time()
    #  cameraConfig0, cameraConfig1  近焦、远焦
    cameraConfig0, cameraConfig1 = cameraConfig # 获取相机参数
    # 对日志文件按时间进行排序,对数据的限制应该在这里
    if timeArea is None:
        try:
            with open('xypAutoCalibVanishPoint.json', 'r') as file:
                jsonData = file.read()

            jsonData = json.loads(jsonData)
            if jsonData["enable"]:
                startTime = datetime.datetime(jsonData["startTime"]["year"], jsonData["startTime"]["month"],
                                          jsonData["startTime"]["day"], jsonData["startTime"]["hour"],
                                          jsonData["startTime"]["minute"], jsonData["startTime"]["second"])
                endTime = datetime.datetime(jsonData["endTime"]["year"], jsonData["endTime"]["month"],
                                            jsonData["endTime"]["day"],
                                            jsonData["endTime"]["hour"], jsonData["endTime"]["minute"],
                                            jsonData["endTime"]["second"])
                timeArea = [startTime, endTime]
            else:
                endTime = datetime.datetime.now()
                startTime = endTime - datetime.timedelta(hours=2)
                timeArea = [startTime, endTime]
        except Exception as e:# 默认距离现在两小时内的数据
            xypDebug(f"xypAutoCalibVanishPoint.json 出现问题{e}")
            endTime = datetime.datetime.now()
            startTime = endTime - datetime.timedelta(hours=2)
            timeArea = [startTime,endTime]

    xypDebug(f"防区信息：{[i.data_list_800_450 for i in defences[0]],[i.data_list_800_450 for i in defences[1]]}")
    xypDebug(f"数据搜索范围：{timeArea[0]}  -->  {timeArea[1]}")
    logPath = ClibLog.sortLogFile(logPath,timeArea)
    vanishPoint0 = None
    vanishPoint1 = None
    if len(logPath) != 0:
        # 多进程加载数据，假如数据只要前几个日志，进程越多反而越慢，但是日志越往后，进程越大越有利
        processNum = 5
        t = MyProcessPool(processNum) # 创建进程池
        for path in logPath:
            t.addTask(processFunc, path, defences,timeArea)
        # 等待
        while 1:
            # 如果没有任务
            if (len(t.threadRun) == 0 and len(t.threadWait) == 0):
                t.shutdown()
                cameraData0 = t.camResult0
                cameraData1 = t.camResult1
                break
            else:
                time.sleep(0.01)
        xypDebug(f"数据处理时间：{time.time() - sss:.2f}s")
        if len(cameraData0) != 0:
            vanishPoint0 = solveVanishPoint(cameraData0, cameraConfig0)
        if len(cameraData1) != 0:
            vanishPoint1 = solveVanishPoint(cameraData1, cameraConfig1)
    else:
        xypDebug(f"数据处理时间：{time.time() - sss:.2f}s")
    # if platform.system() == "Linux":
    #     f = open("./c0.txt","wb")
    #     pk.dump(cameraData0,f)
    #     f.close()
    #     f = open("./c1.txt", "wb")
    #     pk.dump(cameraData1,f)
    #     f.close()
    # else:
        # f = open("D:/xyp/guardData/0921/c0.txt", "rb")
        # cameraData0 =pk.load(f)
        # f.close()
        # f = open("D:/xyp/guardData/0921/c1.txt", "rb")
        # cameraData1  =pk.load(f)
        # f.close()

    print("camera0近焦标前数据:", cameraConfig0)
    if vanishPoint0 is not None:
        vanishPoint0, fov=vanishPoint0
        cameraConfig0["success"] = 1
        cameraConfig0["vanishingPoint"][1] = round(vanishPoint0, 0)
        cameraConfig0["fov_V_deg"] = fov
        print("camera0近焦标定成功:", cameraConfig0)
    else:
        cameraConfig0["success"] = 0
        print("camera0近焦标定失败:", cameraConfig0)

    print("camera1远焦标前数据:", cameraConfig1)
    if vanishPoint1 is not None:
        vanishPoint1, fov = vanishPoint1
        cameraConfig1["success"] = 1
        cameraConfig1["vanishingPoint"][1] = round(vanishPoint1, 0)
        cameraConfig1["fov_V_deg"]= fov
        print("camera1远焦标定成功:", cameraConfig1)
    else:
        cameraConfig1["success"] = 0
        print("camera1远焦标定失败:", cameraConfig1)

    print(f"标定总耗时: {time.time() - sss}")
    return (cameraConfig0, cameraConfig1)

class defence(): # 测试用
    def __init__(self,d):
        self.data_list_800_450 = d

if platform.system() == "Linux":
    logPath = "/ssd/zipx/log/"
else:
    # logPath = r"D:\xyp\guardData\0831"
    # logPath = r"D:\xyp\guardData\0913\0"
    logPath = r"D:\xyp\guardData\1007"
    # logPath = r".\0"

jsonData = {
    "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 13, "minute": 56, "second": 33},
    "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 13, "minute": 59, "second": 13}
}

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 13, "minute": 59, "second": 26},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 2, "second": 10}
# }

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 3, "second": 40},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 7, "second": 10}
# }

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 7, "second": 20},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 10, "second": 54}
# }

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 15, "second": 00},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 18, "second": 43}}

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 18, "second": 49},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 22, "second": 47}}

# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 24, "second": 55},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 29, "second": 7}}
#
# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 29, "second": 13},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 33, "second": 9}}
#
# jsonData = {
#     "startTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 35, "second": 0},
#     "endTime": {"year": 2023, "month": 10, "day": 7, "hour": 14, "minute": 38, "second": 55}}

jsonData = {
    "startTime": {"year": 2021, "month": 10, "day": 7, "hour": 14, "minute": 39, "second": 0},
    "endTime": {"year": 2025, "month": 10, "day": 7, "hour": 14, "minute": 42, "second": 30}}


startTime = datetime.datetime(jsonData["startTime"]["year"], jsonData["startTime"]["month"],
                              jsonData["startTime"]["day"], jsonData["startTime"]["hour"],
                              jsonData["startTime"]["minute"], jsonData["startTime"]["second"])
endTime = datetime.datetime(jsonData["endTime"]["year"], jsonData["endTime"]["month"], jsonData["endTime"]["day"],
                            jsonData["endTime"]["hour"], jsonData["endTime"]["minute"],
                            jsonData["endTime"]["second"])

if __name__ == "__main__":
    if 1:
        camConfig = [{"fov_V_deg": 23.755424257641963, "fov_H_deg": 1, "vanishingPoint": [412, 199], "camera_height": 2.2,
                      "rad_per_pixel": 0.0009213563744532932},
                     {"fov_V_deg": 4.4672, "fov_H_deg": 1, "vanishingPoint": [664, 182], "camera_height": 2.2,
                      "rad_per_pixel": 0.0001732, "vanishPoint": [547, 88]}]
    else:
        camConfig = [{"fov_V_deg": 25.017, "fov_H_deg": 1, "vanishingPoint": [399, 201], "camera_height": 2.6,
                      "rad_per_pixel": 0.0009702869437353906},
                     {"fov_V_deg": 3.661411, "fov_H_deg": 1, "vanishingPoint": [484, 164], "camera_height": 2.6,
                      "rad_per_pixel": 0.0001420081890710829, "vanishPoint": [547, 88]}]
    # random.seed(3)
    defences = [[defence([(5.3125, 447.3125), (4.0, 411.6875), (342.0, 261.0), (428.0, 264.375), (358.6875, 449.3125)])], [defence([(28.0, 447.3125), (533.3125, 198.4375), (607.3125, 202.4375), (467.3125, 448.0)])]]
    timeArea = [startTime,endTime]
    calibVanishPoint(logPath, camConfig, defences,timeArea)
    # import cv2 as cv
    # img0 = cv.imread("0.jpg")
    # img0 = cv.resize(img0,(800,450))
    # img1 = cv.imread("1.jpg")
    # img1 = cv.resize(img1, (800, 450))
    # v0=203
    # v1=155
    # img0[v0-1:v0+2]*=0
    # img1[v1 - 1:v1 + 2] *= 0
    # cv.imshow("img0",img0)
    # cv.imshow("img1", img1)
    # cv.waitKey(0)
    #
    #
    #
    #
    #
