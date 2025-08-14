import time
import datetime
import cv2 as cv
import traceback
import threading
import numpy as np
from xypTool.debug import xypLog
import matplotlib.pyplot as plt
from scipy.stats import norm

class aaa():
    def __init__(self,threshold):
        self.threshold = threshold
        self.resultHistory = [0]
        self.result =0
        self.mean = 0
        self.n = 0
        self.state = 0
        self.changeTime =  time.monotonic()
    def flashState(self, state, timeThreshold):
        nowTime = time.monotonic()
        if not self.state and not state:  # 0->0
            self.changeTime = nowTime
        elif self.state and state:  # 1->1
            self.changeTime = nowTime
        elif not self.state and state:  # 0->1
            if nowTime - self.changeTime > timeThreshold:
                self.state = state
                self.changeTime = nowTime
        elif self.state and not state:  # 1->0
            if nowTime - self.changeTime > timeThreshold:
                self.state = state
                self.changeTime = nowTime
    def updateState(self,v):
        self.n += 1
        delta = float(v) - self.mean
        newMean = self.mean + delta * (1 /  self.n)
        state = self.state
        self.flashState((newMean-self.mean)>0,3)
        if self.state != state: # 均值连续往一个方向变化n秒
            self.mean = v
            self.n = 1 # 重新计算均值
        else:
            self.mean = newMean
        if self.mean < self.threshold:
            self.resultHistory.append(1)
            self.resultHistory =  self.resultHistory[-3:]
            print(self.resultHistory,self.result)
            if np.sum(self.resultHistory)==len(self.resultHistory):
                self.result=1
        else:
            self.resultHistory.append(0)
            self.resultHistory = self.resultHistory[-3:]
            if np.sum(self.resultHistory) ==0 :
                self.result=0

