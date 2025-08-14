# # coding:utf-8
# import asyncio
# import threading
# import time
# from tkinter.tix import Tree
# import websockets
# import datetime
# import pyaudio
# import struct
#
# CHUNK = 2048
# CHANNELS = 1  # 输入/输出通道数
# RATE = 8000  # 音频数据的采样频率
# RECORD_SECONDS = 0.3  # 记录秒
# payload_size = struct.calcsize("L")  # 返回对应于格式字符串fmt的结构，L为4
#
#
# class Audio_Receiver_websocket(threading.Thread):
#     def __init__(self):
#         self.check = False
#         self.pyAudio = pyaudio.PyAudio()  # 实例化PyAudio,并于下面设置portaudio参数
#         self.stream = None
#         self.data = "".encode("utf-8")
#         self.stream = self.pyAudio.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, output=True,
#                                         frames_per_buffer=CHUNK)
#
#         # 接收客户端消息并处理，
#
#     async def recv_msg(self, websocket):
#         index_rx = 0
#         print(f"{datetime.datetime.now()}, recv_msg start")
#         data = "".encode("utf-8")
#         while True:
#             try:
#                 index_rx += 1
#                 data = await websocket.recv()
#                 print(f"{datetime.datetime.now()},Audio_Recevier,index_rx={index_rx}")
#                 self.stream.write(data)
#             except Exception as error_s:
#                 pass
#
#     # 服务器端主逻辑
#     # websocket和path是该函数被回调时自动传过来的，不需要自己传
#     async def main_logic(self, websocket, path):
#         # await check_permit(websocket)
#         print(f"{datetime.datetime.now()},main_logic")
#         await self.recv_msg(websocket)
#
#     def __del__(self):
#         if self.stream is not None:
#             self.stream.stop_stream()  # 暂停播放 / 录制
#             self.stream.close()  # 终止流
#         self.pyAudio.terminate()  # 终止会话
#
#
# if __name__ == "__main__":
#     # 把ip换成自己本地的ip
#     audio_receiver = Audio_Receiver_websocket()
#     start_server = websockets.serve(audio_receiver.main_logic, '127.0.0.1', 8888, ping_interval=None)
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(start_server)
#     loop.run_forever()
#     # time.sleep(60)
#     print(f"{datetime.datetime.now()},loop.close")
#     loop.close()
