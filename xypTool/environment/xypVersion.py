# 生成该项目运行环境
import platform
import sys
from xypFileTool import checkPath
from xypSystemCmd import systemCmdExecute


def createExecuteEnvInfo(savePath = "./config/executeEnvInfo.txt",pwd=None):
    systemName = platform.system()
    pythonVersion = sys.version

    executeFlag,output, error  = systemCmdExecute("pip3 list",pwd)
    print("操作系统:", systemName)
    print(f"Python 版本: {pythonVersion}")
    if output:
        print(f"OUTPUT:\n{output}")
    if error:
        print(f"ERROR:\n{error}")

    checkPath(savePath,pwd)
    with open(savePath, 'wt') as file:
        file.write(f"{systemName}\n"+f"Python 版本: {pythonVersion}\n"+output)
if __name__=="__main__":
    systemName = platform.system()
    if systemName == "Windows":
        createExecuteEnvInfo()
    elif systemName == "Linux":
        createExecuteEnvInfo(pwd="TDDPc5kc4WnYcy")
