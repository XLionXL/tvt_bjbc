import sys
import time
import datetime
import traceback
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QDateTimeEdit, QPushButton,QLineEdit
import threading

def analyseXypLog(path, timeZone=None):
    # 解析日志内容
    '''
    :param path: 日志位置
    :return:返回数据格式为[[timeStamp0,[obj0,obj1...]],...]
    '''
    with open(path, "r",encoding='utf-8') as f:
        radarData = []
        radarStr = "radar data&"
        cameraData = {0:[],1:[]}
        cameraStr= "camera data&"
        while 1:
            line = f.readline()
            if line == "" or (not line.endswith("\n")):  # \n是为了确定是完整的日志行
                break
            if "- DEBUG: " in line:
                frameTime ,info = line.split(" - DEBUG: ")
                frameTime = datetime.datetime.strptime(frameTime, "%Y-%m-%d %H:%M:%S,%f").timestamp() # 时间戳


                if timeZone is not None and  (not (timeZone[0]<frameTime and frameTime  < timeZone[1])):
                    continue
                elif info.startswith(radarStr):
                    info = eval((info.strip()[len(radarStr):]))
                    radarData.append([frameTime, [i[:3] for i in info]])

                elif info.startswith(cameraStr):
                    info = eval((info.strip()[len(cameraStr):]))
                    for camInfo in info:
                        camId = camInfo["id"]
                        cameraData[camId].append([frameTime,[i['bbox'] for i in camInfo["data"]]])
        return radarData,cameraData

def generateColors(n):
    colors = []
    cmap = plt.get_cmap('tab20')  # 使用tab10色板，包含10种不同的颜色
    for i in range(n):
        color = cmap(i)
        colors.append(color)
    return colors

