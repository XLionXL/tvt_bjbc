import time
import datetime
import threading
import traceback
import cv2 as cv
import numpy as np
from xypTool.debug import xypLog

class RstpCapture():
    def __init__(self,rstp,timeout=10,test=False):
        self.rstp = rstp
        self.test = test
        self.timeout = timeout  # 时间在某些系统不一定可靠
        self.fps,self.w,self.h=self.getRstpArgs()
        self.state = False
        self.image = np.zeros((self.h, self.w, 2), dtype=np.uint8)
        self.lastImage = np.zeros((self.h, self.w, 2), dtype=np.uint8)
        threading.Thread(target=self.gstreamerCapImage).start()
        threading.Thread(target=self.monitor).start()
    def getRstpArgs(self):
        cap = cv.VideoCapture(self.rstp)
        fps = int(cap.get(cv.CAP_PROP_FPS))
        w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return fps,w,h

    def monitor(self):
        # 检测超过10s拉的帧都是同一帧（同时也兼顾长时间未拉到图片），重启
        lastTime = time.monotonic()
        while True:
            try:
                if self.state: # 正常运行中
                    if np.array_equal(self.image, self.lastImage): # 完全相等
                        if time.monotonic()-lastTime>self.timeout: # 10s同帧
                            lastTime = time.monotonic() # 刷新时间，防止频繁重启
                            self.state=False # 重启
                    else:
                        lastTime = time.monotonic() # 刷新时间
                        self.lastImage = self.image # 赋值
                time.sleep(1)
            except Exception as e:
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")

    def gstreamerCapImage(self):
        # nano下极低延迟cou占用拉流，启用英伟达硬件加速
        # 不能加载bgr的，建议bgr在调用时操作，否则会延时，appsink drop=1 这边处理慢时丢弃其他的，sync=false，不启用音频同步等功能
        gst = f"rtspsrc location={self.rstp} latency={10} ! rtph264depay ! h264parse ! nvv4l2decoder !nvvidconv ! videoconvert ! video/x-raw,format=YUY2 ! appsink drop=1 sync=false"
        while True:
            try:
                cap = cv.VideoCapture(gst, cv.CAP_GSTREAMER)
                self.state = True
                while True:
                    ret, frame = cap.read()
                    if ret:
                        self.image = frame  # yuy2
                    if not self.state:
                        cap.release()
                        raise
            except Exception as e:
                xypLog.xypError(f"camera gstreamer error:{self.rstp} exception:{e}\ntraceback:{traceback.format_exc()}")

    def getImage(self):
        img = cv.cvtColor(self.image, cv.COLOR_YUV2BGR_YUY2)
        if self.test: # 测试延时
            currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            img=cv.putText(img, currentTime, (0, self.h//2) , cv.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        return img


if __name__ == "__main__":
    cam = RstpCapture(r'rtsp://admin:Admin123@192.168.8.12:8554/1',test=True)
    from xypPushImage import PushStream
    pushStream = PushStream(ip='0.0.0.0', port=8093, mode=0)
    while 1:
        img = cam.getImage()
        pushStream.task.append(img)
        time.sleep(1/cam.fps)
