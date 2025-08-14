import datetime
import platform
import pyttsx3
import threading
import time
from comm_serialMCU import SerialMCU


def mcu_cmd_task():
    if "Windows" not in platform.platform():
        mcu = SerialMCU("/dev/ttyTHS1", )  # MCU数据
    else:
        mcu = SerialMCU("COM2", )  # MCU数据
    # mcu 给声光报警器供电
    mcu.start("x12")
    time.sleep(1)
    data_bytes = mcu.decoder.gen_frame(b'\x00\x10\x00\x00\x00\x04\x00\x00\x00\x01', "little")
    print(f"data_bytes={data_bytes}")
    while True:
        mcu.comm_send(data_bytes, showDataHex=True)
        time.sleep(0.7)


cmd_thread = threading.Thread(target=mcu_cmd_task, name="mcu_cmd_task_Thread")
cmd_thread.setDaemon(True)
cmd_thread.start()

say = pyttsx3.init()
say.setProperty('rate', 200)
say.setProperty('volume', 0.9)

for camera_id in range(3):
    msg=f"test {camera_id + 1}"
    print(f"{datetime.datetime.now()},msg={msg}")
    say.say(msg)
    say.runAndWait()

say.setProperty('rate', 175)
say.setProperty('volume', 0.9)
say.setProperty('voice', 'zh')

for camera_id in range(30):
    msg=f"请离开，您已进入警戒区 {camera_id + 1}"
    print(f"{datetime.datetime.now()},msg={msg}")
    say.say(msg)
    say.runAndWait()
