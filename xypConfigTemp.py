import json
import socket
import struct
import threading
import traceback

CONFIG = {}
class PullAndPStream():
    def __init__(self,push=('10.8.2.14',8900),pull=('10.8.2.14',8901),mode=0):
        # 创建Socket连接
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 取消端口关闭后的等待期,重启程序就不会出现端口被占用的情况
        self.serverSocket.bind(push)
        self.serverSocket.listen(10)
        self.client = {}

        # self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.clientSocket.connect(pull)

        threading.Thread(target=self.clientHandle).start()
        # threading.Thread(target=self.pull).start()
        print(f"PullAndPStream pull:{pull} push:{push} init done")
    def clientHandle(self):
        while True:
            # 接受客户端连接
            clientConnection, clientAddress = self.serverSocket.accept()
            print(f"new client {clientAddress}")
            self.client[clientAddress] = clientConnection
            self.sendToClient(clientConnection)
            threading.Thread(target=self.cliendListen,args=(clientConnection,)).start()
            # jsonData = json.dumps(CONFIG)
            # clientConnection.sendall(struct.pack("<L", len(jsonData)))
            # clientConnection.sendall(jsonData.encode())
            # lenInfo =clientConnection.recv(struct.calcsize("<L"))
            # dataLen = struct.unpack("<L", lenInfo)[0]
            # data = b""
            # while len(data) < dataLen:
            #     pkg = clientConnection.recv(dataLen - len(data))
            #     if not pkg:
            #         break
            #     data += pkg
            # print(json.loads(data), "111")

    def sendToAll(self):
        pass
    def sendToClient(self,clientConnection):
        jsonData = json.dumps(CONFIG)
        clientConnection.sendall(struct.pack("<L", len(jsonData)))
        clientConnection.sendall(jsonData.encode())
    def cliendListen(self,clientConnection):
        while True:
            try:
                data = b""
                remote_address = clientConnection.getpeername()
                print('Remote address:', remote_address)
                lenInfo = clientConnection.recv(struct.calcsize("<L"))
                dataLen = struct.unpack("<L", lenInfo)[0]
                while len(data) < dataLen+3:
                    pkg = clientConnection.recv(1)
                    print(pkg,"ewwe")
                    if not pkg:
                        break
                    data += pkg
                print(data, "111")
            except:
                traceback.print_exc()










PullAndPStream()