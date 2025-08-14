# coding:utf-8
import datetime
import os.path
import platform
import pyttsx3
import threading
import time

import user_pw
from buffer_queue import BufferQueue
from comm_serialMCU import SerialMCU


class Voice_Save_Speaker():
    def __init__(self):
        self.className = "Voice_Save_Speaker"


class PronounceConsumerThread(threading.Thread):
    def __init__(self, main_folder=os.path.join("/usr", "bin", "zipx", "zj-guard"), my_user_pw=None,pronounce_english=0):
        threading.Thread.__init__(self, daemon=True)
        self.className = "PronounceConsumerThread"
        self.main_folder=main_folder
        self.pronounce_alarm_type_queue0 = BufferQueue(1)
        self.voice_speaker = Voice_Save_Speaker()
        self.get_volume_callback = None
        self.voice_folder = None
        self.running = True
        self.my_user_pw=my_user_pw
        if pronounce_english:
            self.msg_dict = {"joint": f"Intrusion detected! Intrusion detected!",
                             "camera": f"Intrusion detected! Intrusion detected!",
                             "radar": f"Intrusion detected! Intrusion detected!"}
        else:
            self.msg_dict = {"joint": f"请迅速离开，您已进入警戒区",
                             "camera": f"请迅速离开，您已进入警戒区",
                             "radar": f"请迅速离开，您已进入警戒区。"}

        self.ip = "192.168.8.200"
        self.user = "tvt"

    def run(self):
        while self.running:
            sleep_time = 0.2
            speak_volume = self.get_volume()
            try:
                if not self.pronounce_alarm_type_queue0.empty():
                    alarmType = self.pronounce_alarm_type_queue0.get(timeout=0.5)
                    print(datetime.datetime.now(), "pronounceQueue0", alarmType)
                    # self.sayVoice_by_alarmType_with_mcu_cmd(speak_volume=0.9, alarmType="camera",)
                    self.sayVoice_by_alarmType_with_mcu_cmd(speak_volume, alarmType="camera",)  # 20221013 zzl web控制speak_volume
                    sleep_time = 0
            except Exception as e:
                pass
            time.sleep(sleep_time)

    def exit(self):
        self.running=False
        time.sleep(1)
        # if self.thread is not None:
        #     self.thread.join()
        # self.thread=None
        print(f"{self.className},exit")

    def sayVoice_by_alarmType_with_mcu_cmd(self, speak_volume, alarmType="camera"):
        """
        :param speak_volume:音量大小，0.0~1.0
        :param alarmType:报警类型字符串
        :return:
        """
        if alarmType in self.msg_dict.keys():
            msg = self.msg_dict[alarmType]
        else:
            msg = alarmType
            pass
        print("sayVoice_by_alarmType_with_mcu_cmd: ", msg, speak_volume)
        # 发出声音
        self.say_message(msg, speak_volume)

    def say_message(self, msg, speak_volume):
        if "Windows" not in platform.platform():
            print(datetime.datetime.now(), f"{self.className},say_message start Say ")
            path_speak_py = os.path.join(self.main_folder, "speak.py")
            if self.my_user_pw is not None and False:
                # cmd2 = f"python3 {path_speak_py} -m \"{msg}\" -v {speak_volume} "
                cmd2 = f"ssh {self.user}@{self.ip} -Y 'python3 {path_speak_py} -m \"{msg}\" -v {speak_volume}' "
                print(cmd2)
                my_user_pw.system_cmd(cmd2)
            else:
                cmd2 = f"ssh {self.user}@{self.ip} -Y 'python3 {path_speak_py} -m \"{msg}\" -v {speak_volume}' "
                print(cmd2)
                os.system(cmd2)
            print(datetime.datetime.now(), f"{self.className},say_message exit Say cmd2={cmd2}")
        else:
            my_speak = pyttsx3.init()
            my_speak.setProperty('rate', 200)
            my_speak.setProperty('volume', 0.9)
            # my_speak.setProperty('voice', 'en')
            my_speak.say(msg)
            my_speak.runAndWait()

    def get_volume(self):
        if self.get_volume_callback is not None:
            speak_on_off, speak_volume = self.get_volume_callback()
        else:
            speak_on_off, speak_volume = 0, 0.0
        volume_out = speak_volume if speak_on_off > 0 else 0
        return volume_out


if __name__ == "__main__":
    my_user_pw = user_pw.User_PW()
    thread_pronounce = PronounceConsumerThread(my_user_pw=my_user_pw)
    thread_pronounce.start()

    if "Windows" not in platform.platform():
        mcu = SerialMCU("/dev/ttyTHS1", )  # MCU数据
    else:
        mcu = SerialMCU("COM2", )  # MCU数据

    mcu.start("x13")
    data_bytes = mcu.decoder.gen_frame(b'\x00\x10\x00\x00\x00\x04\x00\x00\x00\x01', "little")
    mcu.comm_send(data_bytes, showDataHex=True)
    time.sleep(1)
    mcu.comm_send(data_bytes, showDataHex=True)
    thread_pronounce.sayVoice_by_alarmType_with_mcu_cmd(0.9)
    mcu.comm_send(data_bytes, showDataHex=True)
    thread_pronounce.sayVoice_by_alarmType_with_mcu_cmd(0.9)
    mcu.comm_send(data_bytes, showDataHex=True)
    thread_pronounce.sayVoice_by_alarmType_with_mcu_cmd(0.9)
    mcu.exit()
    thread_pronounce.exit()
    print("test exit")
