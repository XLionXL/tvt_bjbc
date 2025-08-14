import numpy as np
import threading
import time

from xypRemoteTool import SSH


# SSH连接参数
class RemoteCap():
    def __init__(self):
        # RTSP流地址
        rtsp_url ="rtsp://admin:Admin123@192.168.8.11:8554/0"
        # '-vf', 'fps=10,scale=400:600',  # 设定帧率为每秒 10 帧并指定图片大小为 400x600

        ssh = SSH("10.8.2.14", "22", "tvt", "TDDPc5kc4WnYcy", 1)
        self.h=1080//3
        self.w=1920//3
        print( self.h, self.w)
        self.size=self.h*self.w*3
        # ffmpeg -i your_stream_url_here -c copy -f mpegts pipe:1
        self.fps=25
        s=f"ffmpeg -rtsp_transport tcp -i {rtsp_url} -vf fps={self.fps},scale={ self.w}:{ self.h} -f image2pipe -pix_fmt bgr24 -vcodec rawvideo -"
        stdin, stdout, stderr =ssh.executeCommand(s)
        self.stdout=stdout
        threading.Thread(target=self.capImage).start()
        self.image=None
        while self.image is None:
            time.sleep(1)
    def capImage(self):
        # 在远程主机上执行命令以获取RTSP流

        # 使用OpenCV显示RTSP流
        while True:
            # frame_length = int.from_bytes(stdout.read(4), byteorder='little')
            # if not frame_length:
            #     break
            frame_data = self.stdout.read(self.size)
            if frame_data:
                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(self.h,self.w,3)
                # print(frame)
                self.image=frame
            time.sleep(1 / self.fps)
    def getImage(self):
        img =self.image
        return img
# RemoteCap()