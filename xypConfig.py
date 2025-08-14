import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import threading
import traceback
from PIL import Image, ImageDraw
from xypFileTool import checkPath, JsonFileManage, YamlFileManage

from handleCameraData import ImageTool
from xypChannel import Publish
from xypTool.debug import xypLog

'''
配置规范：
  1.自带初始值(防止外部配置读取异常)
  2.设置值方法
  3.读取值方法
  4.保存值方法
  5.修改与修改互斥，修改与使用互斥，使用与使用不互斥
'''
# class aConfig():


#
#
# class CameraAlarmObjectConfig():
#     def __init__(self,configName, filePath):
#         self.configName = configName
#         # 初始化数据
#         self.data= {configName:[0]}
#         if isinstance(filePath,str):
#             self.data["configPath"]=filePath
#         self.fileManage = JsonFileManage(self.data["configPath"])
#         self.config = self.fileManage.load()
#         if  self.config is not None:
#             self.data=value
#         self.webPublish = Publish(self.configName, "sendToWeb")   # 获取发布者
#     def _createHandle(self,modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#
#     def _setData(self, setData=None):
#         print(f"configSet start:{self.configName} -> {setData} ")
#         self._data = setData
#         self._publishToWeb()
#         print(f"configSet done:{self.configName} = {self._data} ")
#
#     def _saveData(self):
#         if self.fileManage is not None:  # 单独保存
#             self.fileManage.save(self._data)
#         else:  # 生成保存数据，外部保存
#             return self._data
#
#     def _publishToWeb(self,client=None):
#         self.webPublish.publish({"client": client, "data":{"code": 116, "msg": "success", "data": {"alarm_obj": self._data}}})
#
# class GpioSwitchConfig(SafeData):
#     def __init__(self, configName,filePath=None):
#         self.configName = configName
#         # 初始化数据
#         config = {"Relay_off": 0, "Opt_off": 0}
#         self.fileManage = None
#         if filePath is not None:
#             self.fileManage = JsonFileManage(filePath)
#             value = self.fileManage.load()
#             if value is not None:
#                 config = value
#         super().__init__(config, configName)  # 普通数据转为安全数据
#         self.webPublish = Publish(self.configName, "sendToWeb")  # 获取发布者
#
#     def _createHandle(self, modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#     def _setData(self, setData):
#         print(f"configSet start:{self.configName} -> {setData} ")
#         self._data = setData
#         self._publishToWeb()
#         print(f"configSet done:{self.configName} = {self._data} ")
#
#     def _saveData(self):
#         if self.fileManage is not None:  # 单独保存
#             self.fileManage.save(self._data)
#         else:  # 生成保存数据，外部保存
#             return self._data
#     def _publishToWeb(self,client=None):
#         self.webPublish.publish({"client": client, "data":{"code": 117,"msg": "success","data": self._data}})
#
# class RadarSceneConfig(SafeData):
#     def __init__(self, configName, filePath=None):
#         self.configName = configName
#         # 初始化数据
#         config = 0
#         self.fileManage = None
#         if filePath is not None:
#             self.fileManage = JsonFileManage(filePath)
#             value = self.fileManage.load()
#             if value is not None:
#                 config = value
#         super().__init__(config, configName)  # 普通数据转为安全数据
#         self.webPublish = Publish(self.configName, "sendToWeb")  # 获取发布者
#         self.radarPublish = Publish(self.configName, "sendToRadar")
#     def _createHandle(self, modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             publishToRadar = self._publishToRadar
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#     def _setData(self, setData):
#         print(f"configSet start:{self.configName} -> {setData} ")
#         self._data = setData
#         self._publishToRadar()
#         self._publishToWeb()
#         print(f"configSet done:{self.configName} = {self._data} ")
#
#     def _saveData(self):
#         if self.fileManage is not None:# 单独保存
#             self.fileManage.save(self._data)
#         else: # 生成保存数据，外部保存
#             return self._data
#     def _publishToWeb(self,client=None):
#         self.webPublish.publish({"client": client, "data":{"code": 114,"msg": "success","data": {"scene": self._data}}})
#
#     def _publishToRadar(self):
#         self.radarPublish.publish(b"\x71\x04\x00\x01" +bytes([self._data]))
#
# class RadarFrequencyConfig(SafeData):
#     def __init__(self, configName, filePath=None):
#         self.configName = configName
#         # 初始化数据
#         config = 0
#         self.fileManage = None
#         if filePath is not None:
#             self.fileManage = JsonFileManage(filePath)
#             value = self.fileManage.load()
#             if value is not None:
#                 config = value
#         super().__init__(config, configName)  # 普通数据转为安全数据
#         self.webPublish = Publish(self.configName, "sendToWeb")  # 获取发布者
#         self.radarPublish = Publish(self.configName, "sendToRadar")
#     def _createHandle(self, modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             publishToRadar = self._publishToRadar
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#     def _setData(self, setData):
#         print(f"configSet start:{self.configName} -> {setData} ")
#         self._data = setData
#         self._publishToRadar()
#         self._publishToWeb()
#         print(f"configSet done:{self.configName} = {self._data} ")
#
#     def _saveData(self):
#         if self.fileManage is not None:  # 单独保存
#             self.fileManage.save(self._data)
#         else:  # 生成保存数据，外部保存
#             return self._data
#     def _publishToWeb(self,client=None):
#         self.webPublish.publish({"client": client, "data":{"code": 115,"msg": "success","data": {"frequency": self._data}}})
#
#     def _publishToRadar(self):
#         self.radarPublish.publish(b"\x71\x08\x00\x01" +bytes([self._data]))
#
# class RadarSensitivityConfig(SafeData):
#     def __init__(self, configName, filePath=None):
#         self.configName = configName
#         # 初始化数据
#         config = 0
#         self.fileManage = None
#         if filePath is not None:
#             self.fileManage = JsonFileManage(filePath)
#             value = self.fileManage.load()
#             if value is not None:
#                 config = value
#         super().__init__(config, configName)  # 普通数据转为安全数据
#         self.webPublish = Publish(self.configName, "sendToWeb")  # 获取发布者
#         self.radarPublish = Publish(self.configName, "sendToRadar")
#     def _createHandle(self, modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             publishToRadar = self._publishToRadar
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#     def _setData(self, setData): #
#         print(f"configSet start:{self.configName} -> {setData} ")
#         self._data = setData
#         self._publishToRadar()
#         self._publishToWeb()
#         print(f"configSet done:{self.configName} = {self._data} ")
#
#     def _saveData(self):
#         if self.fileManage is not None:  # 单独保存
#             self.fileManage.save(self._data)
#         else:  # 生成保存数据，外部保存
#             return self._data
#     def _publishToWeb(self,client=None):
#         self.webPublish.publish({"client":client,"data":{"code": 113,"msg": "success","data": {"sensitivity": self._data}}})
#
#     def _publishToRadar(self):
#         self.radarPublish.publish(b"\x71\x02\x00\x01"+bytes([self._data]))
#
# class RadarAreaConfig(SafeData):
#     def __init__(self,configName,vanishHandle,filePath=None):
#         self.configName = configName
#         self.vanishHandle = vanishHandle
#
#         self.webPublish = Publish( self.configName , "sendToWeb")  # 获取发布者
#         self.areaBaseAttr = ["type", "areaId", "userArea", "enable", "code"]  # 区域基础属性
#
#         self.displayPath = "./aa"  # 区域可视化保存地址
#         checkPath(self.displayPath)  # 目录不存在则创建目录
#
#         # 优先级高的可以覆盖优先级低的，相同等级的可以相互覆盖，值越大优先级越低
#         # 0:屏蔽区或者无区域，1:误报区，10:报警区，101:拓展区，(可用值[0~255]，剩余空隙可拓展)
#         self.priority = [0, 1, 10, 101]  # 目前已有等级
#
#         # 设置离散关系
#         self.radarValidArea = [[-25, 0], [-25, 250], [25, 250], [25, 0]]  # 雷达有效范围
#         self.resolution = [200, 1000]  # 离散后图像分辨率
#         self.radarDiscret = self.getRadarDiscretRelate()  # 获取雷达离散为像素的函数
#
#         self.availableId=dict.fromkeys(range(256)) # 可分配id
#         self.areaMask = None  # 存储区域掩膜
#
#         # 初始化数据
#         config = []
#         self.fileManage = None
#         if filePath is not None:
#             checkPath(filePath)
#             self.fileManage = JsonFileManage(filePath)
#             value = self.fileManage.load()
#             if value is not None:
#                 config = value
#         # 普通数据转为安全数据
#         super().__init__(config, self.configName)
#
#     def _createHandle(self, modify):
#         class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
#             getData = self._getData
#             release = self._release
#             publishToWeb = self._publishToWeb
#             if modify:
#                 setData = self._setData
#                 saveData = self._saveData
#         return Standard
#     def _setDataCompatible(self, setData,radarAreaData): # 兼容当前外部设置
#         '''
#         setData 当前传入格式：
#         雷达区域直接设置：
#             {code: 112 data:{0:[{type verteces},{type shielding}...]}}
#             期望后期格式为
#                 {code: 112 data:[{type userArea} ...]}
#         图像转雷达区域设置：
#             {code: 1 data:[{type userArea} ...]}
#         误报区设置：
#             {code: 2 data:[{type userArea} ...]}
#         属性设置
#             {code: 0 data:[area ...]}
#             area:{areaId type userArea [,...]}
#         加载：
#             由本程序生成并加载的不用兼容处理，格式为输出格式
#         输出
#             当前输出格式为[{type code userArea}]
#         '''
#
#         code = setData["code"]
#         areaData = setData["data"]
#         compatibleData = {}
#
#         # 获取可用区域id
#         for area in radarAreaData:
#             self.availableId.pop(area["areaId"], None)
#
#         '''data->[area...]'''
#         if code == 112:  # 更新指定防区数据
#             areaData=areaData["0"]
#
#         for area in areaData:
#             # "type", "areaId", "userArea", "enable", "code"
#             if "type" not in area:
#                 if "verteces" in area:
#                     area["type"] = 10
#                 elif "shielding" in area:
#                     area["type"] = 0
#             else:
#                 if area["type"] == 1 :
#                     area["type"]=10
#
#             if "areaId" not in area:
#                 areaId = next(iter(self.availableId.keys()))
#                 self.availableId.pop(areaId)
#                 area["areaId"] = areaId
#
#             if "userArea" not in area:
#                 if "verteces" in area:
#                     area["userArea"] = area["verteces"]
#                 elif "shielding" in area:
#                     area["userArea"] = area["shielding"]
#             if "enable" not in area:
#                 area["enable"] = 1
#             if "code" not in area:
#                 area["code"] = code
#
#             area = {k: v for k, v in area.items() if k in self.areaBaseAttr}
#             compatibleData[area["areaId"]] = area
#
#         for area in radarAreaData:  # 获取要删除的防区
#             if area["code"] == code or (code==112 and area["code"]==1):#(code==112 and area["code"]==1)图像映射的防区目前会和112一起接收
#                 if area["areaId"] not in compatibleData:
#                     self.availableId[area["areaId"]] = None  # 释放区域id
#                     compatibleData[area["areaId"]] = None
#
#         return compatibleData
#     def _setData(self, setData): # 区域设置
#         '''
#         setData：防区或者防区的设置,为None表示获取防区，为dict、list表示设置、加载，为其True表示单纯刷新生成属性
#         '''
#         try:
#             radarAreaData = self._data
#             print("radarAreaSet start", setData)
#             if isinstance(setData, dict):  # 更新防区
#                 setData =  self._setDataCompatible(setData,radarAreaData) # 区域设置内容兼容处理
#                 '''
#                 setData的格式:{areaId:area ...}
#                 area: [areaAttr0 areaAttr1 ...] or None
#                 '''
#                 # 更改现有防区
#                 areaNum = len(radarAreaData)
#                 for idx, radarArea in enumerate(radarAreaData[::-1], 1):
#                     if radarArea["areaId"] in setData:
#                         instruct = setData.pop(radarArea["areaId"])
#                         if instruct is None:
#                             radarAreaData.pop(areaNum-idx)
#                         else:
#                             radarArea.update(instruct)
#                 # 添加新防区
#                 radarAreaData.extend(setData.values())
#
#             elif isinstance(setData, list): # 加载防区
#                 radarAreaData.extend(setData)
#
#             for area in radarAreaData:  # 防区信息增强
#                 # userArea 用户区域
#                 # validArea 有效的区域
#                 # validExtendArea 有效的拓展区域
#                 radarValidArea = Polygon(self.radarValidArea)
#                 userArea = Polygon(area["userArea"])
#                 if radarValidArea.intersects(userArea):
#                     area["validArea"] = list(radarValidArea.intersection(userArea).exterior.coords)[:-1]
#                     if area["type"] == 10:  # 报警区才有拓展
#                         extendArea = self.areaScale(area["validArea"][::-1], 2)  # 拓展2m,[::-1],雷达坐标系和图像坐标系y值相反
#                         area["validExtendArea"] = list(
#                             radarValidArea.intersection(Polygon(extendArea)).exterior.coords)[:-1]
#                     else:
#                         area["validExtendArea"] = None
#                 else:
#                     area["validArea"] = None
#                     area["validExtendArea"] = None
#             self._data =  radarAreaData
#             self._areaDisplay()  # 区域可视化
#             self._areaMaskCreate()  # 区域mask创建
#             print("radarAreaSet done", )
#             self._publishToWeb()
#             return True
#         except:
#             xypDebug("radarAreaSet error", traceback.format_exc())
#             return False
#
#     def _saveData(self, ):    # 区域保存
#         radarAreaDataSave = []
#         for area in self._data:
#             if area["type"] != 1:  # 不保存误报区
#                 radarAreaDataSave.append({k: v for k, v in area.items() if k in self.areaBaseAttr})
#         if self.fileManage is not None:
#             self.fileManage.save(radarAreaDataSave)
#         else:
#             return radarAreaDataSave
#     def _publishToWeb(self,client =None):# 当前与web的兼容发送
#         try:
#             "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
#             radarAreaData =self._data
#             radarAreaDataSend = []
#             for area in radarAreaData:
#                 areaSend = {}
#                 if area["type"] == 10:
#                     areaSend["type"] = 1
#                     areaSend["verteces"] = area["userArea"]
#                 elif  area["type"] == 0:
#                     areaSend["type"] = 0
#                     areaSend["shielding"] = area["userArea"]
#                 else:
#                     continue
#                 areaSend["code"] =  area["code"]
#                 areaSend["enable"] = area["enable"]
#                 areaSend["areaId"] = area["areaId"]
#                 radarAreaDataSend.append(areaSend)
#             "<<<<<<<<<<<<<<<<<<<<<<<兼容处理"
#             self.webPublish.publish({"client":client,"data":{"code": 112, "msg": "success", "data":  {"0": radarAreaDataSend}}})
#         except:
#             print("areaSendToWeb error",traceback.print_exc())
#
#     def getRadarDiscretRelate(self): #雷达离散为像素关系
#         x = [i[0] for i in self.radarValidArea]
#         y = [i[1] for i in self.radarValidArea]
#
#         self.scaleX = self.resolution[0]/(max(x)-min(x))
#         self.scaleY = self.resolution[1]/(max(y)-min(y))
#         # 雷达点有效范围是[50,100]的话坐标x是[-25,25],坐标y是[0,100]
#         offset = -min(x)
#         return lambda pos: [(pos[0] + offset)* self.scaleX,self.resolution[1]-pos[1]*self.scaleY ] # 雷达离散为像素关系的函数
#
#     def _areaMaskCreate(self, ):
#         radarAreaData=self._data
#         areaMask = Image.new('L', self.resolution, "black")
#         areaIdMask = Image.new('L', self.resolution, "white")
#
#         areaDraw = ImageDraw.Draw(areaMask) # 用于绘制区域掩码
#         areaIdDraw = ImageDraw.Draw(areaIdMask) # 用于绘制区域id
#
#         # 将优先级低的先画，防止覆盖优先级高的，type越大优先级越低
#         for areaType in self.priority[::-1]:
#             for area in radarAreaData:
#                 if areaType == 101 and area["validExtendArea"] is not None:
#                     areaDraw.polygon([tuple(self.radarDiscret(i)) for i in area["validExtendArea"]], fill=areaType)
#                 elif area["type"] == areaType and area["validArea"] is not None:
#                     areaDraw.polygon([tuple(self.radarDiscret(i)) for i in area["validArea"]], fill=areaType)
#                     areaIdDraw.polygon([tuple(self.radarDiscret(i)) for i in area["validArea"]], fill=area["areaId"])
#
#         nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#         areaMask.save(os.path.join(self.displayPath, f"{nowTime}_radar_areaMask.jpg"))
#         areaMask = np.stack([np.array(areaMask), np.array(areaIdMask)], axis=-1)
#         self.areaMask = areaMask
#     def areaScale(self, data, dis):
#         """
#         多边形等距缩放 https://zhuanlan.zhihu.com/p/97819171
#         data: [n,2->(x,y)], 多边形按照逆时针顺序排列的的点集，不是逆时针会造成dis为正反而缩小、拓展失败等情况，注意这里的逆时针是以图像坐标系为参考系
#         dis: 缩放距离
#         """
#         if dis == 0:
#             return data
#         data = np.array(data)
#         num = len(data)
#         newData = []
#         for idx in range(num):
#             # idx % num 数据跑马灯
#             vectorA = data[idx] - data[(idx - 1) % num]
#             vectorB = data[idx] - data[(idx + 1) % num]
#
#             lengthA = np.linalg.norm(vectorA)
#             lengthB = np.linalg.norm(vectorB)
#             if (lengthA * lengthB == 0):  # 点重合
#                 continue
#             direction = vectorA / lengthA + vectorB / lengthB  # 方向
#             if (np.cross(vectorA, vectorB)) > 0:  # 如果是凹
#                 direction = -direction
#
#             sinV = np.cross(vectorA, vectorB) / (lengthA * lengthB)  # 夹角sin值
#             if sinV == 0:
#                 continue
#             else:
#                 unitLength = abs(1 / sinV)  # 单位长度
#             newPoint = data[idx] + dis * unitLength * direction
#             newData.append(newPoint)
#         return newData
#
#     def _areaDisplay(self,):# 区域可视化
#         radarAreaData=self._data
#         nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#         fig = plt.figure(f"radar area, unit:m")
#         ax = plt.subplot()
#         ax.cla()
#         radarAreaDataUseless = [area for area in radarAreaData if not area["enable"]]
#         radarAreaDataUseful = [area for area in radarAreaData if area["enable"]]
#         for enableFlag, radarArea in enumerate([radarAreaDataUseless, radarAreaDataUseful]):  # 先绘制失效的
#             if enableFlag == 0:
#                 edgecolor = (0.5, 0.5, 0.5, 1)
#                 linewidth = 2
#             else:
#                 edgecolor = None
#                 linewidth = 0
#             # 将优先级低的先画，防止覆盖优先级高的，type越大优先级越低
#             for areaType in self.priority[::-1]:
#                 for area in radarAreaData:
#                     if areaType == 101 and area["validExtendArea"] is not None: # 绘制拓展区
#                         polygon = plt.Polygon(area["validExtendArea"], closed=True, facecolor=(0, 0, 1, 1), edgecolor=edgecolor, linewidth=linewidth)
#                         ax.add_patch(polygon)
#                     elif area["type"] == areaType:
#                         if area["type"] == 0:
#                             fillColor = (0, 0, 0, 0.8)  # 黑
#                         elif area["type"] == 1:
#                             fillColor = (1, 1, 0, 0.8)  # 黄
#                         elif area["type"] == 10:
#                             fillColor = (1, 0, 0, 0.8)  # 红
#                         # 绘制用户给出区域
#                         polygon = plt.Polygon(area["userArea"], closed=True, facecolor=fillColor, edgecolor=edgecolor,
#                                               linewidth=linewidth)
#                         ax.add_patch(polygon)
#                         # 绘制有效区
#                         if area["validArea"] is not None:
#                             polygon = plt.Polygon(area["validArea"], closed=True, facecolor=(0, 1, 0, 0.5),
#                                                   edgecolor=edgecolor, linewidth=linewidth)
#                             ax.add_patch(polygon)
#         x = [i[0] for i in self.radarValidArea]
#         y = [i[1] for i in self.radarValidArea]
#         ax.set_xlim(min(x)-5,max(x)+5)
#         ax.set_ylim(min(y),max(y)+20)
#         savePath = f"{self.displayPath}/{nowTime}_radarArea.jpg"
#         fig.savefig(savePath)
#
#     def getObjArea(self, orgBox): # 获取目标所属区域
#         # 注意在区域重叠时，返回值的areaType, area["areaId"]会是重叠区域中的其中一个区域
#         x, y = orgBox
#         handle=self.apply(False)
#         if  self.areaMask is not None:
#             x,y = self.radarDiscret([x,y])
#             x = int(round(min(self.resolution[0] - 1, max(x, 0))))
#             y = int(round(min(self.resolution[1] - 1, max(y, 0))))
#             areaType, areaId = self.areaMask[y, x]
#             handle.release()
#             return int(areaType), int(areaId) # json不支持uint8格式
#
#         else:  # 防区为空
#             handle.release()
#             return 0, 255
class ImageAreaConfig():
    def __init__(self, configName,filePath,vanishHandle,radarAreaHandle=None, resolution=(800, 450)):
        self.configName=configName
        self.resolution = resolution  # 目标分辨率
        self.vanishHandle = vanishHandle
        self.radarAreaHandle = radarAreaHandle

        self.webPublish = Publish(self.configName, "sendToWeb")
        self.areaBaseAttr = ["type", "areaId", "userArea", "camId", "resolution", "enable", "code"]

        self.displayPath = "./aa"  # 区域可视化保存地址
        checkPath(self.displayPath)

        # 优先级高的可以覆盖优先级低的，相同等级的可以相互覆盖，值越大优先级越低
        # 0:屏蔽区或者无区域，1:误报区，10:报警区，101:拓展区，(可用值[0~255]，剩余空隙可拓展)
        self.priority = [0, 1, 10]  # 目前已有等级
        self.areaMask = {0: None, 1: None}  # 存储图像掩膜
        self.availableId = dict.fromkeys(range(256))  # 可分配id

        if isinstance(filePath, str):
            self.fileManage = YamlFileManage(filePath)
            data = self.fileManage.load()
            if data is not None:
                self.data = data
            else:
                self.data = []
                self.data["configPath"] = filePath
                self.saveData()
        else:
            self.data = filePath
            self.fileManage = JsonFileManage(self.data["configPath"])


    def getData(self):
        data = self.data[self.configName]
        return data

    def _createHandle(self, modify):
        class Standard():  # 用于规范用法，必须occupy成功后才有getData之类的方法
            getData = self._getData
            release = self._release
            publishToWeb = self._publishToWeb
            if modify:
                setData = self._setData
                saveData = self._saveData

        return Standard
    def setDataCompatible(self, setData,imageAreaData):  # 区域兼容处理
        # 对于视觉区域
        '''
        setData 当前传入格式：
        web防区设置：
            {code:100 data:{0:[area ...],1:[area ...]}}
            area:{alarm_level data_list [,...]}
        web屏蔽区设置：
            {code:110 data:{0:[area ...],1:[area ...]}}
            area:{reserved data_list [,...]}
        误报区设置
            {code: 2 data:{0:[area ...],1:[area ...]}}
            area:{type userArea [,...]}
        属性设置
            {code: 0 data:[area ...]}
            area:{areaId type userArea [,...]}

        输出
            compatibleData=[area ...]
            area:{type userArea camId resolution code enable}

        注意{type userArea camId resolution code enable}为基本属性，每个区域都必须带有
        其余属性为生成属性，即基于area基本属性生成的属性，基本属性发生更改，依赖基本属性生成的数据都需要更改。
        '''
        code = setData["code"]
        data = setData["data"]

        compatibleData = {}
        if code == 0:  # 更新指定防区数据
            print("error xwqe")
        else:  # 更新整个相同的code数据
            for camId in data:
                if camId in ["0", "1", 0, 1]:
                    for area in data[camId]:
                        areaId = next(iter(self.availableId.keys()))
                        self.availableId.pop(areaId)
                        if code == 100:
                            areaType = 10
                        elif code == 110:
                            areaType = 0

                        area=  {"type":areaType,
                        "userArea":[i[:2] for i in area["data_list"]],
                        "camId":int(camId),
                        "resolution": [1280, 720],
                        "code":code,
                        "enable":1,
                         "areaId":areaId
                         }
                        compatibleData[area["areaId"]] = area
        for areaId in imageAreaData:  # 获取要删除的防区
            if imageAreaData[areaId]["code"] == code:
                if areaId not in compatibleData:
                    self.availableId[areaId]=None
        return compatibleData

    def setData(self, setData=None):  # 区域设置
        '''
        setData：防区或者防区的设置,为None表示获取防区，为dict、list表示设置、加载
        '''
        try:

            print("imageAreaSet start", setData)
            imageAreaData = self.getData().copy()
            if setData:  # 更新防区
                setData = self.setDataCompatible(setData,imageAreaData)  # 将设置的防区指令兼容成本程序可用形式
                '''
                setData的格式:{areaId:area ...}
                area: [areaAttr0 areaAttr1 ...] or None
                '''
                # 更改现有防区
                imageAreaData.update(setData.values())
                imageAreaData = {k:v for k,v in imageAreaData if v}
                # 区域可用id检测
                for areaId in imageAreaData:
                    self.availableId.pop(areaId, None)
                self.data[self.configName] = imageAreaData
                self.areaDisplay()  # 区域可视化
                self._areaMaskCreate()  # 区域mask创建
                self._saveData()
            print("imageAreaSet done")
            self._publishToWeb()
            calibInfo.release()
            return True
        except:
            print("imageAreaSet error", traceback.format_exc())
            return False

    def _saveData(self, ):  # 区域保存
        imageAreaDataSave = []
        for area in self._data:
            imageAreaDataSave.append({k: v for k, v in area.items() if k in self.areaBaseAttr})
        if self.fileManage is not None:
            self.fileManage.save(imageAreaDataSave)
        else:
            return imageAreaDataSave
    def _publishToWeb(self, client=None):  # 当前与web的兼容发送
        imageAreaData = self._data
        for code in [100,110]:
            imageAreaDataSend = {0: [], 1: []}
            for area in imageAreaData:
                "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
                if area["code"] == code:
                    #  self.areaBaseAttr
                    areaSend = {}
                    areaSend["alarm_level"] = 2 if code == 100 else -2
                    areaSend["areaId"] = area["areaId"]
                    areaSend["data_list"] = ImageTool.convertResolution(area["userArea"], area["resolution"], (1280, 720),
                                                                        "xy").tolist()  # 网页需要1280*720的
                    areaSend["camId"] = area["camId"]
                    areaSend["resolution"] = (1280, 720)
                    areaSend["enable"] = area["enable"]
                    areaSend["code"] = area["code"]
                    imageAreaDataSend[area["camId"]].append(areaSend)
                "<<<<<<<<<<<<<<<<<<<<<<<兼容处理"

            print("imageAreaSet send",{"code": code, "msg": "success", "data": imageAreaDataSend})
            self.webPublish.publish({"client":client,"data":{"code": code, "msg": "success", "data": imageAreaDataSend}})
    def _areaMaskCreate(self, ):  # 加快判断是否在区域内，创建图像mask
        imageAreaData=self._data
        for camId in self.areaMask:
            areaMask = Image.new('L', self.resolution, "black")
            areaIdMask = Image.new('L', self.resolution, "white")
            areaDraw = ImageDraw.Draw(areaMask)
            areaIdDraw = ImageDraw.Draw(areaIdMask)
            # 将优先级低的先画，防止覆盖优先级高的，type越大优先级越低
            for areaType in self.priority[::-1]:
                for area in imageAreaData:
                    if area["enable"] and area["camId"] == camId:
                        if areaType == 101 and area["validExtendArea"] is not None:
                            areaDraw.polygon([tuple(i) for i in area["validExtendArea"]], fill=areaType)
                        elif area["type"] == areaType and area["validArea"] is not None:
                            areaDraw.polygon([tuple(i) for i in area["validArea"]], fill=areaType)
                            areaIdDraw.polygon([tuple(i) for i in area["validArea"]], fill=area["areaId"])
            nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            areaMask.save(os.path.join(self.displayPath, f"{nowTime}_camera{camId}_areaMask.jpg"))
            self.areaMask[camId] = np.stack([np.array(areaMask), np.array(areaIdMask)], axis=-1)

    def areaScale(self, data, dis):  # 区域缩放
        """
        多边形等距缩放 https://zhuanlan.zhihu.com/p/97819171
        data: [n,2->(x,y)], 多边形按照逆时针顺序排列的的点集
        dis: 缩放距离
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

    def areaDisplay(self, ):
        imageAreaData = self.getData()
        nowTime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        for camId in [0, 1]:
            fig = plt.figure(f"camera{camId} area, unit:px", facecolor='white')
            ax = plt.subplot()
            ax.cla()
            imageAreaDataUseless = [area for area in imageAreaData.values() if not area["enable"] and area["camId"] == camId]
            imageAreaDataUseful  = [area for area in imageAreaData.values() if area["enable"] and area["camId"] == camId]
            for enableFlag, imageArea in enumerate([imageAreaDataUseless, imageAreaDataUseful]):  # 先绘制失效的
                if enableFlag == 0:
                    edgecolor = (0.5, 0.5, 0.5, 1)
                    linewidth = 2
                else:
                    edgecolor = None
                    linewidth = 0
                for areaType in self.priority[::-1]:
                    for area in imageArea:
                        if area["type"] == areaType:
                            if area["type"] == 0:
                                fillColor = (0, 0, 0, 0.8)  # 黑
                            elif area["type"] == 1:
                                fillColor = (1, 1, 0, 0.8)  # 黄
                            elif area["type"] == 10:
                                fillColor = (1, 0, 0, 0.8)  # 红
                            polygon = plt.Polygon(area["userArea"], closed=True, facecolor=fillColor,
                                                  edgecolor=edgecolor, linewidth=linewidth)
                            ax.add_patch(polygon)
                            if area["validArea"] is not None:
                                polygon = plt.Polygon(area["validArea"], closed=True, facecolor=(0, 1, 0, 0.5),
                                                      edgecolor=edgecolor, linewidth=linewidth)
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
                            polygon = plt.Polygon(
                                self.vanishHandle.estimateImageToRadar(area["validExtendArea"], camId), closed=True,
                                facecolor=(0, 0, 1, 1),
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
                                ax.add_patch(polygon)  # userArea在无效区域绘制会出现问题，保证融合色一致
                                polygon = plt.Polygon(self.vanishHandle.estimateImageToRadar(area["validArea"], camId),
                                                      closed=True, facecolor=(0, 1, 0, 0.5),
                                                      edgecolor=edgecolor, linewidth=linewidth)
                                ax.add_patch(polygon)
            ax.set_xlim(-50, 50)
            ax.set_ylim(0, 250)
            savePath = f"{self.displayPath}/{nowTime + f'_meter_camera{camId}_imageArea.jpg'}"
            print(f"Image area display path {savePath}, unit:m")
            fig.savefig(savePath)

        # plt.show()

    def getObjArea(self, orgBox, camId):  # 获取目标所属区域
        # 注意在区域重叠时，返回值的areaType, area["areaId"]会是重叠区域中的其中一个区域
        if len(orgBox) == 2:  # x,y
            x, y = orgBox
        else:  # x,y,w,h
            x, y = orgBox[0] + orgBox[2] / 2, orgBox[1] + orgBox[3]

        handle=self.apply(False)
        if self.areaMask[camId] is not None:
            x = int(round(min(self.resolution[0] - 1, max(x, 0))))
            y = int(round(min(self.resolution[1] - 1, max(y, 0))))
            areaType, areaId = self.areaMask[camId][y, x]  # json不支持uint8格式
            handle.release()
            return int(areaType), int(areaId)
        else:  # 防区为空
            handle.release()
            return 0, 255



class CameraVanishConfig():
    def __init__(self, configName,filePath=None, resolution=(800, 450)):
        self.resolution = resolution
        self.configName = configName

        self.webPublish = Publish(self.configName, "sendToWeb")
        self.modifyLock = threading.Lock()
        self.calibBaseAttr = ["resolution", "vanishPointMain", "cameraHeight",
                              "radPerPixelFovV","vanishPointAuto"]  # 这些属性是必需的，会保存的，其他属性都可以根据这些属性生成

        if isinstance(filePath,str):
            self.fileManage = YamlFileManage(filePath)
            data = self.fileManage.load()
            if data is not None:
                self.data = data
            else:
                self.data={configName: {k:{"cameraHeight": 2,"radPerPixelFovV": 0.001,"resolution": [800,450],
                                           "vanishPointMain": [400,225],
                                           "vanishPointAuto": {"imageToRadar":{},"radarToImage":{}},
                      } for k in range(2)}}
                self.data["configPath"] = filePath
                self.saveData()
        else:
            self.data=filePath
            self.fileManage = JsonFileManage(self.data["configPath"])

    def getData(self):
        data = self.data[self.configName]
        return  data

    def setDataCompatible(self, setData):
        # {'code': 108, 'data': {'index': 1, 'vanishingPoint': [616, 137], 'camera_height': 2.3}}
        # {"code": 106, "msg": "success", "data": {
        #     "0": {"fov_V_deg": 3.6614114505309927, "fov_H_deg": 1, "vanishingPoint": [380, 236], "camera_height": 2.12,
        #           "rad_per_pixel": 0.000934721, "vanishPoint": [547, 88], "resolution": [800, 450],
        #           "imageManageArea": [[1, 237], [799, 237], [799, 449], [1, 449]],
        #           "worldManageArea": [[-887.4110622018463, 2268.0557969522274], [887.4110622018463, 2268.0557969522274],
        #                               [4.111055577195252, 10.507084969524145],
        #                               [-4.111055577195252, 10.507084969524145]]},
        #     "1": {"fov_V_deg": 4.461411450530993, "fov_H_deg": 1, "vanishingPoint": [316, 142], "camera_height": 2.12,
        #           "rad_per_pixel": 0.000221075, "vanishPoint": [547, 88], "resolution": [800, 450],
        #           "imageManageArea": [[1, 143], [799, 143], [799, 449], [1, 449]],
        #           "worldManageArea": [[-848.0807142621244, 9589.505667585807], [848.0807142621244, 9589.505667585807],
        #                               [2.7582350006738627, 31.188199102615556],
        #                               [-2.7582350006738627, 31.188199102615556]]}}}
        code = setData["code"]
        data = setData["data"]

        if code == 108:
            data = {data['index']: {"vanishPointMain":data['vanishingPoint'],"cameraHeight":data['camera_height'] }}
        else:

            data = {camId:{"vanishPointMain": v['vanishingPoint'],
                                "cameraHeight": v['camera_height'],
                                "radPerPixelFovV": v["rad_per_pixel"],
                                "resolution":self.resolution,
                                "vanishPointAuto": v["vanishPointAuto"]    }   for camId,v in data.items()}
        return data


    def setData(self, setData=None):
        try:
            with self.modifyLock:
                xypLog.xypDebug(f"{self.configName} config set start", setData)
                if setData is not None: # 设置数据
                    data = {k:v.copy() for k,v in self.data[self.configName].items()}

                    setData = self.setDataCompatible(setData)
                    '''
                    setData的格式:{camUrl:calibInfo ...}
                    calibInfo: [areaAttr0 areaAttr1 ...]
                    '''
                    for cmdId in setData:
                        data[cmdId].update(setData[cmdId])
                    self.data[self.configName] = data
                    self.saveData()
                self.publishToWeb()
                xypLog.xypDebug(f"{self.configName} config set done", setData)
        except Exception as e:
            xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
    def publishToWeb(self, client=None):
        #    {"code": 106, "msg": "success", "data": {
        #     "0": {"fov_V_deg": 3.6614114505309927, "fov_H_deg": 1, "vanishingPoint": [380, 236], "camera_height": 2.12,
        #           "rad_per_pixel": 0.000934721, "vanishPoint": [547, 88], "resolution": [800, 450],
        #           "imageManageArea": [[1, 237], [799, 237], [799, 449], [1, 449]],
        #           "worldManageArea": [[-887.4110622018463, 2268.0557969522274], [887.4110622018463, 2268.0557969522274],
        #                               [4.111055577195252, 10.507084969524145],
        #                               [-4.111055577195252, 10.507084969524145]]},
        #     "1": {"fov_V_deg": 4.461411450530993, "fov_H_deg": 1, "vanishingPoint": [316, 142], "camera_height": 2.12,
        #           "rad_per_pixel": 0.000221075, "vanishPoint": [547, 88], "resolution": [800, 450],
        #           "imageManageArea": [[1, 143], [799, 143], [799, 449], [1, 449]],
        #           "worldManageArea": [[-848.0807142621244, 9589.505667585807], [848.0807142621244, 9589.505667585807],
        #                               [2.7582350006738627, 31.188199102615556],
        #                               [-2.7582350006738627, 31.188199102615556]]}}}
        data = self.getData()
        '''web 只需要 vanishPoint cameraHeight 两个属性'''
        calibInfoSend = {k:{"vanishingPoint": v['vanishPointMain'],
                          "camera_height": v['cameraHeight'],
                          "rad_per_pixel": v["radPerPixelFovV"],
                          "resolution": v['resolution'],
                          "vanishPointAuto": v["vanishPointAuto"]} for k,v in data}
        self.webPublish.publish({"client":client,"data":{"code": 106, "msg": "success","data": calibInfoSend}})

    def saveData(self,):
        data = self.getData()
        calibInfoSave = self.data.copy()
        calibInfoSave[self.configName] = {camId: {k: v for k, v in data[camId].items() if k in self.calibBaseAttr} for camId in data}
        self.fileManage.save(calibInfoSave)

    def imageToRadar(self, imagePoint, camId):
        '''
        points:[[x,y],...] or [x,y] or [[x,y,w,h],...] or [x,y,w,h]
        '''
        data = self.getData()
        calibInfo=data[camId]
        vp = calibInfo["vanishPointAuto"]["imageToRadar"]
        h = calibInfo["cameraHeight"]
        per = calibInfo["radPerPixelFovV"]
        resolution = calibInfo["resolution"]

        imagePoint = np.array(imagePoint)
        objDim = imagePoint.ndim
        if objDim == 1:
            imagePoint = [imagePoint]

        radarPoint = []
        for pos in imagePoint:
            if len(pos) == 2: # [x,y]
                imgX, imgY = pos
            else: # [x,y,w,h]
                imgX, imgY = pos[0] + pos[2] / 2, pos[1] + pos[3]
            if (imgX,imgY) in vp:
                vpY = vp[(imgX,imgY)][1]
            else:
                vpY = calibInfo["vanishPoint"][1]

            angle = 0.5 * np.pi - per * (imgY - vpY)  # 射线与杆的夹角
            temp = np.tan(angle)
            y = h * temp  # 雷达上的y，注意不是射线的长
            # 目前假设：图像垂直中线约为雷达零点，垂直与水平每像数视场角近似相同
            angle = per * (imgX - resolution[0] / 2)  # 射线与杆的夹角
            x = y * np.tan(angle)  # 得用y计算，不同的距离夹角一样但y不同
            radarPoint.append((x, y))

        if objDim == 1: # 保留原格式
            return radarPoint[0]
        else:
            return radarPoint

    def radarToImage(self, radarPoint, camId):
        #   points:[[x,y],...] or [x,y]
        data = self.getData()
        calibInfo = data[camId]
        vp = calibInfo["vanishPointAuto"]["radarToImage"]
        h = calibInfo["cameraHeight"]
        per = calibInfo["radPerPixelFovV"]
        resolution = calibInfo["resolution"]

        radarPoint = np.array(radarPoint)
        objDim = radarPoint.ndim
        if objDim == 1:
            radarPoint = [radarPoint]

        imagePoint = []
        for pos in radarPoint:
            radarX, radarY = pos
            if (int(radarX), int(radarY)) in vp:
                vpY = vp[(int(radarX), int(radarY))][1]
            else:
                vpY = calibInfo["vanishPoint"][1]
            imgY = (0.5 * np.pi - np.arctan(radarY / h)) / per + vpY
            imgX = np.arctan(radarX / radarY) / per + resolution[0] / 2
            imagePoint.append((imgX, imgY))

        if objDim == 1:# 保留原格式
            return imagePoint[0]
        else:
            return imagePoint

    def autoCalib(self,imagePoint,radarPoint):
        vp = ""
        # 动量加权
        pass





class XypConfigCptb():
    def __init__(self,path):
        self._data={}
        self.imageAreaCptb()
        self.radarAreaCptb()
        self.calibCptb()
        checkPath(path)
        self.fileManage = JsonFileManage(path)
        self.fileManage.save(self._data)


    def imageAreaOldVersionCompatible(self, imageAreaData):  # 兼容老旧版本
        if imageAreaData is None:
            return None
        newAreaId = 0
        compatibleData = []
        if isinstance(imageAreaData, dict):
            for camId in imageAreaData:
                if camId in ["0", "1", 0, 1]:
                    for area in imageAreaData[camId]:
                        if "type" not in area:  # 记录命令来源
                            if "alarm_level" in area:
                                if int(area["alarm_level"]) > 0:
                                    area["type"] = 10
                                    area["code"] = 100
                                else:
                                    area["type"] = 0
                                    area["code"] = 110

                            elif "reserved" in area:
                                area["type"] = 0
                                area["code"] = 110

                        if "camId" not in area:
                            area["camId"] = int(camId)  # 旧版可能为字符串
                        if "userArea" not in area:
                            area["userArea"] = [i[:2] for i in area["data_list"]]
                        if "resolution" not in area:
                            area["resolution"] = [1280, 720]
                        if "enable" not in area:
                            area["enable"] = 1
                        if "areaId" not in area:
                            area["areaId"] =newAreaId
                            newAreaId += 1
                        area = {k: v for k, v in area.items() if k in  ["type", "areaId", "userArea", "camId", "resolution", "enable", "code"]
}
                        compatibleData.append(area)
        elif isinstance(imageAreaData, list):
            for area in imageAreaData:
                if "type" not in area:  # 记录命令来源
                    area["type"] = 0
                if "camId" not in area:
                    area["camId"] = 0  # 旧版可能为字符串
                if "code" not in area:
                    if area["type"] == 0:
                        area["code"] = 110
                    else:
                        area["code"] = 100
                if "userArea" not in area:
                    area["userArea"] = [i[:2] for i in area["data_list"]]
                if "resolution" not in area:
                    area["resolution"] = [1280, 720]
                if "enable" not in area:
                    area["enable"] = 1
                if "areaId" not in area:
                    area["areaId"] =  newAreaId
                    newAreaId += 1
                area = {k: v for k, v in area.items() if k in ["type", "areaId", "userArea", "camId", "resolution", "enable", "code"]}
                compatibleData.append(area)
        return compatibleData

    def imageAreaCptb(self):
        self.fileManage = JsonFileManage("./config/imageArea.json")
        setData = self.fileManage.load()
        if setData is not None:
            self._data["imageArea"] = self.imageAreaOldVersionCompatible(setData)
        else:
            # "兼容处理>>>>>>>>>>>>>>>>>>>>>>>"
            imageAreaData0 = None
            imageAreaData1 = None
            try:  # 获取老旧防区
                with open("./config/shibian_t1_17_guard.txt", "rt") as f:
                    d0 = eval(f.read())
                with open("./config/shibian_t1_64_guard.txt", "rt") as f:
                    d1 = eval(f.read())
                imageAreaData0 = {"0": d0, "1": d1}
            except:
                traceback.print_exc()
            try:  # 获取老旧屏蔽区
                imageAreaData1 = JsonFileManage("./config/block_list.json").load()
            except:
                traceback.print_exc()

            imageAreaData0["0"].extend(imageAreaData1["0"])
            imageAreaData0["1"].extend(imageAreaData1["1"])
            self._data["imageArea"] = self.imageAreaOldVersionCompatible(imageAreaData0)


    def radarAreaOldVersionCompatible(self,radarAreaData): # 兼容老旧版本
        if radarAreaData is None:
            return None
        newAreaId = 0
        if isinstance(radarAreaData, list):
            compatibleData = []
            for area in radarAreaData:
                if "enable" not in area:
                    area["enable"] = 1
                if "areaId" not in area:
                    area["areaId"] = newAreaId
                    newAreaId += 1
                if "code" not in area:
                    area["code"] = 112
                area = {k: v for k, v in area.items() if k in ["type", "areaId", "userArea", "enable", "code"]}
                compatibleData.append(area)
        else:
            compatibleData=radarAreaData
        return compatibleData

    def radarAreaCptb(self):
        self.fileManage = JsonFileManage("./config/radarArea.json")
        setData = self.fileManage.load()
        if setData is not None:
            self._data["radarArea"] = self.radarAreaOldVersionCompatible(setData)

    def calibOldVersionCompatible(self,calibInfo):
        if calibInfo is None:
            return None
        for camUrl in calibInfo:  # 转统一名称
            info = calibInfo[camUrl]
            # self.calibBaseAttr["resolution", "vanishPoint", "cameraHeight", "radPerPixelFovV"]
            if "resolution"  not in info:
                info["resolution"] = [800, 450]
            if "vanishPoint" not in info:
                info["vanishPoint"] = info["vanishingPoint"]
            if "cameraHeight" not in info:
                info["cameraHeight"] = info["camera_height"]
            if "radPerPixelFovV" not in info:
                info["radPerPixelFovV"] = info["rad_per_pixel"]
            calibInfo[camUrl] = {k: v for k, v in info.items() if k in ["resolution", "vanishPoint", "cameraHeight", "radPerPixelFovV"]}
        return calibInfo

    def calibCptb(self):
        self.fileManage = JsonFileManage("./config/calibration.json")
        setData = self.fileManage.load()
        if setData is not None:
            self._data["cameraVanish"] = self.calibOldVersionCompatible(setData)

class XypConfig():
    def __init__(self):
        # 创建配置类
        self.cameraVanishConfig=CameraVanishConfig("calibration","./config/calibration2.json")
        # self.configConfig["cameraAlarmObject"] =   CameraAlarmObjectConfig("cameraAlarmObject")
        # self.configConfig["gpioSwitch"] =          GpioSwitchConfig("gpioSwitch")
        # self.configConfig["radarScene"] =          RadarSceneConfig("radarScene")
        # self.configConfig["radarFrequency"] =      RadarFrequencyConfig("radarFrequency")
        # self.configConfig["radarSensitivity"] =    RadarSensitivityConfig("radarSensitivity")
        # self.configConfig["cameraVanish"] = CameraVanishConfig("cameraVanish")
        # self.configConfig["imageArea"] = ImageAreaConfig("imageArea", self.configConfig["cameraVanish"] )
        # self.configConfig["radarArea"] = RadarAreaConfig("radarArea", self.configConfig["cameraVanish"] )

    #     self.configConfigLock = threading.Lock()
    #
    #     configPath = "./config/xypConfigNew.json"
    #     if not os.path.exists(configPath): # 旧设备进行兼容
    #         XypConfigCptb(configPath)
    #         checkPath(configPath)
    #
    #     # 初始化数据
    #     self.fileManage = JsonFileManage(configPath)
    #     self.configSave = self.fileManage.load()
    #     if self.configSave is None:
    #         self.configSave = {}
    #
    #     for configName in self.configConfig:
    #         config = self.configConfig[configName]
    #         if configName in self.configSave:
    #             config._setData(self.configSave[configName])
    #         saveData=config._saveData()
    #         if saveData is not None: # 保存当前配置
    #             self.configSave[configName] = saveData
    #     self.fileManage.save(self.configSave)
    #
    # def sendConfig(self,configName=None, client=None):
    #     #client==None时群发
    #     #configName==None时发送所有数据
    #     with self.configConfigLock:
    #         try:
    #             if configName is not None:
    #                 config = self.configConfig[configName]
    #                 configHandle = config.apply(False)
    #                 configHandle.publishToWeb(client)
    #                 configHandle.release()
    #             else:
    #                 for config in self.configConfig.values():
    #                     configHandle = config.apply(False)
    #                     configHandle.publishToWeb(client)
    #                     configHandle.release()
    #         except Exception as e:
    #             print(f"sendConfig error  {config.configName} {e} {traceback.format_exc()}")
    #
    # def setConfig(self,configName,configValue): # 对配置的修改都应该在这里完成
    #     with self.configConfigLock:
    #         try:
    #             config = self.configConfig[configName]
    #             configHandle = config.apply(True)
    #             configHandle.setData(configValue)
    #             saveData = configHandle.saveData()
    #             if saveData is not None:
    #                 self.configSave[configName] = saveData
    #             configHandle.release()
    #             if configName == "cameraVanish":
    #                 configHandle = self.configConfig["imageArea"].apply(True)
    #                 configHandle.setData([])
    #                 saveData = configHandle.saveData()
    #                 if saveData:
    #                     self.configSave["imageArea"] = saveData
    #                 configHandle.release()
    #             self.fileManage.save(self.configSave)
    #         except Exception as e:
    #             print(f"setConfig error {configName} {e} {traceback.format_exc()}")
if __name__ == "__main__":
    pass
else:
    xypConfig =XypConfig()