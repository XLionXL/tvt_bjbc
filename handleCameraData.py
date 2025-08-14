#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平面路面视觉与雷达融合处理模块

该模块包含多个类，主要用于相机标定信息管理、图像区域处理、相机数据处理及坐标系转换，
针对平面路面场景实现视觉目标检测与雷达数据的融合应用，支持多线程安全操作和Web端数据交互。

核心功能概述：
1. 相机标定与灭点管理：获取相机RTSP地址，处理水平/垂直视场角、灭点、相机高度等标定参数，
   实现图像坐标与雷达坐标的双向转换，为空间映射提供基础。
2. 图像区域管理：定义并处理不同类型的区域（防区、屏蔽区、误报区等），支持区域的创建、转换、
   可视化及与Web端的数据交互，通过掩码加速区域内目标判断。
3. 相机数据处理：接收并处理相机目标检测数据，进行坐标转换、区域判断、历史数据清理等，
   实现目标信息的标准化与缓存管理。
4. 工具函数：提供图像分辨率转换、坐标格式转换等辅助功能，兼容不同来源的数据格式。

类结构与核心功能：
- CameraVanishHandle：相机标定与灭点管理类
  - 管理相机RTSP地址列表，通过进程查询自动获取并处理超时情况
  - 加载、转换、保存相机标定信息（视场角、灭点、相机高度等）
  - 实现图像坐标与雷达坐标的双向转换，基于相机参数和灭点计算空间映射

- ImageTool：图像工具类（静态方法）
  - 提供图像分辨率转换（含裁剪适配），支持"xy"和"xywh"格式坐标
  - 实现边界框与多边形顶点的格式转换

- ImageAreaHandle：图像区域管理类
  - 定义并管理不同类型区域（防区、屏蔽区等），支持多线程安全访问
  - 处理区域兼容性转换，自动计算有效区域及拓展区域
  - 生成区域掩码加速目标区域判断，支持区域可视化与Web端数据交互

- HandleCameraData：相机数据处理类
  - 接收相机目标检测数据，进行坐标转换和区域判断
  - 管理目标历史数据缓存，实现过期数据清理
  - 提供目标信息查询接口，支持与雷达数据融合应用

依赖说明：
- 第三方库：matplotlib、numpy、shapely（几何计算）、cv2（图像处理）、PIL（图像绘制）
- 系统工具：subprocess（进程查询）、threading（多线程）、ctypes（C扩展调用）
- 自定义模块：xypFileTool（文件管理）、xypLogDebug（日志调试）

