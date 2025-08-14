import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import os.path
import pickle as pk
import re
import sys
import time
import traceback
# from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QDateTimeEdit, QPushButton


def analyseXypLog(path,timeZone=None):
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
    scoreData ={}
    while 1:
        line = f.readline()
        if line == "" or (not line.endswith("\n")):  # \n是为了确定是完整的日志行
            break
        if "- DEBUG: " in line:
            frameTime ,info = line.split(" - DEBUG: ")
            frameTime = datetime.datetime.strptime(frameTime, "%Y-%m-%d %H:%M:%S,%f")+datetime.timedelta(seconds=1.5)
            if timeZone is not None:
                if not (timeZone[0]<frameTime and frameTime  < timeZone[1]):
                    continue
            frameTime =frameTime.time()# 不要日期
            if info.startswith("input_camera&"):
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
                infoDict = eval((info.strip()[len("input_camera&"):]))
                for i in infoDict["list"]:
                    if i["id"] == 0:
                        camera0BoxData.append([frameTime,[infoDict["stamp"], np.asarray([j["bbox"] for j in i["data"]])]])
                        camera0DtoData.append([frameTime,[infoDict["stamp"], np.asarray([j["dto"][1:3] for j in i["data"]])]])
                    if i["id"] == 1:
                        camera1BoxData.append([frameTime,[infoDict["stamp"], np.asarray([j["bbox"] for j in i["data"]]) * 0.625]])  # 1280 * 720 转化分辨率到 800 * 450
                        camera1DtoData.append([frameTime,[infoDict["stamp"], np.asarray([j["dto"][1:3] for j in i["data"]])]])
            elif info.startswith("input radar data&"):
                info = eval((info.strip()[len("input radar data&"):]))  # [time,objId0,x0,y0,objId1,x1,y1...]
                # 以前版本 input_radar[1689649199.9447095, 8312, 1.311, 72.31]
                # radarData.append([info[0], [{"id": info[i], "xy": info[i + 1:i + 3]} for i in range(len(info))[1::3]]])
                # 当前版本 input_radar[[8312, 1.311, 72.31,0,0],[8313, 1.313, 72.31,0,0]]
                if len(info[1]) != 0:
                    radarData.append([frameTime,[info[0], np.asarray([i[1:3] for i in info[1]])]])
            elif info.startswith("camera="):
                info = re.split("(=)|(,)|( )|(/)", info)
                data = []
                for i in info:
                    if (i is not None) and (i != "=" and i != "," and i != " " and i != "/" and i != ''):
                        data.append(i)
                if len(scoreData) == 0:
                    scoreData["time"] = [frameTime]
                    scoreData[data[0]] = [[float(data[1]), float(data[2])]]
                    scoreData[data[3]] = [float(data[4])]
                    scoreData[data[5]] = [[float(data[6]), float(data[7])]]
                    scoreData[data[8]] = [[float(data[9]), float(data[10])]]
                    scoreData[data[11]] = [float(data[12])]
                    scoreData[data[13]] = [float(data[14])]
                else:
                    scoreData["time"] .append(frameTime)
                    scoreData[data[0]].append([float(data[1]), float(data[2])])
                    scoreData[data[3]].append(float(data[4]))
                    scoreData[data[5]].append([float(data[6]), float(data[7])])
                    scoreData[data[8]].append([float(data[9]), float(data[10])])
                    scoreData[data[11]].append(float(data[12]))
                    scoreData[data[13]].append(float(data[14]))
    f.close()
    return radarData,camera0BoxData,camera1BoxData,camera0DtoData,camera1DtoData, scoreData


