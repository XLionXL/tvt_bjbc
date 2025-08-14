from xypDebugConfig import xypLogPath, logDeBugFlag
if logDeBugFlag:
    import os
    import time
    import logging
    import datetime
    from logging import handlers
    import platform
    import subprocess


def cmdExecute(cmd, sudo="TDDPc5kc4WnYcy"):
    if sudo:
        cmd = f"sudo -S {cmd}"
    print(f"{datetime.datetime.now()}, cmd: {cmd}")
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate(input=(sudo + "\n").encode('utf-8'))  # 等待执行完并返回输出
    if error:
        print(f"{datetime.datetime.now()}, error: {error.decode('utf8')}")
        return False
    if output:
        print(f"{datetime.datetime.now()}, output:{output.decode('utf8')}")
    return True


def checkPath(path, isFile=True):
    if isFile:  # 如果是文件
        dir = os.path.dirname(path)
        if platform.system() == 'Linux':
            if not os.path.exists(dir):
                cmdExecute(f"mkdir -p {dir}")
            cmdExecute(f"touch {path}")
            cmdExecute(f"chmod 777 {path}")
        else:
            if not os.path.exists(dir):
                os.makedirs(dir)
            with open(path, "wt") as f:
                pass
    else:
        if platform.system() == 'Linux':
            if not os.path.exists(path):
                cmdExecute(f"mkdir -p {path}")
            cmdExecute(f"chmod 777 {path}")
        else:
            if not os.path.exists(path):
                os.makedirs(path)

class xypLogger(object):
    def __init__(self,filename,level='info',when='H',backCount=48,fmt='%(asctime)s - %(levelname)-s: %(message)s'):
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
        # 日志器记录句柄
        self.logger.addHandler(screenHandler)
        self.logger.addHandler(fileHandler)
def xypWarning(*data):
    if xypLog is not None:
        strData = ''
        for d in data:
            strData += str(d) + "&"
        xypLog.logger.warning(strData[:-1])
def xypCritical(*data):
    if xypLog is not None:
        strData = ''
        for d in data:
            strData += str(d) + "&"
        xypLog.logger.critical(strData[:-1])

def xypError(*data):
    if xypLog is not None:
        strData = ''
        for d in data:
            strData += str(d) + "&"
        xypLog.logger.error(strData[:-1])
def xypInfo(*data):
    if xypLog is not None:
        strData = ''
        for d in data:
            strData += str(d) + "&"
        xypLog.logger.info(strData[:-1])
def xypDebug(*data):
    if xypLog is not None:
        strData = ''
        for d in data:
            strData += str(d) + "&"
        xypLog.logger.debug(strData[:-1])

if __name__ == "__main__":
    print(xypLogPath)
    if logDeBugFlag:
        if not os.path.exists(xypLogPath):
            os.makedirs(xypLogPath)
        xypLog = xypLogger(os.path.join(xypLogPath, f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log').replace("\\","/"),
            level='debug')
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
    if logDeBugFlag:
        checkPath(xypLogPath,False)
        print("xypLogPath",os.path.join(xypLogPath, f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log'))
        xypLog = xypLogger(os.path.join(xypLogPath, f'{datetime.datetime.now().strftime("%Y-%m-%d %H-%M")}.log').replace("\\","/"),
            level='debug')
    else:
        xypLog = None