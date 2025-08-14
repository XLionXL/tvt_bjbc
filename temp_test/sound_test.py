# coding:utf-8
import datetime

import os
import playsound
import pyttsx3

from pydub import AudioSegment
from pydub.playback import play



# def play_pyAudio(filename ):
#     CHUNK = 1024
#     import PyAudio
#     wf = wave.open(filename, 'rb')
#     p = PyAudio.PyAudio()
#     stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
#                     channels=wf.getnchannels(),
#                     rate=wf.getframerate(),
#                     output=True)
#     data = wf.readframes(CHUNK)
#     while data != b'':
#         stream.write(data)
#         data = wf.readframes(CHUNK)
#     stream.stop_stream()
#     stream.close()
#     p.terminate()

def play_AudioSebment(file_path):
    print(datetime.datetime.now(), f"play_AudioSebment start Say ")
    song = AudioSegment.from_wav(file_path)
    play(song)
    print(datetime.datetime.now(), f"play_AudioSebment exit Say ")

def play_playsound(file_path):
    print(datetime.datetime.now(), f"play_playsound start Say ")
    playsound.playsound(file_path)
    print(datetime.datetime.now(), f"play_playsound exit Say ")

def play_system(file_path):
    print(datetime.datetime.now(), f"play_system start Say ")
    os.system(f"sudo `play {file_path}`")
    print(datetime.datetime.now(), f"play_system exit Say ")

def play_pyttsx3(msg,language='zh'):
    say = pyttsx3.init()
    say.setProperty('rate', 200)
    say.setProperty('volume', 0.8)
    say.setProperty('voice', 'en')
    print(datetime.datetime.now(),f"play_pyttsx3 start Say msg={msg}")
    say.say(msg)
    say.runAndWait()
    say.stop()
    print(datetime.datetime.now(), f"play_pyttsx3 exit Say msg={msg}")

def play_python3(msg):
    print(datetime.datetime.now(), f"play_system start Say ")
    os.system(f"sudo `python3 {msg}`")
    print(datetime.datetime.now(), f"play_system exit Say ")

def save_mp3_pyttsx3(msg,mp3_path,language='en'):
    say = pyttsx3.init()
    say.setProperty('rate', 200)
    say.setProperty('volume',1)
    say.setProperty('voice', language)
    print(datetime.datetime.now(),f"save_mp3_pyttsx3 start save mp3 msg={msg}")
    say.save_to_file(msg,mp3_path)
    say.runAndWait()
    say.stop()
    print(datetime.datetime.now(), f"save_mp3_pyttsx3 exit save mp3 msg={msg},path={mp3_path}")



# file_path=r"./1dccfe0cb2d0f0835f76674b22843ba2.mp3"

# Play_mp3.play(file_path)
# play_playsound(file_path)
# play_AudioSebment(file_path)
# play_system(file_path)
# play_pyttsx3(f"您已进入相机和雷达警戒区，请迅速离开。")

save_mp3_pyttsx3(f"Intrusion detected! Intrusion detected!" ,"./Intrusion.mp3")