def analyseOriginLog(path,timeZone=None):
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

    camera0ConfidenceData = []
    camera1ConfidenceData = []
    radarData = []
    scoreData ={}
    while 1:
        line = f.readline()
        if line == "" or (not line.endswith("\n")):  # \n是为了确定是完整的日志行
            break
        if "- DEBUG: " in line:
            frameTime ,info = line.split(" - log_system_info.py[line:56] - DEBUG: ")
            frameTime = datetime.datetime.strptime(frameTime, "%Y-%m-%d %H:%M:%S,%f")+datetime.timedelta(seconds=1.5)
            if timeZone is not None:
                if not (timeZone[0] < frameTime and frameTime < timeZone[1]):
                    continue
            frameTimes =     frameTime.timestamp()
            # frameTime =frameTime.time()# 不要日期

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
                        camera0BoxData.append([infoDict["stamp"], np.asarray([j["bbox"] for j in i["data"]])])
                        camera0DtoData.append([infoDict["stamp"], np.asarray([j["dto"][1:3] for j in i["data"]])])
                        camera0ConfidenceData.append([infoDict["stamp"], np.asarray([j["confidence"] for j in i["data"]])])
                    if i["id"] == 1:
                        camera1BoxData.append([infoDict["stamp"], np.asarray([j["bbox"] for j in i["data"]]) * 0.625])  # 1280 * 720 转化分辨率到 800 * 450
                        camera1DtoData.append([infoDict["stamp"], np.asarray([j["dto"][1:3] for j in i["data"]])])
                        camera1ConfidenceData.append([infoDict["stamp"], np.asarray([j["confidence"] for j in i["data"]])])
            elif info.startswith("input_radar"):
                info = eval((info.strip()[len("input_radar"):]))  # [time,objId0,x0,y0,objId1,x1,y1...]
                # 以前版本 input_radar[1689649199.9447095, 8312, 1.311, 72.31]
                radarData.append([info[0], [i[1:3] for i in info[1]]])

            elif info.startswith("camera="):
                info = re.split("(=)|(,)|( )|(/)", info)
                data = []
                for i in info:
                    if (i is not None) and (i != "=" and i != "," and i != " " and i != "/" and i != ''):
                        data.append(i)
                if len(scoreData) == 0:
                    scoreData["time"] = [frameTime]
                    scoreData[data[0]] = [[float(data[1]), float(data[2])]]
                    scoreData[data[3]] = [float(data[4])]
                    scoreData[data[5]] = [[float(data[6]), float(data[7])]]
                    scoreData[data[8]] = [[float(data[9]), float(data[10])]]
                    scoreData[data[11]] = [float(data[12])]
                    scoreData[data[13]] = [float(data[14])]
                else:
                    scoreData["time"] .append(frameTime)
                    scoreData[data[0]].append([float(data[1]), float(data[2])])
                    scoreData[data[3]].append(float(data[4]))
                    scoreData[data[5]].append([float(data[6]), float(data[7])])
                    scoreData[data[8]].append([float(data[9]), float(data[10])])
                    scoreData[data[11]].append(float(data[12]))
                    scoreData[data[13]].append(float(data[14]))
    f.close()
    return radarData,camera0BoxData,camera1BoxData,camera0DtoData,camera1DtoData,camera0ConfidenceData,camera1ConfidenceData, scoreData

def analyseLog(path,timeZone):
    if "system" in os.path.basename(path):
        return  analyseOriginLog(path,timeZone)
    else:
        return  analyseXypLog(path,timeZone)


def displayOneData(data,dataName, savePath=None,timeZone=None):
    # data: [n,2->(timeStamp,[number1,number2...])]
    timeStamp = np.array([i[0] for i in data])
    if timeZone is not None:
        startTime = datetime.datetime.strptime(timeZone[0], "%Y-%m-%d %H:%M:%S").timestamp()
        endTime = datetime.datetime.strptime(timeZone[1], "%Y-%m-%d %H:%M:%S").timestamp()
        timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
    else:
        timeZoneMask = np.ones_like(timeStamp).astype(np.bool_)
    data = [d for d, flag in zip(data, timeZoneMask) if flag]

    intervalSecond = 5  # 单位间隔，5秒一个单位

    fig=plt.figure(dataName)
    ax = plt.subplot()
    # 绘制数据
    color = ["r","y","b","g","black","pink"] # 对于一帧数据应该够用了
    for dataIdx,dataFrame in enumerate(data):
        timeStamp = mdates.date2num(datetime.datetime.fromtimestamp(dataFrame[0]))
        # ax.axvline(x=timeStamp, color='gray', linestyle='-')
        minObjV = np.inf
        maxObjV = -np.inf
        for objIdx,obj in enumerate(dataFrame[1]):
            minObjV = min(minObjV,obj)
            maxObjV = max(maxObjV,obj)
            ax.scatter(timeStamp, obj, c=color[objIdx], marker='.')
        if not np.isinf(minObjV)  and not np.isinf(maxObjV) and minObjV != maxObjV:
            ax.plot([timeStamp,timeStamp],[minObjV,maxObjV], c="gray")


    # 设置x轴标签
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()
    plt.pause(0.001)
    if savePath is not None:
        with open(savePath, 'wb') as f:
            pk.dump(fig, f)



