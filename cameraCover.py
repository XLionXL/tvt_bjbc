import cv2
import numpy as np
import threading
import time
from datetime import datetime, timedelta


# 摄像头遮蔽检测
class CameracCover(object):
    def __init__(self):
        self.isCover = False

    def ret_results(self):
        return self.isCover

    # 摄像头遮蔽检测
    def cameracCover(self, urllist):
        """
        遮挡检测，
        :param urllist:
        :return:
        """
        # t = threading.currentThread()
        # print('Thread id : %d' % t.ident)
        for url in urllist:
            # print(url)
            # url = 'rtsp://admin:~Admin123@10.8.4.131/video1'
            cap = cv2.VideoCapture(url)
            if(cap.isOpened()):
                # cap = cv2.VideoCapture(0)
                # 图像切分的尺寸 (3*3)可以自己设置
                cut_size = 3

                # while(1):
                # 读取帧
                _, frame = cap.read()
                # cv2.imshow('frame', frame)
                # 灰度图
                grey_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # cv2.imshow('grey_img', grey_img)
                # 拉普拉斯变换
                gray_lap = cv2.Laplacian(grey_img, cv2.CV_64F)
                # cv2.imshow('gray_lap', gray_lap)

                grey_img_shape = grey_img.shape
                height, width = grey_img_shape[0], grey_img_shape[1]
                height_div = height // cut_size
                width_div = width // cut_size

                # 循环的尺寸，这样循环就不会取到边界
                range_height_size = height_div * cut_size
                range_width_size = width_div * cut_size

                # 切分循环
                for i in range(0, range_height_size, height_div):
                    for j in range(0, range_width_size, width_div):
                        # 获取当前区域的灰度图像素
                        subimg = grey_img[j: j + width_div, i: i + height_div]

                        # 获取当前区域 拉普拉斯算子 的边缘信息像素信息
                        sublap = gray_lap[j: j + width_div, i: i + height_div]

                        # 获取标准差
                        stddev_g = np.std(subimg)
                        stddev_l = np.std(sublap)
                        # if stddev_g < 25 and stddev_l < 10:
                        if stddev_g < 18 and stddev_l < 10:
                            #print("图像遮挡")
                            self.isCover = True
                        else:
                            self.isCover = False
                # # k = cv2.waitKey(5) & 0xFF
                # # if k == 27:
                # # 	break
                cap.release()
            else:
                cap.release()
        # cv2.destroyAllWindows()
        # return self.isCover


    # 间隔时间执行函数
    def runTask(self, func, urlList, day=0, hour=0, min=0, second=0):
        # 初始化时间
        now = datetime.now()
        strnow = now.strftime('%Y-%m-%d %H:%M:%S')
        # print("now:", strnow)
        # 下次运行时
        period = timedelta(days=day, hours=hour, minutes=min, seconds=second)
        next_time = now + period
        strnext_time = next_time.strftime('%Y-%m-%d %H:%M:%S')
        # print("next run:", strnext_time)
        while True:
            # 获取系统当前时间
            iter_now = datetime.now()
            iter_now_time = iter_now.strftime('%Y-%m-%d %H:%M:%S')
            if str(iter_now_time) >= str(strnext_time):
                # 开始时间
                # print("start work: %s" % iter_now_time)
                # 调用任务函数
                func(urlList)
                # print(func(urlList))
                # print("task done.")
                # 获得下一次迭代的时间
                iter_time = iter_now + period
                strnext_time = iter_time.strftime('%Y-%m-%d %H:%M:%S')
                # print("next_iter: %s" % strnext_time)
                # 继续下一个迭代
                continue


if __name__ == '__main__':
    cac = CameracCover()
    try:
        threads = threading.Thread(target=cac.runTask, args=(cac.cameracCover, ['rtsp://admin:~Admin123@10.8.4.131/video1','rtsp://admin:~Admin123@10.8.4.131/video1'], 0, 0, 0, 0.05))
        threads.setDaemon(True)
        threads.start()
    except:
        print("Error: 无法启动线程")
    print(cac.ret_results())
    time.sleep(10)
    print(cac.ret_results())
