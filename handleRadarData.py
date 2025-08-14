#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雷达区域管理与数据处理模块

该模块包含雷达区域管理和雷达数据处理两个核心类，主要用于雷达探测区域的定义、目标检测数据的处理与分析，
实现雷达目标的精准定位、轨迹跟踪及区域判断，支持多线程安全操作和与Web端的数据交互。

核心功能概述：
1. 雷达区域管理：定义并管理雷达坐标系下的各类区域（防区、屏蔽区等），支持区域的创建、转换、可视化及与Web端的数据交互，通过掩码加速区域内目标判断。
2. 雷达数据处理：接收并处理雷达目标检测数据，进行坐标转换、轨迹跟踪、历史数据管理等，实现目标信息的标准化与缓存管理，支持虚拟轨迹生成与报警判断。
3. 工具函数：提供区域缩放、坐标离散化、数据格式转换等辅助功能，兼容不同来源的数据格式。

类结构与核心功能：
- RadarAreaHandle：雷达区域管理类
  - 定义雷达有效范围，支持区域的创建、加载、保存及多线程安全访问
  - 处理区域兼容性转换，自动计算有效区域及拓展区域
  - 生成区域掩码加速目标区域判断，支持区域可视化与Web端数据交互
  - 提供基于射线法或C扩展的区域内目标判断接口

- HandleRadarData：雷达数据处理类
  - 接收雷达目标检测数据，进行坐标转换、区域判断及轨迹跟踪
  - 管理目标历史数据缓存，实现过期数据清理与虚警区域更新
  - 生成虚拟轨迹辅助目标跟踪，支持报警条件判断与数据可视化
  - 提供目标轨迹查询接口，支持与视觉数据融合应用

依赖说明：
- 第三方库：matplotlib、numpy、shapely（几何计算）、cv2（图像处理）、PIL（图像绘制）
- 系统工具：threading（多线程）、ctypes（C扩展调用）、datetime（时间处理）
- 自定义模块：xypFileTool（文件管理）、xypLogDebug（日志调试）、xypLog（日志记录）

应用场景：适用于基于雷达的平面监控系统，如道路安防、边境监控等，通过雷达数据的精准处理与区域判断，实现目标的实时跟踪与报警。

区域与坐标说明：
- 雷达坐标系：以雷达为原点，X轴为水平方向，Y轴为距离方向（前方）
- 区域类型：0（屏蔽区）、1（误报区）、10（报警区）、101（拓展区），优先级从高到低
- 坐标转换：支持雷达坐标与图像坐标的映射，通过旋转矩阵实现角度校准

