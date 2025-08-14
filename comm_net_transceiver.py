"""
使用udp协议收发网络数据
"""
import datetime
import io
import socket
import threading
import time
import traceback
from queue import Queue

from buffer_queue import BufferQueue
from comm_radar_driver_shibian import RadarDriver_UDP


class MsgReceiveThread(threading.Thread):

    def __init__(self, queue, udp_socket):
        super(MsgReceiveThread, self).__init__(daemon=True)
        self.udp_socket: socket.socket = udp_socket
        self.queue: Queue = queue

    def run(self) -> None:
        while True:
            recv_data = self.udp_socket.recvfrom(4 * 1024)
            # print(recv_data)
            if recv_data:
                self.queue.put(recv_data)


class ConsumerThread(threading.Thread):
    def __init__(self, queue, function):
        threading.Thread.__init__(self, daemon=True)
        self.queue = queue
        self.function = function

    def run(self):
        while True:
            m = self.queue.get()
            self.function(m)


class UdpDataSocket:

    def __init__(self, target_ip="255.255.255.255", target_port=9999, bind_port=10001):
        self.udp_socket = None
        self.bind_port=bind_port
        self.upd_open()

        # 设置目标ip和端口
        self.target_ip = target_ip
        self.target_port = target_port
        self.msg_callback = None
        self.latest_data_stamp = time.time()

        queue_size = 3

        # 消息接收线程
        self.receive_queue = BufferQueue(queue_size)
        receiveThread = MsgReceiveThread(self.receive_queue, self.udp_socket)
        receiveThread.start()
        
        # 开启子线程轮询消息队列
        self.cThread = ConsumerThread(self.receive_queue, self.handle_msg_receive)

    def upd_open(self, ):
        # 创建udp的socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # 允许发送广播
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        # 绑定端口
        self.udp_socket.bind(("", self.bind_port))

    def listen(self, msg_callback):
        self.msg_callback = msg_callback
        print("msg_callback", self.msg_callback)

    def start(self):
        print(f"{datetime.datetime.now()}------camera listen at port:{self.bind_port} ")
        if not self.cThread.is_alive():
            self.cThread.start()

    def handle_msg_receive(self, recv_data):
        # msg, ip_port = recv_data
        # content = msg.decode("utf-8")
        if self.msg_callback is not None:
            # start = time.time()
            self.msg_callback(recv_data)
            self.latest_data_stamp = time.time()
            # print(recv_data)
            # end = time.time()
            # print("---------camera_duration: ", end - start)

    def publish(self, msg):
        # 发送数据
        encode_data = f"{str(msg)}\n".encode("utf-8")
        self.udp_socket.sendto(encode_data, (self.target_ip, self.target_port))

    def close(self):
        self.udp_socket.close()


def UdpDataSocket_test():
    # 默认广播到9999端口
    data_socket = UdpDataSocket(bind_port=9999)
    # data_socket.publish("haha")
    data_socket.listen(lambda data: print(data[1], data[0].decode("utf-8")))
    while True:
        length = len(threading.enumerate())
        time.sleep(0.5)
        if length <= 1:
            break
    # for i in range(100):
    #     data_socket.publish(f"hello: {i}")
    #     time.sleep(1)


class Udp_Camera_With_Reconnect(RadarDriver_UDP):
    # 支持重连的udp接收端
    def __init__(self, decoder, target_ip="255.255.255.255", target_port=9999, bind_port=10001):
        super(Udp_Camera_With_Reconnect, self).__init__(decoder, local_port=bind_port)
        self.radar_address = (target_ip, target_port)
        # 设置目标ip和端口
        self.target_ip = target_ip
        self.target_port = target_port
        self.bind_port = bind_port
        self.className="Udp_Camera_With_Reconnect"
        self.timeout_for_reconnect=60
        self.msg_callback = None

    def listen_radar_data_handler(self, msg_callback):
        self.msg_callback = msg_callback
        print("msg_callback", self.msg_callback)

    def comm_read(self):
        if self.comm_isOpen:
            try:
                recv = self.comm_handle.recvfrom(4096)
                return recv
            except Exception as e:
                return None

    def _run_receive(self):
        self.running = True
        print(f"{datetime.datetime.now()},{self.className},_run_receive start")
        while self.running:
            try:
                # 确认是否重连，如果超时没有数据，则重连
                self.comm_open_if_need()
                # 读取数据并处理
                recv = self.comm_read()
                if recv is not None:
                    if time.time()-self.latest_data_stamp>30:
                        # 超过30秒的间隔没有数据，则打印接收到的数据，用于调试
                        print(f"{datetime.datetime.now()},{self.className},recv interval>30 for debug:{recv}")
                    self.msg_callback(recv)
                    self.latest_data_stamp=time.time()
                # else:
                #     self.msg_callback(None)
                #     time.sleep(0.250)
            except Exception as e:
                print("_run_receive error")
                traceback.print_exc()
                outputBuffer = io.StringIO()
                traceback.print_exc(file=outputBuffer)

def Udp_Camera_test():
    # 默认广播到9999端口
    data_socket = Udp_Camera_With_Reconnect(bind_port=10001)
    data_socket.listen_radar_data_handler(lambda data: print(data[1], data[0].decode("utf-8")))
    data_socket.start(daemon=False)
    time.sleep(60)
    data_socket.exit()


if __name__ == '__main__':
    pass
    # UdpDataSocket_test()
    Udp_Camera_test()
