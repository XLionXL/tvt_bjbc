import json
import socket


def set_keepalive_linux(sock, after_idle_sec=1 * 60, interval_sec=30, max_fails=10):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if hasattr(socket, "TCP_KEEPIDLE") and hasattr(socket, "TCP_KEEPINTVL") and hasattr(socket, "TCP_KEEPCNT"):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)  # idle后多久开始检测 60s, 缺省7200
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)  # 发包间隔 30s，缺省75s
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)  # 最多尝试次数 10，缺省9次


def _send_json_str(remote_socket, serialized):
    try:
        # 检查套接字是否已关闭（fileno()返回-1表示无效）
        if remote_socket.fileno() == -1:
            raise OSError("Socket has been closed")
        # 发送数据（带重试逻辑）
        tx_data = f'{len(serialized)}\n'.encode() + serialized
        total_sent = 0
        while total_sent < len(tx_data):
            sent = remote_socket.send(tx_data[total_sent:])
            if sent == 0:
                raise BrokenPipeError("Client disconnected")
            total_sent += sent
    except (BrokenPipeError, OSError) as e:
        raise  # 抛给上层处理，让服务器移除该客户端
        

def _recv_json_data(socket):
    # read the length of the data, letter by letter until we reach EOL
    length_str = ''
    char = socket.recv(1).decode()
    if char is None:
        return -1
    while char != '\n' or len(length_str)<=1:
        length_str += char
        char = socket.recv(1).decode()
        if char is None:
            return -1
    length_str = length_str.strip()
    if len(length_str)<=0:
        total = 0
    else:
        total = int(length_str)
    # use a memoryview to receive the data chunk by chunk efficiently
    view = memoryview(bytearray(total))
    next_offset = 0
    try:
        while total - next_offset > 0:
            recv_size = socket.recv_into(view[next_offset:], total - next_offset)
            next_offset += recv_size

        #print(r"total:" + str(total) + ", context:" + str(view.tobytes(), encoding="utf8"))
        deserialized = json.loads(view.tobytes())
    except (TypeError, ValueError) as e:
        raise Exception('Data received was not in JSON format')

    return deserialized