import re
import datetime
import json
import numpy as np
import os
# import py7zr
# import paramiko
import platform
# import py7zr
import re
import shutil
import threading
import time
import traceback
import yaml

from xypSystemCmd import systemCmdExecute


def checkPath(path): # 检查文件路径，文件路径不存在则创建路径
    try:
        path = os.path.abspath(path) # 获取绝对路径，以适配./xxx等相对路径
        # 获取文件夹路径
        if "." in os.path.basename(path): # 最后一个路径存在"."则path为文件，否则path为文件夹
            folder = os.path.dirname(path)
            file = path
        else:
            folder = path
            file = None

        systemName = platform.system()
        if systemName == "Windows":
            if not os.path.exists(folder):
                systemCmdExecute(f"mkdir {folder}",isPrint=False)
                systemCmdExecute(f"icacls {folder} /grant Everyone:F /T",isPrint=False) # 文件夹才有/T
            if file is not None and not os.path.exists(file):
                systemCmdExecute(f"cd . > {file}",isPrint=False)
                systemCmdExecute(f"icacls {file} /grant Everyone:F",isPrint=False)
            time.sleep(1) # 有点慢
        elif systemName == "Linux":
            if not os.path.exists(folder):
                systemCmdExecute(f"mkdir -p {folder}",isPrint=False)
                systemCmdExecute(f"chmod -R 777 {folder}",isPrint=False)
            if file is not None and not os.path.exists(file):
                systemCmdExecute(f"touch {file}",isPrint=False)
                systemCmdExecute(f"chmod -R 777 {file}",isPrint=False)
        else:
            print(f"{datetime.datetime.now()} checkPath error: unknown {systemName}")
            return False
        return True
    except Exception as e:
        print(f"{datetime.datetime.now()} checkPath error: {e} {traceback.format_exc()}")
        return False

def removePath(path): # 删除文件
    try:
        path = os.path.abspath(path) # 获取绝对路径，以适配./xxx等相对路径
        # 获取文件夹路径
        if "." in os.path.basename(path): # 最后一个路径存在"."则path为文件，否则path为文件夹
            file = True
        else:
            file = False

        systemName = platform.system()
        if systemName == "Windows":
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            # if file:
            #     systemCmdExecute(f"del {path}",isPrint=False)
            # else:
            #     systemCmdExecute(f"rd /s /q {path}",isPrint=False)
        elif systemName == "Linux":
            systemCmdExecute(f"rm -rf {path}",isPrint=False)
        else:
            print(f"{datetime.datetime.now()} checkPath error: unknown {systemName}")
            return False
        return True
    except Exception as e:
        print(f"{datetime.datetime.now()} checkPath error: {e} {traceback.format_exc()}")
        return False
class JsonFileManage:
    def __init__(self, filePath):
        self.filePath = os.path.abspath(filePath)

    def save(self, data):
        print(f"{datetime.datetime.now()}, JsonFileManage save {self.filePath}")
        checkPath(self.filePath)
        with open(self.filePath, "wt") as file:
            data = self.convertSeqToList(data)
            json.dump(data, file)

    def load(self):
        print(f"{datetime.datetime.now()}, JsonFileManage load {self.filePath}")
        if not os.path.exists(self.filePath):  # 没有
            print(f"{datetime.datetime.now()}, JsonFileManage load fail: no file path is {self.filePath}")
            return None
        try:  # json文件格式错误
            with open(self.filePath, "rt") as file:
                data = json.load(file)
            return data
        except Exception as e:
            print(f"{datetime.datetime.now()}, JsonFileManage load fail:error: {e}\n{traceback.format_exc()}")
            return None

    def convertSeqToList(self, data):  # 序列转list
        if isinstance(data, dict):
            return {key: self.convertSeqToList(value) for key, value in data.items()}
        elif isinstance(data, (np.ndarray, tuple, list)):
            return [self.convertSeqToList(i) for i in data]
        else:
            return data

class YamlFileManage:
    def __init__(self, filePath):
        self.filePath = os.path.abspath(filePath)
    def save(self, data):
        print(f"{datetime.datetime.now()}, YamlFileManage save {self.filePath}")
        checkPath(self.filePath)
        with open(self.filePath, "wt") as file:
            data = self.convertSeqToList(data)
            yaml.dump(data,file, default_flow_style=False)
    def load(self):
        print(f"{datetime.datetime.now()}, YamlFileManage load {self.filePath}")
        if not os.path.exists(self.filePath):  # 没有
            print(f"{datetime.datetime.now()}, YamlFileManage load fail: no file path is {self.filePath}")
            return None
        try:  # yaml文件格式错误
            with open(self.filePath, "rt") as file:
                data = yaml.safe_load(file)
            return data
        except Exception as e:
            print(f"{datetime.datetime.now()}, YamlFileManage load fail:error: {e}\n{traceback.format_exc()}")
            return None

    def convertSeqToList(self, data):  # 序列转list
        if isinstance(data, dict):
            return {key: self.convertSeqToList(value) for key, value in data.items()}
        elif isinstance(data, (np.ndarray, tuple, list)):
            return [self.convertSeqToList(i) for i in data]
        else:
            return data

def findFiles(searchPath, filterBySuffix=None, mode=0):
    # mode:0 返回绝对路径，1 返回带一层searchPath的相对路径，2 返回不带searchPath的相对路径
    searchPath = os.path.abspath(searchPath)  # 转绝对路径以适应./..等符号
    if mode == 0:
        n = 0
    elif mode == 1:
        n = len(searchPath) - len(os.path.basename(searchPath))
    elif mode == 2:
        n = len(searchPath) + 1
    else:
        raise ValueError("mode error!")
    folderStructure = os.walk(searchPath)  # 获取目录结构
    filePaths = []
    for i in folderStructure:
        currentFolderDirs, sonFolderNames, sonFileNames = i
        currentFolderDirs = currentFolderDirs[n:]
        for sfn in sonFileNames:
            if filterBySuffix is None or os.path.splitext(sfn)[1] in filterBySuffix:
                filePaths.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
    return filePaths