def displayScoreData(scoreData, timeZone=None):
    timeStamp = np.array(scoreData["time"])
    cameraScore = np.array(scoreData["camera"])
    radarScore = np.array(scoreData["radar"])
    jointScore = np.array(scoreData["joint"])
    moveScore = np.array(scoreData["move_coefficient"])
    block = np.array(scoreData["block"])
    alarm = np.array(scoreData["alarm"])

    if timeZone is not None:
        startTime = datetime.datetime.strptime(timeZone[0], "%Y-%m-%d %H:%M:%S").timestamp()
        endTime = datetime.datetime.strptime(timeZone[1], "%Y-%m-%d %H:%M:%S").timestamp()
        timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
    else:
        timeZoneMask = np.ones_like(timeStamp).astype(np.bool_)

    timeStamp = timeStamp[timeZoneMask]
    cameraScore = cameraScore[timeZoneMask]
    radarScore =  radarScore [timeZoneMask]
    jointScore =  jointScore [timeZoneMask]
    moveScore = moveScore[timeZoneMask]
    block = block[timeZoneMask]
    alarm = alarm[timeZoneMask]

    intervalSecond = 5   # 单位间隔，5秒一个单位

    # 将datetime对象转换为matplotlib格式, 直接用timeStamp也可以，就是可能会慢,注意不是浮点数，是datatime的时间戳：timeStamp = mdates.date2num(datetime.datetime.fromtimestamp(timeStamp))
    matplotlibTime = mdates.date2num(timeStamp)

    plt.figure("cameraScore")
    ax = plt.subplot()
    # 绘制数据
    ax.plot(matplotlibTime,cameraScore[:, 0], c="b", marker='.', label="cameraScore")
    ax.plot(matplotlibTime,cameraScore[:, 1], c="black", label="cameraThresold")
    # 设置x轴标签
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45) # 设置x轴旋转
    ax.legend()


    plt.figure("radarScore")
    ax = plt.subplot()
    ax.plot(matplotlibTime,radarScore[:, 0], c="g", marker='.', label="radarScore")
    ax.plot(matplotlibTime,radarScore[:, 1], c="black", label="radarThresold")
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()


    plt.figure("jointScore")
    ax = plt.subplot()
    ax.plot(matplotlibTime,jointScore[:, 0], c="r", marker='.', label="jointScore")
    ax.plot(matplotlibTime,jointScore[:, 1], c="black", label="jointThresold")
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()

    plt.figure("alarm")
    ax = plt.subplot()
    ax.plot(matplotlibTime,alarm, c="pink", marker='.', label="alarm")
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()

    plt.figure("moveScore")
    ax = plt.subplot()
    ax.plot(matplotlibTime,moveScore, c="b", marker='.', label="moveScore")
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()

    plt.figure("block")
    ax = plt.subplot()
    ax.plot(matplotlibTime,block, c="b", marker='.', label="block")
    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=intervalSecond))  # 每5秒一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 刻度值样式
    ax.tick_params(axis='x', rotation=45)  # 设置x轴旋转
    ax.legend()

    plt.pause(0.001)



