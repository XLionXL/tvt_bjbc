# -*- coding: gbk -*-
import datetime
import time

from Camera_Http_EnZhi import Camera_Http_EnZhi
from Camera_Http_YuCheng import Camera_Http_YuCheng


class Camera_Train_Icr:
    def __init__(self):
        self.class_name="Camera_Train_Icr"
        self.isTrainInView=False
        self.camera_YC = Camera_Http_YuCheng("192.168.8.11", "admin", 'Admin123')
        self.camera_NZ = Camera_Http_EnZhi("192.168.8.12", "admin", 'Admin123')
        self.control_icr_timeStamp = time.time() - 9999


    def set_camera_icr_by_train(self, isTrainInView=True):
        """
        相机红外灯控制具体执行函数，有火车时关闭自研宇辰和恩智相机红外灯
        :param isTrainInView:是否有火车的输入
        :return:
        """
        self.camera_YC.camera_icr_set(isTrainInView)
        self.camera_NZ.controlIcrbyTrainstatus(isTrainInView)
        self.isTrainInView = isTrainInView
        self.control_icr_timeStamp = time.time()


class Camera_Icr_GPIO:

    Pin1_Near_OnOff = 29   # Pin118>>>NANO_GPIO1>>>ZB_GPIO1,Pin1
    Pin4_Near_IRC = 31   # Pin216>>>NANO_GPIO7>>>ZB_GPIO7,Pin4
    Pin6_Far_IRL = 15   # Pin218>>>NANO_GPIO8>>>ZB_GPIO8,Pin6
    Pin8_far_OnOff = 33   # Pin228>>>NANO_GPIO9>>>ZB_GPIO9,Pin8
    Pin9_far_IRC = 32   # Pin206>>>NANO_GPIO5>>>ZB_GPIO5,Pin9

    def __init__(self):
        import RPi.GPIO as GPIO
        self.class_name="Camera_Icr_GPIO"
        self.isTrainInView=False
        # self.camera_YC = Camera_Http_YuCheng("192.168.8.11", "admin", 'Admin123')
        GPIO.setmode(GPIO.BOARD)  # Numbers GPIOs by physical location
        GPIO.setwarnings(False)  # 忽略GPIO警告
        # 近焦 恩智相机
        GPIO.setup(Camera_Icr_GPIO.Pin1_Near_OnOff, GPIO.OUT)
        GPIO.setup(Camera_Icr_GPIO.Pin4_Near_IRC, GPIO.OUT)
        # 远焦 宇成相机
        GPIO.setup(Camera_Icr_GPIO.Pin6_Far_IRL, GPIO.IN)
        GPIO.setup(Camera_Icr_GPIO.Pin8_far_OnOff, GPIO.OUT)
        GPIO.setup(Camera_Icr_GPIO.Pin9_far_IRC, GPIO.OUT)
        self.control_icr_timeStamp = time.time() - 9999

    def set_camera_icr_by_train(self, isTrainInView=True):
        """
        相机红外灯控制具体执行函数，有火车时关闭自研宇辰和恩智相机红外灯
        :param isTrainInView:是否有火车的输入
        :return:
        """
        import RPi.GPIO as GPIO
        output_icr = GPIO.LOW if isTrainInView else GPIO.HIGH
        # 近焦 恩智相机
        # isTrainInView = True >> GPIO.LOW >> 红外灯灭 & 彩色模式
        GPIO.output(Camera_Icr_GPIO.Pin1_Near_OnOff, output_icr)
        GPIO.output(Camera_Icr_GPIO.Pin4_Near_IRC, output_icr)
        # 远焦 宇成相机
        # isTrainInView = True >> GPIO.HIGH >> 红外灯灭 & 彩色模式
        output_icr = GPIO.HIGH if isTrainInView else GPIO.LOW
        GPIO.output(Camera_Icr_GPIO.Pin8_far_OnOff, output_icr)

        self.isTrainInView = isTrainInView
        self.control_icr_timeStamp = time.time()


if __name__ == "__main__":
    if 0:
        camera_train_icr = Camera_Train_Icr()
        for index in range(3):
            camera_train_icr.set_camera_icr_by_train(True)
            time.sleep(20)
            camera_train_icr.set_camera_icr_by_train(False)
            time.sleep(20)
    elif 1:
        camera_train_icr = Camera_Icr_GPIO()
        for index in range(10):
            camera_train_icr.set_camera_icr_by_train(True)
            time.sleep(20)
            camera_train_icr.set_camera_icr_by_train(False)
            time.sleep(20)

