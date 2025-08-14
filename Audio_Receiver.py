# coding:utf-8
import datetime
import pickle
import pyaudio
import struct
import threading
import time
from socket import *

PORT=18889
CHUNK = 1024
CHANNELS = 2  # 输入/输出通道数
RATE = 44100  # 音频数据的采样频率
CONFIGS_DICT = {
    "PORT":PORT,
    "CHUNK": CHUNK,
    "CHANNELS": CHANNELS,
    "RATE": RATE,
}

class Audio_Receiver(threading.Thread):

    def __init__(self, port=PORT, version=4):
        threading.Thread.__init__(self)
        self.class_name = "Audio_Recevier"
        self.setDaemon(False)
        self.ADDR = ('', port)
        if version == 4:
            self.sock = socket(AF_INET, SOCK_STREAM)
        else:
            self.sock = socket(AF_INET6, SOCK_STREAM)
        self.p = pyaudio.PyAudio()  # 实例化PyAudio,并于下面设置portaudio参数
        self.stream = None
        self.running = True

    def exit(self):
        self.running = False
        time.sleep(2)
        self.sock.close()  # 关闭套接字
        if self.stream is not None:
            self.stream.stop_stream()  # 暂停播放 / 录制
            self.stream.close()  # 终止流
        self.p.terminate()  # 终止会话

    def run(self):
        self.running = True
        self.sock.bind(self.ADDR)
        self.sock.listen(1)  # 排队个数
        self.sock.settimeout(2)
        time_start = time.time()
        while self.running:
            try:
                conn, addr = self.sock.accept()
                break
            except:
                if time.time() - time_start <= 10:
                    continue
                else:
                    self.exit()
                    return

        self.data_buffer = "".encode("utf-8")
        payload_size = struct.calcsize("L")  # 返回对应于格式字符串fmt的结构，L为4
        self.stream = self.p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=RATE, output=True,
                                  frames_per_buffer=CHUNK)
        index_package = 0
        while self.running:
            index_package += 1
            if self.rx_data_to_buffer(conn, payload_size):
                # 解码帧长，
                packed_size = self.data_buffer[:payload_size]
                self.data_buffer = self.data_buffer[payload_size:]
                # 解码并播放一帧数据，
                msg_size = struct.unpack("L", packed_size)[0]
                if self.rx_data_to_buffer(conn, msg_size):
                    frame_data = self.data_buffer[:msg_size]
                    self.data_buffer = self.data_buffer[msg_size:]
                    frames = pickle.loads(frame_data)
                    for frame in frames:
                        self.stream.write(frame, CHUNK)
                else:
                    self.exit()
            else:
                self.exit()



    def rx_data_to_buffer(self, conn, target_size):
        is_conn_ok=True
        time_of_date_new = time.time()
        while self.running and len(self.data_buffer) < target_size:
            data_new = conn.recv(81920)
            self.data_buffer += data_new
            if len(data_new) > 0:
                time_of_date_new = time.time()
            if time.time() - time_of_date_new > 1:
                # 2秒收不到数据，断开语音喊话
                self.data_buffer=b''
                is_conn_ok=False
                return is_conn_ok
        return is_conn_ok


def audio_receiver_test(json_obj):
    audio_server = Audio_Receiver()
    audio_server.setName("x3")
    audio_server.start()


if __name__ == "__main__":
    audio_receiver_test(None)

