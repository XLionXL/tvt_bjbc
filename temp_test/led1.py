#!/usr/bin/env python3
import RPi.GPIO as GPIO
import datetime
import os
import platform
import time


class TVT_J17:
    Pin1 = 29   # Pin118>>>NANO_GPIO1>>>ZB_GPIO1,Pin1
    Pin4 = 31   # Pin216>>>NANO_GPIO7>>>ZB_GPIO7,Pin4
    Pin6 = 15   # Pin218>>>NANO_GPIO8>>>ZB_GPIO8,Pin6
    Pin8 = 33   # Pin228>>>NANO_GPIO9>>>ZB_GPIO9,Pin8
    Pin9 = 32   # Pin206>>>NANO_GPIO5>>>ZB_GPIO5,Pin9


class TVT_J17_2:
    Pin1_out = 29   # Pin118>>>NANO_GPIO1>>>ZB_GPIO1,Pin1
    Pin4_out = 31   # Pin216>>>NANO_GPIO7>>>ZB_GPIO7,Pin4
    Pin6_out = 15   # Pin218>>>NANO_GPIO8>>>ZB_GPIO8,Pin6
    Pin8_out = 33   # Pin228>>>NANO_GPIO9>>>ZB_GPIO9,Pin8
    Pin9_out = 32   # Pin206>>>NANO_GPIO5>>>ZB_GPIO5,Pin9
    PinX1_out = 11
    PinX2_in = 13
    PinX3_in = 16
    PinX4_in = 18
    PinX5_in = 22


# 无mcu工控板
class TVT_J17_No_MCU:
    Pin1_out = 29   # Pin118>>>NANO_GPIO1>>>ZB_GPIO1,Pin1
    # Pin4_out = 31   # Pin216>>>NANO_GPIO7>>>ZB_GPIO7,Pin4
    # Pin6_out = 15   # Pin218>>>NANO_GPIO8>>>ZB_GPIO8,Pin6
    # Pin8_out = 33   # Pin228>>>NANO_GPIO9>>>ZB_GPIO9,Pin8
    # Pin9_out = 32   # Pin206>>>NANO_GPIO5>>>ZB_GPIO5,Pin9
    # PinX1_out = 11
    # PinX2_in = 13
    # PinX3_in = 16
    # PinX4_in = 18
    # PinX5_in = 22


class TVT_GPIO:

    def init(self, pin_list, mode=GPIO.OUT):

        GPIO.setmode(GPIO.BOARD)  # Numbers GPIOs by physical location
        print(f"GPIO.getmode={GPIO.getmode()},GPIO.BOARD={GPIO.BOARD}")
        print(f"GPIO.VERSION={GPIO.VERSION}")
        print(f"GPIO.RPI_INFO={GPIO.RPI_INFO}")
        GPIO.setwarnings(False)  # 忽略GPIO警告
        for pin in pin_list:
            GPIO.setup(pin, mode)

    def setColor_loop(self, pin_list, loop_num=100):
        for index in range(loop_num):
            GPIO.output(pin_list, GPIO.HIGH)
            print(f"{datetime.datetime.now()},output=High")
            time.sleep(3)
            GPIO.output(pin_list, GPIO.LOW)
            print(f"{datetime.datetime.now()},output=Low")
            time.sleep(3)

    def setColor_loop_gpio_power(self, pin_list, loop_num=100):
        for index in range(loop_num):
            for pin in pin_list:
                cmd=f"echo high > /sys/class/gpio/{pin}/direction"
                os.system(cmd)
                print(f"{datetime.datetime.now()},cmd={cmd}")
            print(f"{datetime.datetime.now()},output=High")
            time.sleep(3)
            for pin in pin_list:
                cmd=f"echo low > /sys/class/gpio/{pin}/direction"
                os.system(cmd)
                print(f"{datetime.datetime.now()},cmd={cmd}")
            print(f"{datetime.datetime.now()},output=Low")
            time.sleep(3)

    def destroy(self, pin_list):
        GPIO.output(pin_list, GPIO.LOW)
        GPIO.cleanup()


# 程序入口
if __name__ == "__main__":
    if "Windows" in platform.platform():
        print(TVT_J17.Pin1)
    else:
        # pin_list = [29, 31, 15, 33, 32]
        # pin_list = [TVT_J17.Pin1, TVT_J17.Pin4, TVT_J17.Pin6, TVT_J17.Pin8, TVT_J17.Pin9]
        pin_list = ["gpio3", "gpio4", "gpio5", ]
        # pin_list = [TVT_J17_No_MCU.Pin1,]
        gpio=TVT_GPIO()
        try:
            print(f"{datetime.datetime.now()},output pin_list={pin_list}")
            # gpio.init(pin_list)
            gpio.setColor_loop_gpio_power(pin_list, 100)
        except KeyboardInterrupt:
            pass
        finally:
            pass
            # gpio.destroy(pin_list)
