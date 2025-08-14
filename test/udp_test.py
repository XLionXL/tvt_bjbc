import socket


def receive_udp_data(port):
    # 创建UDP套接字
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 绑定端口
    udp_socket.bind(("", port))

    # 持续读取数据并打印
    while True:
        data, addr = udp_socket.recvfrom(1024)  # 接收数据，最大接收长度为1024字节
        print(f"Received data:{data.hex()}", )  # 字节转为字符串并打印

    # 关闭套接字
    udp_socket.close()


# 调用函数开始接收UDP数据
receive_udp_data(15555)