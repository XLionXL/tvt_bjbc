import time
import threading
import traceback
import cv2 as cv
import numpy as np
import pickle as pk
import matplotlib.pyplot as plt
from xypTool.debug import xypLog

# 该模块参数由北京原视频调出
class ChooseArea():
    def __init__(self, frameSize=(800, 450)):
        # 定义全局变量

        self.drawing = False
        self.startX, self.startY = -1, -1
        self.mask = None
        self.areaMasks = []
        self.rectangles = []
        self.frameSize = frameSize

    def getGradient(self,image): # 获取梯度
        r,c = image.shape[:2]
        if r*c>200:
            image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
            # 计算对比度
            gradientX = cv.Sobel(image, cv.CV_64F, 1, 0, ksize=3)
            gradientY = cv.Sobel(image, cv.CV_64F, 0, 1, ksize=3)
            gradient = np.sqrt(np.square(gradientX) + np.square(gradientY))
            gradient = gradient / 4
            edge = cv.Canny(image, 15, 200)
            mask = gradient.copy()
            mask[edge<=45]=0
            display = np.concatenate([gradient.astype(np.uint8),edge,mask.astype(np.uint8)],axis=1)
            cv.namedWindow(f'gradient{len(self.rectangles)}', cv.WINDOW_NORMAL)
            cv.imshow(f'gradient{len(self.rectangles)}',display)
            self.mask = mask
    # 鼠标事件回调函数
    def drawRectangle(self,event, x, y, flags, param): # 左键绘制，右键撤销，中间结束
        if event == cv.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.startX, self.startY = x, y
        elif event == cv.EVENT_LBUTTONUP:
            self.drawing = False
            x0 = min(self.startX, x)
            y0 = min(self.startY, y)
            x1 = max(self.startX, x)
            y1 = max(self.startY, y)
            self.rectangles.append([(x0, y0), (x1,y1)])
            self.areaMasks.append(self.mask)
        elif event == cv.EVENT_MOUSEMOVE:
            if self.drawing:
                imgCopy = self.img.copy()
                for rect in self.rectangles:
                    cv.rectangle(imgCopy,rect[0],rect[1] , (0, 255, 0), 2)
                cv.rectangle(imgCopy, (self.startX, self.startY), (x, y), (0, 255, 0), 2)
                self.getGradient(self.img[min(self.startY,y): max(self.startY,y),  min(self.startX,x):max(self.startX,x)])
                cv.imshow('image', imgCopy)
        elif event == cv.EVENT_RBUTTONDOWN:
            if self.rectangles:
                self.rectangles.pop()
                self.areaMasks.pop()
                cv.destroyWindow(f'gradient{len(self.rectangles)}')
                imgCopy = self.img.copy()
                for rect in self.rectangles:
                    cv.rectangle(imgCopy, rect[0], rect[1], (0, 255, 0), 2)
                cv.imshow('image', imgCopy)
        elif event == cv.EVENT_MBUTTONUP:
            self.run =False

    def getVideoFrame(self,videoPath,frameIdx=10):
        cap = cv.VideoCapture(videoPath)
        while frameIdx:
            frameIdx -=1
            ret, frame = cap.read()
        return frame
    def choose(self,img, savePath=None):
        self.mask = None
        self.areaMasks = []
        self.rectangles = []
        self.img = cv.resize(img, self.frameSize)
        cv.namedWindow('image', cv.WINDOW_NORMAL)
        cv.imshow('image', self.img)
        cv.setMouseCallback('image', self.drawRectangle)
        self.run = True
        while  self.run:
            cv.waitKey(1)
        cv.destroyAllWindows()
        data = [[r,a] for r,a in zip(self.rectangles,self.areaMasks)]
        print("choose area:",self.rectangles)
        if savePath is not None:
            with open(savePath, 'wb') as f:
                pk.dump(data, f)
        return data