# 该模块参数由北京原视频调出
class CalDiff():
    def __init__(self, cap,  frameInterval=5, frameSize=(800, 450),debug=False):
        self.cap = cap

        self.aa = aaa(1500000)
        self.debug = debug
        self.frameSize = frameSize
        self.kernel = np.ones((3, 3), np.uint8)
        self.waitTime = 1 / cap.fps * frameInterval # 5帧
        if self.debug:
            self.history = {}
            self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3)
            plt.pause(0.1)

        self.sameNum = 3  # 相同3次为噪声
        self.saveNum = 8

        self.lastFrame  = np.zeros(self.frameSize[::-1], dtype=np.float64)
        self.nowDiff = None




        self.useDiffChangeTime=time.monotonic()

        self.diffNum = [self.lastFrame ] * self.saveNum  # diff 合集
        self.diff=[ self.lastFrame.astype(np.uint8), self.diffNum ]
        self.staticDiff = [self.lastFrame ] * self.saveNum  # diff 合集
        self.clear = [0] * self.saveNum

        self.changeV = 0
        self.useDiff = self.aa.result
        threading.Thread(target=self.calDiff).start()
        if self.debug:
            self.dealDiff()
        threading.Thread(target=self.dealDiff).start()


    def calDiff(self, ):
        gmm = cv.createBackgroundSubtractorMOG2(detectShadows=False,varThreshold=10,history=80)
        self.s=[]
        while True:
            try:
                startTime = time.monotonic()
                img = cv.resize(self.cap.getImage(), self.frameSize)
                frame = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
                if np.array_equal(self.lastFrame,frame):  # 同一张图片
                    self.nowDiff = None
                    time.sleep(0.1)
                    continue
                if self.debug:
                    cv.namedWindow('frame', cv.WINDOW_NORMAL)
                    frameC=frame.copy()
                    frameC=cv.putText(frameC, str(self.useDiff), (10, 35), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 5)
                    cv.imshow("frame", frameC)

                # frame = cv.GaussianBlur(frame, (0, 0),3)
                # frame = cv.GaussianBlur(frame, (3, 3), 0)
                if self.debug:
                    cv.namedWindow('blurFrame', cv.WINDOW_NORMAL)
                    cv.imshow("blurFrame", frame)


                diff= gmm.apply(frame)#, learningRate=0
                if self.debug:
                    cv.namedWindow('diff', cv.WINDOW_NORMAL)
                    cv.imshow("diff", diff)
                    cv.waitKey(1)
                diff = cv.medianBlur(diff, 5)
                # diff = cv.medianBlur(diff, 5)
                # diff = cv.erode(diff, self.kernel, iterations=2)
                # diff = cv.dilate(diff, self.kernel, iterations=2)
                self.nowDiff= diff.astype(np.float64)
                choose = (130,200)
                if self.debug:
                    diff2=diff.copy()
                    v = np.sum(diff2[choose[0]:choose[1]],axis=0)
                    cv.rectangle(diff2, (0, choose[0]), (799, choose[1]), (255, 0, 255), 5)
                    cv.namedWindow('diff2', cv.WINDOW_NORMAL)
                    cv.imshow("diff2", diff2)
                    cv.waitKey(1)
                    self.s.append(v)











                self.changeV = np.sum(cv.absdiff(self.lastFrame.astype(np.uint8), frame))
                self.lastFrame = frame
                spendTime = time.monotonic() - startTime
                time.sleep(max(self.waitTime - spendTime, 0))
            except Exception as e:
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
    def flashUseDiffState(self,useDiff, timeThreshold):
        nowTime = time.monotonic()
        if not self.useDiff and not useDiff:  # 0->0
            self.useDiffChangeTime = nowTime
        elif self.useDiff and useDiff:  # 1->1
            self.useDiffChangeTime = nowTime
        elif not self.useDiff and useDiff:  # 0->1
            if nowTime - self.useDiffChangeTime > timeThreshold:
                self.useDiff = useDiff
                self.useDiffChangeTime = nowTime
        elif self.useDiff and not useDiff:  # 1->0
            if nowTime - self.useDiffChangeTime > timeThreshold:
                self.useDiff = useDiff
                self.useDiffChangeTime = nowTime

    def dealDiff(self, ):

        s = []
        s2 = []
        s3 = []
        while True:
            try:
                diff = self.nowDiff  # , learningRate=0
                changeV =self.changeV

                if self.debug:
                    s.append(self.changeV)
                    s2.append(self.aa.mean)
                    s3.append(self.aa.state)
                    self.ax1.plot(s,c="b")
                    print(self.aa.mean)
                    self.ax1.plot(s2,c="r")
                    self.ax2.plot(s3, c="g")
                    if len(self.s):
                        v = self.s.pop(-1)
                        # self.ax3.plot(v)

                        x = np.arange(0, 800)  # x轴的索引值
                        # 生成高斯分布数据
                        y = norm.pdf(x, np.mean(v),  np.std(v))
                        self.ax3.set_ylim(0,0.02)
                        self.ax3.plot(y)

                    plt.pause(0.01)
                    self.ax1.cla()
                    self.ax3.cla()
                try:
                    xypLog.xypDebug(f"isUseDiff:{self.cap.rstp,self.useDiff,changeV<1500000,changeV,self.aa.state,self.aa.mean,self.aa.result,}")
                except:
                    xypLog.xypDebug(f"isUseDiff:{self.useDiff,changeV<1500000,changeV,}")

                if diff is not None:
                    startTime = time.monotonic()
                    if self.debug:
                        cv.namedWindow('diff__', cv.WINDOW_NORMAL)
                        cv.imshow("diff__", diff.astype(np.uint8))

                    if self.debug:
                        cv.namedWindow('diff', cv.WINDOW_NORMAL)
                        cv.imshow("diff", diff.astype(np.uint8))



                    self.diffNum.append(diff)
                    self.diffNum = self.diffNum[-self.saveNum:]

                    diffTemp = np.sum(self.diffNum[-self.saveNum:-self.sameNum], axis=0)
                    diff = np.sum(self.diffNum[-self.sameNum:], axis=0)
                    diffNum = diffTemp + diff

                    self.staticDiff.append( (diff >= self.sameNum * 255).astype(np.uint8))
                    self.staticDiff = self.staticDiff[-self.saveNum:]
                    staticDiff = np.sum(self.staticDiff, axis=0)

                    diffNum[staticDiff>0] = 0
                    diffNum[diffNum != 0] = 1  # 注意不是~staticDiff

                    if self.debug:
                        cv.namedWindow(f'moveDiffNew', cv.WINDOW_NORMAL)
                        cv.imshow(f"moveDiffNew", diffNum)
                        cv.waitKey(1)

                    # diff = cv.erode(diff, self.kernel, iterations=1)
                    # diff = cv.dilate(diff, self.kernel, iterations=2)
                    diffNum = cv.medianBlur(diffNum.astype(np.uint8), 5)
                    # diff = cv.erode(diff, self.kernel, iterations=1)

                    self.aa.updateState(changeV) # 正常数>=5个记为一次1
                    self.useDiff=self.aa.result
                    if self.debug:
                        imgg = np.concatenate(self.diffNum,axis=1).astype(np.uint8)
                        for x in range(0, imgg.shape[1], self.diffNum[0].shape[1]):
                            imgg = cv.line(imgg, (x, 0), (x, imgg.shape[0]), (255, 255, 255), 20)
                        cv.namedWindow(f'imgg', cv.WINDOW_NORMAL)
                        cv.imshow(f"imgg", imgg)
                    self.diff = [diffNum,self.diffNum.copy()]
                    # print(np.sum(self.clear))
                    if self.debug:
                        # print(self.useDiff)
                    #     # img=np.zeros_like(img)
                    #     img=self.nowImg
                    #     cv.imshow(f"mergeDiff0", cv.addWeighted(img, 0.5, cv.cvtColor(self.diff.astype(np.uint8) * 255,
                    #                                                                   cv.COLOR_GRAY2BGR), 0.5, 0))
                    #
                        cv.waitKey(1)
                    spendTime = time.monotonic() - startTime
                    time.sleep(max(0.5 - spendTime,0))
                else:
                    self.aa.updateState(changeV)  # 正常数>=5个记为一次1
                    self.useDiff=self.aa.result
                    time.sleep(1/self.cap.fps)
            except Exception as e:
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")

    def getDiff(self):
        diff = self.diff  # diff值只有0和1
        return diff

def aa():
    while True:
        diff =( a.getDiff()*255).astype(np.uint8)
        pushStream.task.append(cv.resize(diff, (0, 0), fx=0.5, fy=0.5))
import os
import glob
class readData():
    def __init__(self):
        self.fps=1

        def get_image_files(directory):
            # 使用 glob 模块获取指定目录下所有图片文件的路径
            image_files = glob.glob(os.path.join(directory, '*.jpg')) + glob.glob(
                os.path.join(directory, '*.jpeg')) + glob.glob(os.path.join(directory, '*.png')) + glob.glob(
                os.path.join(directory, '*.gif'))
            # 排序图片文件列表
            sorted_image_files = sorted(image_files)
            return sorted_image_files

        # 指定目录
        directory_path =r"D:\xyp\a\bice\guard_tvt\diffData\2"
        # 获取图片文件列表
        image_files = get_image_files(directory_path)

        # 打印排序后的图片文件列表
        self.s=[]
        for image_file in image_files:
            print(image_file)
            self.s.append(   cv.imread(image_file))
    def getImage(self):
        print(len(self.s))
        return self.s.pop(0)


if __name__ == "__main__":
    from bbbbb import VideoPlayer
    from xypCaptureImage import RstpCapture
    from xypPullImage import PullStream