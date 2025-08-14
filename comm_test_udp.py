# -*- coding: utf-8 -*-
import datetime
import socket  # 导入socket模块
import time  # 导入time模块


def udp_test(local_ip_port=("localhost", 17000), test_time_s=10):
    # 创建一个套接字socket对象，用于进行通讯
    # socket.AF_INET 指明使用INET地址集，进行网间通讯
    # socket.SOCK_DGRAM 指明使用数据协议，即使用传输层的udp协议
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(local_ip_port)  # 为服务器绑定一个固定的地址，ip和端口
    server_socket.settimeout(2)  # 设置一个时间提示，如果10秒钟没接到数据进行提示
    time_start = time.time()
    while time.time() - time_start < test_time_s:
        try:
            now = time.time()  # 获取当前时间
            # 接收客户端传来的数据 recvfrom接收客户端的数据，默认是阻塞的，直到有客户端传来数据
            # recvfrom 参数的意义，表示最大能接收多少数据，单位是字节
            # recvfrom返回值说明
            # receive_data表示接受到的传来的数据,是bytes类型
            # client  表示传来数据的客户端的身份信息，客户端的ip和端口，元组
            receive_data, client = server_socket.recvfrom(1024)
            time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"{time_str} rx {client}>>{local_ip_port},data={receive_data}")  # 打印接收的内容
        except socket.timeout:  # 如果没有接收数据进行提示（打印 "time out"）
            time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"{time_str} {local_ip_port} time out")


# server 接收端
# 设置服务器默认端口号
if __name__ == "__main__":
    udp_test(local_ip_port=("192.168.8.200", 17000), test_time_s=10)
    udp_test(local_ip_port=("192.168.8.200", 15000), test_time_s=10)
    udp_test(local_ip_port=("192.168.8.200", 15555), test_time_s=10)