class Weather():
    def __init__(self,cap, areaPath=None,frameInterval=3,frameSize=(800, 450),debug=False):
        self.cap = cap
        self.waitTime = 1 / cap.fps * frameInterval
        self.isUseCamera = 1
        self.debug=debug
        self.frameSize=frameSize
        self.useCamera =1
        self.lastFrame =np.zeros(self.frameSize[::-1])

        self.useCameraChangeTime=time.time()
        with open(areaPath, 'rb') as f:
            self.areaMasks = pk.load(f)
        if self.debug:
            from xypTool.common import tool
            self.tool0  =tool.DynamicCanvas(0)
            self.tool1 = tool.DynamicCanvas(1)
        # self.tool2 = tool.DynamicCanvas(2)
        # self.tool3 = tool.DynamicCanvas(3)
        # self.tool4 = tool.DynamicCanvas(4)
        # self.tool5 = tool.DynamicCanvas(5)
        # self.tool6 = tool.DynamicCanvas(6)
        # self.tool7 = tool.DynamicCanvas(7)
        if self.debug:
            self.history = {}
            self.fig, (self.ax1, self.ax2) = plt.subplots(2)
            plt.pause(0.1)
        if self.debug:
            self.check()
        else:
            threading.Thread(target=self.check).start()

    def flashUseCameraState(self, useCamera, timeThreshold):
        nowTime = time.time()
        if not self.useCamera and not useCamera:  # 0->0
            self.useCameraChangeTime = nowTime
        elif self.useCamera and useCamera:  # 1->1
            self.useCameraChangeTime = nowTime
        elif not self.useCamera and useCamera:  # 0->1
            if nowTime - self.useCameraChangeTime > timeThreshold:
                self.useCamera = useCamera
                self.useCameraChangeTime = nowTime
        elif self.useCamera and not useCamera:  # 1->0
            if nowTime - self.useCameraChangeTime > timeThreshold:
                self.useCamera = useCamera
                self.useCameraChangeTime = nowTime
    def check(self):
        t = 1200 # 注意是子码流的参数
        while True:
            try:
                startTime = time.time()
                image = self.cap.getImage()
                image = cv.resize(image, self.frameSize)
                image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
                if np.array_equal(self.lastFrame,image):  # 同一张图片
                    self.flashUseCameraState(0, 10)
                    time.sleep(0.1)
                    continue
                else:
                    self.lastFrame=image

                useCamera=1
                sss=[]
                for idx, (point, mask) in enumerate(self.areaMasks):
                    x0, y0 = point[0]
                    x1, y1 = point[1]
                    img = image[y0:y1, x0:x1]
                    v=cv.Laplacian(img, cv.CV_64F).var()
                    sss.append([v,580])
                    if self.debug:
                        self.tool0.addData(v, idx)
                    if  v < 580:
                        useCamera =0
                        break
                if useCamera:
                    v=cv.Laplacian(image, cv.CV_64F).var()
                    if self.debug:
                        self.tool1.addData(v, -1)
                    sss.append([v, 800])
                    if v < 800:
                        useCamera = 0
                self.flashUseCameraState(useCamera,10)
                if self.debug:
                    for idx, (point, mask) in enumerate(self.areaMasks):
                        x0, y0 = point[0]
                        x1, y1 = point[1]
                        image = cv.rectangle(image, (x0, y0), (x1, y1),255,3)
                    image = cv.putText(image,str(self.useCamera) , (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8,
                                          (0, 0, 255), 2)
                    cv.namedWindow('image', cv.WINDOW_NORMAL)
                    cv.imshow("image", image)
                    cv.waitKey(1)

                spendTime = time.time() - startTime

                try:
                    xypLog.xypDebug(f"check {sss} {self.cap.rstp} {spendTime}  {self.waitTime} {startTime} {useCamera} {self.useCamera}")
                except:
                    xypLog.xypDebug(f"check {sss} {spendTime}  {self.waitTime} {startTime} {useCamera} {self.useCamera}")

                time.sleep(max(self.waitTime - spendTime, 0.01))
                self.lastFrame=image
                # print(spendTime,"wwwwww")
                #
                if self.debug:
                    self.tool0.display()
                    self.tool1.display()
                #
                # self.tool3.addData(x00, "色彩精度")
                # self.tool4.addData(x11, "色彩精度2")
                #
                # s1.append(sharpness(image))
                # s1=s1[-50:]
                # self.tool6.addData(np.mean(s1), "6")
                #
                #


                #
                #
                # self.tool2.display()
                # self.tool3.display()
                # self.tool4.display()
                # self.tool5.display()
                # self.tool6.display()
                #
                #





                # start = time.time()
                # score = 0
                # for idx, (point, mask) in enumerate(self.areaMasks):
                #     x0, y0 = point[0]
                #     x1, y1 = point[1]
                #     img = image[y0:y1, x0:x1]
                #     img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
                #     if self.debug:
                #         cv.namedWindow('img', cv.WINDOW_NORMAL)
                #         cv.imshow("img", img)
                #     gradientX = cv.Sobel(img, cv.CV_64F, 1, 0, ksize=3)
                #     gradientY = cv.Sobel(img, cv.CV_64F, 0, 1, ksize=3)
                #     gradient = np.sqrt(np.square(gradientX) + np.square(gradientY))
                #     gradient = gradient / 4
                #     gradient[mask < 45] = 0
                #     data = gradient[gradient != 0]
                #     if len(data):
                #         v = np.mean(data)
                #     else:
                #         v = 0
                #     if v > 15:
                #         score += 1
                #
                #     if self.debug:
                #         if idx not in self.history:
                #             self.history[idx] = [v]
                #         else:
                #             self.history[idx].append(v)
                #         self.ax1.plot(self.history[idx], label=str(idx))
                #         display = np.concatenate([gradient.astype(np.uint8), mask.astype(np.uint8)], axis=1)
                #         cv.namedWindow('display', cv.WINDOW_NORMAL)
                #         cv.imshow("display", display)
                #
                #     # display = np.concatenate([img.astype(np.uint8), mask.astype(np.uint8)], axis=1)
                #     # cv.imwrite("aadisplay.jpg", display)
                #     # time.sleep(2)
                #
                # score = score / len(self.areaMasks)
                # if self.debug:
                #     if "score" not in self.history:
                #         self.history["score"] = [self.isUseCamera]
                #     else:
                #         self.history["score"].append(self.isUseCamera)
                #         self.history["score"] = self.history["score"][-50:]
                #     self.ax2.plot(self.history["score"], label="score")
                #     plt.draw()
                #     cv.waitKey(1)
                #     self.ax1.cla()
                #     self.ax2.cla()
                # self.isUseCamera = self.isUseCamera * 0.9 + score * 0.1

                # if self.debug:
                #     print(spendTime,self.waitTime - spendTime)
            except Exception as e:
                print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")


if __name__ == "__main__":
    c=ChooseArea()
    weatherPath0="./config/weather0.pkl"
    weatherPath1="./config/weather1.pkl"
    # c.choose(c.getVideoFrame(r"C:\Users\admins\Desktop\vedio\2024-05-10_10-09-55_i000152_c0.mp4"), weatherPath0)
    c.choose(c.getVideoFrame(r"D:\降雨原视频\55.mp4") , weatherPath1)

    # from xypCaptureImage import RstpCapture
    from xypPullImage import PullStream
    # cam = RstpCapture(r"D:\新建文件夹\940北京原视频(1)\11.mp4", mode=1)
    # cam = RstpCapture("D:\降雨原视频\eee.mp4", mode=1)
    from bbbbb import VideoPlayer
    #晚上
    # cam = VideoPlayer(r"D:\降雨原视频\55.mp4", 1 * 60 + 20, 17 * 60 + 48) # 雾
    # cam = VideoPlayer(r"D:\降雨原视频\1.mp4", 8 * 60 +21 , 17 * 60 +48) # 雨
    # 白天
    # cam = VideoPlayer(r"D:\降雨原视频\1.mp4", 8 * 60 +21 , 17 * 60 +48) # 雾
    # cam = VideoPlayer(r"D:\降雨原视频\1(2).mp4", 13 * 60 + 0, 17 * 60 + 48) # 雨

    # cam = VideoPlayer(r"D:\降雨原视频\1(2).mp4", 5 * 60 + 22, 17 * 60 + 48) # 雨
    # cam = VideoPlayer(r"C:\Users\admins\Desktop\2024-05-28_03-31-30_i000028_c1.mp4", 0, 17 * 60 + 48) # 雨

    cam = VideoPlayer(r"D:\xyp\guardData\0531\2024-05-31_03-20-59_i000029_c1.mp4", 0, 17 * 60 + 48) # 雨

    weatherPath1=r"D:\xyp\guardData\0531\weather1.pkl"
    w = Weather(cam, weatherPath1, frameSize=(800, 450),debug=True)

# import os
# a=weather()
# # a.tenengrad(cv.imread(r"C:\Users\admins\Desktop\1.jpg"))
# # cv.waitKey(0)
#
# imgList = list(os.walk("../img"))[0][2]
# imgList = [os.path.abspath(os.path.join("../img",i)) for i in imgList]
# print(imgList)
# for i in imgList[6:]:
#     # i = r"D:\xyp\guardData\0422\2024-04-23_11-07-56_i000005_c1.mp4"
#     # i = r"D:\xyp\guardData\0422\2024-04-23_16-25-24_i000041_c1.mp4"
#     i=r"D:\新建文件夹\940北京原视频(1)\9.mp4"
#     # i=r"D:\新建文件夹\940北京原视频(1)\3.mp4"
#     if not i.endswith(".mp4"):
#         continue
#         a.tenengrad(cv.imread(i))
#     else:
#
#         cap = cv.VideoCapture(i)
#         num = 0
#         while True:
#             # 从视频中读取一帧
#             ret, frame = cap.read()
#             # 检查是否成功读取帧
#             if ret:
#                 a.tenengrad(frame)
#
#             else:
#                 num+=1
#                 if num>50:
#                     num=0
#                     break
# plt.show()