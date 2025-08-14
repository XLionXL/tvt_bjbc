import datetime
import json
import platform
import socket
import subprocess
import threading
import time
import traceback
from abc import ABCMeta, abstractmethod

import common_FireTimer
from buffer_queue import BufferQueue
from comm_net_common import set_keepalive_linux, _send_json_str, _recv_json_data
from common_thread import ConsumerThread
from config_manager import JsonObjEncoder

CODE_ERROR = -1
TCP_TX_BUFFER_SIZE = 16384 * 4


class TcpServer(metaclass=ABCMeta):
    def __init__(self, port):
        self.consumer_start_timeStamp = time.time()
        self.consumer_thread = None
        self.thread_of_run = None
        self.send_ok_timeStamp = time.time()
        self.recvQ_ipPort_dict={}
        self.reStart_guard_callback = None
        self.port = port
        self.get_tcp_recvQ_firer = common_FireTimer.FireTimer_withCounter_InSpan(-1, -1)
        self.msg_queue = BufferQueue(10)

        self.server_socket = None
        self.port = port

        self.client_dict_pool = dict()
        self.udp_debug_callback=None
        self.init_server_socket()

    def init_server_socket(self, ):
        self.close_server_socket()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 1. 创建套接字
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 2. 配置socket
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 无延时
        self.server_socket.settimeout(2)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, TCP_TX_BUFFER_SIZE)
        tx_size = self.server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        print(f"TcpServer server_socket tx_size={tx_size}")
        # 开启长连接保活机制
        set_keepalive_linux(self.server_socket)
        print(f"{datetime.datetime.now()} TcpServer init_server_socket start at port:{self.port} ")
        self.server_socket.bind(("", self.port))
        # 3. 变为监听套接字
        self.server_socket.listen(128)

    def _handle_msg_send(self, msg):
        json_obj, client, client_key = msg
        try:
            if client_key:
                sock = self.client_dict_pool[client_key]
            data = f"{json.dumps(json_obj, ensure_ascii=False, cls=JsonObjEncoder)}\n".encode()
        except (TypeError, ValueError, BrokenPipeError, OSError) as e:
            if client_key in self.client_dict_pool:
                del self.client_dict_pool[client_key]
                sock.close()  # 确保套接字关闭
            return
        # 回复设置数据
        if client is not None:
            try:
                _send_json_str(client, data)
            except Exception as e:
                e1 = traceback.format_exc().replace("rror", "rro")
                e2 = str(e).replace("rror", "rro")
                print(f"_handle_msg_send client_key={client_key} disconnect 1:{e1}{e2}")
                self.release_client(client_key)
            return

        if self.get_tcp_recvQ_firer.isFireTime(1):
            self.check_tcp_close_deadClient()

        # 群发
        self.send_ok_timeStamp = time.time()
        for client_key in list(self.client_dict_pool.keys()):
            try:
                # 正常发送或者 buffer占用太高释放tcp连接
                _send_json_str(self.client_dict_pool[client_key], data)
            except Exception as e:
                e1=traceback.format_exc().replace("rror","rro")
                e2=str(e).replace("rror","rro")
                print(f"_handle_msg_send client_key={client_key} disconnect erro={e1}{e2}")
                self.release_client(client_key)

    def check_tcp_close_deadClient(self):
        # 检查tcp状态，断开已经阻塞的tcp客户端
        recvQ_ipPort_list = self.get_tcp_recvQ_size_by_netstat()
        if len(recvQ_ipPort_list) > 0:
            for recvQ_ipPort in recvQ_ipPort_list:
                print(f"{datetime.datetime.now()} check_tcp_close_deadClient to release {recvQ_ipPort}")
                self.release_client(recvQ_ipPort[2])
            # 更新send_ok_timeStamp 避免频繁操作
            # self.send_ok_timeStamp=time.time()

    @staticmethod
    def get_tcp_recvQ_size_by_netstat(cmd="netstat -ant|grep 127.0.0.1:8888|grep -v tcp6", filterKey='127.0.0.1', ):
        """
        在shell中通过 netstat -anp|grep 127.0|grep ESTABLISHED 命令获得当前TCP连接状态，找出那些发送队列阻塞的连接
        :param cmd:显示推理进程的ps命令
        :param filterKey:用于过滤的字符串
        :return:
        """
        receQ_ipPort_list = []
        if "Windows" not in platform.platform():
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            line_list = p.stdout.readlines()
            try:
                for index, line_byte in enumerate(line_list):
                    try:
                        # "tcp        1      0 127.0.0.1:44510         127.0.0.1:8888          CLOSE_WAIT".split()
                        line_str = str(line_byte, encoding='utf-8').strip()
                        segment_list = line_str.split()
                        if len(segment_list)<5:
                            continue
                            print(f"get_tcp_recvQ_size_by_netstat len(segment_list)<4 index={index},line_str={segment_list}")
                        elif "127.0.0.1" not in "".join(segment_list):
                            continue
                        elif "127.0.0.1" in segment_list[3]:
                            recvQ_size, ipPort, tcp_client = int(segment_list[2]), segment_list[3], segment_list[4]
                            if recvQ_size > 50 * 1000:
                                receQ_ipPort_list.append((recvQ_size, ipPort, tcp_client))
                    except ValueError:
                        print(f"get_tcp_recvQ_size_by_netstat Value except")
                        pass
                # print(f"get_tcp_recvQ_size_by_netstat receQ_ipPort_list={receQ_ipPort_list}")
            except:
                print(f"get_tcp_recvQ_size_by_netstat error line_list={line_list},{traceback.format_exc()}")
            finally:
                p.kill()
        return receQ_ipPort_list

    def _send(self, json_obj, client=None, client_key=None):
        self.msg_queue.put([json_obj, client, client_key]) # 将json_obj放入队列中

    def handle_client_connect(self, client_socket: socket.socket, client_addr):
        client_key = f"{client_addr[0]}:{client_addr[1]}"
        self.client_dict_pool[client_key] = client_socket
        self.on_client_connect(client_socket, client_key)
        try:
            while True:
                if client_key not in self.client_dict_pool:
                    print(f"客户端 [{client_key}] 已断开")
                    break
                # recv_data = client_socket.recv(1024 * 4)
                # 接收并解析客户端发来的请求报文
                try:
                    json_obj = _recv_json_data(client_socket)
                except TimeoutError:
                    pass
                except OSError as e:
                    print("Client erro=", e)
                    self.release_client(client_key)
                    return
                except Exception as e:
                    print("json error=", type(e), e)
                    self._send(self.gen_err_response(), client_socket, client_key)
                    continue
                # 判断客户端发来的消息是否为空
                if json_obj == -1:
                    print(f"client connect error,release {client_key}")
                    self.release_client(client_key)
                    return


                if type(json_obj) is not dict or "code" not in json_obj:
                    print("json error", json_obj)
                    self._send(self.gen_err_response(), client_socket, client_key)
                    continue
                response = self.on_client_request(json_obj)
                self._send(response, client_socket, client_key)

        except Exception as e:
            print("client connect error=", e)
            traceback.print_exc()
            self.release_client(client_key)

    @abstractmethod
    def on_client_connect(self, client_socket, client_key):
        pass

    @abstractmethod
    def on_client_request(self, json_obj):
        """
        处理请求， 返回响应结果对象
        :param json_obj:
        :return:
        """
        pass

    def release_client(self, client_key):
        if client_key in self.client_dict_pool:
            client_socket = self.client_dict_pool.pop(client_key)
            if client_socket is not None:
                client_socket.close()
                print(f"TcpServer release_client {client_key}")

    def response(self, code=-1, msg="", data=None):
        obj_dict = {
            "code": code,
            "msg": msg,
        }
        if data is not None:
            obj_dict["data"] = data

        return obj_dict

    def gen_err_response(self):
        return self.response(CODE_ERROR, "请求失败，请求体中需包含有效code字段，并保证json格式正确")

    def gen_default_response(self, code):
        return self.response(CODE_ERROR, f"request code error={code}", )

    def run(self):
        self.close_consumer_thread()
        self.init_consumer_thread()
        # 等待对方链接
        while True:
            try:
                new_socket, new_addr = self.server_socket.accept()
                # new_socket.settimeout(1)  # 3s
            except:
                continue
            try:
                # 创建一个新的线程来完成这个客户端的请求任务
                # 提示打印已有连接
                if self.udp_debug_callback is not None:
                    connects_str=f"connects={len(self.client_dict_pool)},"
                    for index in self.client_dict_pool:
                        peername_str=str(self.client_dict_pool[index].getpeername())
                        connects_str+=f"({index},{peername_str})"
                    self.udp_debug_callback(connects_str)

                # tcp 连接测试，临时代码，需要删除
                # max_client=128
                # while len(self.client_dict_pool)>=max_client:
                #     # client_key=list(self.client_dict_pool.keys())
                #     print(f"{datetime.datetime.now()},reStart_guard by {max_client} connections,{self.client_dict_pool.keys()}")
                #     if self.reStart_guard_callback is not None:
                #         print(f"{datetime.datetime.now()},reStart_guard by {max_client} connections,reStart_guard_callback start")
                #         self.reStart_guard_callback()
                #         print(f"{datetime.datetime.now()},reStart_guard by {max_client} connections,reStart_guard_callback finish")
                #         time.sleep(2)
                #     pass
                new_thread = threading.Thread(target=self.handle_client_connect, args=(new_socket, new_addr),name="x15")
                new_thread.setDaemon(True)
                new_thread.start()
            except Exception as e:
                print(f"TcpServer run error={e}, {traceback.format_exc()}")

    def init_consumer_thread(self):
        if self.consumer_thread is None:
            print(f"{datetime.datetime.now()} TcpServer init_consumer_thread")
            self.consumer_thread = ConsumerThread(self.msg_queue, self._handle_msg_send)
            self.consumer_thread.setDaemon(True)
            self.consumer_thread.start()
            self.consumer_start_timeStamp = time.time()

    def run_forever(self, is_block=True):
        if is_block:
            self.run()
        else:
            self.thread_of_run = threading.Thread(target=self.run)
            self.thread_of_run.setDaemon(True)
            self.thread_of_run.start()

    def close(self):
        if self.thread_of_run is not None:
            self.thread_of_run.join(1)
            self.thread_of_run = None

        for client_key, client in self.client_dict_pool.items():
            if client is not None:
                client.close()
        self.client_dict_pool = dict()
        self.close_consumer_thread()

    def close_consumer_thread(self):
        if self.consumer_thread is not None:
            print(f"{datetime.datetime.now()} TcpServer close_consumer_thread")
            self.consumer_thread.join(1)
            self.consumer_thread = None

    def close_server_socket(self):
        if self.server_socket is not None:
            print(f"{datetime.datetime.now()} TcpServer close_server_socket at port:{self.port} ")
            self.server_socket.close()
            self.server_socket = None


if __name__=="__main__":
    tcp_server = TcpServer(8888)
    time.sleep(5)
    recvQ_ipPort_lst = tcp_server.get_tcp_recvQ_size_by_netstat()
    print(f"recvQ_ipPort_lst={recvQ_ipPort_lst}")
    tcp_server.close()