# class RangeTimeDisplay(QMainWindow):
#     def __init__(self,data):
#         super().__init__()
#         self.setWindowTitle("DateTime Range Plotter")
#         self.setGeometry(100, 100, 800, 600)
#
#         self.widget = QWidget(self)
#         self.setCentralWidget(self.widget)
#         layout = QVBoxLayout(self.widget)
#         self.data=data
#
#
#         layout.addWidget(QLabel("Start Time:"))
#         self.startTimeEdit = QDateTimeEdit()
#         self.startTimeEdit.setDateTime(datetime.datetime.fromtimestamp(data[0][0]))
#         self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
#         layout.addWidget(self.startTimeEdit)
#
#         layout.addWidget(QLabel("End Time:"))
#         self.endTimeEdit = QDateTimeEdit()
#         self.endTimeEdit.setDateTime(datetime.datetime.fromtimestamp(data[-1][0]))
#         self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
#         layout.addWidget(self.endTimeEdit)
#
#
#         self.displayButton = QPushButton("Plot")
#         self.displayButton.clicked.connect(self.display)
#         layout.addWidget(self.displayButton)
#
#
#         self.figName = "track"
#         self.fig = plt.figure(self.figName)
#         self.ax = plt.subplot()
#
#         layout.addWidget(self.fig.canvas)
#
#
#
#     def display(self):
#         try:
#             self.displayTrack(self.data)
#         except:
#             traceback.print_exc()
#
#     def displayTrack(self, data):
#         '''
#         data: [[timeStamp,[[x,y],[x,y]]]...]
#         '''
#
#         plt.figure(self.figName)
#         self.ax.cla()
#         self.ax.set_xlim(-50, 50)
#         self.ax.set_ylim(0, 250)
#         self.timeText = self.ax.text(0.5, 1.05, '', ha='center', va='center', fontsize=12, transform=self.ax.transAxes)
#         timeStamp = np.array([i[0] for i in data])
#
#         startTime = self.startTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
#         endTime = self.endTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
#         timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
#         data = [d for d, flag in zip(data, timeZoneMask) if flag]
#
#         dataStartTime = data[0][0]  # 数据起始时间
#         startNowTime = time.time()  # 当前真实起始时间
#
#         clearTime = [0, []]
#         for d in data:
#             dataTime, objs = d
#             # 当前帧过去的时间 dataTime - timeStamp[0]
#             # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
#             waitTime = dataTime - dataStartTime  # 需要等待的时常
#             while True:
#                 pastTime = time.time() - startNowTime
#                 dataNowTime = pastTime + dataStartTime  # 虚拟出的数据当前时间
#                 if dataNowTime - clearTime[0] > 5:  # 5s没有新雷达数据
#                     while clearTime[1]:
#                         clearTime[1].pop().remove()
#                 if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
#                     clearTime[0] = dataNowTime
#                     for obj in objs:
#                         scatter = self.ax.scatter(obj[0], obj[1], marker='.', c="r")
#                         clearTime[1].append(scatter)
#                     break
#                 self.timeText.set_text(datetime.datetime.fromtimestamp(dataNowTime).strftime("%Y-%m-%d %H:%M:%S"))
#                 self.fig.canvas.draw()
#                 self.fig.canvas.flush_events()









if __name__=="__main__":
    defences = [[[3.346510731996906, 30.7714540514303], [4.632277640767955, 32.02100660197035], [4.840441775504251, 12.882338381449475], [4.063004336968363, 0], [3.0696532851801375, 0]],
                [[-2.8757163321996284, 0], [-1.919746167732102, 49.008879105782015], [3.230273626667291, 47.85676775561873], [2.8850532601240477, 0]],
                [[-2.3631315517521334, 0], [-0.8840850008102308, 101.0964076641026], [5.338795073696986, 98.18049041346012], [4.465843154076969, 68.84592159518336], [4.1915511645340695, 0]]]

    timeZone=None
    # timeZone=('2023-08-21 15:23:20','2023-08-21 15:23:40')
    # timeZone=('2023-10-31 09:40:49','2023-10-31 09:45:49')
    s=time.time()

    while (1):
        path = input("input path: ")
        path = path.replace("\"","")
        radarData,camera0BoxData,camera1BoxData,camera0DtoData,camera1DtoData, camera0ConfidenceData,camera1ConfidenceData,scoreData = \
            analyseLog(path,timeZone)

        # displayOneData(camera0ConfidenceData,"camera0ConfidenceData","./camera0ConfidenceData.matplotlib")

        # with open('./camera0ConfidenceData.matplotlib', 'rb') as f:
        #     fig = pk.load(f)
        #
        #
        # fig.show()
        # plt.show()
        # print(time.time()-s)
        displayScoreData(scoreData,timeZone =timeZone)

        # displayScoreData(scoreData, timeZone=timeZone)
        # print(time.time()-s)

        # app = QApplication(sys.argv)
        # window = RangeTimeDisplay(radarData)
        # window.show()
        # sys.exit(app.exec_())
        plt.show()