#Deprecation!
def copyTo7Z(zipOutputPath, password=None):
    if not os.path.exists(zipOutputPath):
        os.mkdir(zipOutputPath)
    zipName = os.path.join(zipOutputPath, os.path.basename(os.path.dirname(__file__)) + ".7z").replace("\\", "/")
    fileAbsPaths = findFiles(os.path.dirname(__file__), mode=0)
    fileRelatePaths = findFiles(os.path.dirname(__file__), mode=2)
    with py7zr.SevenZipFile(zipName, 'w', password=password) as f:
        for absFile, RelateFile in zip(fileAbsPaths, fileRelatePaths):
            f.write(absFile, arcname=RelateFile)

#Deprecation!
def mergeTo7Z(mergeZip, password=''):
    fileAbsPaths = findFiles(os.path.dirname(__file__), mode=0)
    fileRelatePaths = findFiles(os.path.dirname(__file__), mode=1)
    with py7zr.SevenZipFile(mergeZip, 'a', password=password) as f:
        for absFile, RelateFile in zip(fileAbsPaths, fileRelatePaths):
            f.write(absFile, arcname=RelateFile)

# 管理目录空间：
class FileSpaceManage():
    def __init__(self,directory,limit=None,intervalTime="1s"):
        self.directory=directory
        self.timeUnits = {'S': 1, 'M': 60, 'H': 60 ** 2, 'D': 60 ** 2 * 24, 'MO': 60 ** 2 * 24 * 30, 'Y': 60 ** 2 * 24 * 365} # 单位s
        self.sizeUnits = {'B': 1, 'KB': 1024, 'MB': 1024 ** 2, 'GB': 1024 ** 3, 'TB': 1024 ** 4} # 单位b
        if limit is  not  None:
            if isinstance(limit,str):
                limit = [limit]
            self.limit = limit
            number, unit = self.splitNumberAndUnit(intervalTime)
            self.intervalTime = number * self.timeUnits[unit]  # 转单位为秒
            threading.Thread(target=self.autoManage).start()

    def splitNumberAndUnit(self,value):
        numberRule = re.compile(r'[+-]?\d+\.?\d*[eE]?[+-]?\d?')
        number = re.search(numberRule, value).group()
        unit = value[len(number):]
        number = float(number)
        return number, unit.upper()
    def autoManage(self):
        try:
            mangeTime = -self.intervalTime
            while True:
                nowTime = time.time()
                if nowTime - mangeTime > self.intervalTime:
                    for limit in self.limit:
                        self.manage(limit)
                    mangeTime=nowTime
                else:
                    time.sleep(self.intervalTime)
        except Exception as e:
            print(f"exception:{e}\ntraceback:{traceback.format_exc()}")

    def manage(self,limit):# 只对顶层目标管理，必须全是目录或者全是文件，不能共存
        dataPath = os.listdir(self.directory)
        dataPath =[os.path.join(self.directory,i) for i in dataPath]
        dataPathTime=[]
        # 可能运行中文件会消失
        for path in dataPath:
            try:
                modifyTime = os.path.getmtime(path)
                dataPathTime.append([modifyTime,path])
            except Exception as e:
                print(f"exception:{e}\ntraceback:{traceback.format_exc()}")

        dataPath = sorted(dataPathTime, key=lambda x: x[0],reverse=True)  # 越早的数据越排后面

        number, unit=self.splitNumberAndUnit(str(limit))
        if unit in self.timeUnits:
            timeLimit = number * self.timeUnits[unit]  # 转单位为秒
            currentTime = datetime.datetime.now().timestamp()
            for data in dataPath:
                modifyTime, path = data
                if currentTime - modifyTime > timeLimit:
                    print(f"{datetime.datetime.now()} FileSpaceManage delete {path}")
                    # 可能运行中文件会消失
                    try:
                        removePath(path)
                    except Exception as e:
                        print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
        elif unit in self.sizeUnits:
            sizeLimit = number * self.sizeUnits[unit]  # 转单位为字节
            currentSize = 0
            for data in dataPath:
                modifyTime, path = data
                if os.path.isfile(path):
                    currentSize += os.path.getsize(path)
                elif os.path.isdir(path):
                    dataPath = findFiles(path)
                    totalSize = 0
                    for filePath in dataPath:
                        try:
                            totalSize += os.path.getsize(filePath)
                        except Exception as e:
                            print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
                    currentSize +=totalSize
                else:
                    print(f"file manage error {path}")
                # 可能运行中文件会消失
                if currentSize > sizeLimit:
                    try:
                        removePath(path)
                    except Exception as e:
                        print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
        else:
            for data in dataPath[int(number):]:
                modifyTime, path = data
                print(f"{datetime.datetime.now()} FileSpaceManage delete {path}")
                # 可能运行中文件会消失
                try:
                    removePath(path)
                except Exception as e:
                    print(f"exception:{e}\ntraceback:{traceback.format_exc()}")


if __name__=="__main__":
    # checkPath("./xyp")

    # checkPath("./xyp/xyp.xyp")
    # a=FileSpaceManage(r"D:\xyp\a\bice\guard_tvt\aa",["100b"],"1s")
    time.sleep(555)