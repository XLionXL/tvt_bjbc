import datetime
import logging
import os
import time
from logging import handlers
from xypTool.common import xypFileTool


class xypLogger(object):
    # 算一个小时日志20mb，三个月20*24*30*3=43,200mb
    def __init__(self,filename,level='info',when='M',backCount=3,fmt='%(asctime)s - %(levelname)-s: %(message)s',isPrint=False):
        levelDict = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }

        self.logger = logging.getLogger(filename)
        self.logger.setLevel(levelDict[level])  # 设置日志级别
        # 屏幕句柄
        screenHandler = logging.StreamHandler() # 往屏幕上输出
        # 文件句柄，按when(小时)截断文件，最多有backCount个截断文件，超过则循环覆盖
        fileHandler = handlers.TimedRotatingFileHandler(filename=filename,when=when,backupCount=backCount,encoding='utf-8')#往文件里写入#指定间隔时间自动生成文件的处理器

        fmt = logging.Formatter(fmt)#设置日志格式
        screenHandler.setFormatter(fmt)  #设置屏幕上显示的格式
        fileHandler.setFormatter(fmt)#设置文件里写入的格式
        # 日志器添加句柄
        if isPrint:
            self.logger.addHandler(screenHandler)
        self.logger.addHandler(fileHandler)


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

if __name__ == "__main__":
    logDeBugFlag = True
    if logDeBugFlag:
        xypLogPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),"log",f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log')
        xypLog = xypLogger(xypLogPath.replace("\\","/"),
            level='debug',isPrint=True)
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
        xypFileTool.checkPath(xypLogPath)
        xypLog = xypLogger(xypLogPath,level='debug')
    else:
        xypLog = None