应用场景：适用于平面路面的视觉监控系统，如道路安防、交通流量统计等，
通过融合相机视觉数据与雷达空间信息，实现目标的精准定位与区域判断。
"""
import matplotlib
import re
import threading
from shapely.geometry import Polygon
from xypTool.common import xypFileTool
import cv2 as cv
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import time
from xypLogDebug import xypDebug
import traceback
import numpy as np
from ctypes import CDLL, c_int, c_float, c_bool, POINTER
from xypTool.debug import xypLog
import os
import platform
import subprocess
import datetime
from PIL import Image, ImageDraw


# 本模块是针对平面路面的策略

class CameraVanishHandle():
    def __init__(self, calibrationFilePath=os.path.join(".", "config", "calibration.json"), resolution=(800, 450)):
        self.fileManage = xypFileTool.JsonFileManage(calibrationFilePath)
        self.resolution = resolution
        self.calibInfoLock = threading.Lock()
        self.rstpList = self.getCameraRtsp()
        # self.rstpList = ['rtsp://admin:Admin123@192.168.8.12:8554/0', 'rtsp://admin:Admin123@192.168.8.11:8554/0']

        self._calibInfoShare = {}
        calibInfo = self.fileManage.load()

        self.calibInfoSet(calibInfo)

    @property  # 定义函数为属性，用于在线程里面处理会动态修改的共享变量
    # 建议使用以引用的形式使用，即xxx = calibInfo, 然后使用xxx，防止多次拷贝
    def calibInfo(self):
        with self.calibInfoLock:
            # return copy.deepcopy(self._calibInfoShare) # 性能不足不能采用深度拷贝
            return self._calibInfoShare  # 可能造成使用时值发生改变

    @calibInfo.setter  # imageAreaData设置值时调用
    def calibInfo(self, value):
        with self.calibInfoLock:
            self._calibInfoShare = value


    def getCalibInfoByCamId(self, camId):
        return self.calibInfo[self.rstpList[camId]]

    def getCameraRtsp(self):
        pwd = "TDDPc5kc4WnYcy"
        command = f"echo '{pwd}'|sudo -S ps -aux | grep infer_main | grep rtsp"
        startTime = time.time()
        spendTime = 0
        while spendTime < 60:
            output = subprocess.check_output(command, shell=True).decode('utf-8')
            output = re.split("\s", output)
            rstpList = [i for i in output if i.startswith("rtsp://")]
            if len(rstpList) > 0:
                return rstpList
            spendTime = time.time() - startTime
            print(f"Waiting camera rstp: {spendTime:.1f}/60s")
            if spendTime % 3 > 0:
                subprocess.check_output(f"echo '{pwd}'|sudo -S systemctl restart zipx.service", shell=True)
                print(f"Restart zipx.service")
            time.sleep(0.5)
        return []

    def calibInfoSet(self, data):
        try:
            xypDebug("calibInfoSet start", data)
            setCalibInfo = self.calibInfoCompatible(data)
            calibInfo = self.calibInfo
            for camUrl in setCalibInfo:
                if camUrl in calibInfo:
                    calibInfo[camUrl].update(setCalibInfo[camUrl])
                else:
                    calibInfo[camUrl] = setCalibInfo[camUrl]

                if "resolution" not in calibInfo[camUrl]:
                    calibInfo[camUrl]["resolution"] = [800, 450]

                if "imageManageArea" not in calibInfo[camUrl] or "vanishPoint" in setCalibInfo[camUrl]:
                    vpY = calibInfo[camUrl]["vanishPoint"][1]  # 灭点v值
                    # 灭点以下的区域,且离底部10个像素
                    calibInfo[camUrl]["imageManageArea"] = [[1, vpY + 1], [self.resolution[0] - 1, vpY + 1],
                                                            [self.resolution[0] - 1, self.resolution[1] - 1],
                                                            [1, self.resolution[1] - 1]]
                if "worldManageArea" not in calibInfo[camUrl] or "vanishPoint" in setCalibInfo[camUrl]:
                    calibInfo[camUrl]["worldManageArea"] = self.estimateImageToRadar(
                        calibInfo[camUrl]["imageManageArea"], calibInfo[camUrl])

            self.calibInfo = calibInfo
            self.calibInfoSave()

            xypDebug("calibInfoSet done", calibInfo)
        except:
            xypDebug("calibInfoSet error", traceback.format_exc())

    def calibInfoCompatible(self, data):
        cptbData = {}
        if "code" in data:  # web传入
            code = data["code"]
            data = data["data"]
            if code == 108:
                cptbCalib = {}
                if "vanishingPoint" in data:
                    cptbCalib["vanishPoint"] = data["vanishingPoint"]
                if "camera_height" in data:
                    cptbCalib["cameraHeight"] = data["camera_height"]
                cptbData[self.rstpList[int(data["index"])]] = cptbCalib
            else:
                for camId in data:
                    calib = data[camId]
                    cptbCalib = {}
                    if "fov_V_deg" in calib:
                        cptbCalib["degFovV"] = calib["fov_V_deg"]
                    else:
                        cptbCalib["degFovV"] = calib["degFovV"]
                    if "fov_H_deg" in calib:
                        cptbCalib["degFovH"] = calib["fov_H_deg"]
                    else:
                        cptbCalib["degFovH"] = calib["degFovH"]
                    if "vanishingPoint" in calib:
                        cptbCalib["vanishPoint"] = calib["vanishingPoint"]
                    else:
                        cptbCalib["vanishPoint"] = calib["vanishPoint"]
                    if "camera_height" in calib:
                        cptbCalib["cameraHeight"] = calib["camera_height"]
                    else:
                        cptbCalib["cameraHeight"] = calib["cameraHeight"]
                    if "rad_per_pixel" in calib:
                        cptbCalib["radPerPixelFovV"] = calib["rad_per_pixel"]
                    else:
                        cptbCalib["radPerPixelFovV"] = calib["radPerPixelFovV"]
                    cptbData[self.rstpList[int(camId)]] = cptbCalib

        else:  # 兼容旧版
            for camUrl in data:  # 转统一名称
                cptbCalib = {}
                calib = data[camUrl]
                if "fov_V_deg" in calib:
                    cptbCalib["degFovV"] = calib["fov_V_deg"]
                else:
                    cptbCalib["degFovV"] = calib["degFovV"]
                if "fov_H_deg" in calib:
                    cptbCalib["degFovH"] = calib["fov_H_deg"]
                else:
                    cptbCalib["degFovH"] = calib["degFovH"]
                if "vanishingPoint" in calib:
                    cptbCalib["vanishPoint"] = calib["vanishingPoint"]
                else:
                    cptbCalib["vanishPoint"] = calib["vanishPoint"]
                if "camera_height" in calib:
                    cptbCalib["cameraHeight"] = calib["camera_height"]
                else:
                    cptbCalib["cameraHeight"] = calib["cameraHeight"]
                if "rad_per_pixel" in calib:
                    cptbCalib["radPerPixelFovV"] = calib["rad_per_pixel"]
                else:
                    cptbCalib["radPerPixelFovV"] = calib["radPerPixelFovV"]
                cptbData[camUrl] = cptbCalib
        return cptbData

    def calibInfoSendToWeb(self):
        calibInfo = self.calibInfo
        calibInfoSend = {}
        '''web 只需要 vanishPoint cameraHeight 两个属性'''
        for camId, camUrl in enumerate(self.rstpList):
            calibInfoSend[camId] =  {}
            calibInfoSend[camId].update(calibInfo[camUrl])
            calibInfoSend[camId]["vanishingPoint"] = calibInfoSend[camId]["vanishPoint"]
            calibInfoSend[camId]["camera_height"] = calibInfoSend[camId]["cameraHeight"]
            calibInfoSend[camId].pop("vanishPoint")
            calibInfoSend[camId].pop("cameraHeight")
        return calibInfoSend

    def calibInfoSave(self):
        calibInfo = self.calibInfo
        '''只保存 degFovV degFovH vanishPoint cameraHeight radPerPixelFovV 五个属性'''

        calibInfoSave = {}
        for camUrl in calibInfo:
            calibInfoSave[camUrl] = {k: v for k, v in calibInfo[camUrl].items() if
                                     k in ["degFovV", "degFovH", "vanishPoint", "cameraHeight", "radPerPixelFovV"]}
        self.fileManage.save(calibInfoSave)

    def estimateImageToRadar(self, points, mode):
        if isinstance(mode, int):
            calibInfo = self.calibInfo[self.rstpList[mode]]
        else:
            calibInfo = mode

        h = calibInfo["cameraHeight"]
        vp = calibInfo["vanishPoint"]
        resolution = calibInfo["resolution"]
        per = calibInfo["radPerPixelFovV"]

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

    def estimateRadarToImage(self, points, mode):
        """
        将雷达坐标系中的点估计到图像坐标系中
        
        参数:
            points: 雷达坐标系中的点，可以是单个点[x, y]或多个点的列表[[x1, y1], [x2, y2], ...]
            mode: 相机模式，可为相机索引(int)或直接传入校准信息(dict)
            
        返回:
            图像坐标系中的点，格式与输入保持一致（单点或点列表）
        """
        # 获取相机校准信息
        if isinstance(mode, int):
            # 通过相机索引获取校准信息（拖框模式使用共享校准信息）
            calibInfo = self.calibInfo[self.rstpList[mode]]
        else:
            # 直接使用传入的校准信息
            calibInfo = mode

        # 提取校准参数
        h = calibInfo["cameraHeight"]  # 相机安装高度（米）
        vp = calibInfo["vanishPoint"]  # 消失点坐标（像素）
        resolution = calibInfo["resolution"]  # 图像分辨率（像素）
        per = calibInfo["radPerPixelFovV"]  # 垂直视场角每像素对应的弧度
        
        # 确保输入点为numpy数组并处理不同维度的输入
        points = np.array(points)
        objDim = points.ndim  # 获取输入点的维度（1维表示单点，2维表示多点）
        if objDim == 1:
            points = [points]  # 将单点转换为列表以便统一处理

        # 存储转换后的图像坐标点
        cvtObjs = []
        
        # 对每个雷达坐标点进行转换
        for obj in points:
            objX, objY = obj  # 雷达坐标系中的X（横向）和Y（纵向）坐标
            _, vpY = vp  # 消失点的Y坐标
            resolutionX, _ = resolution  # 图像宽度
            
            # ===== 计算图像坐标系中的Y坐标 =====
            # 1. 计算目标与相机的垂直夹角：arctan(objY / h)
            # 2. 将垂直夹角转换为相对于水平线的角度：0.5*np.pi - arctan(objY / h)
            # 3. 将角度转换为像素值：除以每像素对应的弧度(per)
            # 4. 以消失点Y坐标为基准进行偏移
            y = (0.5 * np.pi - np.arctan(objY / h)) / per + vpY
            
            # ===== 计算图像坐标系中的X坐标 =====
            # 1. 计算目标的水平夹角：arctan(objX / objY)
            # 2. 将角度转换为像素值：除以每像素对应的弧度(per)
            # 3. 以图像中心为基准进行偏移（resolution[0]/2）
            x = np.arctan(objX / objY) / per + resolutionX / 2
            
            # 保存转换后的坐标点
            cvtObjs.append((x, y))

        # 根据输入格式返回结果（单点或点列表）
        if objDim == 1:
            return cvtObjs[0]  # 输入为单点时返回单点
        else:
            return cvtObjs  # 输入为列表时返回列表


class ImageTool():
    def __init__(self):
        pass

    @staticmethod
    def convertResolution(data, inputResolution=(1280, 720), outputResolution=(800, 450), mode="xywh"):
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

    @staticmethod
    def iConvertResolution(data, inputResolution=(1280, 720), outputResolution=(800, 450), mode="xywh"):
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

    @staticmethod
    def xywhToPoint(box):
        x, y, w, h = box
        pointBox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        return pointBox


class ImageAreaHandle:
    def __init__(self, filePath, vanishHandle, displayPath, resolution=(800, 450)):
        self.fileManage = xypFileTool.JsonFileManage(filePath)  # json文件管理器
        xypFileTool.checkPath(displayPath)  # 目录不存在则创建目录
        self.displayPath = displayPath  # 区域可视化保存地址
        self.resolution = resolution  # 目标分辨率

        self._imageAreaDataShare = []  # 存储区域
        self._areaMaskShare = {0: None, 1: None}  # 存储图像掩膜

        self.areaLock = threading.Lock()  # 区域信息锁
        self.areaMaskLock = threading.Lock()  # 掩膜锁
        # 优先级高的可以覆盖优先级低的，相同等级的可以相互覆盖，值越大优先级越低
        # 0:屏蔽区或者无区域，1:误报区，10:报警区，101:拓展区，(可用值[0~255]，剩余空隙可拓展)
        self.priority = [0, 1, 10, 101]  # 目前已有等级

        self.isInAreaCode, self.isInArea = self.getIsInAreaFunction()  # 获取判断是否在区域内的函数

        self.vanishHandle = vanishHandle  # 灭点工具

        # 加载防区
        if os.path.exists(filePath):
            imageAreaData = self.fileManage.load()
            if imageAreaData is None:  # 加载失败
                imageAreaData = []
        else:
            imageAreaData = []

        # "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
        if self.fileManage.load() is None:
            imageAreaData0 = None
            imageAreaData1 = None
            try:  # 获取老旧防区
                with open("./config/shibian_t1_17_guard.txt", "rt") as f:
                    d0 = eval(f.read())
                with open("./config/shibian_t1_64_guard.txt", "rt") as f:
                    d1 = eval(f.read())
                imageAreaData0 = {0: d0, 1: d1}
            except:
                traceback.print_exc()
            try:  # 获取老旧屏蔽区
                imageAreaData1 = xypFileTool.JsonFileManage("./config/block_list.json").load()
            except:
                traceback.print_exc()
            if imageAreaData0 is not None:
                self.areaSet({'code': 100, 'data': imageAreaData0})  # 以web设置形式传入
            if imageAreaData1 is not None:
                self.areaSet({'code': 110, 'data': imageAreaData1})  # 以web设置形式传入
        else:
            self.areaSet(imageAreaData)
        # "<<<<<<<<<<<<<<<<<<<<<<<兼容处理"

    @property  # 定义函数为属性，用于在线程里面处理会动态修改的共享变量
    # 建议使用以引用的形式使用，即xxx = imageAreaData, 然后使用xxx，防止多次拷贝
    def imageAreaData(self):
        with self.areaLock:
            # return copy.deepcopy(self._imageAreaDataShare)  # 性能不足不能采用深度拷贝
            return self._imageAreaDataShare  # 可能造成使用时值发生改变


    @imageAreaData.setter  # imageAreaData设置值时调用
    def imageAreaData(self, value):
        with self.areaLock:
            self._imageAreaDataShare = value

    @property  # 定义函数为属性，用于在线程里面处理会动态修改的共享变量
    # 建议使用以引用的形式使用，即xxx = areaMask, 然后使用xxx，防止多次拷贝
    def areaMask(self):
        with self.areaMaskLock:
            # return copy.deepcopy(self._areaMaskShare) # 性能不足不能采用深度拷贝
            return self._areaMaskShare  # 可能造成使用时值发生改变

    @areaMask.setter  # areaMask设置值时调用
    def areaMask(self, value):
        with self.areaMaskLock:
            self._areaMaskShare = value

    # 获取判断是否在区域内的函数
    def getIsInAreaFunction(self):
        try:  # cIsInArea
            code = "c"
            device = platform.platform()[0:15]
            insidePath = os.path.abspath(os.path.join(".", "dependent", f'inside_{device}.so'))
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
                            x < (endPoint[0] - startPoint[0]) * (y - startPoint[1]) / (
                            endPoint[1] - startPoint[1]) +
                            startPoint[0]):
                        cnt += 1  # 有交点就加1
                return True if cnt % 2 == 1 else False

            isInArea = pythonIsInArea
        return code, isInArea

    # 区域兼容处理
    def areaCompatible(self, data):
        # 对于视觉区域
        '''
        data 当前传入格式：
        web防区设置：
            {code:100 data:{0:[area ...],1:[area ...]}}
            area:{alarm_level data_list [,...]}
        web屏蔽区设置：
            {code:110 data:{0:[area ...],1:[area ...]}}
            area:{reserved data_list [,...]}
        误报区设置
            {code: 2 data:{0:[area ...],1:[area ...]}}
            area:{type userArea [,...]}

        数据更新设置
            [area ...]
            area:{type userArea camId resolution code enable}
        输出
            [area ...]
            area:{type userArea camId resolution code enable}

        area{type userArea camId resolution code enable}为设置属性，区域应带有的，也就是必须属性
        其余属性为生成属性，即基于area设置属性生成的属性，设置属性发生更改，生成属性以及区域图像掩码都需要更改。

        '''
        if isinstance(data, dict):
            code = data["code"]
            areaData = data["data"]
            imageAreaData = self.imageAreaData

            imageAreaData = [area for area in imageAreaData if area["code"] != code]

            if code == 100:  # 防区数据
                for camId in areaData:
                    if camId in ["0", "1", 0, 1]:
                        for area in areaData[camId]:
                            areaInfo = {}
                            areaInfo["type"] = 10
                            areaInfo["code"] = code
                            areaInfo["camId"] = int(camId)  # 旧版可能为字符串
                            areaInfo["userArea"] = [i[:2] for i in area["data_list"]]
                            areaInfo["resolution"] = [1280, 720]
                            areaInfo["enable"]  =area["enable"]  if  "enable" in area else 1
                            imageAreaData.append(areaInfo)
            elif code == 110:  # 屏蔽区数据
                for camId in areaData:
                    if camId in ["0","1",0,1]:
                        for area in areaData[camId]:
                            areaInfo = {}
                            areaInfo["type"] = 0
                            areaInfo["code"] = code
                            areaInfo["camId"] = int(camId)  # 旧版可能为字符串
                            areaInfo["userArea"] = [i[:2] for i in area["data_list"]]
                            areaInfo["resolution"] = [1280, 720]
                            areaInfo["enable"] = area["enable"] if "enable" in area else 1
                            imageAreaData.append(areaInfo)

            elif code == 2:
                pass

        elif isinstance(data, list):  # 无需兼容，加载的数据
            imageAreaData = data
        else: # 更新生成数据
            imageAreaData = self.imageAreaData
        return imageAreaData

    # 区域保存
    def areaSave(self, imageAreaData):
        '只保存 {type camId userArea resolution enable code} 几个属性'
        imageAreaDataSave = []
        for area in imageAreaData:
            imageAreaDataSave.append(
                {k: v for k, v in area.items() if k in ["type", "userArea", "camId", "resolution","enable","code"]})
        self.fileManage.save(imageAreaDataSave)

    # 加快判断是否在区域内，创建图像mask
    def areaMaskCreate(self, imageAreaData):
        self.areaMaskCreateRun = True  # 线程运行标识符

        self.areaMask = {0: None, 1: None}
        areaMask = {0: None, 1: None}
        for camId in areaMask:
            mask = Image.new('L', self.resolution, "black")
            idMask = Image.new('L', self.resolution, "white")

            draw = ImageDraw.Draw(mask)
            idDraw = ImageDraw.Draw(idMask)

            # 将优先级低的先画，防止覆盖优先级高的，type越大优先级越低
            for areaType in self.priority[::-1]:
                for area in imageAreaData:
                    if not self.areaMaskCreateRun:
                        return 0
                    if area["enable"] and area["camId"]==camId:
                        if areaType == 101 and area["validExtendArea"] is not None:
                            draw.polygon([tuple(i) for i in area["validExtendArea"]], fill=areaType)
                        elif area["type"] == areaType and area["validArea"] is not None:
                            draw.polygon([tuple(i) for i in area["validArea"]], fill=areaType)
                            idDraw.polygon([tuple(i) for i in area["validArea"]], fill=area["areaId"])

            nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            mask.save(os.path.join(self.displayPath, f"{nowTime}_camera{camId}_areaMask.jpg"))
            areaMask[camId] = np.stack([np.array(mask), np.array(idMask)], axis=-1)  # 一次性更新以便同步
        self.areaMask = areaMask

    # 视觉防区设置雷达防区
    def imageAreaSetRadarArea(self, radarAreaHandle):
        try:
            xypDebug("imageAreaSetRadarArea start")
            imageAreaData = self.imageAreaData
            data = []
            for area in imageAreaData:
                if area["validArea"] is not None:
                    validWorldArea =self.vanishHandle.estimateImageToRadar(area["validArea"], area["camId"])
                    if area["type"] ==10:  # 暂时只映射防区
                        data.append({"type": 10, "userArea": validWorldArea})
            return radarAreaHandle.areaSet({"code": 1, "data": data})  # 以web设置形式传入
        except:
            xypDebug("imageAreaSetRadarArea error", traceback.format_exc())
            return False

    # 区域设置
    def areaSet(self, data=None):
        try:
            xypDebug("imageAreaSet start", data)
            # 区域兼容处理
            imageAreaData = self.areaCompatible(data)

            '''区域信息增强，生成属性'''
            # 生成防区Id
            for areaId, area in enumerate(imageAreaData):
                area["areaId"] =areaId
            # 生成有效区域、拓展区域

            for area in imageAreaData:
                # userArea 用户区域
                # validArea 有效区域
                # validExtendArea 有效的拓展区域
                if not np.array_equal(area["resolution"], self.resolution):  # 如果分辨率存在且不符合目标分辨率self.resolution
                    area["userArea"] = ImageTool.convertResolution(area["userArea"], area["resolution"],self.resolution, "xy").tolist()
                    area["resolution"] = self.resolution
                calibInfo = self.vanishHandle.getCalibInfoByCamId(area["camId"])
                validImageArea = calibInfo["imageManageArea"]
                validWorldArea = calibInfo["worldManageArea"]
                a=time.time()
                p1 = Polygon(validImageArea)
                p2 = Polygon(area["userArea"])
                p3 = Polygon(validWorldArea)


                if p1.intersects(p2):
                    # 计算有效防区，即灭点以下
                    '''validArea'''
                    area["validArea"] = list(p1.intersection(p2).exterior.coords)[:-1]
                    if self.isInAreaCode == "c":
                        polyNum = len(area["validArea"])
                        cArea = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in area["validArea"]))
                        area["cValidArea"] = [polyNum, cArea]
                    else:
                        area["cValidArea"] = None
                    '''validExtendArea'''
                    if area["type"] == 10:  # 报警区才有拓展
                        extendArea = self.areaScale(self.vanishHandle.estimateImageToRadar(area["validArea"], area["camId"]),2)
                        validExtendArea = list(p3.intersection(Polygon(extendArea)).exterior.coords)[:-1]
                        area["validExtendArea"] = self.vanishHandle.estimateRadarToImage(validExtendArea, area["camId"])
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

            # 区域设置
            self.imageAreaData = imageAreaData
            self.areaSave(imageAreaData)  # 区域保存
            self.areaDisplay(imageAreaData)  # 区域可视化
            # 区域创建mask
            # 停止线程

            for thread in threading.enumerate():
                if thread.getName() == "imageAreaMaskCreate":
                    self.areaMaskCreateRun = False
                    break
            # 等待线程结束
            while True:
                breakFlag = True
                for thread in threading.enumerate():
                    if thread.getName() == "imageAreaMaskCreate":
                        breakFlag = False
                if breakFlag:
                    break
                time.sleep(0.1)
            # 重开线程后台慢慢生成mask
            threading.Thread(target=self.areaMaskCreate, args=(imageAreaData,),name="imageAreaMaskCreate").start()

            xypDebug("imageAreaSet done", imageAreaData)
            print("视觉防区存储成功")
            return True
        except:
            xypDebug("imageAreaSet error", traceback.format_exc())
            print("imageAreaSet error", traceback.format_exc())
            return False

    # 区域缩放
    def areaScale(self, data, dis):
        """
        多边形等距缩放 https://zhuanlan.zhihu.com/p/97819171
        data: [n,2->(x,y)], 多边形按照逆时针顺序排列的的点集
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

    # 区域回复给web
    def areaSendToWeb(self, isIgnore=False):
        imageAreaData = self.imageAreaData

        '只发送 {type camId areaId userArea resolution} 五个属性'
        imageAreaDataSend = {0: [], 1: []}
        for area in imageAreaData:
            "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
            if isIgnore:
                if area["type"] ==0:
                    areaSend = {}
                    areaSend["data_list"] = ImageTool.convertResolution(area["userArea"], area["resolution"],
                                                                        (1280, 720), "xy").tolist()  # 网页需要1280*720的
                    areaSend["alarm_level"] = 0
                    areaSend["camId"] = area["camId"]
                    areaSend["areaId"] = area["areaId"]
                    areaSend["resolution"] = (1280, 720)
                    imageAreaDataSend[area["camId"]].append(areaSend)
            else:
                if area["type"] ==10:
                    areaSend = {}
                    areaSend["data_list"] = ImageTool.convertResolution(area["userArea"], area["resolution"],
                                                                        (1280, 720), "xy").tolist()  # 网页需要1280*720的
                    areaSend["alarm_level"] =1
                    areaSend["camId"] = area["camId"]
                    areaSend["areaId"] = area["areaId"]
                    areaSend["resolution"] = (1280, 720)
                    imageAreaDataSend[area["camId"]].append(areaSend)
            "<<<<<<<<<<<<<<<<<<<<<<<兼容处理"
        return imageAreaDataSend

    def areaDisplay(self,imageAreaData):
        nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        for camId in [0, 1]:
            fig = plt.figure(f"camera{camId} area, unit:px", facecolor='white')
            ax = plt.subplot()
            ax.cla()

            imageAreaDataUseless = [area  for area in imageAreaData if not area["enable"] and area["camId"]==camId]
            imageAreaDataUseful = [area  for area in imageAreaData if area["enable"] and area["camId"]==camId]
            for enableFlag,imageArea in enumerate([imageAreaDataUseless,imageAreaDataUseful]) :# 先绘制失效的
                if enableFlag == 0:
                    edgecolor = (0.5, 0.5, 0.5, 1)
                    linewidth = 2
                else:
                    edgecolor = None
                    linewidth = 0
                for areaType in self.priority[::-1]:
                    for area in imageArea:
                        if areaType == 101 and area["validExtendArea"] is not None:
                            polygon = plt.Polygon(area["validExtendArea"], closed=True, facecolor=(0, 0, 1, 1), edgecolor=edgecolor, linewidth=linewidth)
                            ax.add_patch(polygon)
                        elif area["type"] == areaType:
                            if area["type"] == 0:
                                fillColor = (0, 0, 0, 0.8)  # 黑
                            elif area["type"] == 1:
                                fillColor = (1, 1, 0, 0.8)  # 黄
                            elif area["type"] == 10:
                                fillColor = (1, 0, 0, 0.8)  # 红
                            polygon = plt.Polygon(area["userArea"], closed=True, facecolor=fillColor, edgecolor=edgecolor, linewidth=linewidth)
                            ax.add_patch(polygon)
                            if area["validArea"] is not None:
                                polygon = plt.Polygon(area["validArea"], closed=True, facecolor=(0, 1, 0, 0.5), edgecolor=edgecolor, linewidth=linewidth)
                                ax.add_patch(polygon)
            ax.set_xlim(0, self.resolution[0])
            ax.set_ylim(0, self.resolution[1])
            ax.invert_yaxis()
            savePath = f"{self.displayPath}/{nowTime + f'_pixel_camera{camId}_imageArea.jpg'}"
            print(f"Image area display path {savePath}, unit:px")
            fig.savefig(savePath)

        for camId in [0, 1]:
            fig = plt.figure(f"camera{camId} area, unit:m", facecolor='white')
            ax = plt.subplot()
            ax.cla()
            imageAreaDataUseless = [area for area in imageAreaData if not area["enable"] and area["camId"] == camId]
            imageAreaDataUseful = [area for area in imageAreaData if area["enable"] and area["camId"] == camId]
            for enableFlag, imageArea in enumerate([imageAreaDataUseless, imageAreaDataUseful]):  # 先绘制失效的
                if enableFlag == 0:
                    edgecolor = (0.5, 0.5, 0.5, 1)
                    linewidth = 2
                else:
                    edgecolor = None
                    linewidth = 0
                for areaType in self.priority[::-1]:
                    for area in imageArea:
                        if areaType == 101 and area["validExtendArea"] is not None:
                            polygon = plt.Polygon(self.vanishHandle.estimateImageToRadar(area["validExtendArea"],camId), closed=True, facecolor=(0, 0, 1, 1),
                                                  edgecolor=edgecolor, linewidth=linewidth)
                            ax.add_patch(polygon)
                        elif area["type"] == areaType:
                            if area["type"] == 0:
                                fillColor = (0, 0, 0, 0.8)  # 黑
                            elif area["type"] == 1:
                                fillColor = (1, 1, 0, 0.8)  # 黄
                            elif area["type"] == 10:
                                fillColor = (1, 0, 0, 0.8)  # 红

                            if area["validArea"] is not None:
                                polygon = plt.Polygon(self.vanishHandle.estimateImageToRadar(area["validArea"], camId),
                                                      closed=True, facecolor=fillColor,
                                                      edgecolor=edgecolor, linewidth=linewidth)
                                ax.add_patch(polygon) # userArea在无效区域绘制会出现问题，保证融合色一致
                                polygon = plt.Polygon(self.vanishHandle.estimateImageToRadar(area["validArea"],camId), closed=True, facecolor=(0, 1, 0, 0.5),
                                                      edgecolor=edgecolor, linewidth=linewidth)
                                ax.add_patch(polygon)
            ax.set_xlim(-50, 50)
            ax.set_ylim(0, 250)
            savePath = f"{self.displayPath}/{nowTime + f'_meter_camera{camId}_imageArea.jpg'}"
            print(f"Image area display path {savePath}, unit:m")
            fig.savefig(savePath)

        # plt.show()

    def getObjArea(self, orgBox, camId):

        if len(orgBox) == 2:
            x, y = orgBox
        else:
            x, y = orgBox[0] + orgBox[2] / 2, orgBox[1] + orgBox[3]
        areaMask = self.areaMask

        if areaMask[camId] is not None:
            x = int(round(min(self.resolution[0] - 1, max(x, 0))))
            y = int(round(min(self.resolution[1] - 1, max(y, 0))))
            areaType, areaId = areaMask[camId][y, x]  # json不支持uint8格式
            return int(areaType), int(areaId)
        else:
            imageAreaData = self.imageAreaData

            if self.isInAreaCode == "c":
                for areaType in self.priority:
                    for area in imageAreaData:
                        if area["enable"]:
                            if area["type"] == areaType and area["camId"] == camId and area["cValidArea"] is not None:
                                polyNum, cArea = area["cValidArea"]
                                if self.isInArea(float(x), float(y), polyNum, cArea):
                                    return areaType, area["areaId"]
                            elif areaType == 101 and area["camId"] == camId and area["cValidExtendArea"] is not None:
                                polyNum, cArea = area["cValidExtendArea"]
                                if self.isInArea(float(x), float(y), polyNum, cArea):
                                    return areaType, area["areaId"]
            else:
                for areaType in self.priority:
                    for area in imageAreaData:
                        if area["enable"]:
                            if area["type"] == areaType and area["camId"] == camId and area["validArea"] is not None:
                                if self.isInArea([x, y], area["validArea"]):
                                    return areaType, area["areaId"]
                            elif areaType == 101 and area["camId"] == camId and area["validExtendArea"] is not None:
                                if self.isInArea([x, y], area["validExtendArea"]):
                                    return areaType, area["areaId"]
        return 0, -1  # 都不在


