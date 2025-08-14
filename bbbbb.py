import cv2 as cv
import time
import threading
class VideoPlayer():

    def __init__(self,videoPath, startTime, endTime,normalSpeed=True, fps=None):
        self.cap = cv.VideoCapture(videoPath)
        self.videoPath=videoPath
        # 获取视频帧率
        if fps is None:
            fps = self.cap.get(cv.CAP_PROP_FPS)
        self.fps = fps
        # 计算开始和结束帧的索引
        self.startFrame = int(startTime * fps)
        self.endFrame = min(int(endTime * fps), int(self.cap.get(cv.CAP_PROP_FRAME_COUNT)))#和总帧数比较
        # 设置当前帧为开始帧
        self.cap.set(cv.CAP_PROP_POS_FRAMES, self.startFrame)

        self.image=None
        self.normalSpeed=normalSpeed
        threading.Thread(target=self.play).start()
    def play(self):
        while True:
            self.cap = cv.VideoCapture(self.videoPath)
            self.cap.set(cv.CAP_PROP_POS_FRAMES, self.startFrame)

            while True:
                ret, frame = self.cap.read()
                if  ret:
                    self.image=frame
                    # cv.namedWindow('image', cv.WINDOW_NORMAL)
                    # cv.imshow('image', frame)
                    # cv.waitKey(1)
                    if self.normalSpeed:
                        time.sleep(1/self.fps)
                # 如果到达了结束帧，退出循环
                if  self.cap.get(cv.CAP_PROP_POS_FRAMES) >=  self.endFrame:
                    break
        # 释放视频对象
        self.cap.release()

    def getImage(self):
        while True:
            if self.image is not None:
                image = self.image
                return image
            else:
                time.sleep(0.1)
# video_path = r"D:\xyp\a\bice\video\3\part_1.mp4"
# VideoPlayer(video_path, 0, 100)


