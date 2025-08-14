#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2023/4/24 15:11
# @Author  : Zc
# @Site    : 
# @File    : LightBoard.py
# @Software: PyCharm
import datetime
import enum
import subprocess
import threading
import time


class GpioName(enum.Enum):
    GPIO01 = 149  # 远焦摄像头控制
    GPIO07 = 168  # 近焦摄像头控制
    GPIO11 = 200  # 远焦灯板控制
    GPIO13 = 38   # 近焦灯板控制
    SPI1_SCK = 14 # 远焦光敏输入
    SPI1_CS1 = 232  # 近焦光敏输入

class LightBoard(threading.Thread):
    """
        灯板控制线程类:
           根据近、远焦光敏电平值变化，有、无火车情况，实现向灯板及相机输出高低电平。
           近焦灯板高、低电平不会导致灯板重启
           远焦灯板高电平板子重启、低电平板子正常
    """
    def __init__(self):
        super(LightBoard, self).__init__()
        self.IR_L12 = False # 近焦灯板
        self.IR_L11 = False # 远焦灯板
        self.train = True  # 有无火车
        # self.isTrue = False # 灯板阈值
        # self.isIR_L11 = True
        self.initGpioName()

    def initGpioName(self):
        for gpio_name in GpioName:
            self.controlGpio(gpio_name.value,0)
        self.inputGpio(GpioName.GPIO11.value,"low")
        self.inputGpio(GpioName.GPIO13.value, "low")
            # self.relay_control_gpio(1)

    def controlGpio(self,gpio_name,value):
        """
            0 echo 149 > /sys/class/gpio/export
            2 cat /sys/class/gpio/gpio1/value
        """
        if value == 0:
            cmd = f"echo {gpio_name} > /sys/class/gpio/export"
        else:
            cmd = f"cat /sys/class/gpio/gpio{gpio_name}/value"
        print(f"{datetime.datetime.now()}, controlGpio, os.system cmd={cmd}")
        # os.system(cmd)
        return self.subprocessCmd(cmd)

    def inputGpio(self,gpio_name,value):
        """
            echo high > /sys/class/gpio/gpio149/direction
        """
        cmd = f"echo {value} > /sys/class/gpio/gpio{gpio_name}/direction"
        print(f"{datetime.datetime.now()}, inputGpio, os.system cmd={cmd}")
        # os.system(cmd)
        return self.subprocessCmd(cmd)


    def mainControl(self,irBool,trainBool):
        """
            irBool:近焦、远焦光敏值
            trainBool:有无火车
        """
        if irBool:
            # 白天
            self.inputGpio(GpioName.GPIO13.value, "low")  # IR_L12 0电平直接给灯板HW管脚，关灯
            self.inputGpio(GpioName.GPIO07.value, "low")  # IR_L12 0电平直接给相机IR，彩色模式
            self.inputGpio(GpioName.GPIO11.value, "low")  # 0电平给灯板OFF管脚，关灯
            self.inputGpio(GpioName.GPIO01.value, "low")  # 0电平给相机IR管脚，彩色模式

        else:
            # 晚上
            if trainBool:
                # 有火车
                self.inputGpio(GpioName.GPIO13.value, "low")  # 0电平直接给灯板HW管脚，关灯
                self.inputGpio(GpioName.GPIO07.value, "low")  # 0电平给相机IR，彩色模式
                self.inputGpio(GpioName.GPIO11.value, "high")  # 3.3V电平给灯板OFF管脚，关灯
                self.inputGpio(GpioName.GPIO01.value, "high")  # 3.3V电平给相机IR管脚，黑白模式
            else:
                # 无火车
                self.inputGpio(GpioName.GPIO13.value, "high")  # IR_L12 1电平直接给灯板HW，开灯
                self.inputGpio(GpioName.GPIO07.value, "high")  # IR_L12 1电平直接给相机IR，黑白模式
                self.inputGpio(GpioName.GPIO11.value, "low")  # 0电平给灯板OFF管脚，开灯
                self.inputGpio(GpioName.GPIO01.value, "high")  # 3.3V电平给相机IR管脚，黑白模式


    def subprocessCmd(self, cmd):
        # cmd = f"echo '{self.sudo_pw}'| {cmd}"
        process = subprocess.Popen(cmd + "\n", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result_stdout = process.stdout.readlines()
        try:
            print(f"cmd={cmd},result={[result.decode('UTF-8') for result in result_stdout]}")
        except:
            pass
        return [result.decode('UTF-8') for result in result_stdout]

    def run(self):
        while True:
            near = self.controlGpio(GpioName.SPI1_CS1.value,2) # 获取近端光敏输入值
            far = self.controlGpio(GpioName.SPI1_SCK.value,2) # 获取远端光敏输入值
            self.IR_L12 = int(near[0].split("\n")[0])
            self.IR_L11 = int(far[0].split("\n")[0])
            time.sleep(1)


if __name__ == '__main__':
    gpio = LightBoard()
    gpio.start()
    # 测试:白天/晚上有无火车情况
    time.sleep(3)
    while True:
        gpio.mainControl(gpio.IR_L11 & gpio.IR_L12,False)

