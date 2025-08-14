import datetime
import logging
import os
import shutil
import time
from logging import handlers
import traceback
from xypTool.common import xypFileTool


class xypLogger(object):
    # 算一个小时日志20mb，三个月20*24*30*3=43,200mb
    def __init__(self, logPath, level='error', when='M', backCount=3, fmt='%(asctime)s - %(levelname)-s: %(message)s', isPrint=False,limitNum=None, limtTime = None,limitSize = None):
        print(f"{datetime.datetime.now()} log init: logPath:{logPath}, level:{level}, when:{when}, backCount:{backCount}, isPrint:{isPrint},limitNum:{limitNum}, limtTime:{limtTime},limitSize:{limitSize}")

        if "python3_main_py" in str(traceback.extract_stack()): # 必须由python3_main_py为首调用
            self.fileSpaceInit(logPath,limitNum, limtTime,limitSize )
        levelDict = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        self.logger = logging.getLogger(logPath)
        self.logger.setLevel(levelDict[level])  # 设置日志级别
        # 屏幕句柄
        # screenHandler = logging.StreamHandler() # 往屏幕上输出
        # 文件句柄，按when(小时)截断文件，最多有backCount个截断文件，超过则循环覆盖
        fileHandler = handlers.TimedRotatingFileHandler(filename=logPath, when=when, backupCount=backCount, encoding='utf-8')#往文件里写入#指定间隔时间自动生成文件的处理器

        fmt = logging.Formatter(fmt)#设置日志格式
        # screenHandler.setFormatter(fmt)  #设置屏幕上显示的格式
        fileHandler.setFormatter(fmt)#设置文件里写入的格式
        # 日志器添加句柄
        # if isPrint:
        #     self.logger.addHandler(screenHandler)
        self.logger.addHandler(fileHandler)

    def fileSpaceInit(self,logPath,limitNum, limtTime,limitSize):
        try:
            # 创建目录并保证有权限
            xypLogFolder = os.path.dirname(os.path.abspath(logPath))
            xypLogFolderOld = os.path.join(xypLogFolder, "old")
            xypFileTool.checkPath(xypLogFolder)
            xypFileTool.checkPath(xypLogFolderOld)

            # 将老的数据移动到xypLogFolderOld文件夹，并对xypLogFolderOld文件夹进行空间管理
            files = [fileRelatPath for fileRelatPath in os.listdir(xypLogFolder) if
                     os.path.isfile(os.path.join(xypLogFolder, fileRelatPath))]
            for fileRelatePath in files:
                shutil.move(os.path.join(xypLogFolder, fileRelatePath), os.path.join(xypLogFolderOld, fileRelatePath))

            # 空间管理
            xypLogSpaceManage = xypFileTool.FileSpaceManage(xypLogFolderOld)
            if limitNum is not None:
                xypLogSpaceManage.manage(limitNum)
            if limtTime is not None:
                xypLogSpaceManage.manage(limtTime)
            if limitSize is not None:
                xypLogSpaceManage.manage(limitSize)
        except Exception as e:
            print(f"exception:{e}\ntraceback:{traceback.format_exc()}")

def xypWarning(*data):
    if xypLog is not None:
        strData="&".join(str(item) for item in data)
        xypLog.logger.warning(strData)
def xypCritical(*data):
    if xypLog is not None:
        strData="&".join(str(item) for item in data)
        xypLog.logger.critical(strData)

def xypError(*data):
    if xypLog is not None:
        strData="&".join(str(item) for item in data)
        xypLog.logger.error(strData)
def xypInfo(*data):
    if xypLog is not None:
        strData="&".join(str(item) for item in data)
        xypLog.logger.info(strData)
def xypDebug(*data):
    if xypLog is not None:
        strData="&".join(str(item) for item in data)
        xypLog.logger.debug(strData)


import sys
import inspect






if __name__ == "__main__":
    logDeBugFlag = True
    if logDeBugFlag:
        xypLogFolder = os.path.join(os.path.dirname(os.path.abspath(__file__)),"log")
        xypLogFolderOld = os.path.join(xypLogFolder, "old")
        xypFileTool.checkPath(xypLogFolder)
        xypFileTool.checkPath(xypLogFolderOld)

        files = [fileRelatPath for fileRelatPath in os.listdir(xypLogFolder) if os.path.isfile(os.path.join(xypLogFolder, fileRelatPath))]
        for fileRelatePath in files:
            shutil.move(os.path.join(xypLogFolder, fileRelatePath), os.path.join(xypLogFolderOld, fileRelatePath))

        xypLogPath = os.path.join(xypLogFolder,f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log')
        # xypFileTool.checkPath(xypLogPath)


        xypLog = xypLogger(xypLogPath.replace("\\","/"),
            level='debug',when="S",backCount=10,isPrint=False)
        xypLogSpaceManage = xypFileTool.FileSpaceManage(xypLogFolderOld)
        xypLogSpaceManage.manage("20s")
        xypLogSpaceManage.manage("3kb")

    else:
        xypLog = None
    while 1:
        time.sleep(1)
        xypDebug(time.time())
        xypDebug(time.time())
        xypInfo(time.time())
        xypWarning(time.time())
        xypError(time.time())
        xypCritical(time.time())
else:
    logDeBugFlag=True
    if logDeBugFlag:
        xypLogPath = "/ssd/xyp/xypLog/"+f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log'
        xypLog = xypLogger(xypLogPath,level='debug',isPrint=True,when="H",backCount=2400,limitNum=4800, limtTime = "0.5Y",limitSize="20GB")
    else:
        xypLog = None


        # s =
        # s =
        # # print(s)
        # # item = s[-1]
        # # print(type(item))
        # # print(item[0])
        # # print(item[1])
        # # print(item[2])
        # # print(item[3])
        # print('%s 在调用我!' % s)
        # if s[-2][2] == 'a':
        #     print('测试成功！' + str(type(s[-2][2])))
        # else:
        #     print('测试失败')