class RangeTimeDisplay(QMainWindow):
    def __init__(self,logPath=None):
        super().__init__()
        self.logPath =logPath
        self.setWindowTitle("DateTime Range Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        layout = QVBoxLayout(self.widget)


        layout.addWidget(QLabel("Log Path:"))

        self.inputLineEdit = QLineEdit()
        self.inputText = ''
        layout.addWidget(self.inputLineEdit)

        layout.addWidget(QLabel("Start Time:"))
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
        layout.addWidget(self.startTimeEdit)

        layout.addWidget(QLabel("End Time:"))
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
        layout.addWidget(self.endTimeEdit)


        self.displayButton = QPushButton("Plot")
        self.displayButton.clicked.connect(self.display)
        layout.addWidget(self.displayButton)


        self.radarFigName = "track"
        self.radarFig = plt.figure(self.radarFigName)
        self.radarAx = plt.subplot()
        layout.addWidget(self.radarFig.canvas,1)

        # self.boxFigName = "box"
        # self.boxFig = plt.figure(self.boxFigName)
        # self.boxAx = plt.subplot()
        # layout.addWidget(self.boxFig.canvas,1)

    def display(self):
        try:
            if self.logPath is None:
                inputText = self.inputLineEdit.text()
            else:
                inputText=self.logPath
            if inputText !=   self.inputText:
                self.inputText=inputText
                self.radarData,self.cameraData = analyseXypLog(inputText)
                self.startTimeEdit.setDateTime(datetime.datetime.fromtimestamp(self.radarData[0][0]))
                self.endTimeEdit.setDateTime(datetime.datetime.fromtimestamp(self.radarData[-1][0]))

            self.displayTrack(self.radarData)
            # self.displayBox(self.cameraData)
        except:
            traceback.print_exc()


    def displayTrack(self, data):
        '''
        data: [[timeStamp,[[x,y],[x,y]]]...]
        '''

        plt.figure(self.radarFigName)
        self.radarAx.cla()
        self.radarAx.set_xlim(-50, 50)
        self.radarAx.set_ylim(0, 250)
        self.timeText = self.radarAx.text(0.5, 1.05, '', ha='center', va='center', fontsize=12, transform=self.radarAx.transAxes)
        timeStamp = np.array([i[0] for i in data])
        colorList = generateColors(20)
        startTime = self.startTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        endTime = self.endTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
        data = [d for d, flag in zip(data, timeZoneMask) if flag]

        dataStartTime = data[0][0]  # 数据起始时间
        startNowTime = time.time()  # 当前真实起始时间

        clearTime = {}
        for d in data:
            dataTime, objs = d
            # 当前帧过去的时间 dataTime - timeStamp[0]
            # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
            waitTime = dataTime - dataStartTime  # 需要等待的时常
            while True:
                pastTime = time.time() - startNowTime
                dataNowTime = pastTime + dataStartTime  # 虚拟出的数据当前时间
                for k in list(clearTime.keys()):
                    radarTrack = clearTime[k]
                    if dataNowTime - radarTrack["flashTime"] > 5:  # 5s没有新雷达数据
                        track = radarTrack["track"]
                        while track:
                            track.pop().remove()
                        colorList.append(radarTrack["color"])
                        clearTime.pop(k)
                if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
                    for obj in objs:
                        objId ,x,y = obj
                        if objId not in clearTime:
                            color = colorList.pop()
                        else:
                            color = clearTime[objId]["color"]
                        scatter = self.radarAx.scatter(x,y, marker='.', color=color)
                        if objId not in clearTime:
                            clearTime[objId] ={"flashTime":dataNowTime,"track":[scatter], "color":color}
                        else:
                            clearTime[objId]["flashTime"] = dataNowTime
                            clearTime[objId]["track"].append(scatter)
                    break
                self.timeText.set_text(datetime.datetime.fromtimestamp(dataNowTime).strftime("%Y-%m-%d %H:%M:%S"))
                self.radarFig.canvas.draw()
                self.radarFig.canvas.flush_events()

    def displayBox(self, data):
        '''
        data: [[timeStamp,[[x,y],[x,y]]]...]
        '''

        plt.figure(self.boxFigName)
        self.boxAx.cla()
        self.boxAx.set_xlim(0, 800)
        self.boxAx.set_ylim(0, 450)
        self.boxAx.invert_yaxis()

        self.timeText = self.boxAx.text(0.5, 1.05, '', ha='center', va='center', fontsize=12,
                                          transform=self.boxAx.transAxes)
        data=data[1]
        timeStamp = np.array([i[0] for i in data])
        colorList = generateColors(20)
        startTime = self.startTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        endTime = self.endTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
        data = [d for d, flag in zip(data, timeZoneMask) if flag]

        dataStartTime = data[0][0]  # 数据起始时间
        startNowTime = time.time()  # 当前真实起始时间

        clearTime = []
        for d in data:
            dataTime, objs = d
            # 当前帧过去的时间 dataTime - timeStamp[0]
            # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
            waitTime = dataTime - dataStartTime  # 需要等待的时常
            while True:
                pastTime = time.time() - startNowTime
                dataNowTime = pastTime + dataStartTime  # 虚拟出的数据当前时间
                clearTimeCache = []
                for c in clearTime:
                    if dataNowTime - c[0] > 5:  # 5s没有新雷达数据
                        c[1].remove()
                    else:
                        clearTimeCache.append(c)
                clearTime =clearTimeCache


                if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
                    for obj in objs:
                        x, y,w,h = obj
                        rectangle = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor='red',
                                                      facecolor='none')
                        self.boxAx.add_patch(rectangle)
                        clearTime.append([dataNowTime,rectangle])
                    break
                self.timeText.set_text(datetime.datetime.fromtimestamp(dataNowTime).strftime("%Y-%m-%d %H:%M:%S"))
                self.boxFig.canvas.draw()
                self.boxFig.canvas.flush_events()


if __name__=="__main__":


    app = QApplication(sys.argv)
    window = RangeTimeDisplay(r"D:\xyp\guardData\0511\2024-05-10 17-59.log.2024-05-10_21")
    window.show()
    sys.exit(app.exec_())



