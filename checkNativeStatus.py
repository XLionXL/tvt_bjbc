# -*- coding: utf-8 -*-

#######################################################
# FileName: checkLinkStatus.py
# Description: 链路检测线程
#######################################################

import threading
import time
#import pyping
import subprocess
# import pyping
import subprocess
import threading
import time


class CheckNativeStatus(threading.Thread):
    def __init__(self, stream):
        threading.Thread.__init__(self)
        self.stream = stream
        self.setDaemon(True)

    def run(self):
        """
        启动检测过程
        :return:
        """
        while True:
            p = subprocess.Popen('ps -aux|grep infer_main', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            text = str(p.stdout.readlines()[0], encoding='utf-8').split(" ")
            if (text[-1].replace("\n", "")) == self.stream:
                print("推理正在运行...")
            else:
                print("推理运行故障...")
            time.sleep(60)


if __name__ == "__main__":
    with open("config/source_list.json", "r") as f:
        a = f.readline().replace("[","").replace("]","").split(",")
    print(a[0])
