import platform
import os
import platform
import time
# import requests
# import zipfile
import urllib.request
from xypSystemCmd import systemCmdExecute


def checkPath(path, pwd=None): # 检查文件路径，文件路径不存在则创建路径
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
                systemCmdExecute(f"mkdir {folder}", pwd)
                systemCmdExecute(f"icacls {folder} /grant Everyone:F /T", pwd) # 文件夹才有/T
            if file is not None and not os.path.exists(file):
                systemCmdExecute(f"cd . > {file}", pwd)
                systemCmdExecute(f"icacls {file} /grant Everyone:F", pwd)
            time.sleep(1) # 有点慢
        elif systemName == "Linux":
            if not os.path.exists(folder):
                systemCmdExecute(f"mkdir -p {folder}",pwd)
                systemCmdExecute(f"chmod -R 777 {folder}", pwd)
            if file is not None and not os.path.exists(file):
                systemCmdExecute(f"touch {file}",pwd)
                systemCmdExecute(f"chmod -R 777 {file}",pwd)
        else:
            print(f"{datetime.datetime.now()} checkPath error: unknown {systemName}")
            return False
        return True
    except Exception as e:
        print(f"{datetime.datetime.now()} checkPath error: {e} {traceback.format_exc()}")
        return False

class CondarcHandle():
    def __init__(self):
        self.data = {
            "channels": ["https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main",
                         "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r",
                         "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2", ]
        }



    def load(self,file):
        data = {}
        while True:
            line =file.readline()
            if not line:
                break
            else:
                if not line.startswith(" "):
                    nowData = line.strip()
                    data[nowData]=[]
                else:
                    data[nowData].append(line.rstrip())
        return data


    def save(self):
        checkPath(r"C:\Users\.condarc","001229")
        with open(r"C:\Users\.condarc", "wt") as f:
            for k,v in self.data.items():
                f.write(k+":\n")
                for i in v:
                    f.write("  - "+i+"\n")


    def load(self,file):
        data = {}
        while True:
            line =file.readline()
            if not line:
                break
            else:
                if not line.startswith(" "):
                    nowData = line.strip()
                    data[nowData]=[]
                else:
                    data[nowData].append(line.rstrip())
        return data
    def set(self,name,value):
        if isinstance(value,list):
            self.data[name] = value
        else:
            self.data[name] = [value]
    def remove(self,name,value):
        self.data[name].remove(value)

    def append(self, name, value):
        if value not in self.data[name]:
            self.data[name].append(value)


class PipConfigHandle():
    def __init__(self):
        self.data ='''[global]
index-url=https://pypi.mirrors.ustc.edu.cn/simple/
extra-index-url=
	http://mirrors.aliyun.com/pypi/simple/
	http://pypi.douban.com/simple/
	https://pypi.tuna.tsinghua.edu.cn/simple/

[install]
trusted-host=
	pypi.mirrors.ustc.edu.cn
	mirrors.aliyun.com
	pypi.douban.com
	pypi.tuna.tsinghua.edu.cn
'''


    def save(self):
        checkPath(r"C:\Users\pip\pip.ini","001229")
        with open(r"C:\Users\pip\pip.ini", "wt") as f:
            f.write(self.data)




def window64GetEnvPackage(envPath):
    flag, output, error = systemCmdExecute(f"conda activate {envPath} && conda list")
    existPkg = {}
    for pkg in output.split("\n"):
        pkg = pkg.strip()
        if pkg[0].isalpha():  # 字母开头
            attr = [part for part in pkg.split(' ') if part.strip()]
            existPkg[attr[0]]=attr[1]
    savePath = f"./{os.path.basename(envPath)}_Env.xyp"
    checkPath(savePath)
    with open(savePath, "wt") as f:
        f.write(str(existPkg))
    return existPkg

def window64InstallPackage(envPath, pkgInfo):
    # pkgInfo: [[packageName,packageVersion]]


    taskList = []
    if "python" in pkgInfo: # python调到第一
        taskList.append(["python",pkgInfo.pop("python")])
        taskList.append(["pip", None])
    for pkgName,version in pkgInfo.items():
        taskList.append([pkgName,version])

    existPackage = window64GetEnvPackage(envPath)

    for pkg in taskList:
        pkgName,version=pkg
        if pkgName not in existPackage or (version is not None and version != existPackage[pkgName]):
            print(f"{pkgName}{'=' + version if version else ''} install ...")
            cmd = f"conda install {pkgName}{'=' + version if version else ''} -y"
            flag, output, error = systemCmdExecute(f"conda activate {envPath} && {cmd}")
            if error:
                cmd = f"pip install {pkgName}{'==' + version if version else ''}"
                flag, output, error = systemCmdExecute(f"conda activate {envPath} && {cmd}")
                if error:
                    print(f"window64InstallPackage error: {pkgName}")
                    continue
        print(f"window64InstallPackage done: {pkgName}")

    window64GetEnvPackage(envPath)


def windows64InstallCondaEnv(envPath, pkgInfo={},fixMode = False):

    flag,output,error = systemCmdExecute("conda -V")
    if "conda" not in output: # 安装conda
        url = 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe'  # 要下载的文件的网址
        savePath = './miniCondaInstall.exe'  # 保存文件的路径
        urllib.request.urlretrieve(url, savePath)
        print("请手动安装...")
        systemCmdExecute(os.path.basename(savePath))
        time.sleep(1)
        flag, output, error = systemCmdExecute("conda -V")
        if "conda" not in output:
            print("安装成功后出现conda找不到的情况, 请尝试重新运行或者重启IDE, 这可能是由于IDE不会刷新环境变量导致的...")
            exit()

    # 配置conda配置
    flag, output, error = systemCmdExecute(f"conda config --show root_prefix")
    condaRootPath = output.split(" ")[1]
    myEnvRootPath  = os.path.join(condaRootPath, 'xypEnv')
    condarcHandle = CondarcHandle()
    condarcHandle.set("envs_dirs",[condaRootPath,myEnvRootPath])
    condarcHandle.save()
    # 配置pip配置
    pipConfigHandle=PipConfigHandle()
    pipConfigHandle.save()


    flag,output,error = systemCmdExecute("conda env list")
    if os.path.dirname(envPath):
        envPath=envPath
    else:
        envPath = os.path.join(myEnvRootPath, envPath)
    if envPath not in output:
        print(f"创建环境:{envPath}")
        flag, output, error = systemCmdExecute(f"conda create -p {envPath} -y")
    else:
        print(f"环境已经存在:{envPath}")

    if fixMode: # 重新创建环境
        print("环境已经存在，重新创建环境")
        originPkgInfo = window64GetEnvPackage(envPath)
        flag, output, error = systemCmdExecute(f"conda remove -p {envPath} --all -y") # 删除环境
        flag, output, error = systemCmdExecute(f"conda create -p {envPath} -y")

        originPkgInfo.update(pkgInfo)
        window64InstallPackage(envPath, originPkgInfo)
    else:
        window64InstallPackage(envPath, pkgInfo)



if __name__ == "__main__":
    # flag,output,error = systemCmdExecute("conda env list")
    pkgInfo = window64GetEnvPackage(r"C:\Users\admins\miniconda3\envs\py38")
    # pkgInfo = eval(open("./py38_Env(1).xyp").read())
    for p in pkgInfo:
        if p != "python":
            pkgInfo[p]=None
        else:
            pkgInfo[p] = "3.7.9"
    windows64InstallCondaEnv(r"py37",pkgInfo,)
