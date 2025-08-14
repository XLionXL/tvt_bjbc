import numpy as np
import pandas as pd
# import cv2 as cv
from abc import abstractmethod
from collections import OrderedDict


class LogAnalyseTool():
    def __init__(self):
        self.nearCamImageShape = (800 ,450)  # (X,Y)
        self.farCamImageShape = (800 ,450)  # (X,Y)
        # 有效范围
        self.nearCamWorldRangeXY= ((-20, 20),(0, 70)) # ((minX,maxX),(minY,maxY)),单位m
        self.farCamWorldRangeXY = ((-20, 20), (0, 250)) # ((minX,maxX),(minY,maxY)),单位m
        # 有效范围
        self.nearCamImageRangeXY = ((-1, self.nearCamImageShape[0]), (-1,self.nearCamImageShape[1]))  # ((minX,maxX),(minY,maxY)),单位px
        self.farCamImageRangeXY = ((-1, self.nearCamImageShape[0]), (-1,self.nearCamImageShape[1]))  # ((minX,maxX),(minY,maxY)),单位px

    @ staticmethod
    def addAlignByTime(*dataSet, allowSpanTime=1.0 / 8.0,):  # 通过时间对齐帧，以第一组数据的时间为基准
        # dataSet中每个元素都是是按帧划分的数据，如dataSet[0]格式为：[[time,data],...]
        # allowSpanTime匹配的最小时间差距不超过的秒数，如数据帧率中最快的是1/8秒，就设置为1/8秒，即不能跳帧匹配
        alignData = np.array(dataSet[0], dtype=object)  # [[time,data],...]
        # 兼容pandas==0.22.0

        import datetime
        alignData =pd.DataFrame(OrderedDict([('timestamp',pd.to_datetime([datetime.datetime.fromtimestamp(i) for i in alignData[:, 0]], format='%H:%M:%S.%f')), ('data',alignData[:, 1])])) # 兼容写法，要有序序列，否则生成DataFrame
        alignData = alignData.sort_values(by='timestamp')
        for i in range(1, len(dataSet)):  # 循环其他数据
            newData = np.array(dataSet[i], dtype=object)  # [[time,data],...]
            newData = pd.DataFrame(OrderedDict([('timestamp',pd.to_datetime([datetime.datetime.fromtimestamp(i) for i in newData[:, 0]], format='%H:%M:%S.%f')), ('data',newData[:, 1])]))
            newData = newData.sort_values(by='timestamp')
            alignData = pd.merge_asof(alignData, newData, on='timestamp', direction='nearest',suffixes=(str(i-1),str(i)),tolerance=pd.Timedelta('{} milliseconds'.format(allowSpanTime*1000)))


        # alignData = alignData.to_numpy()
        alignData = alignData.dropna()
        alignData = alignData.values # 兼容写法，获取numpy类型数据

        return alignData

    @staticmethod
    def removeOutlierByGaussian(data, multiple=1):
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

    @abstractmethod
    def analyseLog(self,*args,**kwargs):
        pass
    @ abstractmethod
    def cleanLog(self,*args,**kwargs):
        pass


    # @abstractmethod
    def updateLogInfo(self,*args,**kwargs):
        pass

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



if __name__ == "__main__":
    data = np.arange(80).reshape(-1)
    print(data[LogAnalyseTool.removeOutlierByThreshold(data, t=(20, 30))])
    print(data[LogAnalyseTool.removeOutlierByGaussian(data, 1)])
    data = np.arange(80).reshape(-1,2)
    print(data[LogAnalyseTool.removeOutlierByThreshold(data, t=(20, 30))])
    print(data[LogAnalyseTool.removeOutlierByGaussian(data, 1)])