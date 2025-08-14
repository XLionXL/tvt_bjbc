import cv2 as cv
import datetime
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import traceback
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QDateTimeEdit, QPushButton

cv.imshow("A",np.zeros([13,13],dtype=np.uint8))

class RangeTimeDisplay(QMainWindow):
    def __init__(self,data):
        super().__init__()
        self.setWindowTitle("DateTime Range Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        layout = QVBoxLayout(self.widget)
        self.data=data


        layout.addWidget(QLabel("Start Time:"))
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setDateTime(datetime.datetime.fromtimestamp(data[0][0]))
        self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
        layout.addWidget(self.startTimeEdit)

        layout.addWidget(QLabel("End Time:"))
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setDateTime(datetime.datetime.fromtimestamp(data[-1][0]))
        self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 显示秒
        layout.addWidget(self.endTimeEdit)


        self.displayButton = QPushButton("Plot")
        self.displayButton.clicked.connect(self.display)
        layout.addWidget(self.displayButton)


        self.figName = "track"
        self.fig = plt.figure(self.figName)
        self.ax = plt.subplot()

        layout.addWidget(self.fig.canvas)



    def display(self):
        try:
            self.displayTrack(self.data)
        except:
            traceback.print_exc()

    def displayTrack(self, data):
        '''
        data: [[timeStamp,[[x,y],[x,y]]]...]
        '''

        plt.figure(self.figName)
        self.ax.cla()
        self.ax.set_xlim(-50, 50)
        self.ax.set_ylim(0, 250)
        self.timeText = self.ax.text(0.5, 1.05, '', ha='center', va='center', fontsize=12, transform=self.ax.transAxes)
        timeStamp = np.array([i[0] for i in data])

        startTime = self.startTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        endTime = self.endTimeEdit.dateTime().toMSecsSinceEpoch() / 1000
        timeZoneMask = (startTime < timeStamp) & (timeStamp < endTime)
        data = [d for d, flag in zip(data, timeZoneMask) if flag]

        dataStartTime = data[0][0]  # 数据起始时间
        startNowTime = time.time()  # 当前真实起始时间

        clearTime = [0, []]
        for d in data:
            dataTime, objs = d
            # 当前帧过去的时间 dataTime - timeStamp[0]
            # 当前帧过去的时间 (dataTime + time.time()) - (timeStamp[0] + time.time())
            waitTime = dataTime - dataStartTime  # 需要等待的时常
            while True:
                pastTime = time.time() - startNowTime
                dataNowTime = pastTime + dataStartTime  # 虚拟出的数据当前时间
                if len(clearTime[1])>5:
                    clearTime[1].pop(0).remove()
                # if dataNowTime - clearTime[0] > 5:  # 5s没有新雷达数据
                #     while clearTime[1]:
                #         clearTime[1].pop().remove()
                if pastTime >= waitTime:  # 真实时间流逝超过waitTime时
                    clearTime[0] = dataNowTime
                    for obj in objs:
                        scatter = self.ax.scatter(obj[0], obj[1], marker='.', c="r")
                        clearTime[1].append(scatter)
                    break
                self.timeText.set_text(datetime.datetime.fromtimestamp(dataNowTime).strftime("%Y-%m-%d %H:%M:%S"))
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()


class a():
    def __init__(self):
        self.track=[]
    def updateRadarRecord(self, radarData=[], nowTime=time.time()):
        # for t in self.track[::-1]:
        #     if nowTime-t["updateTime"]>8:
        #         self.track.pop(-1)
        while radarData:
            self.track= sorted(self.track,key=lambda x: x["traceLenth"],reverse=True)
            obj = radarData.pop(0)
            if obj["type"]:
                objPos = obj["position"]
                for t in self.track:
                    track = t["track"]
                    lastObjPos = track[-1]["position"]
                    pObjPos = t["predictPoint"]
                    area= t["area"]
                    pArea = t["pArea"]
                    if len(t["track"]) == 1:
                        dis = np.linalg.norm(objPos - lastObjPos)
                        if dis == 0:
                            obj = None
                            break
                        elif dis <  area:
                            t["predictPoint"] = 2 * objPos - lastObjPos
                            t["pArea"] = dis
                            t["updateTime"] = nowTime
                            t["traceLenth"] += 1
                            track.append(obj)
                            obj = None
                            break
                    else:
                        dis = np.linalg.norm(objPos - lastObjPos)
                        pDis = np.linalg.norm(objPos - pObjPos)
                        if dis == 0:
                            obj = None
                            break
                        elif pDis < pArea:
                            t["predictPoint"] = 2 * objPos - lastObjPos
                            t["pArea"] = dis
                            t["updateTime"] = nowTime
                            t["traceLenth"] += 1
                            track.append(obj)
                            obj = None
                            break
                        elif dis < area:
                            t["predictPoint"] = 2 * objPos - lastObjPos
                            t["pArea"] = dis
                            t["updateTime"] = nowTime
                            track.append(obj)
                            obj=None
                            break
                if obj is not None:
                    self.track.append({"updateTime": nowTime, "track": [obj], "predictPoint": None, "area": 3, "pArea": 3,
                                       "traceLenth": 1})
            else:
                pass

        x=0
        xx=0
        for i in self.track:
            xx=max(xx,i["traceLenth"])
        self.score=xx

        print(xx,"maxxx")
        # with self.updateRadarRecordLock:
        #     # 需要先清理，因为只有调用该函数才会清理，防止长时间不调用再调用时使用过老数据
        #     self.removeTimeOutScore(self.radarScoreRecord, nowTime)
        #     self.removeTimeOutRecord(self.radarDataRecordM, nowTime)
        #     self.removeTimeOutRecord(self.radarDataRecordS, nowTime)
        #     if len(radarData) >0 :
        #         # xypDebug("inputCamera", cameraData)
        #         # 排除在屏蔽区和无区域的点
        #         #radarData:[{'camId': 1, 'timeStamp': 1702344133.2067347,
        #         # 'position': [7.1671213996945831, 109.24137255264542],
        #         # 'xywh': [757.5, 207.5, 41.25, 70.0], 'type': 1},...]
        #         radarData = [obj for obj in radarData if  0< obj["type"] <= 101 ]
        #         # 修改self.radarDataRecord_与radarData，将radarData数据放入self.radarDataRecord_对应层并记录radarData的数据所在的层的信息
        #         self.updateLayer(self.radarDataRecordM, radarData, "M")
        #         self.updateLayer(self.radarDataRecordS, radarData, "S")
        #         # radarData:[{'camId': 1, 'timeStamp': 1702344133.2067347,
        #         # 'position': [7.1671213996945831, 109.24137255264542],
        #         # 'xywh': [757.5, 207.5, 41.25, 70.0], 'type': 1
        #         # "layerM":5,"searchSizeM":(10,10),
        #         # "layerS":5,"searchSizeS":(10,10)
        #         # },...]
        #         alarmM,alarmObjLayerInfoM= self.getRadarScore(radarData, "M")  # 是否报警，引起报警的目标信息
        #         alarmS,alarmObjLayerInfoS= self.getRadarScore(radarData, "S")  # 是否报警，引起报警的目标信息
        #
        #         if alarmM:  # 如果动态报警
        #             nowScore = 2
        #             nowAlarmObj = alarmObjLayerInfoM # 添加引起动态报警的目标信息
        #         elif alarmS:  # 如果静态报警且无动态报警
        #             nowScore = 1
        #             nowAlarmObj = alarmObjLayerInfoS  # 添加引起静态报警的目标信息
        #         else:  # 都不报警
        #             nowScore=0
        #             nowAlarmObj=[]
        #
        #         self.radarScoreRecord["timeStamp"].append(nowTime)
        #         self.radarScoreRecord["score"].append(nowScore)
        #         self.radarScoreRecord["object"].append(nowAlarmObj)
        #
        #         maxScoreIdx = np.argmax(self.radarScoreRecord["score"])
        #         maxScore = self.radarScoreRecord["score"][maxScoreIdx]
        #         maxAlarmObj = self.radarScoreRecord["object"][maxScoreIdx]
        #
        #         # 判断报警状态，认为3s内最大的分数作为当前分数
        #         nowAlarmState = self.flashAlarmState(maxScore)
        #         self.radarScoreRecord["alarmState"].append(nowAlarmState)
        #         # 假警处理
        #         self.judgeFalseAlarm(nowAlarmState, self.radarScoreRecord)
        #         # 雷达评分对外接口，外部以pop(0)读取
        #         self.radarScoreExternalInterface.append((nowTime,maxScore,maxAlarmObj,nowAlarmState))
        #         xypDebug("radarScoreRecord", self.radarScoreRecord)
        #         xypDebug("radarScoreExternalInterface", self.radarScoreExternalInterface)

def cptb(data):
    s=a()

    n=len(data)
    ioo=0
    for idx,i in enumerate(data):
        print(idx,"/",n)
        d = []
        # print(datetime.datetime.fromtimestamp(i[0]))
        for j in i[1]:
            ioo+=1
            d.append({"type":1,"position":np.array(j)})
        s.updateRadarRecord(d)
    print(ioo,"ioooo")
    n=len(s.track)
    x=[]
    for idx, t in enumerate(s.track):
        x.append(len(t["track"]))
    print(np.sum(x),"pweow")
    plt.pause(0.01)
    # plt.plot(sorted(x))
    # plt.show()
    plt.xlim(-40,40)
    plt.ylim(0, 200)
    # ttt = sorted(s.track,key=lambda x:len(x["track"]),reverse=True)
    for idx, t in enumerate(s.track):
        print(idx, "/", n)

        x = [tt["position"][0] for tt in t["track"]]
        y = [tt["position"][1] for tt in t["track"]]
        plt.xlim(-40, 40)
        plt.ylim(0, 200)
        plt.pause(0.01)
        nn=len(x)
        print(t["traceLenth"])
        # for a1,b in enumerate(zip(x,y)):
        #     print(a1, "//", nn)
        #     xx, yy=b
        #     plt.scatter(xx, yy)
        #     plt.draw()
        #     cv.waitKey(0)


        plt.scatter(x, y)
        plt.draw()
        cv.waitKey(0)
        plt.clf()

if __name__=="__main__":

    timeZone=None

    with open(r"D:\xyp\guardData\0320\b.txt") as f:
        temp=f.readlines()
    radarData=[]
    n =len("2024-03-27 14:47:43.869831 ")
    for i in temp:
        radarData.append([i[:n-1],eval(i[n:])])

    for i in radarData:
        i[0] = datetime.datetime.strptime(i[0], '%Y-%m-%d %H:%M:%S.%f').timestamp()

    cptb(radarData)

    app = QApplication(sys.argv)
    window = RangeTimeDisplay(radarData)
    window.show()
    sys.exit(app.exec_())
    plt.show()



