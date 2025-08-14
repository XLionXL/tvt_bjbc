import cv2 as cv
import pickle
import socket
import struct
import threading
import time
import traceback


class PushStream():
    def __init__(self,ip='0.0.0.0',port=8091,mode=0):
        # 创建Socket连接
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 取消端口关闭后的等待期,重启程序就不会出现端口被占用的情况
        self.serverSocket.bind((ip, port))
        self.serverSocket.listen(10)
        self.client = {}
        self.task=[]
        self.mode=mode # 0传输图片，用cv.imencode快，1几乎为万能模式，但慢
        threading.Thread(target=self.clientHandle).start()
        threading.Thread(target=self.push).start()
        print(f"PushStream {ip} {port} init done")


    def clientHandle(self):
        while True:
            # 接受客户端连接
            clientConnection, clientAddress = self.serverSocket.accept()
            print(f"new client {clientAddress}")
            self.client[clientAddress]=clientConnection

    def push(self,):
        lastClientTime= time.time()
        lastTaskTime = time.time()
        while True:
            try:
                nowTime =time.time()
                if len(self.client):
                    lastClientTime = time.time()
                    if len(self.task):
                        lastTaskTime = time.time()
                        self.task=self.task[-1:]
                        data = self.task.pop(0)
                        if self.mode==0:
                            ret, data = cv.imencode('.jpg', data)
                        else:
                            data = pickle.dumps(data)
                        for address,connection in self.client.items():
                            connection.sendall(struct.pack("<L", len(data)))
                            # 发送数据
                            connection.sendall(data)
                    else:
                        if nowTime - lastTaskTime >2:
                            print("push no task")
                            time.sleep(0.5)
                else:
                    if nowTime - lastClientTime > 2:
                        print("push no client")
                        self.task = []
                        time.sleep(1)
            except socket.error:
                print(f"Client {address} has disconnected.")
                self.client.pop(address)
                connection.close()
            except:
                print(f"push error { traceback.format_exc()}")
               

def sendVideo():
    p = PushStream(ip='0.0.0.0', port=8091, mode=0)
    cap = cv.VideoCapture("rtsp://admin:Admin123@192.168.8.12:8554/0")
    while True:
        try:
            ret, frame = cap.read()
            # print('111')
            # frame = cv.resize(frame, (1920 // 3, 1080 // 3)).
            frame = cv.resize(frame, (800, 450))
            p.task.append(frame)
        except:
            print(f"sendVideo error {traceback.format_exc()}")


if __name__ =="__main__":
    sendVideo()

    # [(388, 325),
    # (457, 326),
    # (439, 300),
    # (391, 295)]

    # [(261, 343),
    # (549, 307),
    # (561, 310),
    # (732, 404),
    # (759, 401),
    # (799, 427),
    # (799, 382),
    # (610, 300)]
