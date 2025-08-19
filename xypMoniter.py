import cv2 as cv
import datetime
import numpy as np
import os
import time
import traceback
from xypTool.common import xypFileTool
from buffer_queue import BufferQueue
from common_FireTimer import *
from common_hysteresis_threshold import EDGE_DETECT
from config_manager import ConfigManager, MainEngine_Config
from drawRadarDataTool import RadarDisplay
from moniter_trace_alarm_event import Monitor_alarm_Event
from xypCaptureImage import RstpCapture
from xypFrameDiff import CalDiff
from xypPushImage import PushStream
from xypTool.debug import xypLog
from xypWeather import Weather
import itertools
THRESHOLD_NEAR_FAR = 55


class MonitorTrace:
    def __init__(self, config=None, main_config=None,imageAreaHandle=None,resolution=(800, 450),radarDriver=None):

        self.cameraDataHandle = None
        self.radarDataHandle = None

        self.deviceControlForBeiJing = None
        self.lastSendDeviceStatusTime = 0
        self.alarmRecord = []  # 记录报警分数
        self.imageAreaHandle=imageAreaHandle

        self.alarm_state_dict = {1: 0, 2: 0, 3: 0}
        self.fog_coef_near = 1.0  # 默认原来的fog参数配置


        self.alarm_idx = 0
        self.alarm_state = 3


        self.gpio_alarm_relay_callback = None
        self.config: ConfigManager = config
        self.main_config: MainEngine_Config = main_config
        self.radarDisplay = RadarDisplay(template_png_path=os.path.join(config.config_folder, "radarPicTemplate.png"))
        self.scores_string = ""



        self.image_coef = 1920.0 / 800.0  # 800*450 >>> 1920*1080的转换系数.

        self.alarm_distance_final = 0
        self.isAlarm = 0
        self.alarmojbs = [{'id': 0, 'bboxs': []}, {'id': 1, 'bboxs': []}]
        self.bbox_list_dict = {0: [], 1: [], 'timestamp': 0}  # 0 1 是相机id
        self.alarmojbs_cnt = 0

        self.reportdata_for_web = {}
        self.usingCrossToWeightConfidence = False
        self.udp_debug_callback = None

        self.get_corsssection_ofObj_callback_dict = {}
        self.acousto_optic_alarm_callback = None
        self.report_cnt = 0
        self.report_alarm_cnt = 0
        self.acousto_optic_alarm_callback_firetimer = FireTimer()

        self.saveAlarmPicture_task_enQueue = None
        self.save_c01_radar_pic_callback = None
        self.savePic_callback_firetimer = FireTimer()
        self.web_url_firetimer = FireTimer()

        # debug mcu delay
        self.acousto_optic_test_fireTime = FireTimer()
        self.acousto_optic_test_alarm = False

        # 20220614 火车阻塞报警
        self.is_train_block_alarm = 0
        self.is_train_block_alarm_block_fire_timer = FireTimer_WithCounter(2)
        self.isTrianInView_edge = EDGE_DETECT()

        self.debug_fire = FireTimer()
        self.send_alarm_event_callback = None
        self.monitor_alarm_event = Monitor_alarm_Event()
        self.saveAlarmInfo2= {}

        # 以下四个变量在flashAlarmState函数中更新
        self.alarm = 0  # 当前报警
        self.state = 0  # 记录报警状态
        self.alarmId = 0  # 报警id
        self.alarmEnableTime = time.time()

        self.useCamera = 1 # 当前视觉
        self.useCameraChangeTime = time.time()
        self.mergeAlarmTime = 15

        self.nowTime = time.time() #当前时间
        self.alramMerge = time.time() # 上一次
        self.videoPath = None
        self.imagePath = None
        self.alarmInfo = {}
        self.resolution = resolution
        #720 1280
        self.cam0 = RstpCapture('rtsp://admin:Admin123@192.168.8.12:8554/1',test=False)
        self.cam1 = RstpCapture('rtsp://admin:Admin123@192.168.8.11:8554/1',test=False)

        self.diff0 = CalDiff(self.cam0,frameSize=(800, 450))
        self.diff1 = CalDiff(self.cam1,frameSize=(800, 450))

        self.timeMoniterMax={}

        with open("/ssd/xyp/tempConfigWeather.txt","rt") as f:
            txt = f.read()
        if "1" in txt: # 目前天气遮挡比较难用，先做一个可关闭接口
            self.weather0 = Weather(self.cam0, "./config/weather0.pkl", frameSize=(800, 450))
            self.weather1 = Weather(self.cam1, "./config/weather1.pkl", frameSize=(800, 450))
            self.weather = 1
        else:
            self.weather=0

        with open("/ssd/lss/guard_tvt-BJCOMP2025/tempConfigPushInfo.txt","rt") as f:
            txt = f.read() 
        if "1" in txt:
            self.pushStream=PushStream(ip='0.0.0.0',port=8091,mode=0)
        else:
            self.pushStream = None
        self.radarAlarm = 0
        self.radarTrack = []
        self.cameraObj = []
        self.moveMask = np.zeros((900, 800) ,dtype=np.uint8)

        self.imageCoef = 1920.0 / 800.0  # 800*450 >>> 1920*1080的转换系数.

        self.timeState = {}

        self.dayFile =datetime.datetime.now().strftime('%Y-%m-%d')

        self.radarDiffAlarmFlag= {"time": time.time(),"alarmNum":0,"alarmPos":[]}
        self.singleRadarAlarmWait={"time": time.time(),"wait":0}



        # 后期希望假如配置文件的变量
        self.calibrateEnable  = 0 # 是否启动标定模式，标定模式用于比赛或者路面较为平坦的精准标定情况下,表示相信视觉框的距离
        self.cameraDiffEnable = 1 # 是否启用帧差



        self.radarDriver= radarDriver

        while True:
            try:
                print("sadasd",radarDriver)
                print(self.radarDriver.decoder.gen_frame(b"\x71\x0C\x00\x01" + bytes([1])),"rrtetretre")
                print(''.join(['%02X' % b for b in self.radarDriver.decoder.gen_frame(b"\x71\x0C\x00\x01" + bytes([0]))]))
                self.radarDriver.comm_send(self.radarDriver.decoder.gen_frame(b"\x71\x0C\x00\x01" + bytes([0])))
                break
            except:
                time.sleep(0.5)

    def flashAlarmState(self,alarm):
        if not self.alarm and not alarm: # 0->0
            self.state = 0
        elif not self.alarm and alarm:# 0->1
            self.state = 1
            self.alarmId += 1
            self.alarmEnableTime = self.nowTime
        elif self.alarm and alarm: # 1->1
            self.state = 2
            self.alarmEnableTime =self.nowTime
        elif self.alarm and not alarm :# 1->0
            if self.nowTime - self.alarmEnableTime > self.mergeAlarmTime:
                self.state = 3
            else:
                alarm = 4 # alarm为4表示虚拟报警
                self.state = 2
        self.alarm = alarm


    def pushInfo(self):
        if self.pushStream is None:
            return 0
        def drawRadar(radarTrack,moveMask,color,width):
            for track in radarTrack:

                for obj in track["virtual"]:
                    for camId, box in enumerate(obj["xywh"]):
                        x, y, w, h = box
                        if camId == 1:
                            y = y + 450
                        x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                        if np.array_equal(color,[0, 255, 0]):
                            moveMask = cv.rectangle(moveMask, (x1, y1), (x2, y2), (255,0,255), width)
                        else:
                            moveMask = cv.rectangle(moveMask, (x1, y1), (x2, y2), (255,150,255), width)

                for obj in track["track"]:
                    for camId, box in enumerate(obj["xywh"]):
                        x, y, w, h = box
                        if camId == 1:
                            y = y + 450
                        x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                        moveMask = cv.rectangle(moveMask, (x1, y1), (x2, y2), color, width)

            return moveMask

        def drawCamera(cameraObj,moveMask,color,width):
            for obj in cameraObj:
                x, y, w, h = obj["xywh"]
                if obj["camId"] == 1:
                    y = y + 450
                x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                moveMask = cv.rectangle(moveMask, (x1, y1), (x2, y2),color,width)
            return moveMask

        # if self.alarm == 1:
        #     moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
        #     moveMask = drawCamera([obj for obj in self.cameraObj if obj["alarm"]], moveMask, [0, 255, 255], 3)
        #     moveMask = drawCamera([obj for obj in self.cameraObj if not obj["alarm"]], moveMask, [0, 0, 255], 3)
        #     moveMask = drawRadar(self.radarTrack, moveMask, [255, 0, 0], 3)
        # elif self.alarm == 2:
        #     moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
        #     moveMask = drawRadar([track for track in self.radarTrack if track["alarm"]], moveMask, [0, 255, 0], 3)
        #     moveMask = drawRadar([track for track in self.radarTrack if not track["alarm"]], moveMask, [255, 0, 0], 3)
        # elif self.alarm == 3:
        #     moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
        #     drawRadar(self.radarTrack, moveMask, [255, 255, 0], 3)
        # else:
        #     moveMask = np.zeros([900, 800,3], dtype=np.uint8)+127
        #     moveMask[self.moveMask==1]=[255, 255,255]
        #     moveMask = drawCamera(self.cameraObj, moveMask, [0, 0, 255], 3)
        #     moveMask = drawRadar(self.radarTrack, moveMask, [255, 0, 0], 3)
        # self.pushStream.task.append(cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR))
        # # self.pushStream.task.append(cv.resize(moveMask, (0, 0), fx=0.5, fy=0.5))
        if self.alarm == 1:
            moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
            if not self.diffUse:
                moveMask[self.moveMask == 1] = [200, 200, 230]
            drawMask = np.zeros_like(moveMask,dtype=np.uint8)
            drawMask = drawRadar(self.radarTrack, drawMask, [255, 0, 0], 3)
            drawMask = drawCamera([obj for obj in self.cameraObj if obj["alarm"]], drawMask, [0, 255, 255], 3)
            drawMask = drawCamera([obj for obj in self.cameraObj if not obj["alarm"]], drawMask, [0, 0, 255], 3)
            ddraw = np.sum(drawMask, axis=-1)
            moveMask[ddraw != 0] = moveMask[ddraw != 0] * 0.5 + drawMask[ddraw != 0] * 0.5
        elif self.alarm == 2:
            moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
            if not self.diffUse:
                moveMask[self.moveMask == 1] = [200, 200, 230]
            drawMask = np.zeros_like(moveMask,dtype=np.uint8)
            drawMask = drawRadar([track for track in self.radarTrack if track["alarm"]], drawMask, [0, 255, 0], 3)
            drawMask = drawRadar([track for track in self.radarTrack if not track["alarm"]], drawMask, [255, 0, 0], 3)
            drawMask = drawCamera(self.cameraObj, drawMask, [0, 0, 255], 3)
            ddraw = np.sum(drawMask, axis=-1)
            moveMask[ddraw != 0] = moveMask[ddraw != 0] * 0.5 + drawMask[ddraw != 0] * 0.5
        elif self.alarm == 3:
            moveMask = cv.cvtColor(self.moveMask.astype(np.uint8) * 255, cv.COLOR_GRAY2BGR)
            if not self.diffUse:
                moveMask[self.moveMask == 1] = [200, 200, 230]
            drawMask = np.zeros_like(moveMask,dtype=np.uint8)
            drawMask = drawRadar([track for track in self.radarTrack if track["alarm"]], drawMask, [255, 255, 0], 3)
            drawMask = drawRadar([track for track in self.radarTrack if not track["alarm"]], drawMask, [255, 0, 0], 3)
            drawMask = drawCamera(self.cameraObj, drawMask, [0, 0, 255], 3)
            ddraw = np.sum(drawMask,axis=-1)
            moveMask[ddraw!=0]=moveMask[ddraw!=0]*0.5+drawMask[ddraw!=0]*0.5

        else:
            moveMask = np.zeros([900, 800, 3], dtype=np.uint8) + 127
            moveMask[self.moveMask == 1] = [255, 255, 255]
            if not self.diffUse:
                moveMask[self.moveMask == 1] = [200, 200, 230]

            drawMask = np.zeros_like(moveMask,dtype=np.uint8)
            drawMask = drawCamera(self.cameraObj, drawMask, [0, 0, 255], 3)
            drawMask = drawRadar(self.radarTrack, drawMask, [255, 0, 0], 3)
            ddraw = np.sum(drawMask, axis=-1)
            moveMask[ddraw != 0] = moveMask[ddraw != 0] * 0.5 + drawMask[ddraw != 0] * 0.5

        currentTime = datetime.datetime.fromtimestamp(self.nowTime).strftime("%Y-%m-%d %H:%M:%S")
        # 在图像上写入当前时间
        if self.useCamera:
            moveMask=cv.putText(moveMask, currentTime, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            moveMask=cv.putText(moveMask, currentTime, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        moveMask[447:453]=255
        self.pushStream.task.append(cv.resize(moveMask, (0, 0), fx=0.5, fy=0.5))
        self.pushStream.task.append(moveMask)

        # diff0 = cv.cvtColor(cv.resize(self.cam0.getImage(), self.resolution), cv.COLOR_BGR2GRAY)
        # diff1 = cv.cvtColor(cv.resize(self.cam1.getImage(), self.resolution), cv.COLOR_BGR2GRAY)
        #
        # self.pushStream.task.append(cv.resize(np.concatenate([diff0, diff1], axis=0), (0, 0), fx=0.5, fy=0.5))
        # xypLog.xypDebug("sssssssssssssssssssssssssssssssss")
    def calculate_intersection_union(self,y1, y2, y3, y4):
        # 确定线段AB的区间和线段CD的区间
        segment_ab = (min(y1, y2), max(y1, y2))
        segment_cd = (min(y3, y4), max(y3, y4))

        # 计算交集
        intersection_start = max(segment_ab[0], segment_cd[0])
        intersection_end = min(segment_ab[1], segment_cd[1])

        if intersection_start <= intersection_end:
            intersection = intersection_end - intersection_start
        else:
            intersection = 0

        return intersection

    # 视觉+帧差适用于遮挡情况，这里默认不是遮挡的情况
    # def moveMaskReferByCamera(self): # 只负责横穿
    #     isAlarm = False
    #     # 这里最好不要带上和距离相关的，因为这是在非平面通用的
    #     for obj in self.cameraObj:
    #         if self.calibrateEnable: # 帧差启用
    #             x, y, w, h = obj["xywh"]
    #             if obj["camId"] == 0:
    #                 if not self.diffUse0: # 帧差启用但帧差不可用（如光影疯狂干扰）时
    #                     obj["alarm"] = 1
    #                     continue
    #                 elif self.calibrateEnable and (obj["position"][1] > 60 or obj["position"][1] <10):
    #                     # 近焦大于60m框就太小了，容易框到帧差噪声点，小于10m框高度太小；虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
    #                     obj["alarm"] = 0
    #                     continue
    #                 elif not self.calibrateEnable and w*h < 30: # 框太小容易框到帧差噪声点
    #                     obj["alarm"] = 0
    #                     continue
    #             else:
    #                 if not self.diffUse1:  # 帧差启用但帧差不可用（如光影疯狂干扰）时
    #                     obj["alarm"] = 1
    #                     continue
    #                 elif self.calibrateEnable and (obj["position"][1] > 250 or obj["position"][1] <50):
    #                     # 远焦大于250m框就太小了，容易框到帧差噪声点；小于50m框高度太小，虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
    #                     obj["alarm"] = 0
    #                     continue
    #                 elif not self.calibrateEnable and w * h < 30: # 框太小容易框到帧差噪声点
    #                     obj["alarm"] = 0
    #                     continue
    #                 else:
    #                     y=y+450
    #             x1, y1, x2, y2 = x, int(y + 0.2 * h), x + w, int(y + 0.8 * h)# 很多噪声，现在看中间部分
    #             ratio=np.mean(self.moveMask[y1:y2, x1:x2])
    #             if ratio > 0.3:
    #                 obj["alarm"] = 1
    #             else:
    #                 obj["alarm"] = 0
    #         else:
    #             obj["alarm"] = 1
    #
    #     # 目的是为了框中人，怎么框中人比较合理呢
    #     # 直觉来说，视觉框包住其百分之九十，视觉框有一半的情况（被遮挡）
    #     # 不能太大雷达框，所以雷达框去除包住的视觉框部分后，剩余部分不应该超过视觉框的一半，不然留空太多了，但至少框中人了
    #     alarmCameraObj0 =  [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 0]
    #     alarmCameraObj1 =  [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 1]
    #     for camId, alarmCameraObj in enumerate([alarmCameraObj0, alarmCameraObj1]):
    #         if len(alarmCameraObj):
    #         # 真实的移动物体alarmCameraObj是有移动性的，但是不跟踪框的轨迹难以判断移动性，后期最好有轨迹跟踪提高准确性
    #             if self.calibrateEnable: # 用于准确标定时，如比赛的情况下
    #                 # 后期期望加入配合的雷达的自动标定技术
    #                 cameraPos = np.array([obj["position"] for obj in alarmCameraObj])
    #                 cameraBox = np.array([obj["xywh"] for obj in alarmCameraObj])
    #
    #                 # 对于一个视觉框，假如有雷达框可以包住其百分之八十，且雷达框高度不超过视觉的1.2倍或者宽度不超过1.1倍，则认为这个视觉框附近存在雷达目标
    #                 radarTrack = [np.array(track["track"],dtype=object)[self.gusFilter(np.array([obj["position"][1] for obj in track["track"]]), 3,True)] for track in self.radarTrack]
    #                 radarBox = np.array([obj["xywh"][camId] for track in radarTrack for obj in track ])
    #
    #                 # radarBoxX1 = radarBox[:, 0]
    #                 radarBoxY1 = radarBox[:, 1]
    #                 radarBoxW = radarBox[:, 2]
    #                 radarBoxH = radarBox[:, 3]
    #                 # radarBoxX2 = radarBoxX1 + radarBoxW
    #                 radarBoxY2 = radarBoxY1 + radarBoxH
    #                 mask=[]
    #                 for cBox in cameraBox:
    #                     x1,y1,w,h =cBox
    #                     x2,y2 = x1+w,y1+h
    #                     y1 = np.array([ y1] * len(radarBox))
    #                     y2 = np.array([ y2] * len(radarBox))
    #                     intersectionY1  = np.max([y1,radarBoxY1],axis=0)
    #                     intersectionY2  = np.min([y2,radarBoxY2],axis=0)
    #
    #                     sFlag = ((intersectionY2 - intersectionY1) > 0.9 * h)
    #                     # hFlag=(radarBoxW < 1.2*w) # 非遮挡物
    #                     wFlag=((radarBoxH-(intersectionY2 - intersectionY1)) < 0.5*h) # 非遮挡物
    #                     mask.append(np.any(sFlag & wFlag))
    #
    #                 # if len(radarTrack)>1:
    #                 #     radarBox = np.stack([np.mean([obj["xywh"][camId] for obj in track],axis=0) for track in radarTrack],axis=0)
    #                 #
    #                 # else:
    #                 #     radarBox = np.array([np.mean([obj["xywh"][camId] for obj in track],axis=0) for track in radarTrack])
    #                 #
    #                 # radarBoxX1 = radarBox[:,0]
    #                 # radarBoxY1 = radarBox[:,1]
    #                 # radarBoxW = radarBox[:,2]
    #                 # radarBoxH = radarBox[:,3]
    #                 # radarBoxX2 = radarBoxX1+radarBoxW
    #                 # radarBoxY2 = radarBoxY1+radarBoxH
    #                 #
    #                 #
    #                 #
    #                 # intersectionY1 = np.tile(radarBoxY1, (len(cameraBox), 1))
    #                 # for i in range(len(cameraBox)):
    #                 #     intersectionY1[i][intersectionY1[i] < cameraBoxY1[i]] = cameraBoxY1[i]
    #                 #
    #                 # intersectionY2 = np.tile(radarBoxY2, (len(cameraBox), 1))
    #                 # for i in range(len(cameraBox)):
    #                 #     intersectionY2[i][intersectionY2[i] > cameraBoxY2[i]] = cameraBoxY2[i]
    #                 #
    #                 # mask = np.sum(((intersectionY2 - intersectionY1) / cameraBoxH.reshape(-1,1)),axis=1) > 0.7
    #
    #                 radarRY = np.array([np.mean(self.gusFilter(np.array([obj["position"][1] for obj in track["track"]]), 3)) for track in self.radarTrack])
    #                 if np.any(cameraPos[:, 1] > 180):  # 北京200m阈值
    #                     diffY = np.min(np.abs(radarRY - np.mean(self.gusFilter(cameraPos[:, 1][cameraPos[:, 1] > 180]))))  # 与最近的雷达轨迹的距离
    #                     if diffY < 20:
    #                         isAlarm = True
    #                         return isAlarm
    #                 elif len(alarmCameraObj) >= 3:  # 一定程度过滤误识别，相当于要出现3个误报点
    #                     alarmCameraObj =    np.array(alarmCameraObj )[mask]
    #                     for pair in itertools.combinations(alarmCameraObj, 2):
    #                         rx1, ry1 = pair[0]["position"]
    #                         rx2, ry2 = pair[1]["position"]
    #                         x1, y1, w1, h1 = pair[0]["xywh"]
    #                         x2, y2, w2, h2 = pair[1]["xywh"]
    #
    #                         shiftX = np.abs(rx1 - rx2)
    #                         shiftY = np.abs(ry1 - ry2)
    #
    #                         distanceX = np.abs((x1 + 0.5 * w1) - (x2 + 0.5 * w2))
    #                         distanceY = np.abs((y1 + h1) - (y2 + h2))
    #                         w = max(w1, w2)
    #                         h = min(h1, h2)
    #                         if (w < distanceX or 1 < shiftX):
    #                             if (shiftY < 10 or distanceY < 0.1 * h) or (((shiftY < 50 or distanceY < 0.5 * h) and (len(pair[0]["virtual"]) or len(pair[1]["virtual"])))):
    #                                 # 前面是距离，适合近处视觉框飘忽不定的情况，飘动大的实际位移小
    #                                 # 后面是图像y指，适合远处小飘动，移动距离过大的情况
    #                                 # 满足报警条件，但是需要雷达也有点
    #                                 # x1, y1, w1, h1
    #                                 # x2, y2, w2, h2
    #                                 # for box in [pair[0]["xywh"],pair[1]["xywh"]]:
    #                                 #     x1, y1, w, h = box
    #                                 #     x2=x1+w
    #                                 #     y2=y1+h
    #                                 #     intersectionY1 = radarBoxY1.copy()
    #                                 #     intersectionY2 = radarBoxY2.copy()
    #                                 #     intersectionY1[intersectionY1<y1] = y1
    #                                 #     intersectionY2[intersectionY2>y2] = y2
    #                                 #     a=(intersectionY2-intersectionY1)/h
    #                                 #     print(np.max(a),np.min(a),"sadasdas")
    #                                 #     mask0 = ((a)>0.8) & ( (radarBoxW<1.1*w) | (radarBoxH<1.2*h))
    #                                 #     if np.any(mask0):  # 与最近的雷达轨迹的距离
    #                                 isAlarm=True
    #                                 return isAlarm
    #
    #
    #             # cameraPos = np.array([list(obj["position"])+list(obj["xywh"]) for obj in alarmCameraObj])
    #             #
    #             #
    #             #
    #             # radarRY = np.array([np.mean(self.gusFilter(np.array([obj["position"][1] for obj in track["track"]]),3)) for track in self.radarTrack])
    #             #
    #             # radarBoxHeadY = np.array([np.mean(self.gusFilter(np.array([obj["xywh"][1] for obj in track["track"]]),3)) for track in self.radarTrack])
    #             # radarBoxFootY = np.array([np.mean(self.gusFilter(np.array([obj["xywh"][1]+obj["xywh"][3] for obj in track["track"]]),3)) for track in self.radarTrack])
    #             # if np.any(cameraPos[:,1] > 180):  # 北京200m阈值
    #             #     diffY = np.min(np.abs(radarRY - np.mean(self.gusFilter(cameraPos[:,1][cameraPos[:,1]>180]))))  # 与最近的雷达轨迹的距离
    #             #     if diffY <20:
    #             #         isAlarm = True
    #             # elif len(alarmCameraObj) >= 3:  # 一定程度过滤误识别，相当于要出现3个误报点
    #             #
    #             #
    #             #
    #             #
    #             #
    #             #
    #             #
    #             #
    #             #
    #             #     for pair in itertools.combinations(alarmCameraObj, 2):
    #             #         rx1, ry1 = pair[0]["position"]
    #             #         rx2, ry2 = pair[1]["position"]
    #             #         x1, y1, w1, h1 = pair[0]["xywh"]
    #             #         x2, y2, w2, h2 = pair[1]["xywh"]
    #             #
    #             #         shiftX = np.abs(rx1 - rx2)
    #             #         shiftY = np.abs(ry1 - ry2)
    #             #
    #             #         distanceX = np.abs((x1+0.5*w1 )- (x2+0.5*w2))
    #             #         distanceY = np.abs((y1+h1) - (y2+h2))
    #             #         w = max(w1, w2)
    #             #         h = min(h1, h2)
    #             #         if (w < distanceX or  1<shiftX ):
    #             #             if (shiftY < 10 or distanceY < 0.1*h) : # 这是小飘动，距离还是比较准的
    #             #                 # 前面是距离，适合近处视觉框飘忽不定的情况，飘动大的实际位移小
    #             #                 # 后面是图像y指，适合远处小飘动，移动距离过大的情况
    #             #                 # 满足报警条件，但是需要雷达也有点
    #             #                 if  np.min(np.abs(radarRY - (ry1 + ry2) * 0.5))< 10: # 与最近的雷达轨迹的距离
    #             #                     isAlarm = True
    #             #                     break
    #             #             elif (shiftY < 50 or distanceY < 0.5*h) and (len(pair[0]["virtual"]) or len(pair[1]["virtual"])): # 由于进入不同区域导致的大飘动，0.5代表台阶不超过0.5的人
    #             #
    #             #                 y = [ry1,ry2]
    #             #                 if len(pair[0]["virtual"]):
    #             #                     vrx, vry = pair[0]["virtual"]
    #             #                     y.append(vry)
    #             #                 if len(pair[1]["virtual"]):
    #             #                     vrx, vry = pair[1]["virtual"]
    #             #                     y.append(vry)
    #             #                 y = np.array(y).reshape(-1,1)
    #             #                 if np.min(np.abs(radarRY -y))< 10: # 与最近的雷达轨迹的距离
    #             #                     isAlarm = True
    #             #                     break
    #             #             else:  #单纯大飘动
    #             #                 pass
    #             else:
    # xywh = np.array([obj["xywh"] for obj in alarmCameraObj])
    # for pair in itertools.combinations(xywh, 2):
    #     x1, y1, w1, h1 = pair[0]
    #     x2, y2, w2, h2 = pair[1]
    #     distanceX = np.abs((x1 + 0.5 * w1) - (x2 + 0.5 * w2))
    #     w = max(w1, w2)
    #     if w < distanceX:  # 认为有横穿轨迹，不管噪声，只是初步筛选
    #         isAlarm = True
    #         break
    #                 # 该部分是不希望有映射距离的，即没有标定时（例如希望在高低不平的地方能用）
    #                 if len(alarmCameraObj) >= 3:  # 一定程度过滤误识别，相当于要出现3个误报点
    #                     xywh = np.array([obj["xywh"] for obj in alarmCameraObj])
    #                     for pair in itertools.combinations(xywh, 2):
    #                         x1, y1, w1, h1 = pair[0]
    #                         x2, y2, w2, h2 = pair[1]
    #                         distanceX = np.abs(x1 - x2)
    #                         distanceY = np.abs(y1 - y2)
    #                         w = max(w1, w2)
    #                         h = max(h1, h2)
    #                         if distanceY < 0.5*h and w < distanceX:
    #                             isAlarm = True
    #                             break
    #     return isAlarm

    def intersectionArea(self,box1, box2):
        # 确定交集矩形的边界
        box2 = np.array(box2)
        box2X1 = box2[:, 0]
        box2Y1 = box2[:, 1]
        box2X2 = box2X1 + box2[:, 2]
        box2Y2 = box2Y1 + box2[:, 3]

        box2X1[box2X1 < box1[0]] = box1[0]
        box2Y1[box2Y1 < box1[1]] = box1[1]

        box2X2[box2X2 > (box1[0] + box1[2])] = box1[0] + box1[2]
        box2Y2[box2Y2 > (box1[1] + box1[3])] = box1[1] + box1[3]

        height = box2Y2 - box2Y1
        width = box2X2 - box2X1

        s = height * width
        s[((height <= 0) | (width <= 0))] = 0


        return not  np.any((s / (box1[2]* box1[3]))>0.5)

    def moveMaskReferByCamera(self):
        # 视觉报警侧重于框中人

        isAlarm = False
        if (self.cameraDiffEnable and self.diffUse):
            # 视觉+帧差
            for obj in self.cameraObj:
                x, y, w, h = obj["xywh"]
                if obj["camId"] == 0:
                    if self.calibrateEnable and (obj["position"][1] > 60 or obj["position"][1] <10):
                        # 近焦大于60m框就太小了，容易框到帧差噪声点，小于10m框高度太小；虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
                        obj["alarm"] = 0
                        continue
                    elif not self.calibrateEnable and w*h < 30: # 框太小容易框到帧差噪声点
                        obj["alarm"] = 0
                        continue
                else:
                    if self.calibrateEnable and (obj["position"][1] > 250 or obj["position"][1] <50):
                        # 远焦大于250m框就太小了，容易框到帧差噪声点；小于50m框高度太小，虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
                        obj["alarm"] = 0
                        continue
                    elif not self.calibrateEnable and w * h < 30: # 框太小容易框到帧差噪声点
                        obj["alarm"] = 0
                        continue
                    else:
                        y=y+450
                x1, y1, x2, y2 = x, y, x + w, y +h # 视觉框看全部
                ratio=np.mean(self.moveMask[y1:y2, x1:x2])
                if ratio > 0.3:
                    obj["alarm"] = 1
                else:
                    obj["alarm"] = 0
            alarmCameraObj0 =  [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 0]
            alarmCameraObj1 =  [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 1]
            for camId, alarmCameraObj in enumerate([alarmCameraObj0, alarmCameraObj1]):
                if len(alarmCameraObj)>=3:
                    moveNum = []
                    for obj in alarmCameraObj:
                        x, y, w, h = obj["xywh"]
                        if obj["camId"] == 1:
                            y = y + 450
                        x1, y1, x2, y2 = x, y, x + w, y + h  # 视觉框看全部
                        data = self.moveMaskSet[y1:y2, x1:x2]
                        data = data[data != 0]
                        if len(data):
                            uniqueV, counts = np.unique(data, return_counts=True)
                            moveNum.append(uniqueV[np.argmax(counts)])
                    # maxNum = len(set(moveNum))

                    q0 = []
                    for i in np.unique(moveNum):
                        q0.append(np.array([int(bit) for bit in bin(int(i / 255))[2:].zfill(8)]))
                    colSum = np.sum(q0, axis=0)
                    maxNum = np.sum(colSum == 1)

                    xypLog.xypDebug("isAlarm camera0", maxNum, moveNum,)
                    if maxNum >=4 and len(q0)>=4:
                        isAlarm = True
                        break
        if not isAlarm:
            # 纯视觉, 判断独立的视觉框个数，漏报风险小，误报风险在于每帧出现位置不同的误报点，也很小
            cameraObj0 = [obj for obj in self.cameraObj if obj["camId"] == 0]
            cameraObj1 = [obj for obj in self.cameraObj if obj["camId"] == 1]
            for camId, cameraObj in enumerate([cameraObj0, cameraObj1]):
                if len(cameraObj):
                    cameraObj[0]["alarm"] = 1
                    isolate = [cameraObj[0]["xywh"]]
                    timeList = [cameraObj[0]["timeStamp"]]
                    for obj in cameraObj[1:]:

                        box1 = obj["xywh"]
                        box2 = np.array(isolate)
                        box2X1 = box2[:, 0]
                        box2X2 = box2X1 + box2[:, 2]
                        box2X1[box2X1 < box1[0]] = box1[0]
                        box2X2[box2X2 > (box1[0] + box1[2])] = box1[0] + box1[2]
                        width = box2X2 - box2X1
                        if not np.any((width / (box1[2])) > 0.5):
                            obj["alarm"] = 1
                            isolate.append(box1)
                            timeList.append(obj["timeStamp"])
                        else:
                            obj["alarm"] = 0
                    num = len(set(timeList))
                    xypLog.xypDebug("isAlarm camera1", num,)
                    if num >= 6:# 横穿至少3个身位
                        isAlarm = True
                        break
        return isAlarm

    # def moveMaskReferByRadar(self,):
    #     # 目标报警数据，雷达+帧差横穿报警
    #     isAlarm = False
    #     if self.cameraDiffEnable: # 启用帧差
    #         if not self.diffUse:  # 帧差启用但帧差不可用（如光影疯狂干扰）时
    #             return isAlarm
    #         for track in self.radarTrack:
    #             moveNum0 = []
    #             moveNum1 = []
    #             for obj in track["virtual"]:
    #                 obj["alarm"] = 0
    #                 if  (obj["position"][1] > 60 or obj["position"][1] < 10):
    #                     # 近焦大于60m框就太小了，容易框到帧差噪声点，小于10m框高度太小；虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
    #                     pass
    #                 else:
    #                     x, y, w, h = obj["xywh"][0]
    #                     x1, y1, x2, y2 = x, int(y + 0.2 * h), x + w, int(y + 0.8 * h)  # 雷达虚警框容易框到帧差边角很多噪声，主要看中间部分
    #                     if x1==x2 or y1==y2:
    #                         pass
    #                     else:
    #                         ratio0 = np.mean(self.moveMask[y1:y2, x1:x2])
    #                         if ratio0 >0.3:
    #                             obj["alarm"] = 1
    #                             data = self.moveMaskSet[y1:y2, x1:x2]
    #                             data = data[data != 0]
    #                             if len(data):
    #                                 uniqueV, counts = np.unique(data, return_counts=True)
    #                                 moveNum0.append(uniqueV[np.argmax(counts)])
    #
    #                 if (obj["position"][1] > 250 or obj["position"][1] < 50):
    #                     # 远焦大于250m框就太小了，容易框到帧差噪声点；小于50m框高度太小，虽然宽度够了，但近处帧差噪声点往往也挺大，容易受干扰
    #                     pass
    #                 else:
    #                     x,y,w,h = obj["xywh"][1]
    #                     y = y + 450
    #
    #                     if obj["position"][1]>180:#北京200
    #                         t = 0.2
    #                         x1, y1, x2, y2 = x, y, x + w, int(y +  h)
    #                     else:
    #                         t = 0.3
    #                         x1, y1, x2, y2 = x, int(y+0.2*h) , x + w, int(y + 0.8*h) # 很多噪声，现在看中间部分
    #                     if x1 == x2 or y1 == y2:
    #                         pass
    #                     else:
    #                         ratio1 = np.mean(self.moveMask[y1:y2, x1:x2])
    #                         if ratio1 > t:
    #                             obj["alarm"] = 1
    #                             data = self.moveMaskSet[y1:y2, x1:x2]
    #                             data = data[data != 0]
    #                             if len(data):
    #                                 uniqueV, counts = np.unique(data, return_counts=True)
    #                                 moveNum1.append(uniqueV[np.argmax(counts)])
    #
    #             q0 = []
    #             for i in np.unique(moveNum0):
    #                 q0.append(np.array([int(bit) for bit in bin(int(i / 255))[2:].zfill(8)]))
    #             colSum = np.sum(q0, axis=0)
    #             num0 = np.sum(colSum == 1)
    #
    #             q1 = []
    #             for i in np.unique(moveNum1):
    #                 q1.append(np.array([int(bit) for bit in bin(int(i / 255))[2:].zfill(8)]))
    #             colSum = np.sum(q1, axis=0)
    #             num1 = np.sum(colSum == 1)
    #
    #
    #
    #             posY = np.array([obj["position"][1] for obj in track["virtual"]])
    #             flag  = np.any(posY>180)
    #
    #             xypLog.xypDebug("isAlarm radar",num0, num1,track["objId"],moveNum0,moveNum1,flag)
    #             if ((num0 >= 4 and len(q0) >= 4) or (num0 ==3 and len(q0) ==3)) or ((num1 >= 4 and len(q1) >= 4)or (num1 ==3 and len(q1) ==3)):
    #                 isAlarm = True
    #                 if ((num0 >= 4 and len(q0) >= 4) or (num0 ==3 and len(q0) ==3)):
    #                     track["alarm"] = num0
    #                 else:
    #                     track["alarm"] = num1
    #             else:
    #                 track["alarm"] = 0
    #
    #
    #     xypLog.xypDebug("radarDiffAlarmFlag",self.radarDiffAlarmFlag)
    #     return isAlarm
    def moveMaskReferByRadar(self,):
        # 目标报警数据，雷达+帧差横穿报警
        isAlarm = False
        if self.cameraDiffEnable: # 启用帧差
            if not self.diffUse:  # 帧差启用但帧差不可用（如光影疯狂干扰）时
                return isAlarm


            for track in self.radarTrack:
                moveNum0 = []
                moveNum1 = []
                mask = np.zeros_like(self.moveMask)


                for obj in track["virtual"]:
                    w1,h1 = obj["xywh"][0][2],obj["xywh"][0][3]
                    w2,h2 = obj["xywh"][1][2],obj["xywh"][1][3]
                    x, y, w, h = obj["xywh"][0]
                    x1, y1, x2, y2 = x, int(y + 0.2 * h), x + w, int(y + 0.8 * h)  # 雷达虚警框容易框到帧差边角很多噪声，主要看中间部分
                    mask[y1:y2, x1:x2] = 1
                    x, y, w, h = obj["xywh"][1]
                    y = y + 450
                    x1, y1, x2, y2 = x, int(y + 0.2 * h), x + w, int(y + 0.8 * h)  # 雷达虚警框容易框到帧差边角很多噪声，主要看中间部分
                    mask[y1:y2, x1:x2] = 1
                    obj["alarm"] = 1


                moveMaskSet=self.moveMaskSet.copy()
                moveMaskSet[mask==0]=0
                data0 = moveMaskSet[:len(moveMaskSet)//2]
                data1 = moveMaskSet[len(moveMaskSet) // 2:]

                for col in data0.T:
                    col = col[col != 0]
                    if len(col)/h1>0.2:
                        uniqueV, counts = np.unique(col, return_counts=True)
                        moveNum0.append(uniqueV[np.argmax(counts)])
                for col in data1.T:
                    col = col[col != 0]
                    if len(col) / h2 > 0.2:
                        uniqueV, counts = np.unique(col, return_counts=True)
                        moveNum1.append(uniqueV[np.argmax(counts)])

                q0 = []

                uniqueV0, counts0 = np.unique(moveNum0, return_counts=True)
                # data0 = np.array(counts0)
                # dataAvg0 = np.mean(data0)
                # dataStd0 = np.std(data0)
                # mask0 = (np.abs(data0 - dataAvg0) <= 1 * dataStd0)  # <=保证了mask至少不全为false
                uniqueV0 = uniqueV0[counts0>0.1*w1]


                for i in uniqueV0:
                    q0.append(np.array([int(bit) for bit in bin(int(i / 255))[2:].zfill(8)]))
                if len(q0):
                    colSum = np.sum(q0, axis=1)
                    num0 = np.sum(colSum == 1)
                else:
                    num0=0
                q1 = []
                uniqueV1, counts1 = np.unique(moveNum1, return_counts=True)
                # data1 = np.array(counts1)
                # dataAvg1= np.mean(data1)
                # dataStd1= np.std(data1)
                # mask1 = (np.abs(data1 - dataAvg1) <= 1 * dataStd1)  # <=保证了mask至少不全为false
                uniqueV1 = uniqueV1[counts1 > 0.1 * w2]
                for i in uniqueV1:
                    q1.append(np.array([int(bit) for bit in bin(int(i / 255))[2:].zfill(8)]))
                if len(q1):
                    colSum = np.sum(q1, axis=1)
                    num1 = np.sum(colSum == 1)

                else:
                    num1 = 0
                xypLog.xypDebug("isAlarm radar",num0, num1,track["objId"],moveNum0,moveNum1)

                if (num0 >= 5 or num1 >= 5) :
                    track["alarm"] = max(num0,num1)
                    isAlarm=True

                else:
                    track["alarm"] = 0




                # posY = np.array([obj["position"][1] for obj in track["virtual"]])
                # flag  = np.any(posY>180)
                #
                # xypLog.xypDebug("isAlarm radar",num0, num1,track["objId"],moveNum0,moveNum1,flag)
                # if ((num0 >= 4 and len(q0) >= 4) or (num0 ==3 and len(q0) ==3)) or ((num1 >= 4 and len(q1) >= 4)or (num1 ==3 and len(q1) ==3)):
                #     isAlarm = True
                #     if ((num0 >= 4 and len(q0) >= 4) or (num0 ==3 and len(q0) ==3)):
                #         track["alarm"] = num0
                #     else:
                #         track["alarm"] = num1
                # else:
                #     track["alarm"] = 0


        xypLog.xypDebug("radarDiffAlarmFlag",self.radarDiffAlarmFlag)
        return isAlarm

    def moveMaskReferBySingleRadar(self):
        isAlarm = False
        for track in self.radarTrack:
            priority = 0
            existTime = track["track"][-1]["timeStamp"] - track["createTime"]
            if existTime >= 4 and len(track["track"]) >= 2:  # 大于5s才有统计意义
                objX = np.array([[obj["position"][0], obj["timeStamp"]] for obj in track["track"]])
                objY = np.array([[obj["position"][1], obj["timeStamp"]] for obj in track["track"]])
                objX = objX[np.argsort(objX[:, 0])]
                objY = objY[np.argsort(objY[:, 0])]

                sortPosX = objX[:, 0]
                sortPosY = objY[:, 0]
                
                sortTimeX = objX[:, 1]
                sortTimeY = objY[:, 1]
             

                startTime = track["track"][0]["timeStamp"]

                maxX = np.max(sortPosX)
                minX = np.min(sortPosX)
                maxY = np.max(sortPosY)
                minY = np.min(sortPosY)
                meanX = np.mean(sortPosX)
                meanY = np.mean(sortPosY)
                xypLog.xypDebug("single isAlarm0", track)
                xypLog.xypDebug("single isAlarm1", maxX, minX, maxY, minY, meanX, meanY)

                maxYtime = max(sortTimeY)
                while 1:
                    maskY = (startTime <= sortTimeY) & (sortTimeY <= (startTime + 10))
                    Y = sortPosY[maskY]
                    if len(Y) < 2:
                        startTime = startTime + 1
                        if startTime > maxYtime:
                            break
                        else:
                            continue
                    disY = Y[1:] - Y[:-1]
                    disY[disY > 1] = 0  # 抓住正常位移的一段

                    maskX = (startTime <= sortTimeX) & (sortTimeX <= (startTime + 10))
                    X = sortPosX[maskX]
                    disX = X[1:] - X[:-1]
                    disX[disX > 1] = 0  # 抓住正常位移的一段

                    disYV = np.sum(disY)
                    disXV = np.sum(disX)
                    tY = sortTimeY[maskY]
                    spendTime = max(tY)-min(tY)

                    v=(max(disYV/spendTime , disXV/spendTime) < 1.5) # 来一点吧

                    xypLog.xypDebug("single isAlarm2", track["objId"], np.sum(disX), np.sum(disY), disX, disY,v)
                    if np.sum(disY) > 6 and existTime > 6 and np.sum(disX) <3 and v:
                        priority = 1
                    if not priority:  # and not self.useCamera# 雾天启用(天气识别会很低，只识别雾天)
                        if (143 <= meanY <= 155):
                            if np.sum(disX) > 6 and existTime > 6 and np.sum(disY) <3 and v:
                                priority = 2
                        elif (197 <= meanY <= 205):
                            if np.sum(disX) > 2.7 and existTime > 6 and np.sum(disY) <3 and v:
                                priority = 2
                        elif (47 <= meanY <= 53):
                            if np.sum(disX) > 3 and existTime > 6 and np.sum(disY) <3 and v:
                                priority = 2

                    startTime = startTime + 1
                    if priority:
                        break

                if not priority:  # 雨天模式
                    vipPosAny = (np.sum((45 <= sortPosY) & (sortPosY <= 55)) + np.sum((95 <= sortPosY) & (sortPosY <= 105)) + np.sum(
                        (143 <= sortPosY) & (sortPosY <= 155)) + np.sum((197 <= sortPosY) & (sortPosY <= 205)))  # 存在特殊点
                    xypLog.xypDebug("single isAlarm4", vipPosAny)
                    if np.linalg.norm([maxX - minX,maxY-minY]) > 1 and track["objId"] in [200, 150] and vipPosAny > 3:  # 特殊目标有点在特殊位置
                        # 197是出现了195.8的，且有3个点的误报
                        priority = 3

                if priority:
                    isAlarm = True
                    var = np.var(sortPosX[1:] - sortPosX[:-1])
                    track["score"] = var
                track["alarm"] = priority

            else:
                track["alarm"] = priority

        # if isAlarm and (not self.useCamera):
        #     self.radarDataHandle.clearObjTrack()

        xypLog.xypDebug("var", [(track["alarm"], track["objId"], track["score"]) for track in self.radarTrack if
                                track["alarm"]])
        return isAlarm
    # def moveMaskReferBySingleRadar(self):
    #     isAlarm=False
    #     for track in self.radarTrack:
    #         priority = 0
    #         existTime = track["track"][-1]["timeStamp"] - track["createTime"]
    #         if existTime >= 5 and len(track["track"])>=2:  # 大于5s才有统计意义
    #             posX = np.array([[obj["position"][0],obj["timeStamp"]] for obj in track["track"] ])
    #             posY = np.array([[obj["position"][1],obj["timeStamp"]] for obj in track["track"] ])
    #             sortPosY = posX[np.argsort(posX[:, 0])]
    #             sortPosX = posY[np.argsort(posY[:, 0])]
    #
    #             sortY = sortPosY[:,0]
    #             sortX = sortPosX[:,0]
    #             sortTimeY = sortPosY[:, 1]
    #             sortTimeX = sortPosX[:, 1]
    #
    #             posX= posX[:,0]
    #             posY= posY[:,0]
    #             startTime=track["track"][0]["timeStamp"]
    #
    #             maxX = np.max(posX)
    #             minX = np.min(posX)
    #             maxY = np.max(posY)
    #             minY = np.min(posY)
    #             meanX = np.mean(posX)
    #             meanY = np.mean(posY)
    #             xypLog.xypDebug("single isAlarm0", track["objId"], posX, posY)
    #             xypLog.xypDebug("single isAlarm1", maxX, minX, maxY, minY, meanX, meanY)
    #
    #
    #             maxYtime = max(sortTimeY)
    #             maxXtime = max(sortTimeX)
    #
    #             while 1:
    #
    #                 mask=(startTime<=sortTimeY)&(sortTimeY<=(startTime+6))
    #                 sortY_ = sortY[mask]
    #                 if (len(sortY_) < 2 and startTime <= maxXtime) or (startTime > maxYtime):
    #                     break
    #
    #                 disY = sortY_[1:] - sortY_[:-1]
    #                 disY[disY > 1] = 0  # 抓住正常位移的一段
    #                 mask = (startTime <= sortTimeX) & (sortTimeX<= (startTime + 6))
    #                 sortX_ =sortX[mask]
    #                 disX = sortX_[1:] - sortX_[:-1]
    #                 disX[disX > 1] = 0  # 抓住正常位移的一段
    #
    #                 xypLog.xypDebug("single isAlarm2", track["objId"],np.sum(disX),np.sum(disY), disX, disY)
    #                 if np.sum(disY) > 6 and existTime > 6:
    #                     priority = 1
    #                 if not priority: # and not self.useCamera# 雾天启用(天气识别会很低，只识别雾天)
    #                     if (145 <= meanY <= 155):
    #                         if np.sum(disX) > 6 and existTime > 6:
    #                             priority = 2
    #                     elif (195 <= meanY <= 205):
    #                         if np.sum(disX) > 2.7 and existTime > 6:
    #                             priority = 2
    #                     elif (45 <= meanY <= 55):
    #                         if np.sum(disX) > 3 and existTime > 6:
    #                             priority = 2
    #                 startTime = startTime + 1
    #                 if priority:
    #                     break
    #
    #             if not priority:  # 雨天模式
    #                 vipPosAny = (np.sum((45 <= posY) & (posY <= 55)) + np.sum((95 <= posY) & (posY <= 105)) + np.sum((145 <= posY) & (posY <= 155)) + np.sum((197 <= posY) & (posY <= 205)))  # 存在特殊点
    #                 xypLog.xypDebug("single isAlarm4", vipPosAny)
    #                 if np.linalg.norm([np.max(posX) - np.min(posX), np.max(posY) - np.min(posY)]) > 1 and track["objId"] in [200, 150] and vipPosAny > 3:  # 特殊目标有点在特殊位置
    #                     # 197是出现了195.8的，且有3个点的误报
    #                     priority = 3
    #             # if len(posX)>1:
    #             #     if meanY > 195:  # 北京200m阈值
    #             #         t = 1
    #             #     else:
    #             #         t = 2
    #             #     xypLog.xypDebug("single isAlarm2", np.linalg.norm([np.max(posX) - np.min(posX), np.max(posY) - np.min(posY)]) ,t)
    #             #     if np.linalg.norm([np.max(posX) - np.min(posX), np.max(posY) - np.min(posY)]) > t: # 非固定点
    #                     # if len(np.unique(posX)) == 1:
    #                     #     lineLenth = maxY - minY
    #                     #     k = np.inf
    #                     #     distance = 0
    #                     # else:
    #                     #     k, b = np.polyfit(posX, posY, 1)
    #                     #     lineLenth = np.linalg.norm([maxX - minX, (maxX * k + b) - ( minX * k + b)])
    #                     #     distance = np.mean(np.abs(k * posX - posY + b) / np.sqrt(k ** 2 + 1))
    #                     #
    #                     # print(distance,lineLenth,k,"sdddddddddddddddddddddd")
    #                     # if distance < 1.5 and lineLenth > 4 and (k >=1.73 or k <= -1.73):# 1=tan(pi/180*60) -1=tan(pi/180*60)
    #                     #     priority = 1
    #                     # sortY =np.sort(posY)
    #                     # disY = sortY[1:]-sortY[:-1]
    #                     # disY[disY>1]=0  # 抓住正常位移的一段
    #                     # if np.sum(disY) > 6  and existTime>6:
    #                     #     if self.useCamera:  # 10s数据 约80个点
    #                     #         # 出现多次白天纵穿误报，正常天气还是需要视觉框
    #                     #         xypLog.xypDebug("single isAlarm-3", np.mean(np.abs(posX - meanX)))
    #                     #         pass
    #                     #         priority = 1
    #                     #     else:
    #                     #         xypLog.xypDebug("single isAlarm3", np.mean(np.abs(posX - meanX)))
    #                     #         priority = 1
    #                     #
    #                     # if not priority:
    #                     #     # vipPosMean = (45 <= meanY <= 55) | (95 <= meanY <= 105) | (145 <= meanY <= 155) | (
    #                     #     #             195 <= meanY <= 205)  # 特殊点位
    #                     #     sortX = np.sort(posX)
    #                     #     disX = sortX[1:] - sortX[:-1]
    #                     #     disX[disX > 1] = 0  # 抓住正常位移的一段
    #                     #
    #                     #     if (145 <= meanY <= 155):
    #                     #         if np.sum(disX) > 3 and existTime > 6:
    #                     #             priority = 2
    #                     #     elif (195 <= meanY <= 205):
    #                     #         if np.sum(disX) > 3 and existTime > 6:
    #                     #             priority = 2
    #                     #     else:
    #                     #         if np.sum(disX) > 6 and existTime > 6:
    #                     #             priority = 2
    #                     # if not self.useCamera: # 10s数据 约80个点
    #                     #     # 关注横穿
    #                     #     xypLog.xypDebug("single isAlarm4",  maxX - meanX , meanX - minX ,t)
    #                     #     if maxX - meanX > t and meanX - minX > 1:#id 150 meanX - minX 1.2
    #                     #         if not priority:
    #                     #             # 各种特征
    #                     #             vipPosMean = (45<=meanY<=55) | (95<=meanY<=105) | (145<=meanY<=155) | (195<=meanY<=205) # 特殊点位
    #                     #             objCreateVelMean = len(track["track"]) / existTime #平均每秒点数
    #                     #             objNum = len(track["track"]) # 点数
    #                     #             vipObj = track["objId"] in [200,150]   # 特殊目标
    #                     #             vipPosAny= (np.sum((45<=posY)&(posY<=55))+ np.sum((95<=posY)&(posY<=105)) + np.sum((145<=posY)&(posY<=155)) + np.sum((197<=posY)&(posY<=205))) # 存在特殊点
    #                     #             var = np.var( posX[1:] - posX[:-1])
    #                     #
    #                     #             noAlarm = (159<=meanY<=161) | (176<=meanY<=178)
    #                     #             xypLog.xypDebug("single isAlarm5", vipPosMean,objCreateVelMean,objNum,vipObj,vipPosAny,var,existTime)
    #                     #             # 出点稳定的情况，即百分百准的情况，可漏不可误
    #                     #             if not vipPosMean and objCreateVelMean>5 and objNum>40 and meanY<205 and existTime >10 and not noAlarm : # 非特殊位置稳定出点
    #                     #                 # note:meanY<205 20240605 出现多次>205虚警
    #                     #                 # 稳定出点的很多虚警点容易6-8s达到误报条件，10s可以让真实点基本出现了
    #                     #                 priority = 2
    #                     #             if vipPosMean and objCreateVelMean > 4 and objNum > 32 and existTime >10  and not noAlarm : # 特殊位置稳定出点
    #                     #                 priority = 2
    #                     #
    #                     #             # 不稳定出点
    #                     #             if vipObj and vipPosAny > 3: # 特殊目标有点在特殊位置
    #                     #                 # 197是出现了195.8的，且有3个点的误报
    #                     #                 priority = 3
    #                     #
    #                     #
    #                     #
    #                     #             # if not priority:
    #                     #             # elif not flag1 and flag2 and flag4:
    #                     #             #     priority = 3
    #                     #             # elif flag3 and vipObj and flag6:
    #                     #             #     priority=3
    #             if priority:
    #                 isAlarm = True
    #                 var = np.var( posX[1:] - posX[:-1])
    #                 track["score"] = var
    #             track["alarm"] = priority
    #
    #         else:
    #             track["alarm"] = priority
    #
    #     # if isAlarm and (not self.useCamera):
    #     #     self.radarDataHandle.clearObjTrack()
    #
    #     xypLog.xypDebug("var", [(track["alarm"] ,track["objId"],track["score"]) for track in self.radarTrack if  track["alarm"]])
    #     return isAlarm

    # def moveMaskReferBySingleRadar(self):
    #     isAlarm=False
    #     for track in self.radarTrack:
    #         priority = 0
    #
    #         existTime = track["track"][-1]["timeStamp"] - track["createTime"]
    #         if existTime >= 5:  # 大于5s才有统计意义
    #             posX = np.array([obj["position"][0] for obj in track["track"]])
    #             posY = np.array([obj["position"][1] for obj in track["track"]])
    #             mask = self.gusFilter(posX,3,True) & self.gusFilter(posY,3,True)
    #             posX = posX[mask]
    #             posY = posY[mask]
    #             xypLog.xypDebug("single isAlarm0",track["objId"],posX,posY)
    #             if len(posX)>1:
    #                 maxX  = np.max(posX)
    #                 minX  = np.min(posX)
    #                 maxY  = np.max(posY)
    #                 minY  = np.min(posY)
    #                 meanX = np.mean(posX)
    #                 meanY = np.mean(posY)
    #
    #                 xypLog.xypDebug("single isAlarm1", maxX, minX, maxY, minY, meanX, meanY)
    #                 if meanY > 195:  # 北京200m阈值
    #                     t = 1
    #                 else:
    #                     t = 2
    #                 xypLog.xypDebug("single isAlarm2", np.linalg.norm([np.max(posX) - np.min(posX), np.max(posY) - np.min(posY)]) ,t)
    #                 if np.linalg.norm([np.max(posX) - np.min(posX), np.max(posY) - np.min(posY)]) > t: # 非固定点
    #                     # if len(np.unique(posX)) == 1:
    #                     #     lineLenth = maxY - minY
    #                     #     k = np.inf
    #                     #     distance = 0
    #                     # else:
    #                     #     k, b = np.polyfit(posX, posY, 1)
    #                     #     lineLenth = np.linalg.norm([maxX - minX, (maxX * k + b) - ( minX * k + b)])
    #                     #     distance = np.mean(np.abs(k * posX - posY + b) / np.sqrt(k ** 2 + 1))
    #                     #
    #                     # print(distance,lineLenth,k,"sdddddddddddddddddddddd")
    #                     # if distance < 1.5 and lineLenth > 4 and (k >=1.73 or k <= -1.73):# 1=tan(pi/180*60) -1=tan(pi/180*60)
    #                     #     priority = 1
    #                     sortY =np.sort(posY)
    #                     disY = sortY[1:]-sortY[:-1]
    #                     disY[disY>1]=0  # 抓住正常位移的一段
    #                     if np.sum(disY) > 6  and existTime>6:
    #                         if self.useCamera:  # 10s数据 约80个点
    #                             # 出现多次白天纵穿误报，正常天气还是需要视觉框
    #                             xypLog.xypDebug("single isAlarm-3", np.mean(np.abs(posX - meanX)))
    #                             pass
    #                             priority = 1
    #                         else:
    #                             xypLog.xypDebug("single isAlarm3", np.mean(np.abs(posX - meanX)))
    #                             priority = 1
    #
    #                     if not priority:
    #                         # vipPosMean = (45 <= meanY <= 55) | (95 <= meanY <= 105) | (145 <= meanY <= 155) | (
    #                         #             195 <= meanY <= 205)  # 特殊点位
    #                         sortX = np.sort(posX)
    #                         disX = sortX[1:] - sortX[:-1]
    #                         disX[disX > 1] = 0  # 抓住正常位移的一段
    #
    #                         if (145 <= meanY <= 155):
    #                             if np.sum(disX) > 3 and existTime > 6:
    #                                 priority = 2
    #                         elif (195 <= meanY <= 205):
    #                             if np.sum(disX) > 3 and existTime > 6:
    #                                 priority = 2
    #                         else:
    #                             if np.sum(disX) > 6 and existTime > 6:
    #                                 priority = 2
    #                     # if not self.useCamera: # 10s数据 约80个点
    #                     #     # 关注横穿
    #                     #     xypLog.xypDebug("single isAlarm4",  maxX - meanX , meanX - minX ,t)
    #                     #     if maxX - meanX > t and meanX - minX > 1:#id 150 meanX - minX 1.2
    #                     #         if not priority:
    #                     #             # 各种特征
    #                     #             vipPosMean = (45<=meanY<=55) | (95<=meanY<=105) | (145<=meanY<=155) | (195<=meanY<=205) # 特殊点位
    #                     #             objCreateVelMean = len(track["track"]) / existTime #平均每秒点数
    #                     #             objNum = len(track["track"]) # 点数
    #                     #             vipObj = track["objId"] in [200,150]   # 特殊目标
    #                     #             vipPosAny= (np.sum((45<=posY)&(posY<=55))+ np.sum((95<=posY)&(posY<=105)) + np.sum((145<=posY)&(posY<=155)) + np.sum((197<=posY)&(posY<=205))) # 存在特殊点
    #                     #             var = np.var( posX[1:] - posX[:-1])
    #                     #
    #                     #             noAlarm = (159<=meanY<=161) | (176<=meanY<=178)
    #                     #             xypLog.xypDebug("single isAlarm5", vipPosMean,objCreateVelMean,objNum,vipObj,vipPosAny,var,existTime)
    #                     #             # 出点稳定的情况，即百分百准的情况，可漏不可误
    #                     #             if not vipPosMean and objCreateVelMean>5 and objNum>40 and meanY<205 and existTime >10 and not noAlarm : # 非特殊位置稳定出点
    #                     #                 # note:meanY<205 20240605 出现多次>205虚警
    #                     #                 # 稳定出点的很多虚警点容易6-8s达到误报条件，10s可以让真实点基本出现了
    #                     #                 priority = 2
    #                     #             if vipPosMean and objCreateVelMean > 4 and objNum > 32 and existTime >10  and not noAlarm : # 特殊位置稳定出点
    #                     #                 priority = 2
    #                     #
    #                     #             # 不稳定出点
    #                     #             if vipObj and vipPosAny > 3: # 特殊目标有点在特殊位置
    #                     #                 # 197是出现了195.8的，且有3个点的误报
    #                     #                 priority = 3
    #                     #
    #                     #
    #                     #
    #                     #             # if not priority:
    #                     #             # elif not flag1 and flag2 and flag4:
    #                     #             #     priority = 3
    #                     #             # elif flag3 and vipObj and flag6:
    #                     #             #     priority=3
    #                     if priority:
    #                         isAlarm = True
    #                         var = np.var( posX[1:] - posX[:-1])
    #                         track["score"] = var
    #                     track["alarm"] = priority
    #                 else:
    #                     track["alarm"] = priority
    #             else:
    #                 track["alarm"] = priority
    #         else:
    #             track["alarm"] = priority
    #
    #     # if isAlarm and (not self.useCamera):
    #     #     self.radarDataHandle.clearObjTrack()
    #
    #     xypLog.xypDebug("var", [(track["alarm"] ,track["objId"],track["score"]) for track in self.radarTrack if  track["alarm"]])
    #     return isAlarm

    def isUseCamera(self):
        # return 0
        if self.weather:
            score0=self.weather0.isUseCamera
            score1= self.weather1.isUseCamera
            socre = min(score0,score1) # 任何一个摄像头被遮挡，单雷达模式
            flag = 1 if score1 > 0.4 else 0


            xypLog.xypDebug(f"isUseCamera {flag},{score0,score1}")
            return flag
        else:
            return 1



    class TimeMoniter():
        def __init__(self,):
            self.startTime = time.monotonic()
            self.flashTime =self.startTime
            self.timeState = {}
        def __call__(self, name):
            if name in self.timeState:
                print("timeMoniter error")
            else:
                nowTime = time.monotonic()
                self.timeState[name] = "{:.3f}".format(nowTime -  self.flashTime).zfill(6)
                self.flashTime = nowTime
        def __str__(self):
            self.totalTime = "{:.3f}".format(time.monotonic()-self.startTime).zfill(6)
            return f"TimeMoniter { self.startTime} {self.totalTime}: {self.timeState}"


    def moniter(self, r_setText_callback=None,
                          d_setText_callback=None,
                          send_merge_data_callback=None,
                          pronounce_queue: BufferQueue = None,
                          remote_call_power_on=None,
                          send_url_data_callback=None,
                          ):
        """
        通过相机、雷达、融合打分机制判断是否报警。
        :param r_setText_callback: 上位机中用于更新界面控件的回调函数 ，显示雷达目标距离和分数
        :param d_setText_callback: 上位机中用于更新界面控件的回调函数 ，显示相机目标距离和分数
        :param send_merge_data_callback:  发送融合信息给web端的回调函数
        :param pronounce_queue: 语音报警模块的报警信息接收队列
        :return: 报警类型
        """
        try:
            timeMoniter = self.TimeMoniter()
            self.nowTime = time.time() # 本次循环该函数的基准时间
            if self.main_config.pika_rabbitmq_enable: # 北京比测与平台定时发送心跳
                if self.nowTime - self.lastSendDeviceStatusTime > 60:
                    self.deviceControlForBeiJing.sendDeviceStatus()
                    self.lastSendDeviceStatusTime = self.nowTime

            # self.useCamera = self.weather0.useCamera & self.weather1.useCamera
            xypLog.xypDebug(f"isUseCamera {self.useCamera}")
            timeMoniter("0.9")
            # self.useCamera=0
            self.radarAlarm, self.radarTrack = self.radarDataHandle.getRadarTrack(5, self.nowTime) # alarm 1 和 alarm 2报警需要限制数据量，复杂度高
            timeMoniter("getRadarTrack")
            # 其余操作堆积在这降低视觉比雷达快的影响
            self.cameraObj = self.cameraDataHandle.getCameraObj(5, self.nowTime)
            timeMoniter("getCameraObj")
            self.diffUse0 = self.diff0.useDiff
            self.diffUse1 = self.diff1.useDiff
            self.diffUse = self.diffUse0 |  self.diffUse1 # 帧差启用但帧差不可用（如光影疯狂干扰）时
            self.diffUse =1
            diff0, diffSet0 = self.diff0.getDiff()
            diff1, diffSet1 = self.diff1.getDiff()
            self.moveMask = np.concatenate([diff0, diff1], axis=0)#*0+1
            self.moveMaskSet = [diffSet0, diffSet1]
            self.moveMaskSet = np.sum([np.concatenate([d0, d1]) * (2 ** cof) for cof, (d0, d1) in
                                       enumerate(zip(self.moveMaskSet[0], self.moveMaskSet[1]))], axis=0)
            timeMoniter("getDiff")
            if 0 < self.radarAlarm < 5: # 雷达点数少于5个点，等待1s，不应该太久，否则可能会导致上一次报警的轨迹都消失了
                time.sleep(1) # 降低视觉比雷达快的影响
                self.radarAlarm, self.radarTrack = self.radarDataHandle.getRadarTrack(5,self.nowTime)
            if self.radarAlarm : # 视觉不可用的情况下单雷达需要更多的数据
                singleRadarAlarm, singleRadarTrack = self.radarDataHandle.getRadarTrack(10, self.nowTime)
            timeMoniter("getRadarTrack2")
            # 策略应该想的是什么样的数据要报警，要具有代表性，越准越好，同时不要去管漏和误，漏的误的最后统一增删查改
            if self.radarAlarm:  # 如果雷达报警
                alarm = 0
                if len(self.cameraObj): # 有视觉目标
                    isAlarm= self.moveMaskReferByCamera()
                    timeMoniter("moveMaskReferByCamera")
                    if isAlarm:
                        alarm = 1
                    xypLog.xypDebug("refer by cameraObj", alarm)
                if alarm ==0:
                    # 注意radarTrack修改的属性不要影响到后面的moveMaskReferBySingleRadar
                    isAlarm =  self.moveMaskReferByRadar()
                    timeMoniter("moveMaskReferByRadar")
                    if isAlarm:
                        alarm = 2
                    xypLog.xypDebug("refer by radarTrack", alarm)
                if alarm == 0:
                    self.radarTrack = singleRadarTrack # 单雷达需要更多的数据
                    isAlarm = self.moveMaskReferBySingleRadar() #
                    timeMoniter("moveMaskReferBySingleRadar")
                    if isAlarm:
                        alarm = 3
                    xypLog.xypDebug("refer by radar", alarm)
            else:
                alarm = 0
                xypLog.xypDebug("refer by radar", alarm)
            # alarm = 3
            # 根据alarm，刷新self.alarm与self.state与self.alarmEnableTime
            # self.alarm: a1是雷达+推理+帧差，a2是雷达+帧差，a3是单雷达，a4是判断不报警了，但还在10秒合并期内，还是被强行认为是报警的
            # self.state: s0 不报警，s1 报警开始，s2报警中，s3 报警结束
            # self.alarmEnableTime：记录上一次真实报警时间（a1、a2、a3中的一个）
            self.flashAlarmState(alarm)
            timeMoniter("flashAlarmState")
            self.pushInfo() # 可视化接口，调用xypPullImage可以查看实时报警情况，开关在/ssd/xyp/tempConfigPushInfo.txt中，重启设置生效
            timeMoniter("pushInfo")
            self.createAlarmInfoPlain()  # 生成本次报警的所有信息
            timeMoniter("createAlarmInfoPlain")
            self.saveImageAndVideo() # 存图
            timeMoniter("saveImageAndVideo")
            """下面比测无关"""
            self.cptbAlarmInfo()  # 比测无关兼容用于发送301数据
            if send_merge_data_callback is not None:  # and not self.is_train_block_alarm:
                # 发送融合信息给web端的回调函数 301报文
                send_merge_data_callback(self.reportdata_for_web)
            timeMoniter("temp")

            for k, v in timeMoniter.timeState.items():
                if k in self.timeMoniterMax:
                    self.timeMoniterMax[k] = max(self.timeMoniterMax[k] , float(timeMoniter.timeState[k]))
                else:
                    self.timeMoniterMax[k] = float(timeMoniter.timeState[k])


            xypLog.xypDebug("alarmInfo",
                            {k: v if k != "objectInfo" else {k2: v2 for k2, v2 in v.items() if k2 != "track"} for k, v
                             in self.alarmInfo.items()})
            xypLog.xypDebug("maxTime",self.timeMoniterMax)
            timeMoniter("timeMoniter")
            xypLog.xypDebug(timeMoniter)
        except Exception as e:
            print(f"{traceback.format_exc()},{e}")
            xypLog.xypDebug(traceback.format_exc(), e)

    def is_alarm_postProcess_pronounce(self, alarm, pronounce_queue, remote_call_power_on):
        # 报警后的声光报警器操作
        if False:
            if self.debug_fire.isFireTime(10):
                print("debug fire camera")
                pronounce_queue.put("camera")
        elif alarm > 0 and pronounce_queue is not None and not remote_call_power_on:  # 20221013 zzl 远程喊话则屏蔽语音报警
            if pronounce_queue.empty():
                if alarm >= 4:
                    pronounce_queue.put("joint")
                elif alarm == 2:
                    pronounce_queue.put("radar")
                elif alarm in [1, 3]:
                    pronounce_queue.put("camera")
            if remote_call_power_on and pronounce_queue.full():
                pronounce_queue.get_nowait()
    def scaleBoxW(self,xywh,camId): # 超出防区反向拉长
        x, y, w, h = xywh
        xypLog.xypDebug("scaleBoxW",  x, y, w, h)

        areaType = list(self.imageAreaHandle.areaMask[camId][:, :, 0][y+h])

        scaleX0 = (x+0.5*w) - 3 * w
        scaleX1 = (x+0.5*w) + 3 * w
        try:
            firstIndex = areaType.index(10)
            lastIndex = len(areaType) - areaType[::-1].index(10) - 1
            # 防区外多一个身位
            lastIndex=lastIndex+w
            firstIndex=firstIndex-w
            areaW = lastIndex - firstIndex

            if areaW>(scaleX1-scaleX0): # 防区大于拉伸6倍框的话
                if areaW < 300 and camId==1:#北京200m
                    scaleX0 = (x + 0.5 * w) - 0.5 * areaW
                    scaleX1 = (x + 0.5 * w) + 0.5 * areaW
                else:
                    scaleX0 =(x+0.5*w) -0.25*areaW
                    scaleX1 =(x+0.5*w) +0.25*areaW




            moreX0 = firstIndex - scaleX0
            moreX1 = scaleX1 - lastIndex
            if moreX0 > -1 and moreX1 > -1:
                pass
            elif moreX0 > -1:
                scaleX0 = scaleX0 + moreX0
                scaleX1 = scaleX1 + moreX0
            elif moreX1 > -1:
                scaleX0 = scaleX0 - moreX1
                scaleX1 = scaleX1 - moreX1
            else:
                pass
        except Exception as e:
            xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
        x = scaleX0
        w = scaleX1 - scaleX0
        return [int(self.imageCoef * i) for i in [x, y, w, h]]

    def saveImageAndVideo(self):
        # 多线程运行需要函数内用局部变量
        # 报警后的图片存储和图片下载链接
        if self.state == 1:
            self.lastSaveImageTime = self.nowTime            
            nowTime = int(self.nowTime * 1000)
            videoCamId = 0 if "c0" in self.videoPath else 1
            radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
            radarBox = [] # 获取拉伸后且在对应分辨率1920*1080下的雷达框
            for obj in self.alarmInfo["objectInfo"]["obj"]:
                if self.alarm==1:
                    camId = obj["camId"]
                    x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                    radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                else:
                    # 雷达框重写设置远近分界线
                    camId =1 if obj["position"][1] >90 else 0
                    x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                    radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])

            self.radarDisplay.drawRadarData(radarImagePath, self.alarmInfo["objectInfo"]["track"][0:1],self.alarmInfo["objectInfo"]['position'][0]) # s1绘制一条轨迹
            self.saveAlarmPicture_task_enQueue(videoCamId, self.videoPath, [])
            # flag: 0 存图不要有框(s3)，1 存图一定要有框(s1 和 第一个 s2)，2 存图有没有框无所谓 (其余s2), 单雷达现在也要存框
            xypLog.xypDebug("radarBox1", radarBox)
            self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath,1)
            self.tx_tieKeYuan_rabbitmq_process(self.alarmInfo["objectInfo"]['position'][0])

            # 用于存储第一次s2
            self.firstSaveInfo ={"time":self.nowTime,"objId":  self.alarmInfo["objectInfo"]["track"][0]["objId"],"objPos": self.alarmInfo["objectInfo"]["position"][0]}
            self.isSaveState2 = True
        elif self.state == 2:
            # self.isSaveState2=True
            if  self.firstSaveInfo["time"]<self.nowTime<=self.firstSaveInfo["time"]+5:
                pass
            elif self.firstSaveInfo["time"]+5<self.nowTime<=self.firstSaveInfo["time"]+10:
                if self.alarm !=4 and self.isSaveState2:
                    self.isSaveState2 = False
                    self.lastSaveImageTime = self.nowTime
                    nowTime = int(self.nowTime * 1000)
                    radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
                    objectInfoVipNum = 0
                    # 思路：第一张s2绘制两条雷达轨迹，能不与s1重复就不重复，轨迹y值相近的为一条轨迹，这种是为了北京两次报警机会执行的策略，正常情况下应该删除
                    radarTrackId= self.firstSaveInfo["objId"]
                    radarTrackPos=self.firstSaveInfo["objPos"]
                    objectInfoVip = {"track": [], "obj": [], "position": []}
                    for track, obj, position in zip(self.alarmInfo["objectInfo"]["track"],
                                                    self.alarmInfo["objectInfo"]["obj"],
                                                    self.alarmInfo["objectInfo"]["position"]):
                        radarId = track["objId"]
                        if radarId != radarTrackId and abs(radarTrackPos - position) > 5:
                            objectInfoVip["track"].append(track)
                            objectInfoVip["obj"].append(obj)
                            objectInfoVip["position"].append(position)
                            radarTrackPos = position
                            objectInfoVipNum += 1
                            if objectInfoVipNum == 1:  # 最多绘制1条
                                break
                    if not objectInfoVipNum:
                        objectInfoVip["track"] = self.alarmInfo["objectInfo"]["track"][:1]
                        objectInfoVip["obj"] = self.alarmInfo["objectInfo"]["obj"][:1]
                        objectInfoVip["position"] = self.alarmInfo["objectInfo"]["position"][:1]

                    radarBox = []  # 获取拉伸后且在对应分辨率1920*1080下的雷达框
                    for obj in objectInfoVip["obj"]:
                        if self.alarm == 1:
                            camId = obj["camId"]
                            x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                            radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                        else:
                            # 雷达框重写设置远近分界线
                            camId = 1 if obj["position"][1] > 90 else 0
                            x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                            radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                    self.radarDisplay.drawRadarData(radarImagePath, objectInfoVip["track"],objectInfoVip["position"][0])
                    # 正如上面所述，第一张s2的定位精度真实精度看名称，但在北京比测中，上传的定位精度是id0的目标，注意区分
                    xypLog.xypDebug("radarBox2", radarBox)
                    self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 1)
                    self.tx_tieKeYuan_rabbitmq_process(objectInfoVip["position"][0])
                else:
                    # 暂时不存其他s2
                    pass
                    # if (self.nowTime - self.lastSaveImageTime > 5):
                    #     self.lastSaveImageTime = self.nowTime
                    #     nowTime = int(self.nowTime * 1000)
                    #     radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
                    #     radarBox = []
                    #     for obj in self.alarmInfo["objectInfo"]["obj"]:
                    #         camId = obj["camId"]
                    #         x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                    #         radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                    #     self.radarDisplay.drawRadarData(radarImagePath, self.alarmInfo["objectInfo"]["track"],self.alarmInfo["objectInfo"]["position"][:1][0])
                    #     self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 2)
            else:
                if  self.isSaveState2:
                    self.isSaveState2 = False
                    self.lastSaveImageTime = self.nowTime
                    nowTime = int(self.nowTime * 1000)
                    radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
                    objectInfoVipNum = 0
                    # 思路：第一张s2绘制两条雷达轨迹，能不与s1重复就不重复，轨迹y值相近的为一条轨迹，这种是为了北京两次报警机会执行的策略，正常情况下应该删除
                    radarTrackId = self.firstSaveInfo["objId"]
                    radarTrackPos = self.firstSaveInfo["objPos"]
                    objectInfoVip = {"track": [], "obj": [], "position": []}
                    for track, obj, position in zip(self.alarmInfo["objectInfo"]["track"],
                                                    self.alarmInfo["objectInfo"]["obj"],
                                                    self.alarmInfo["objectInfo"]["position"]):
                        radarId = track["objId"]
                        if radarId != radarTrackId and abs(radarTrackPos - position) > 5:
                            objectInfoVip["track"].append(track)
                            objectInfoVip["obj"].append(obj)
                            objectInfoVip["position"].append(position)
                            radarTrackPos = position
                            objectInfoVipNum += 1
                            if objectInfoVipNum == 1:  # 最多绘制1条
                                break
                    if not objectInfoVipNum:
                        objectInfoVip["track"] = self.alarmInfo["objectInfo"]["track"][:1]
                        objectInfoVip["obj"] = self.alarmInfo["objectInfo"]["obj"][:1]
                        objectInfoVip["position"] = self.alarmInfo["objectInfo"]["position"][:1]

                    radarBox = []  # 获取拉伸后且在对应分辨率1920*1080下的雷达框
                    for obj in objectInfoVip["obj"]:
                        camId = obj["camId"]
                        x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                        radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                    xypLog.xypDebug("radarBox3", radarBox)
                    self.radarDisplay.drawRadarData(radarImagePath, objectInfoVip["track"],objectInfoVip["position"][0])
                    # 正如上面所述，第一张s2的定位精度真实精度看名称，但在北京比测中，上传的定位精度是id0的目标，注意区分
                    self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 1)
                    self.tx_tieKeYuan_rabbitmq_process(objectInfoVip["position"][0])
                else:
                    # 暂时不存其他s2
                    pass
                    # if (self.nowTime - self.lastSaveImageTime > 5):
                    #     self.lastSaveImageTime = self.nowTime
                    #     nowTime = int(self.nowTime * 1000)
                    #     radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
                    #     radarBox = []
                    #     for obj in self.alarmInfo["objectInfo"]["obj"]:
                    #         camId = obj["camId"]
                    #         x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
                    #         radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
                    #     # self.radarDisplay.drawRadarData(radarImagePath, self.alarmInfo["objectInfo"]["track"])
                    #     self.radarDisplay.drawRadarData(radarImagePath, self.alarmInfo["objectInfo"]["track"],self.alarmInfo["objectInfo"]["position"][:1][0])
                    #     self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 2)
        elif self.state == 3:
            nowTime = int(self.nowTime * 1000)
            radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
            self.radarDisplay.drawRadarData(radarImagePath, {},0)
            self.save_c01_radar_pic_callback(3, self.imagePath, [[-1, -1, -1, -1]], nowTime, radarImagePath, 0)
            self.tx_tieKeYuan_rabbitmq_process(0)

    def tx_tieKeYuan_rabbitmq_process(self,position):
        if self.main_config.pika_rabbitmq_enable:  # self.state !=0 发送 1 2 ... 2 3
            state = self.alarmInfo["state"]
            print(f"报警状态:{state}")
            imagePath = self.alarmInfo["imagePath"]
            videoPath = self.alarmInfo["videoPath"]
            self.deviceControlForBeiJing.sendAlarmInfo(1, 1, state, "人员",  imagePath,videoPath,'', position) # 北京传报警信息
            self.deviceControlForBeiJing.addTask(imagePath)  # 北京传图片
            if self.state==3: # 北京传视频
                self.deviceControlForBeiJing.addTask(videoPath)

    def gusFilter(self,data, n=1, returnMask=False):
        '''
        如果一点需要返回点，即需要有点满足np.abs(data - dataAvg) <= n * dataStd时，n必须大于等于1,原因如下;
        data数据点为1个的时候:(data - dataAvg) = dataStd = 0, n可以取任意值
        data数据点为x个的时候:方差计算公式:sum((data - dataAvg)**2)/x
        因为(data - dataAvg)中最小的是min(data - dataAvg)，有：
        sum((data - dataAvg)**2) >= x*min(data - dataAvg)**2
        sum((data - dataAvg)**2)/x >= min(data - dataAvg)**2
        sqrt(sum((data - dataAvg)**2)/x) >= min(data - dataAvg)
        所以 min(data - dataAvg) 一定小于等于1倍标准差
        '''
        if n < 1:
            raise "gusFilter n must >= 1"
        data = np.array(data)
        dataAvg = np.mean(data)
        dataStd = np.std(data)
        mask = (np.abs(data - dataAvg) <= n * dataStd)  # <=保证了mask至少不全为false
        if returnMask:
            return mask
        else:
            return data[mask]

    def createAlarmInfoPlain(self,):
        # 经过多个版本测试，目前有几个较为准确的雷达轨迹挑选方法，
        # 一个是暴力，雷达位置和图像映射后的位置两两距离之和越小的轨迹最好,在目前数据量限制的情况下满足耗时需求，误匹配风险较小，适用于a1报警，目前a1采用该方法
        # 一个是获取和图像框有交叉的雷达框，计算雷达框生成的mask和图像框生成的mask的比例，这个有缺点，万一雷达框有偏差一直和视觉框不交叉的话会存在问题，耗时会多一点，适用于a1报警
        # 一个是上个方法的变体，雷达框mask和帧差图xor运算，计算白点最少的值，适用于a2报警，目前a2采用该方法
        # 雷达轨迹，挑选最新的轨迹，适用于a3报警，目前a3采用该方法
        # 远焦在远近交接处半个身子或者说被遮挡脚部会有定位精度误差，概率问题，无法避免。成都尝试虚拟出半个身子的真实位置，但北京会弯腰，暂时无解。
        if self.alarm == 0:
            self.alarmInfo["time"] = self.nowTime  # 时间
            self.alarmInfo["alarm"] = self.alarm # 报警类型
            self.alarmInfo["state"] = self.state # 报警状态
            self.alarmInfo["ip"] = self.config.out_ip # ip
            self.alarmInfo["alarmEnableTime"] = self.alarmEnableTime # 上一次真实报警的时间
            self.alarmInfo["objectInfo"] = {"obj": [], "track": [], "position": []}
        elif self.alarm == 1:
            self.alarmInfo["time"] = self.nowTime
            self.alarmInfo["alarm"] = self.alarm
            self.alarmInfo["state"] = self.state
            self.alarmInfo["ip"] = self.config.out_ip
            self.alarmInfo["alarmEnableTime"] = self.alarmEnableTime
            self.alarmInfo["objectInfo"] = {"obj":[],"track":[],"position":[]}
            # if self.calibrateEnable:
            #     alarmCamPos = np.array([obj["position"] for obj in self.cameraObj if obj["alarm"]])
            #     alarmCamPos = alarmCamPos[self.gusFilter(alarmCamPos[:,1],3,True)]
            #     alarmCamPos = np.expand_dims(alarmCamPos,axis=1)
            #     for track in self.radarTrack:
            #         radarPos = np.expand_dims([obj["position"] for obj in track["track"]],axis=0)
            #         dis = np.linalg.norm(alarmCamPos - radarPos,axis=-1)
            #         # 和报警条件配套，因为如果报警的话，视觉框报警处+-10m内肯定有雷达点，添加vip进一步增加距离判断的准确性
            #         if np.min(dis) <10:
            #             track["vip"] = 1
            #         else:
            #             track["vip"] = 0
            #         score = np.sum(dis) / len(track["track"])
            #         track["score"]=score
            #
            # else:
            alarmCameraObj0 = [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 0]
            alarmCameraObj1 = [obj for obj in self.cameraObj if obj["alarm"] and obj["camId"] == 1]
            cameraBestObj = [-np.inf,None]
            for camId, alarmCameraObj in enumerate([alarmCameraObj0, alarmCameraObj1]):
                if len(alarmCameraObj):
                    # 真实的移动物体alarmCameraObj是有移动性的，但是不跟踪框的轨迹难以判断移动性，后期最好有轨迹跟踪提高准确性
                    cameraBox = np.array([obj["xywh"] for obj in alarmCameraObj])
                    cameraBoxX1 = cameraBox[:, 0]
                    cameraBoxY1 = cameraBox[:, 1]
                    cameraBoxH =  cameraBox[:, 3]
                    cameraBoxY2 = (cameraBoxY1 + cameraBoxH)
                    # 对于一个视觉框，假如有雷达框可以包住其百分之八十，且雷达框高度不超过视觉的1.2倍或者宽度不超过1.1倍，则认为这个视觉框附近存在雷达目标
                    for track in self.radarTrack:
                        mask = self.gusFilter(np.array([obj["position"][1] for obj in track["track"]]), 3, True)
                        radarBox = np.array([obj["xywh"][camId] for obj in track["track"]])[mask]
                        rBoxY1 = radarBox[:, 1]
                        rBoxH = radarBox[:, 3]
                        rBoxY2 = rBoxY1 + rBoxH
                        # meshgrid((n,),(m,))  (n,) -> (1,n) -> (m,n), (m,) -> (m,1) -> (m,n)
                        rBoxY1, cBoxY1 = np.meshgrid(rBoxY1, cameraBoxY1)
                        rBoxY2, cBoxY2 = np.meshgrid(rBoxY2, cameraBoxY2)
                        # andArea 第i行表示第i个视觉框与其他所有雷达框的计算
                        andAreaY1 = np.max([ rBoxY1,cBoxY1], axis=0)
                        andAreaY2 = np.min([ rBoxY2,cBoxY2], axis=0)
                        orAreaY1 = np.min([rBoxY1,cBoxY1 ], axis=0)
                        orAreaY2 = np.max([rBoxY2,cBoxY2 ], axis=0)

                        andArea = andAreaY2 - andAreaY1
                        orArea = orAreaY2 - orAreaY1
                        score = (orArea - andArea) / cameraBoxH.reshape(-1, 1)
                        score = np.sum(score) / len(radarBox)
                        if np.max(andArea/cameraBoxH.reshape(-1, 1))> 0.9:
                            track["vip"] = 1
                        else:
                            track["vip"] = 0

                        if "score" not in track:
                            track["score"] = score
                        else:
                            track["score"] = min(score,track["score"])
                    # meshgrid((n,),(m,))  (n,) -> (1,n) -> (m,n), (m,) -> (m,1) -> (m,n)
                    cBoxY1, ccBoxY1 = np.meshgrid(cameraBoxY1, cameraBoxY1)
                    cBoxY2, ccBoxY2 = np.meshgrid(cameraBoxY2, cameraBoxY2)
                    # andArea 第i行表示第i个框与其他所有框的计算
                    andAreaY1 = np.max([cBoxY1, ccBoxY1], axis=0)
                    andAreaY2 = np.min([cBoxY2, ccBoxY2], axis=0)
                    andArea = (andAreaY2 - andAreaY1) / cameraBoxH.reshape(1, -1)
                    andArea[andArea < 0] = 0
                    score = np.sum(andArea, axis=1)
                    maxScore = np.max(score)
                    if maxScore >cameraBestObj[0]:
                        cameraBestObj[0]=maxScore
                        cameraBestObj[1]=alarmCameraObj[np.argmax(score)].copy()
                        mask = andArea[np.argmax(score)] > 0.8 # 向最新的偏移动
                        xx= cameraBoxX1[mask]
                        if len(xx):
                            x,y,w,h = cameraBestObj[1]["xywh"]
                            cameraBestObj[1]["xywh"] =np.array([xx[-1],y,w,h]).astype(np.int64)



            radarTrack = sorted(self.radarTrack, key=lambda x: x["score"])
            radarTrackVip = [track for track in radarTrack if track["vip"]]
            radarTrackAvg = [track for track in radarTrack if not track["vip"]]
            self.alarmInfo["objectInfo"]["track"] = radarTrackVip+radarTrackAvg
            for track in self.alarmInfo["objectInfo"]["track"]:
                positionX = np.mean(self.gusFilter([obj["position"][0] for obj in track["track"] ],3))
                positionY = np.mean(self.gusFilter([obj["position"][1] for obj in track["track"] ], 3))
                # 雷达框拉宽6倍，大约是0.8*6 =4.8m左右
                candidate= [obj for obj in track["track"] if np.abs(obj["position"][0] - positionX) < 4.8]
                if len(candidate):
                    obj = candidate[-1]
                else:
                    # 飘得很厉害，直接选最新的
                    obj = track["track"][-1]

                obj["camId"] = cameraBestObj[1]["camId"]
                obj["xywh"]=obj["xywh"].copy()
                obj["xywh"][obj["camId"]] = cameraBestObj[1]["xywh"]
                self.alarmInfo["objectInfo"]["obj"].append(obj)
                self.alarmInfo["objectInfo"]["position"].append(positionY)

        elif self.alarm == 2:
            self.alarmInfo["time"] = self.nowTime
            self.alarmInfo["alarm"] = self.alarm
            self.alarmInfo["state"] = self.state
            self.alarmInfo["ip"] = self.config.out_ip
            self.alarmInfo["alarmEnableTime"] = self.alarmEnableTime
            self.alarmInfo["objectInfo"] = {"obj":[],"track":[],"position":[]}
            radarMoveMask = np.zeros_like(self.moveMask)
            for track in self.radarTrack:
                if track["alarm"]:
                    s0=0
                    s1=0
                    for obj in track["virtual"]:
                        if obj["alarm"]:
                            x, y, w, h = obj["xywh"][0]
                            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                            radarMoveMask = cv.rectangle(radarMoveMask, (x1, y1), (x2, y2), 1, -1)
                            s0+=w*h
                            x, y, w, h = obj["xywh"][1]
                            s1+=w*h
                            y=y+450
                            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                            radarMoveMask = cv.rectangle(radarMoveMask, (x1, y1), (x2, y2), 1, -1)
                    diff = cv.absdiff(radarMoveMask, self.moveMask)

                    # 理想状态下几乎把白点全干掉了，所以白点越少的越好。除以是为了拉到同一纬度
                    score0 = int(np.sum(diff[:len(diff)//2])) / s0
                    score1 = int(np.sum(diff[len(diff)//2:])) / s1
                    track["score"] = min(score0,score1)
                    self.alarmInfo["objectInfo"]["track"].append(track)

            radarTrackDict = {}
            for track in sorted(self.alarmInfo["objectInfo"]["track"],key=lambda x:x["score"]):
                alarmType =track["alarm"]
                if alarmType not in radarTrackDict:
                    radarTrackDict[alarmType] =[track]
                else:
                    radarTrackDict[alarmType].append(track)

            alarmTypeList = sorted(radarTrackDict.keys(),reverse=True)
            radarTrack =[]
            for i in alarmTypeList:
                radarTrack.extend(radarTrackDict[i])

            self.alarmInfo["objectInfo"]["track"] = radarTrack

            for track in self.alarmInfo["objectInfo"]["track"]:
                positionX = np.mean(self.gusFilter([obj["position"][0] for obj in track["track"]], 3))
                positionY = np.mean(self.gusFilter([obj["position"][1] for obj in track["track"]], 3))
                # 雷达框拉宽6倍，大约是0.8*6 =4.8m左右
                candidate = [obj for obj in track["track"] if np.abs(obj["position"][0] - positionX) < 4.8]
                if len(candidate):
                    obj = candidate[-1]
                else:
                    # 飘得很厉害，直接选最新的
                    obj = track["track"][-1]
                self.alarmInfo["objectInfo"]["obj"].append(obj)
                self.alarmInfo["objectInfo"]["position"].append(positionY)

        elif self.alarm == 3:
            self.alarmInfo["time"] = self.nowTime
            self.alarmInfo["alarm"] = self.alarm
            self.alarmInfo["state"] = self.state
            self.alarmInfo["ip"] = self.config.out_ip
            self.alarmInfo["alarmEnableTime"] = self.alarmEnableTime
            self.alarmInfo["objectInfo"] = {"obj":[],"track":[],"position":[]}

            radarTrack= sorted([tarck for tarck in self.radarTrack if tarck["alarm"]], key=lambda x: x["score"])
            radarTrackAlarm1 = []
            radarTrackAlarm2 = []
            radarTrackAlarm3 = []
            for track in radarTrack:
                if track["alarm"] == 1:
                    radarTrackAlarm1.append(track)
                elif track["alarm"] == 2:
                    radarTrackAlarm2.append(track)
                elif track["alarm"] == 3:
                    radarTrackAlarm3.append(track)
            self.alarmInfo["objectInfo"]["track"] = radarTrackAlarm1 + radarTrackAlarm2 + radarTrackAlarm3
            for track in self.alarmInfo["objectInfo"]["track"]:
                positionX = np.mean(self.gusFilter([obj["position"][0] for obj in track["track"]], 3))
                positionY = np.mean(self.gusFilter([obj["position"][1] for obj in track["track"]], 3))
                # 雷达框拉宽6倍，大约是0.8*6 =4.8m左右
                candidate = [obj for obj in track["track"] if np.abs(obj["position"][0] - positionX) < 4.8]
                if len(candidate):
                    obj = candidate[-1]
                else:
                    # 飘得很厉害，直接选最新的
                    obj = track["track"][-1]
                self.alarmInfo["objectInfo"]["obj"].append(obj)
                self.alarmInfo["objectInfo"]["position"].append(positionY)
        else:
            self.alarmInfo["time"] = self.nowTime
            self.alarmInfo["alarm"] = self.alarm
            self.alarmInfo["state"] = self.state
            self.alarmInfo["ip"] = self.config.out_ip
            self.alarmInfo["alarmEnableTime"] = self.alarmEnableTime
            if len(self.radarTrack):
                self.alarmInfo["objectInfo"] = {"obj": [], "track": [], "position": []}
                radarTrack = sorted(self.radarTrack, key=lambda x: x["createTime"], reverse=True)
                radarTrackVip = []
                radarTrackAvg = []
                for track in radarTrack:
                    pos = np.array([obj["position"] for obj in track["track"]])
                    if (np.max(pos[:, 1]) - np.min(pos[:, 1])) > 6 and (
                            np.max(pos[:, 0]) - np.min(pos[:, 0])) < 1:  # 纵穿加强
                        radarTrackVip.append(track)
                    else:
                        radarTrackAvg.append(track)

                self.alarmInfo["objectInfo"]["track"] = radarTrackVip + radarTrackAvg
                for track in self.alarmInfo["objectInfo"]["track"]:
                    positionX = np.mean(self.gusFilter([obj["position"][0] for obj in track["track"]], 3))
                    positionY = np.mean(self.gusFilter([obj["position"][1] for obj in track["track"]], 3))
                    # 雷达框拉宽6倍，大约是0.8*6 =4.8m左右
                    candidate = [obj for obj in track["track"] if np.abs(obj["position"][0] - positionX) < 4.8]
                    if len(candidate):
                        obj = candidate[-1]
                    else:
                        # 飘得很厉害，直接选最新的
                        obj = track["track"][-1]
                    self.alarmInfo["objectInfo"]["obj"].append(obj)
                    self.alarmInfo["objectInfo"]["position"].append(positionY)
            else:
                # 虚拟报警没雷达轨迹的话沿用上一次的报警信息objectInfo
                pass

        dayFile =datetime.datetime.now().strftime('%Y-%m-%d') # 每天创建新文件夹
        if self.dayFile!=dayFile:
            xypFileTool.checkPath(f"/ssd/alarmpic/alarmFrame/{self.dayFile}")
            self.dayFile=dayFile

        # 生成存图名称
        if self.state == 0:
            self.videoPath = ''
            self.imagePath = ''
        elif  self.state == 1:
            nowTimeFormat = datetime.datetime.fromtimestamp(self.nowTime).strftime("%Y-%m-%d_%H-%M-%S")
            alarmIdFormat ="{:0>6}".format(self.alarmId)
            alarmDistanceFormat ="{:.1f}".format(self.alarmInfo["objectInfo"]['position'][0]).zfill(5)
            self.imagePath = f"/ssd/alarmpic/alarmFrame/{self.dayFile}/{nowTimeFormat}_i{alarmIdFormat}_d{alarmDistanceFormat}_a{self.alarm}_w{self.useCamera}_s1.jpg"
            videoCamId =1 if self.alarmInfo["objectInfo"]['position'][0] >95 else 0
            self.videoPath = f"/ssd/alarmpic/alarmFrame/{self.dayFile}/{nowTimeFormat}_i{alarmIdFormat}_c{videoCamId}.mp4"
        elif self.state == 2:
            nowTimeFormat = datetime.datetime.fromtimestamp(self.nowTime).strftime("%Y-%m-%d_%H-%M-%S")
            alarmIdFormat = "{:0>6}".format(self.alarmId)
            alarmDistanceFormat = "{:.1f}".format(self.alarmInfo["objectInfo"]['position'][0]).zfill(5)
            self.imagePath = f"/ssd/alarmpic/alarmFrame/{self.dayFile}/{nowTimeFormat}_i{alarmIdFormat}_d{alarmDistanceFormat}_a{self.alarm}_w{self.useCamera}_s2.jpg"
        elif self.state == 3:
            nowTimeFormat = datetime.datetime.fromtimestamp(self.nowTime).strftime("%Y-%m-%d_%H-%M-%S")
            alarmIdFormat = "{:0>6}".format(str(self.alarmId))
            self.imagePath = f"/ssd/alarmpic/alarmFrame/{self.dayFile}/{nowTimeFormat}_i{alarmIdFormat}_d000.0_a0_w{self.useCamera}_s3.jpg"
        self.alarmInfo["videoPath"] =  self.videoPath
        self.alarmInfo["imagePath"] =  self.imagePath

    def cptbAlarmInfo(self,):
        # 融合报警目标
        # clear alarmojbs
        self.alarmojbs_cnt = 0
        self.alarmojbs = [{'id': 0, 'bboxs': []}, {'id': 1, 'bboxs': []}]
        self.bbox_list_dict = {0: [], 1: [], 'timestamp': 0}
        for obj in self.alarmInfo["objectInfo"]["obj"]:
            if len(obj["xywh"])==2:
                if obj['position'][1]<50:
                    xywh=obj["xywh"][0]
                else:
                    xywh=obj["xywh"][1]
            else:
                xywh = obj["xywh"]
            cptbAlarmObj = {
                'cameraid': obj["camId"],
                'score': 1,
                'alarmtype': 1,
                'bbox': [float(i) for i in xywh],
                'dto': [1, float(obj['position'][0]), float(obj['position'][1]), 0, 0],
                'in_area': 1,
                'areaId': 1,
            }
            self.alarmojbs[obj["camId"]]["bboxs"].append(cptbAlarmObj)
        self.reportdata_for_web = {
            'alarmojbs': [],
            'stamp': time.time(),
        }

        self.scores_string = f"scores=[" \
                             f"{1:.1f}/{1:.1f}, " \
                             f"{1:.1f}/{1:.1f}, " \
                             f"{1:.1f}/{1:.1f}], " \
                             f"fog_coef_near={self.fog_coef_near}"

        debug_infor_string = f"is_alarm_by_score,{self.scores_string},alarm={self.alarm},sn={self.config.sn}"

        if self.udp_debug_callback is not None:
            # udp打印输出调试分数信息
            self.udp_debug_callback(debug_infor_string)

        # 调试，确认self.reportdata_for_web是否有通讯丢帧
        self.reportdata_for_web['alarmojbs'] = self.alarmojbs
        self.reportdata_for_web['report_cnt'] = f"{self.report_alarm_cnt}/{self.report_cnt}"
        self.reportdata_for_web['trace_score'] = self.scores_string


      # elif self.state == 2:
      #       if not self.useCamera: # 对于单雷达报警，中间的虚拟报警不算
      #           if self.isSaveState2 and self.alarm!=4:
      #               self.singRadarisSaveState2 = True
      #
      #       if (self.nowTime - self.lastSaveImageTime>5) or self.singRadarisSaveState2: # 5s一张图 ,单雷达需要绿色通道，因为10s只会报警一次不能错过
      #           self.lastSaveImageTime = self.nowTime
      #           nowTime = int(self.nowTime * 1000)
      #           radarImagePath = self.imagePath.replace(".jpg", "_radar.jpg")
      #
      #           if not self.useCamera:
      #               isSaveState2 = self.singRadarisSaveState2
      #           else:
      #               isSaveState2 = self.isSaveState2
      #           if isSaveState2:
      #               self.isSaveState2 = False
      #               self.singRadarisSaveState2 = False
      #               objectInfoVipNum=0
      #               # 思路：第一张s2绘制两条雷达轨迹，能不与s1重复就不重复，轨迹y值相近的为一条轨迹，这种是为了北京两次报警机会执行的策略，正常情况下应该删除
      #               radarTrackId, radarTrackPos = self.firstRadarTrackInfo
      #               objectInfoVip = {"track": [], "obj": [], "position": []}
      #               for track,obj,position in zip(self.alarmInfo["objectInfo"]["track"],self.alarmInfo["objectInfo"]["obj"],self.alarmInfo["objectInfo"]["position"]):
      #                   radarId = track["objId"]
      #                   if radarId != radarTrackId and  abs(radarTrackPos-position) > 5:
      #                       objectInfoVip["track"].append(track)
      #                       objectInfoVip["obj"].append(obj)
      #                       objectInfoVip["position"].append(position)
      #                       radarTrackPos = position
      #                       objectInfoVipNum += 1
      #                       if objectInfoVipNum==1:#最多绘制1条
      #                           break
      #               if not objectInfoVipNum:
      #                   objectInfoVip["track"]=self.alarmInfo["objectInfo"]["track"][:1]
      #                   objectInfoVip["obj"]=self.alarmInfo["objectInfo"]["obj"][:1]
      #                   objectInfoVip["position"]=self.alarmInfo["objectInfo"]["position"][:1]
      # 
      #               radarBox = []  # 获取拉伸后且在对应分辨率1920*1080下的雷达框
      #               for obj in objectInfoVip["obj"]:
      #                   camId = obj["camId"]
      #                   x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
      #                   radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
      # 
      # 
      #               self.radarDisplay.drawRadarData(radarImagePath,  objectInfoVip["track"])
      #               # 正如上面所述，第一张s2的定位精度真实精度看名称，但在北京比测中，上传的定位精度是id0的目标，注意区分
      #               self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 1)
      #               self.tx_tieKeYuan_rabbitmq_process(objectInfoVip["position"][0])
      #           else:
      #               radarBox = []
      #               for obj in self.alarmInfo["objectInfo"]["obj"]:
      #                   camId = obj["camId"]
      #                   x, y, w, h = self.scaleBoxW(obj["xywh"][camId], camId)
      #                   radarBox.append([max(0, x), y + (0 if camId == 0 else 1080), min(1919, w), h])
      #               self.radarDisplay.drawRadarData(radarImagePath, self.alarmInfo["objectInfo"]["track"])
      #               self.save_c01_radar_pic_callback(3, self.imagePath, radarBox[0:1], nowTime, radarImagePath, 2)