数据流程：
1. 区域设置：通过Web端或配置文件加载区域数据，经兼容性处理后生成有效区域及掩码
2. 数据接收：接收雷达目标数据，解析并转换为标准化格式
3. 数据处理：进行坐标转换、区域判断、轨迹跟踪及历史数据管理
4. 结果输出：生成报警信息、虚拟轨迹及可视化数据，支持与其他模块（如视觉模块）的数据交互
"""
import cv2 as cv
import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import platform
import threading
import time
import traceback
from PIL import Image, ImageDraw
from ctypes import CDLL, c_int, c_float, c_bool, POINTER
from shapely.geometry import Polygon
from xypLogDebug import xypDebug
from xypTool.common import xypFileTool


class RadarAreaHandle:
    def __init__(self, filePath, vanishHandle,  displayPath):
        self.fileManage = xypFileTool.JsonFileManage(filePath) # json文件管理器
        xypFileTool.checkPath(displayPath)  # 目录不存在则创建目录
        self.displayPath = displayPath  # 区域可视化保存地址
        self.isInAreaCode,self.isInArea = self.getIsInAreaFunction()

        # 优先级高的可以覆盖优先级低的，相同等级的可以相互覆盖，值越大优先级越低
        # 0:屏蔽区或者无区域，1:误报区，10:报警区，101:拓展区，(可用值[0~255]，剩余空隙可拓展)
        self.priority = [0, 1, 10, 101]  # 目前已有等级

        self.radarImageScale = 4 # 雷达离散后图像缩放倍数
        self.radarValidZone=[50,250] # 雷达范围
        self.resolution=[self.radarValidZone[0]*self.radarImageScale,
                         self.radarValidZone[1]*self.radarImageScale] # 离散后图像分辨率

        halfX = self.radarValidZone[0]/2
        self.radarValidArea = [[-halfX,0],
                               [-halfX,self.radarValidZone[1]],
                               [halfX,self.radarValidZone[1]],
                               [halfX,0]]  # 雷达有效范围
        # 雷达坐标离散到图像中
        self.radarDiscret = lambda pos: [(pos[0] +halfX)* self.radarImageScale,self.resolution[1]-pos[1]*self.radarImageScale   ]

        self._radarAreaData = []
        self.areaLock = threading.Lock()
        self.vanishHandle = vanishHandle

        # 加载防区
        if os.path.exists(filePath):
            radarAreaData = self.fileManage.load()
            if radarAreaData is None:
                radarAreaData = []
        else:
            radarAreaData = []
        self.areaSet(radarAreaData)
    @property # 定义函数为属性，用于在线程里面处理会动态修改的共享变量
    # 建议使用以引用的形式使用，即xxx = imageAreaData, 然后使用xxx，防止多次拷贝
    def radarAreaData(self):
        with self.areaLock:
            # return copy.deepcopy(self._radarAreaData) # 性能不足不能采用深度拷贝
            return self._radarAreaData  # 可能造成使用时值发生改变

    @radarAreaData.setter # imageAreaData设置值时调用
    def radarAreaData(self,value):
        with self.areaLock:
            self._radarAreaData = value

    def areaMaskCreate(self, ):
        self.areaMaskCreateRun = True  # 线程运行标识符
        radarAreaData = self.radarAreaData  # 获取拷贝
        self.areaMask = None
        # 250m - 1000px
        # 50m - 200px, 25cm/px
        mask = Image.new('L', self.resolution, "black")
        idMask = Image.new('L', self.resolution, "white")

        draw = ImageDraw.Draw(mask)
        idDraw = ImageDraw.Draw(idMask)

        # 将优先级低的先画，防止覆盖优先级高的，type越大优先级越低
        for areaType in  self.priority[::-1]:
            for area in radarAreaData:
                if not self.areaMaskCreateRun:
                    return 0
                if areaType == 101 and area["validExtendArea"] is not None:
                    draw.polygon([tuple(self.radarDiscret(i)) for i in area["validExtendArea"]], fill=areaType)
                elif area["type"] == areaType and area["validArea"] is not None:
                    draw.polygon([tuple(self.radarDiscret(i))  for i in area["validArea"]], fill=areaType)
                    idDraw.polygon([tuple(self.radarDiscret(i))  for i in area["validArea"]], fill=area["areaId"])

        nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        mask.save(os.path.join(self.displayPath, f"{nowTime}_radar_areaMask.jpg"))
        areaMask = np.stack([np.array(mask), np.array(idMask)], axis=-1)  # 一次性更新以便同步
        self.areaMask = areaMask

    # 获取判断是否在区域内的函数
    def getIsInAreaFunction(self):
        try: # cIsInArea
            code = "c"
            device = platform.platform()[0:15]
            insidePath =os.path.abspath(os.path.join(".", "dependent", f'inside_{device}.so'))
            isInArea = CDLL(insidePath).inside  # 加载inside.so
            isInArea.argtypes = [c_float, c_float, c_int, POINTER(c_float * 2)]
            isInArea.restype = c_bool
        except:
            code = "python"
            def pythonIsInArea(point, area):
                # 射线法判断点是否在区域内
                # point：[x1,y1] or [x1,y1,w,h]
                # area=[[x1,y1],[x2,y2],...,[xn,yn]] 点列表
                if len(point) == 2:
                    x, y = point
                else:
                    x, y = point[0] + point[2] / 2, point[1] + point[3]
                cnt = 0  # 交点个数
                areaPointNum = len(area)
                for idx, startPoint in enumerate(area):  #
                    endPoint = area[(idx + 1) % areaPointNum]
                    if ((startPoint[1] > y) != (endPoint[1] > y)) and (
                            x < (endPoint[0] - startPoint[0]) * (y - startPoint[1]) / (endPoint[1] - startPoint[1]) +
                            startPoint[0]):
                        cnt += 1  # 有交点就加1
                return True if cnt % 2 == 1 else False
            isInArea = pythonIsInArea
        return code,isInArea
    # 区域兼容处理
    def areaCompatible(self, data):
        '''
        data 当前传入格式：
        雷达区域直接设置：
            {code: 112 data:{0:[{type verteces},{type shielding}...]}}
            期望后期格式为
                {code: 112 data:[{type userArea} ...]}
        图像转雷达区域设置：
            {code: 1 data:[{type userArea} ...]}
        误报区设置：
            {code: 2 data:[{type userArea} ...]}

        加载：
            由本程序生成并加载的不用兼容处理，格式为输出格式
        输出
            当前输出格式为[{type code userArea}]
        '''

        if isinstance(data, dict): # web传入
            radarAreaData = self.radarAreaData
            code = data["code"]
            radarAreaData = [area for area in radarAreaData if area["code"] != code]
            if code == 112:
                data = data["data"]["0"]
                for area in data:
                    cptbArea = {}
                    if "verteces" in area:
                        cptbArea["type"] = 10
                        cptbArea["code"] = code
                        cptbArea["userArea"] = area["verteces"]
                    elif "shielding" in area:
                        cptbArea["type"] = 0
                        cptbArea["code"] = code
                        cptbArea["userArea"] = area["shielding"]
                    radarAreaData.append(cptbArea)

            elif code == 1:
                data = data["data"]
                for area in data:
                    cptbArea = {}
                    cptbArea["type"] = area["type"]
                    cptbArea["code"] = code
                    cptbArea["userArea"] = area["userArea"]
                    radarAreaData.append(cptbArea)

            elif code == 2:
                data = data["data"]
                for area in data:
                    cptbArea = {}
                    cptbArea["type"] = area["type"]
                    cptbArea["code"] = code
                    cptbArea["userArea"] = area["userArea"]
                    radarAreaData.append(cptbArea)
            return radarAreaData
        else: # 加载的，由本程序生成，无需兼容
            return data
    # 区域保存
    def areaSave(self):
        radarAreaData =self.radarAreaData
        '只保存 {type code userArea} 三个属性'
        radarAreaDataSave = []
        for area in radarAreaData:
            if area["type"] != 1: # 不保存误报区
                radarAreaDataSave.append({k: v for k, v in area.items() if k in ["type","code","userArea"]})
        self.fileManage.save(radarAreaDataSave)

    def areaScale(self, data, dis):
        """
        多边形等距缩放 https://zhuanlan.zhihu.com/p/97819171
        data: [n,2->(x,y)], 多边形按照逆时针顺序排列的的点集，不是逆时针会造成dis为正反而缩小、拓展失败等情况，注意这里的逆时针是以图像坐标系为参考系
        sec_dis: 缩放距离
        """
        if dis == 0:
            return data
        data = np.array(data)
        num = len(data)
        newData = []
        for idx in range(num):
            # idx % num 数据跑马灯
            vectorA = data[idx] - data[(idx - 1) % num]
            vectorB = data[idx] - data[(idx + 1) % num]

            lengthA = np.linalg.norm(vectorA)
            lengthB = np.linalg.norm(vectorB)
            if (lengthA * lengthB == 0):  # 点重合
                continue
            direction = vectorA / lengthA + vectorB / lengthB  # 方向
            if (np.cross(vectorA, vectorB)) > 0:  # 如果是凹
                direction = -direction

            sinV = np.cross(vectorA, vectorB) / (lengthA * lengthB)  # 夹角sin值
            if sinV == 0:
                continue
            else:
                unitLength = abs(1 / sinV)  # 单位长度
            newPoint = data[idx] + dis * unitLength * direction
            newData.append(newPoint)
        return newData
    # 区域设置
    def areaSet(self, data):
        try:
            xypDebug("radarAreaSet start",data)
            radarAreaData = self.areaCompatible(data) # 区域兼容处理
            # ignoreNum = 0
            # defenceNum = 0
            # for area in radarAreaData:
            #     if area["type"] == 0:
            #         ignoreNum +=1
            #         if ignoreNum > 8:
            #             xypDebug(f"radarAreaSet fail ignoreArea number: {ignoreNum} > 8", data)
            #             return False
            #     if area["type"] ==1:
            #         defenceNum+=1
            #         if defenceNum >4:
            #             xypDebug(f"radarAreaSet fail defenceArea number: {defenceNum} > 4", data)
            #             return False
            # 区域信息增强

            # 刷新防区Id
            radarAreaId = sorted([area["areaId"] for area in radarAreaData if "areaId" in area])
            for minId, nowId in enumerate(radarAreaId):
                if nowId != minId:
                    for area in radarAreaData:
                        if "areaId" in area and area["areaId"] == nowId:
                            area["areaId"] = minId
            minId = len(radarAreaId)
            for area in radarAreaData:# 防区信息增强
                # userArea 用户区域
                # validArea 有效的区域
                # validExtendArea 有效的拓展区域
                p1 = Polygon(self.radarValidArea)
                p2 = Polygon(area["userArea"])
                if p1.intersects(p2):
                    if "validArea" not in area:
                        area["validArea"] = list(p1.intersection(p2).exterior.coords)[:-1]
                        if self.isInAreaCode == "c":
                            polyNum = len(area["validArea"] )
                            cArea = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in area["validArea"]))
                            area["cValidArea"] = [polyNum, cArea]
                        else:
                            area["cValidArea"] = None

                    if "validExtendArea" not in area:
                        if area["type"] == 10:# 报警区才有拓展
                            extendArea= self.areaScale(area["validArea"][::-1],2) # 拓展2m,[::-1],雷达坐标系和图像坐标系y值相反
                            p2 = Polygon(extendArea)
                            area["validExtendArea"]= list(p1.intersection(p2).exterior.coords)[:-1]
                            if self.isInAreaCode == "c":
                                polyNum = len(area["validExtendArea"])
                                cArea = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in area["validExtendArea"]))
                                area["cValidExtendArea"] = [polyNum, cArea]
                            else:
                                area["cValidExtendArea"] = None
                        else:
                            area["validExtendArea"] = None
                            area["cValidExtendArea"] = None
                else:
                    area["validArea"] = None
                    area["cValidArea"] = None
                    area["validExtendArea"] = None
                    area["cValidExtendArea"] = None

                if "enable" not in area:  # 默认区域为启用
                    area["enable"] = 1

                if "areaId" not in area:
                    area["areaId"] = minId
                    minId += 1
            # 区域设置
            self.radarAreaData = radarAreaData
            self.areaSave()            # 区域保存
            self.areaDisplay()    # 区域可视化
            # 区域创建mask
            # 停止线程
            for thread in threading.enumerate():
                if thread.getName() == "radarAreaMaskCreate":
                    self.areaMaskCreateRun = False
                    break
            # 等待线程结束
            while True:
                breakFlag = True
                for thread in threading.enumerate():
                    if thread.getName() == "radarAreaMaskCreate":
                        breakFlag = False
                if breakFlag:
                    break
                time.sleep(0.1)
            # 重开线程后台慢慢生成mask
            threading.Thread(target=self.areaMaskCreate, name="radarAreaMaskCreate").start()
            xypDebug("radarAreaSet done", radarAreaData)
            return True
        except:
            xypDebug("radarAreaSet error", traceback.format_exc())
            return False
    # 区域回复给web
    def areaSendToWeb(self, ):
        try:
            radarAreaData=self.radarAreaData
            "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
            '只发送 {type userArea} 两个属性'
            radarAreaDataSend = []
            s = {0: "shielding",1: "verteces"}
            for area in radarAreaData:
                if area["type"] == 10:
                    areaType = 1
                elif  area["type"] == 0:
                    areaType = 0
                else:
                    continue
                areaSend = {}
                areaSend["type"] = areaType
                areaSend[s[areaType]] = area["userArea"]
                radarAreaDataSend.append(areaSend)
            "<<<<<<<<<<<<<<<<<<<<<<<兼容处理"
            return {"0": radarAreaDataSend}
        except:
            traceback.print_exc()
    # 区域可视化
    def areaDisplay(self):
        radarAreaData = self.radarAreaData
        nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        fig = plt.figure(f"radar area, unit:m")
        ax = plt.subplot()
        ax.cla()
        for areaType in self.priority[::-1]:
            for area in radarAreaData:
                if areaType == 101 and area["validExtendArea"] is not None:
                    polygon = plt.Polygon(area["validExtendArea"], closed=True, fill=None, edgecolor="blue",linewidth=9)
                    ax.add_patch(polygon)
                elif area["type"] == areaType:
                    fillColor=None
                    if area["type"] == 0:
                        fillColor = "black"
                    elif area["type"] == 1:
                        fillColor="yellow"
                    elif area["type"] == 10:
                        fillColor="red"

                    polygon = plt.Polygon(area["userArea"], closed=True, facecolor=fillColor, edgecolor="red", linewidth=6)
                    ax.add_patch(polygon)
                    if area["validArea"] is not None:
                        polygon = plt.Polygon(area["validArea"], closed=True, fill=None, edgecolor="green", linewidth=3)
                        ax.add_patch(polygon)
        ax.set_xlim(-self.radarValidZone[0],self.radarValidZone[0])
        ax.set_ylim(0,self.radarValidZone[1]*2)
        savePath = f"{self.displayPath}/{nowTime}_radarArea.jpg"
        fig.savefig(savePath)

    # 获取目标所属区域
    def getObjArea(self, orgBox):
        # 注意在区域重叠时，返回值的areaType, area["areaId"]会是重叠区域中的其中一个区域
        radarAreaData = self.radarAreaData
        x, y = orgBox

        areaMask = self.areaMask
        if areaMask is not None:
            x,y = self.radarDiscret([x,y])
            x = int(round(min(self.resolution[0] - 1, max(x, 0))))
            y = int(round(min(self.resolution[1] - 1, max(y, 0))))
            areaType, areaId = areaMask[y, x]  # json不支持uint8格式
            return int(areaType), int(areaId)
        else:
            if self.isInAreaCode == "c":
                for areaType in self.priority:
                    for area in radarAreaData:
                        if area["type"] == areaType  and area["cValidArea"] is not None:
                            polyNum, cArea = area["cValidArea"]
                            if self.isInArea(float(x), float(y), polyNum, cArea):
                                return areaType, area["areaId"]
                        elif areaType == 101 and area["cValidExtendArea"] is not None:
                            polyNum, cArea = area["cValidExtendArea"]
                            if self.isInArea(float(x), float(y), polyNum, cArea):
                                return areaType, area["areaId"]
            else:
                for areaType in self.priority:
                    for area in radarAreaData:
                        if area["type"] == areaType and area["validArea"] is not None:
                            if self.isInArea([x, y], area["validArea"]):
                                return areaType, area["areaId"]
                        elif areaType == 101 and area["validExtendArea"] is not None:
                            if self.isInArea([x, y], area["validExtendArea"]):
                                return areaType, area["areaId"]

        return 0  # 都不在





from xypTool.debug import xypLog


class HandleRadarData():
    """
    雷达数据处理核心类
    
    该类负责雷达目标数据的接收、解析、轨迹跟踪、坐标转换及数据交互，实现雷达目标的实时监控与分析。
    通过多线程锁机制保证数据安全性，支持与Web端的数据通信和虚拟轨迹生成，为雷达监控系统提供目标监测与报警功能。
    """
    # HandleCameraData以handleCameraData为全类调用及输入点
    def __init__(self, radarAreaHandle, vanishHandle,  tempClass=None,resolution=(800, 450)):
        """
        初始化雷达数据处理器
        
        参数:
            radarAreaHandle: 雷达区域管理实例，用于区域判断
            vanishHandle: 消失点处理实例，提供坐标转换所需的校准信息
            tempClass: 临时存储类实例，用于TCP数据发送
            resolution: 图像分辨率，默认(800, 450)
        """
        self.radarAreaEnable = 1  # 雷达区域功能启用标志（1：启用，0：禁用）
        self.mask0 = cv.imread("./config/mask0.jpg", 0)  # 相机0（近焦）的掩码图像，用于区域校准
        self.mask1 = cv.imread("./config/mask1.jpg", 0)  # 相机1（远焦）的掩码图像，用于区域校准
        self.radarAreaHandle = radarAreaHandle  # 雷达区域管理实例引用
        self.vanishHandle = vanishHandle  # 消失点处理实例引用，用于坐标转换
        self.tempClass = tempClass  # 临时存储类实例，用于TCP通信

        self.trackLock = threading.Lock()  # 轨迹数据线程锁，保证多线程环境下的数据安全
        self.falseAreaLock = threading.Lock()  # 虚警区域线程锁，保证虚警数据的一致性

        self.track = []  # 备用轨迹列表（未使用）
        self.falseArea = {}  # 虚警区域字典，键为位置元组(x,y)，值为最新时间戳

        self.cacheTime = 10  # 轨迹缓存时间（秒），超过此时长的轨迹点将被清理
        self.radarFrameRate = 10  # 雷达帧率（帧/秒），用于控制轨迹点数量
        self.threshold = 1  # 报警阈值，轨迹长度达到此值时触发报警判断

        self.resolution = resolution  # 图像分辨率（宽，高）
        self.cbtpTrack = {}  # 目标轨迹字典，键为目标ID，值为包含轨迹点的字典

    def clearObjTrack(self, objId=None):
        """
        清除目标轨迹数据
        
        根据目标ID清除指定轨迹，若ID为None则清除所有轨迹，通过线程锁保证操作安全性。
        
        参数:
            objId: 目标ID，为None时清除所有轨迹
        """
        with self.trackLock:
            if objId is None:
                self.cbtpTrack = {}  # 清除所有轨迹
            else:
                self.cbtpTrack.pop(objId)  # 清除指定ID的轨迹

    def updateFalseArea(self, radarTrack=[]):
        """
        更新虚警区域记录
        
        记录虚警位置及时间戳，自动清理超过120秒的历史虚警记录，用于过滤重复虚警目标。
        
        参数:
            radarTrack: 雷达轨迹列表，用于提取虚警位置信息
        """
        with self.falseAreaLock:
            nowTime = time.time()  # 当前时间戳
            # 更新虚警区域的时间戳
            for track in radarTrack:
                for obj in track["track"]:
                    self.falseArea[tuple(obj["position"])] = nowTime
            # 过滤超时的虚警记录（保留120秒内的记录）
            self.falseArea = {k: v for k, v in self.falseArea.items() if nowTime - v < 120}

    def cleanHistory(self, nowTime):
        """
        清理历史轨迹数据
        
        移除超过缓存时间的轨迹点，保持轨迹数据的时效性，避免内存占用过大。
        
        参数:
            nowTime: 当前时间戳，用于判断轨迹点是否超时
        """
        # 遍历所有轨迹ID
        for trackId in list(self.cbtpTrack.keys()):
            track = self.cbtpTrack[trackId]["track"]
            # 移除超时的轨迹点（按时间顺序从头开始清理）
            while track:
                if nowTime - track[0]["timeStamp"] > self.cacheTime:
                    track.pop(0)
                else:
                    break  # 轨迹按时间排序，找到第一个未超时的点即可停止
            # 保留最近cacheTime*frameRate个轨迹点（限制轨迹长度）
            if len(track):
                track[:] = track[-self.cacheTime * self.radarFrameRate:]
            else:
                self.cbtpTrack.pop(trackId)  # 轨迹为空时移除该轨迹

    def updateRadarRecord(self, radarData, nowTime):
        """
        更新雷达目标轨迹记录
        
        处理新的雷达目标数据，过滤虚警区域内的目标，更新有效目标的轨迹信息，自动清理历史数据。
        
        参数:
            radarData: 新的雷达目标数据列表
            nowTime: 当前时间戳，用于轨迹时间标记
        """
        # 更新虚警区域记录
        self.updateFalseArea()
        with self.trackLock:
            # 处理每个目标数据
            while radarData:
                obj = radarData.pop(0)
                # 仅处理有效类型的目标
                if obj["type"]:
                    # 不在虚警区域内的目标才记录轨迹
                    if tuple(obj["position"]) not in self.falseArea:
                        if obj["objId"] not in self.cbtpTrack:
                            # 新目标：创建轨迹字典
                            self.cbtpTrack[obj["objId"]] = {
                                "track": [obj],
                                "createTime": obj["timeStamp"],
                                "objId": obj["objId"]
                            }
                        else:
                            # 已有目标：追加轨迹点
                            self.cbtpTrack[obj["objId"]]["track"].append(obj)
                    else:
                        # 在虚警区域内：更新虚警时间戳
                        with self.falseAreaLock:
                            self.falseArea[tuple(obj["position"])] = time.time()
            # 清理超时的轨迹数据
            self.cleanHistory(nowTime)

    def convertSeqToList(self, data):
        """
        数据序列类型转换
        
        将numpy数组、元组等序列类型转换为列表，确保数据可序列化，便于网络传输。
        
        参数:
            data: 待转换的数据（支持字典、数组、元组等）
        
        返回:
            转换后的列表或原始数据（基本类型）
        """
        if isinstance(data, dict):
            return {key: self.convertSeqToList(value) for key, value in data.items()}
        elif isinstance(data, (np.ndarray, tuple, list)):
            return [self.convertSeqToList(i) for i in data]
        else:
            if isinstance(data, (int, float, str)):
                return data
            elif "numpy" in str(type(data)):
                # numpy类型转换为Python基本类型并保留一位小数
                return round(data.item(), 1)
            else:
                print("error", type(data), data)
                return data
            
    def normalizeBox(self, box):
        """
        规范化边界框坐标
        
        将边界框坐标限制在图像分辨率范围内，避免坐标超出图像尺寸导致的错误。
        
        参数:
            box: 边界框，格式为[x, y, w, h]（x,y为左上角坐标）
        
        返回:
            规范化后的边界框列表
        """
        x, y, w, h = box
        x1, y1, x2, y2 = x, y, x + w, y + h
        # 限制坐标在图像范围内（0至分辨率-1）
        x1 = max(0, min(x1, self.resolution[0] - 1))
        y1 = max(0, min(y1, self.resolution[1] - 1))
        x2 = max(0, min(x2, self.resolution[0] - 1))
        y2 = max(0, min(y2, self.resolution[1] - 1))
        return [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]


    def handleRadarData(self, data, nowTime=None):  # 要实时调用
        """
        处理雷达数据的主函数，将雷达坐标转换为图像坐标并发送至Web端
        
        参数:
            data: 雷达检测到的目标数据列表，格式为[[objId, X, Y, ...], ...]
            nowTime: 数据处理时间戳，默认为None时自动获取当前时间
            
        功能:
            1. 解析雷达原始数据，提取目标ID和坐标
            2. 判断目标所在区域类型（正常区域或屏蔽区）
            3. 进行坐标转换：雷达坐标系 → 图像坐标系
            4. 计算目标在图像中的边界框
            5. 根据掩码图像进行边界框校准
            6. 打包数据并发送至Web端显示
            7. 更新目标轨迹记录
        """
        # 注意现在该部分没数据是不会自动刷新

        try:
            """
            处理雷达数据
            :param radar_targets: 示例：[[2922, 10.5, 254.1, 0.0, 0.0], [2993, 2.5, 15.7, 0.0, 0.0]]
            :return:
            """
            if nowTime is None:  # 传入该数据时的时间点，给定nowtime时为虚拟轨迹测试
                nowTime = time.time()
            if data is not None:
                xypLog.xypDebug("radar data", data)
                radarObjData = []  # 存储处理后的目标信息
                for obj in data:
                    # 解析雷达原始数据，提取目标ID和坐标
                    objId, X, Y = obj[:3]
                    # 区域类型判断：默认正常区域(1)，若在屏蔽区内则标记为屏蔽区(0)
                    areaType = 1  # 不启用视觉转雷达防区，默认为雷达自己设置的防区
                    for zone in [(115.5, 116.5), (117.5, 118.5), (120, 121.5), (157, 158.5), (130, 133), (84, 85), (177, 178)]:
                        if zone[0] <= Y <= zone[1]:
                            areaType = 0  # 标记为屏蔽区
                            break

                    # 遍历每个防区，判断是否在防区内
                    # areaType,areaId = self.radarAreaHandle.getObjArea([objX,objY]) # 启用视觉转雷达防区
                    
                    # =================== 相机0（近焦）的坐标转换 ======================
                        """这里这个角度的偏转只是为了纠正相机的光轴和雷达主方向的偏差"""
                    calibInfo = self.vanishHandle.getCalibInfoByCamId(0)  # 获取相机校准信息
                    with open("/ssd/lss/guard_tvt-BJCOMP2025/angle1.txt") as f:  # 调参用，读取旋转角度
                        radAngle = np.deg2rad(float(f.read()))
                    # 人的估计高度和宽度（单位：米）
                    objHMeter, objWMeter = 1.7, 0.8
                    # 使用旋转矩阵将雷达坐标系中的点(X, Y)旋转radAngle角度，修正雷达与相机的角度偏差
                    objX, objY = np.dot(np.array([X, Y]), np.array([[np.cos(radAngle), -np.sin(radAngle)],
                                                                    [np.sin(radAngle), np.cos(radAngle)]]))
                    #=========================   end   ================================
                    # 根据目标的实际高度和到相机的距离，计算在图像中对应的像素高度和宽度
                    objHPixel = np.arctan(objHMeter / objY) / calibInfo["radPerPixelFovV"]
                    objWPixel = np.arctan(objWMeter / objY) / calibInfo["radPerPixelFovV"]
                    # 通过vanishHandle对象的方法，将雷达坐标中的点估计到图像坐标系中
                    objXPixel, objYPixel = self.vanishHandle.estimateRadarToImage([objX, objY], 0)

                    # 计算目标在图像中的边界框(x, y, w, h)，这里使用了估计的像素位置和尺寸
                    objXYWH0 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel), int(objWPixel), int(objHPixel)]
                    # 对边界框进行归一化处理，确保坐标在有效范围内（0~分辨率-1）
                    objXYWH0 = self.normalizeBox(objXYWH0)
                    x, y, w, h = objXYWH0

                    # 根据掩码图像进行边界框校准（特定区域需要额外调整）
                    if self.mask0[int(y + h), int(x + 0.5 * w)] > 127:
                        # 校准参数（不同距离使用不同的校准系数）
                        # a0, b0 =  4915.61276254207 ,185.15080014600161
                        # a1, b1 =  4283.605878087906 ,187.29330304324412
                        # 近焦校准前
                        # a0, b0 =  5069.36861634,181.658527212
                        # a1, b1 =  4484.25020388,179.896197168
                        a0, b0 = 1887.5606433890775, 224.45785317813616
                        # a1, b1 = 4603.39661590037, 216.86443751308656

                        # 计算偏移量并调整边界框位置
                        dd = (a0 / objY + b0)
                        objXYWH0 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel + dd), int(objWPixel),
                                    int(objHPixel)]
                        objXYWH0 = self.normalizeBox(objXYWH0)
                    
                    # ===== 相机1（远焦）的坐标转换 =====
                    with open("/ssd/lss/guard_tvt-BJCOMP2025/angle2.txt") as f:  # 调参用，读取旋转角度
                        radAngle = np.deg2rad(float(f.read()))
                    calibInfo = self.vanishHandle.getCalibInfoByCamId(1)  # 获取相机1的校准信息
                    # radAngle = np.deg2rad(-0.2)
                    # radAngle = np.deg2rad(0.7)
                    objHMeter, objWMeter = 1.7, 0.8  # 人的估计宽高
                    # 坐标旋转
                    objX, objY = np.dot(np.array([X, Y]), np.array(
                        [[np.cos(radAngle), -np.sin(radAngle)], [np.sin(radAngle), np.cos(radAngle)]]))
                    # 计算像素尺寸
                    objHPixel = np.arctan(objHMeter / objY) / calibInfo["radPerPixelFovV"]
                    objWPixel = np.arctan(objWMeter / objY) / calibInfo["radPerPixelFovV"]
                    # 坐标转换：雷达→图像
                    objXPixel, objYPixel = self.vanishHandle.estimateRadarToImage([objX, objY], 1)

                    # 计算边界框并归一化
                    objXYWH1 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel), int(objWPixel),
                                int(objHPixel)]
                    objXYWH1 = self.normalizeBox(objXYWH1)
                    x, y, w, h = objXYWH1
                    
                    # 根据掩码图像进行边界框校准（相机1）
                    if self.mask1[int(y + h), int(x + 0.5 * w)] > 127:
                        # a0, b0 =  23590.28937409733, 63.495035679231435
                        # a1, b1 =  21203.323122448008, 57.43772127513186
                        # 远焦校准前
                        # a0, b0 =24769.7854137,29.0012897648
                        # a1, b1 =21908.0650211,25.0383627975

                        a0, b0 = 11701.508805282434, 162.26036278055753
                        # a1, b1 =22868.48657544839,57.069436312682946
                        # 计算偏移量并调整边界框
                        dd = (a0 / objY + b0)
                        objXYWH1 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel + dd), int(objWPixel),
                                    int(objHPixel)]
                        objXYWH1 = self.normalizeBox(objXYWH1)

                    # 整理目标信息，包含雷达坐标、图像坐标、区域类型等
                    objInfo = {
                        "objId": objId,
                        "timeStamp": nowTime,
                        "position": np.array([X, Y]),  # 雷达坐标系中的位置
                        "xywh": [np.array(objXYWH0), np.array(objXYWH1)],  # 两个相机中的边界框
                        "type": areaType,  # 区域类型（0：屏蔽区，1：正常区域）
                        "camId": 1 if Y > 60 else 0  # 根据距离选择相机（Y>60使用远焦相机）
                    }
                    radarObjData.append(objInfo)

                # 准备发送至Web端的相机数据（相机1 - 远焦）
                data1 = {
                    'id': 1,
                    'timestamp': time.time(),
                    'data': [
                        {
                            'confidence': 1,  # 置信度（固定为1，表示完全可信）
                            'class': 0,  # 目标类别（0通常表示行人或默认类别）
                            'bbox': [int(jj) for jj in obj["xywh"][1]],  # 边界框坐标
                            'dto': [9998, 0, 0, 0, 0],  # 额外信息（具体含义需根据系统定义）
                            'in_area': 1  # 是否在监测区域内（固定为1）
                        } for obj in radarObjData
                    ]
                }
                
                # 准备发送至Web端的相机数据（相机0 - 近焦）
                data0 = {
                    'id': 0,
                    'timestamp': time.time(),
                    'data': [
                        {
                            'confidence': 1,
                            'class': 0,
                            'bbox': [int(jj) for jj in obj["xywh"][0]],
                            'dto': [9998, 0, 0, 0, 0],
                            'in_area': 1
                        } for obj in radarObjData
                    ]
                }

                # 整合相机状态数据和目标数据，准备发送至Web端
                cameraObjDataSendToWeb = {
                    'camerastatus': [
                        {
                            'nearcameraocclude': '-1',  # 近焦相机遮挡状态（-1表示未知）
                            'farcameraocclude': '-1',  # 远焦相机遮挡状态
                            'deflection': '-1',  # 相机偏斜状态
                            'nighttrainlight': '-1'  # 夜间列车灯光状态
                        }
                    ],
                    'list': [data0, data1],  # 包含两个相机的目标数据
                    'color': 1,  # 显示颜色（1可能表示默认颜色）
                    'stamp': time.time()  # 时间戳
                }

                # 准备发送至Web端的雷达数据
                radarObjDataSendToWeb = {
                    "stamp": nowTime,  # 时间戳
                    "list": [
                        {
                            "id": 0,
                            "data": [
                                {
                                    "in_area": obj["type"],  # 区域类型
                                    "dto": [0, obj["position"][0], obj["position"][1], 0, 0],  # 包含雷达坐标的信息
                                    "xywh_800_450": obj["xywh"]  # 两个相机中的边界框
                                } for obj in radarObjData
                            ]
                        }
                    ]
                }
                
                # 通过TCP发送相机数据和雷达数据至Web端
                self.tempClass.tcp_server.send_camera_data(cameraObjDataSendToWeb)
                self.tempClass.tcp_server.send_radar_data(self.convertSeqToList(radarObjDataSendToWeb))

                # 更新雷达目标轨迹记录，用于后续分析和报警
                self.updateRadarRecord(radarObjData, nowTime)
        
        # 异常处理：捕获并打印错误信息，确保系统稳定运行
        except Exception as e:
            print(time.time(), e, traceback.format_exc(), "handleRadarData error")

    def ligthCopyTrack(self):  # 轻拷贝
        """
        对当前轨迹数据进行轻拷贝
        
        复制轨迹数据结构，避免在处理过程中修改原始数据。
        注意：这是一个浅拷贝，仅复制字典和列表结构，内部对象仍为引用。
        
        返回:
            轨迹数据的轻拷贝副本
        """
        with self.trackLock:  # 加锁保证数据一致性
            trackCopy = {k: v.copy() for k, v in self.cbtpTrack.items()}  # 复制轨迹层
            for track in trackCopy.values():
                track["track"] = [obj.copy() for obj in track["track"]]  # 复制对象层
            return trackCopy  # 返回拷贝结果（注意：内部对象仍为引用，请勿修改）

    def getVirtualObjForX(self, radarTrack):  # 用于帧差+雷达的横穿的虚拟轨迹
        """
        生成横穿轨迹的虚拟目标点
        
        对于水平移动的目标，在其移动路径上生成等间距的虚拟目标点，
        用于增强目标检测效果，特别是在帧差法与雷达融合的场景中。
        
        参数:
            radarTrack: 雷达轨迹列表，每个轨迹包含多个时间点的目标信息
        
        返回:
            包含虚拟目标点的雷达轨迹列表
        """
        for track in radarTrack:
            # 只处理水平方向有移动的目标
            posX = [obj["position"][0] for obj in track["track"]]  # 提取所有X坐标
            maxX = np.max(posX)  # 最大X坐标
            minX = np.min(posX)  # 最小X坐标
            
            if maxX - minX == 0:  # 如果水平方向没有移动
                track["virtual"] = [track["track"][0].copy()]  # 直接使用第一个点作为虚拟点
            else:
                # 在最小和最大X坐标之间生成等间距的虚拟点（间隔0.5单位）
                virtualX = np.arange(minX, maxX, 0.5)
                if virtualX[-1] != maxX:  # 确保包含最大X坐标
                    virtualX = np.append(virtualX, maxX)
                
                # 取轨迹中所有点的Y坐标平均值作为虚拟点的Y坐标
                Y = np.mean([obj["position"][1] for obj in track["track"]])
                
                # 为每个虚拟X坐标生成对应的虚拟目标点
                virtual = []
                for X in virtualX:
                    # ===== 相机0（近焦）的坐标转换 =====
                    calibInfo = self.vanishHandle.getCalibInfoByCamId(0)
                    radAngle = np.deg2rad(-2.5)  # 固定旋转角度
                    objHMeter, objWMeter = 1.7, 0.8  # 人的估计宽高
                    
                    # 坐标旋转和转换
                    objX, objY = np.dot(np.array([X, Y]), np.array(
                        [[np.cos(radAngle), -np.sin(radAngle)], [np.sin(radAngle), np.cos(radAngle)]]))
                    objHPixel = np.arctan(objHMeter / objY) / calibInfo["radPerPixelFovV"]
                    objWPixel = np.arctan(objWMeter / objY) / calibInfo["radPerPixelFovV"]
                    objXPixel, objYPixel = self.vanishHandle.estimateRadarToImage([objX, objY], 0)

                    # 计算并归一化边界框
                    objXYWH0 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel), int(objWPixel),
                                int(objHPixel)]
                    objXYWH0 = self.normalizeBox(objXYWH0)
                    x, y, w, h = objXYWH0

                    # 掩码校准
                    if self.mask0[int(y + h), int(x + 0.5 * w)] > 127:
                        # a0, b0 =  4915.61276254207 ,185.15080014600161
                        # a1, b1 =  4283.605878087906 ,187.29330304324412
                        # 前
                        # a0, b0 = 5069.36861634, 181.658527212
                        # a1, b1 = 4484.25020388, 179.896197168

                        a0, b0 = 4890.693625305797, 222.28883148848425
                        a1, b1 = 4603.39661590037, 216.86443751308656

                        # 计算偏移量并调整边界框
                        dd = (a0 / objY + b0) - (a1 / objY + b1)
                        objXYWH0 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel + dd), int(objWPixel),
                                    int(objHPixel)]
                        objXYWH0 = self.normalizeBox(objXYWH0)

                    # ===== 相机1（远焦）的坐标转换 =====
                    calibInfo = self.vanishHandle.getCalibInfoByCamId(1)
                    radAngle = np.deg2rad(-0.2)  # 固定旋转角度
                    objHMeter, objWMeter = 1.7, 0.8  # 人的估计宽高
                    
                    # 坐标旋转和转换
                    objX, objY = np.dot(np.array([X, Y]), np.array(
                        [[np.cos(radAngle), -np.sin(radAngle)], [np.sin(radAngle), np.cos(radAngle)]]))
                    objHPixel = np.arctan(objHMeter / objY) / calibInfo["radPerPixelFovV"]
                    objWPixel = np.arctan(objWMeter / objY) / calibInfo["radPerPixelFovV"]
                    objXPixel, objYPixel = self.vanishHandle.estimateRadarToImage([objX, objY], 1)

                    # 计算并归一化边界框
                    objXYWH1 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel), int(objWPixel),
                                int(objHPixel)]
                    objXYWH1 = self.normalizeBox(objXYWH1)
                    x, y, w, h = objXYWH1

                    # 掩码校准
                    if self.mask1[int(y + h), int(x + 0.5 * w)] > 127:
                        # a0, b0 =  23590.28937409733, 63.495035679231435
                        # a1, b1 =  21203.323122448008, 57.43772127513186
                        # 远焦校准前
                        # a0, b0 = 24769.7854137, 29.0012897648
                        # a1, b1 = 21908.0650211, 25.0383627975

                        a0, b0 = 26784.448231382783, 48.84529429560239
                        a1, b1 = 22868.48657544839, 57.069436312682946
                        # 计算偏移量并调整边界框
                        dd = (a0 / objY + b0) - (a1 / objY + b1)
                        objXYWH1 = [int(objXPixel - 0.5 * objWPixel), int(objYPixel - objHPixel + dd), int(objWPixel),
                                    int(objHPixel)]
                        objXYWH1 = self.normalizeBox(objXYWH1)

                    # 创建虚拟目标信息
                    objInfo = {
                        "objId": track["objId"],  # 使用原始目标ID
                        "timeStamp": -1,  # 标记为虚拟点（-1表示非真实时间戳）
                        "position": np.array([X, Y]),  # 虚拟点的雷达坐标
                        "xywh": [np.array(objXYWH0), np.array(objXYWH1)],  # 两个相机中的边界框
                        "type": -1,  # 标记为虚拟类型（-1表示非真实目标）
                        "camId": 1 if Y > 60 else 0  # 根据距离选择相机
                    }
                    virtual.append(objInfo)
                
                # 将生成的虚拟点添加到轨迹中
                track["virtual"] = virtual

        return radarTrack

    def getRadarTrack(self, needTime, nowTime):
        """
        获取指定时间范围内的雷达轨迹数据
        
        参数:
            needTime: 需要获取的时间范围（秒）
            nowTime: 当前时间戳
            
        返回:
            alarm: 报警级别（基于轨迹长度）
            radarTrack: 筛选后的雷达轨迹列表，包含虚拟目标点
        """
        radarTrack = self.ligthCopyTrack()  # 轻拷贝当前轨迹数据
        alarm = 0  # 初始化报警级别
        
        # 筛选时间范围内的轨迹点
        for trackId in list(radarTrack.keys()):
            track = radarTrack[trackId]["track"]
            # 移除超时的轨迹点（按时间顺序从头开始清理）
            while track:
                if nowTime - track[0]["timeStamp"] > needTime:
                    track.pop(0)
                else:
                    break  # 轨迹按时间排序，找到第一个未超时的点即可停止
            
            # 保留最近needTime*frameRate个轨迹点（限制轨迹长度）
            if len(track):
                track[:] = track[-needTime * self.radarFrameRate:]
                alarm = max(alarm, len(track))  # 更新报警级别（轨迹长度越长，报警级别越高）
            else:
                radarTrack.pop(trackId)  # 轨迹为空时移除该轨迹
        
        # 如果有有效轨迹且达到阈值，生成虚拟目标点并返回最新的5个轨迹
        if alarm:
            radarTrack = [track for track in radarTrack.values() if len(track["track"]) >= self.threshold][-5:]
            radarTrack = self.getVirtualObjForX(radarTrack)  # 生成虚拟目标点
            return alarm, radarTrack
        else:
            return alarm, []  # 没有有效轨迹，返回空列表

if __name__ == "__main__":
    a=RadarAreaHandle("./aa/xxxx.json","./aa/radarMeter.jpg")

    json112 = {
        "code": 112,
        "msg": "radar_area",
        "data": [{
            "type": 1,
            "verteces": [
                [-9, 51.09090909090909],
                [-0.15, 81.45454545454545],
                [6.2, 0.36363636363636365],
                [-6.3, 0],
                [-9.05, 50.54545454545455],
                [-9, 51.09090909090909]
            ]
        }, {
            "type": 0,
            "shielding": [
                [-2.8757163321996284, 0],
                [-1.919746167732102, 49.008879105782015],
                [3.230273626667291, 47.85676775561873],
                [2.8850532601240477, 0 ]
            ]
        }]
    }
    a.areaSet(json112["data"])
    print(a.areaSendToWeb())



    json112 = {
        "code": 112,
        "msg": "radar_area",
        "data": [{
            "type": 1,
            "verteces": [
                [-9, 51.09090909090909],
                [-0.15, 81.45454545454545],
                [6.2, 0.36363636363636365],
                [-6.3, 0],
                [-9.05, 50.54545454545455],
                [-9, 51.09090909090909]
            ]
        }, {
            "type": 0,
            "shielding": [
                [-2.8757163321996284, 0],
                [-1.919746167732102, 49.008879105782015],
                [3.230273626667291, 107.85676775561873],
                [2.8850532601240477, 0]
            ]
        }]
    }
    time.sleep(2)
    a.areaSet(json112["data"])
    # plt.show()
    plt.figure(f"radar area, unit:m")
    for x in range(-10,10):
        for y in range(-5,100,2):
            if a.getObjArea([x,y])==0:
                plt.scatter(x,y,c="r")
            else:
                plt.scatter(x, y, c="b")
            # print(a.getObjArea([x,y]))
            plt.pause(0.01)
    print(a.areaSendToWeb())
    plt.show()