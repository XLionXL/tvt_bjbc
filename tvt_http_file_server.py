import os.path
import platform
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler


class File_Server:
    def __init__(self, server_ip='127.0.0.1', server_port=8008, directory='/ssd/alarmpic/'):
        self.server_ip=server_ip
        self.server_port = server_port
        self.directory = directory
        self.server = None

    def server_task(self, ):
        try:
            handler_class = partial(SimpleHTTPRequestHandler, directory=self.directory)
            server_address = (self.server_ip, self.server_port)
            print(f"File_Server HTTP on {self.server_ip} port {self.server_port},(http://{self.server_ip}:{self.server_port}/),folder={self.directory},")
            self.server = HTTPServer(server_address, handler_class)
            self.server.serve_forever()
            print(f"File_Server HTTP on exit")
        except Exception as err:
            print(f"File_Server error {err}")

    def server_start(self,name):
        thread_server_task = threading.Thread(target=self.server_task, daemon=False,name=name)
        thread_server_task.start()
        print(f"File_Server HTTP server_start finished")


if __name__ == '__main__':
    folder_list = ['/ssd/alarmpic/', "/usr/bin/zipx/zj-guard/log", "D:\FTP\log"]
    folder_list_exists = [x for x in folder_list if os.path.exists(x)]
    if len(folder_list_exists) > 0:
        folder=folder_list_exists[0]
        if "Windows" not in platform.platform():
            file_server = File_Server(server_ip='10.8.4.217', server_port=31009, directory=folder)
            file_server.server_start("test")
        else:
            file_server = File_Server(server_ip='10.8.4.88', server_port=8008, directory=folder)
            file_server.server_start("test")