class HandleCameraData():
    # HandleCameraData以handleCameraData为全类调用及输入点
    def __init__(self, imageAreaHandle, vanishHandle, filterFlag=True, tempClass=None,resolution=(800, 450)):
        self.tempClass = tempClass
        self.resolution = resolution
        self.vanishHandle = vanishHandle
        self.imageAreaHandle = imageAreaHandle

        self.cameraObj=[]
        self.camreaObjLock = threading.Lock()
        self.cacheTime=5
        self.cameraBoxRate = 100 # 1s 考虑到误识别框一直存在，最多允许 相机数2*识别帧数5*帧最多允许10个目标
        self.mask0 = cv.imread("./config/mask0.jpg", 0)
        self.mask1 = cv.imread("./config/mask1.jpg", 0)

    def updateCameraRecord(self, cameraData, nowTime):
        with self.camreaObjLock:
            for cam in cameraData:
                for obj in cam["data"]:
                    if obj["type"]==10 and obj["class"]==0:
                        self.cameraObj.append(obj)
            self.cleanHistory(nowTime)

    def calculateIou(self,w0, h0, w1, h1):
        # 确定交集的宽度和高度
        interW = min(w0, w1)
        interH = min(h0, h1)
        # 计算交集的面积
        interS = interW * interH

        # 计算并集的面积
        unionS = w0 * h0 + w1 * h1 - interS
        # 计算 IoU
        iou = interS / unionS
        return iou

    def handleCameraData(self, data, nowTime=None):
        """
        这里是子线程，处理目标相机box数据
        具体包括处理遮挡报警和偏转报警
        处理相机目标框信息

        """
        try:
            if nowTime is None:
                nowTime=time.time()
                msg_bytes, ip_port = data
                msg = msg_bytes.decode("utf-8")
                cameraData = json.loads(msg[msg.index("{"):])
            else:
                cameraData={"list":data}

            if "list" in cameraData:  # 存在目标
                with self.camreaObjLock:
                    xypLog.xypDebug("camera data",cameraData['list'])
                    virtualObj=[]
                    for cam in cameraData['list']:
                        camId = cam['id']
                        camObjData = cam["data"]
                        # camTime = cam["timestamp"]

                        for obj in camObjData:
                            orgBox = obj["bbox"]
                            cls= obj["class"]
                            orgBox = ImageTool.convertResolution(orgBox, inputResolution=(640, 640),
                                                                 outputResolution=(800, 450)).tolist()
                            areaType, areaId = self.imageAreaHandle.getObjArea(orgBox, camId)


                            orgBox = self.normalizeBox(orgBox[:4])
                            estimateX, estimateY = self.vanishHandle.estimateImageToRadar(orgBox, camId)
                            x, y, w, h = orgBox

                            estimateWait = None
                            # 视觉框无法精准判断是否处于某个区域（有波动），所以会出问题（可能会误差几十米）
                            # 这里通过变化后的距离的框不能变化太大，作为标准，尽可能减小异常，目前没有好的办法
                            virtual=[]
                            if camId == 0 and (self.mask0[int(y + h), int(x )] or self.mask0[int(y + h), int(x +  w)]) > 127:
                                # 校准后
                                a0, b0 = 1887.5606433890775, 224.45785317813616
                                # a1, b1 = 4603.39661590037, 216.86443751308656


                                dd = (a0 / estimateY + b0) 
                                objXYWH = [x, int(y - dd), w, h]
                                objXYWH = self.normalizeBox(objXYWH)
                                virtual = self.vanishHandle.estimateImageToRadar(objXYWH, camId)

                            elif camId == 1 and (self.mask1[int(y + h), int(x )] or self.mask1[int(y + h), int(x +  w)])> 127:


                                a0, b0 = 11701.508805282434, 162.26036278055753
                                # a1, b1 = 22868.48657544839, 57.069436312682946

                                dd = (a0 / estimateY + b0) 
                                objXYWH = [x, int(y - dd), w, h]
                                objXYWH = self.normalizeBox(objXYWH)
                                virtual= self.vanishHandle.estimateImageToRadar(objXYWH, camId)
                            obj.clear()
                            obj.update({"camId": camId, "timeStamp": nowTime,"class":cls, "position": [estimateX, estimateY],"virtual": virtual,
                                       "xywh": orgBox, "type": areaType, "areaId": areaId})
                        camObjData.extend(virtualObj)
                self.updateCameraRecord(cameraData["list"], nowTime)



                cameraObjDataSendToWeb = {
                    'camerastatus': [{'nearcameraocclude': '-1', 'farcameraocclude': '-1', 'deflection': '-1',
                                      'nighttrainlight': '-1'}],

                    'list': [
                        {'id': v["id"], 'timestamp': 1, 'data': [{'confidence': -1, 'class': 0, 'bbox': [int(jj) for jj in obj["xywh"]],
                                                                      'dto': [9998,0,0, 0, 0],
                                                                      'in_area': 1} for obj in v["data"]]} for v in cameraData['list']],
                    'color': 0,
                    'stamp': time.time()}
                self.tempClass.tcp_server.send_camera_data(cameraObjDataSendToWeb)
        except Exception as e:
            xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")

    def cleanHistory(self,nowTime):
        # 该方案没有系统对时产生意外的风险
        while self.cameraObj:
            if nowTime - self.cameraObj[0]["timeStamp"] > self.cacheTime:
                self.cameraObj.pop(0)
            else:
                break  # track["track"]按时间排序的，节约计算量
        if len(self.cameraObj):
            self.cameraObj = self.cameraObj[-self.cacheTime*self.cameraBoxRate:]
    def ligthCopyCameraObj(self):
        with self.camreaObjLock:
            cameraObj = [obj.copy() for obj in self.cameraObj]
            return cameraObj  # 注意cameraObj里面的那些不能改，只复制到了哪一层

    def getCameraObj(self,needTime,nowTime):
        cameraObj = self.ligthCopyCameraObj()
        while cameraObj:
            if nowTime - self.cameraObj[0]["timeStamp"] > needTime:
                cameraObj.pop(0)
            else:
                break  # cameraObj按时间排序的，节约计算量
        if len(cameraObj):
            cameraObj = cameraObj[-self.cacheTime*self.cameraBoxRate:]
        cameraObj = [obj for obj in cameraObj if not self.isLittleAnimal(obj)] # 小动物过滤
        return cameraObj
    def normalizeBox(self,box):# 规范化框
        # box:[x,y,w,h]，x,y为左上角
        x, y, w, h = box
        x1, y1, x2, y2 = x, y, x + w, y + h
        x1 = max(0, min(x1, self.resolution[0] - 1))
        y1 = max(0, min(y1, self.resolution[1] - 1))
        x2 = max(0, min(x2, self.resolution[0] - 1))
        y2 = max(0, min(y2, self.resolution[1] - 1))
        return [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
    def isLittleAnimal(self, obj):
        estimateY =obj["position"][1]
        camId =obj["camId"]
        h = obj["xywh"][-1]
        calibInfo = self.vanishHandle.getCalibInfoByCamId(camId)
        objHMeter = 1.7 # 人的估计宽高
        objHPixel = np.arctan(objHMeter / estimateY) / calibInfo["radPerPixelFovV"]
        if h > (objHPixel/1.75*0.7):
            return False
        else:
            return True
    

if __name__ == "__main__":
    vanishHandle = CameraVanishHandle()
    imageAreaHandle = ImageAreaHandle(os.path.join(".", "config", "imageArea.json"), vanishHandle, "./aa")
    imageAreaHandl = imageAreaHandle.areaSendToWeb()
    imageAreaHandle.areaSet({"code":100,"data":imageAreaHandl})
    imageAreaHandle.areaSet({"code": 110, "data": imageAreaHandl})
    time.sleep(848)
    a = CameraVanishHandle()

    json108 = {'code': 108, 'data': {'index': 1, 'vanishingPoint': [616, 137], 'camera_height': 11112.3}}
    json106 = {"code": 106, "msg": "success", "data": {
        "0": {"fov_V_deg": 3.6614114505309927, "fov_H_deg": 1, "vanishingPoint": [380, 236], "camera_height": 2.12,
              "rad_per_pixel": 0.000934721, "vanishPoint": [547, 88], "resolution": [800, 450],
              "imageManageArea": [[1, 237], [799, 237], [799, 449], [1, 449]],
              "worldManageArea": [[-887.4110622018463, 2268.0557969522274], [887.4110622018463, 2268.0557969522274],
                                  [4.111055577195252, 10.507084969524145],
                                  [-4.111055577195252, 10.507084969524145]]},
        "1": {"fov_V_deg": 4.461411450530993, "fov_H_deg": 1, "vanishingPoint": [316, 142], "camera_height": 2.12,
              "rad_per_pixel": 0.000221075, "vanishPoint": [547, 88], "resolution": [800, 450],
              "imageManageArea": [[1, 143], [799, 143], [799, 449], [1, 449]],
              "worldManageArea": [[-848.0807142621244, 9589.505667585807], [848.0807142621244, 9589.505667585807],
                                  [2.7582350006738627, 31.188199102615556],
                                  [-2.7582350006738627, 31.188199102615556]]}}}

    a.calibInfoSet(json106)

    a.calibInfoSet(json108)
    a.calibInfoSet(json108)
