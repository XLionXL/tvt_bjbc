import os
import paramiko
import time
import threading
from xypFileTool import findFiles, checkPath


class SSH(paramiko.SSHClient):
    def __init__(self,ip,port,user,pwd,maxRepeat=3):
        super().__init__()
        self.ip=ip
        self.port=int(port)
        self.user=user
        self.pwd = pwd
        self.cmd = lambda x: f"echo '{self.pwd}' | sudo -S {x}"
        self.maxRepeat = maxRepeat
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.open()

    def open(self,):
        for i in range(self.maxRepeat):
            try:
                self.connect(hostname=self.ip ,port=self.port,username=self.user,password=self.pwd)
                self.sftp = self.open_sftp()
                print(f"open ssh done,ssh={(self.ip,self.port)}")
                return True
            except Exception as e:
                time.sleep(0.5)
                print(f"open ssh error:{e},ssh={(self.ip,self.port)},try again {i}...")
        return False
    def rm(self,path):
        self.executeCommand(f"rm -rf {path}")

    def executeCommand(self,cmd):
        stdin, stdout, stderr= self.exec_command(self.cmd(cmd))
        return stdin,stdout.read().decode(),stderr.read().decode()

    # 安全下载文件
    def sftpGet(self,remoteFilePath, localFilePath):
        print(f"sftpPut start {remoteFilePath} >>> {localFilePath}")
        localFolder = os.path.dirname(localFilePath)
        remoteFileSize = self.sftp.stat(remoteFilePath).st_size

        checkPath(localFolder)# 判断本地目录是否存在
        for idx in range(self.maxRepeat):  # 重传次数
            try:
                self.sftp.get(remoteFilePath, localFilePath)
            except Exception as e:
                print(f"sftpPut error {idx} {e}, trying restart ssh ...")
                self.open()
            try:
                localFileSize =  os.path.getsize(localFilePath)
                print(os.path.exists(localFilePath),localFilePath)
                if remoteFileSize != localFileSize:
                    print(f"sftpPut error {idx}, trying retransmission...")
                    continue
                else:
                    print(f"sftpPut done {remoteFilePath} >>> {localFilePath}")
                    return True
            except:
                print(f"sftpPut error {idx}, trying retransmission...")  # 文件不存在stat会报错
                continue
        print(f"sftpPut error {remoteFilePath} >>> {localFilePath}, retransmission exceed limit")
        return False

    # 安全上传文件
    def sftpPut(self,localFilePath,remoteFilePath):
        print(f"sftpPut start {localFilePath} >>> {remoteFilePath}")
        remoteFolder = os.path.dirname(remoteFilePath)
        localFileSize = os.path.getsize(localFilePath)

        stdin, stdout, stderr = self.executeCommand(f"test -d {remoteFolder} && echo 1") # 判断目录是否存在
        if not stdout.read().decode():
            print(f"remote folder absent, create:{remoteFolder}")
            self.executeCommand(f"mkdir -p {remoteFolder}")
            self.executeCommand(f"chmod 777 -R {remoteFolder}")
            stdin, stdout, stderr = self.executeCommand(f"test -d {remoteFolder} && echo 1")
            if not stdout.read().decode():
                print(f"sftpPut error, creat {remoteFolder} fail")
                return 0
            else:
                print(f"remote folder {remoteFolder} create done")

        for idx in range(self.maxRepeat):# 重传次数
            try:
                if localFileSize > 50*1024*1024: # 大于50mb的数据采用断点重传
                    # 检查远程文件传输情况
                    try:
                        remoteFileSize = self.sftp.stat(remoteFilePath).st_size
                    except:
                        remoteFileSize = 0
                    # 本地文件大于远程文件，还没上传完毕，则进行断点续传
                    if localFileSize > remoteFileSize:
                        with open(localFilePath, 'rb') as data:
                            # 定位到上次上传的位置
                            data.seek(remoteFileSize)
                            # 追加上传
                            self.sftp.file(remoteFilePath, mode='ab').write(data.read())
                else:
                    self.sftp.put(localFilePath, remoteFilePath)
            except:
                print(f"sftpPut error {idx}, trying restart ssh ...")
                self.open()
            try:
                remoteFileSize = self.sftp.stat(remoteFilePath).st_size# 如果文件存在
                if localFileSize != remoteFileSize:
                    print(f"sftpPut error {idx}, trying retransmission...")
                    continue
                else:
                    print(f"sftpPut done {localFilePath} >>> {remoteFilePath}")
                    return True
            except:
                print(f"sftpPut error {idx}, trying retransmission...") #文件不存在stat会报错
                continue
        print(f"sftpPut error {localFilePath} >>> {remoteFilePath}, retransmission exceed limit")
        return False

    # 将某个目录内的结构完整打发送到目的目录
    def copyToRemote(self,localFolder, remoteFolder,filterBySuffix=None):
        # 创建远程目标目录
        fileAbsPaths = findFiles(localFolder,filterBySuffix, mode=0)
        fileRelatPaths = findFiles(localFolder,filterBySuffix, mode=2)
        for localFileAbsPath, localFileRelatPath in zip(fileAbsPaths, fileRelatPaths):
            remoteFileAbsPath = os.path.join(remoteFolder, localFileRelatPath).replace("\\","/")
            self.sftpPut(localFileAbsPath, remoteFileAbsPath)
        print('copyToRemote：done!')



    def remoteRunPythonCode(self,pythonCode):
        threading.Thread(target=self.remoteRunPythonCodeThread,args=(pythonCode,)).start()
        print('remoteRunPythonCode: done!')
        killRemoteRunPythonCode = lambda : self.executeCommand(
            f"ps aux|grep remoteRunPythonCode|awk '{{print $2}}'|sudo xargs kill -9")  # 返回杀死方法
        return killRemoteRunPythonCode
    def remoteRunPythonCodeThread(self,pythonCode):
        stdin, stdout, stderr = self.executeCommand(f"ps aux|grep remoteRunPythonCode|awk '{{print $2}}'|sudo xargs kill -9")
        print(stderr)
        stdin, stdout, stderr = self.executeCommand(f"touch /ssd/xyp/remoteRunPythonCode.py")
        print(stderr)
        stdin, stdout, stderr = self.executeCommand(f"chmod 777 /ssd/xyp/remoteRunPythonCode.py")
        print(stderr)
        stdin, stdout, stderr = self.executeCommand(f"cat << EOF > /ssd/xyp/remoteRunPythonCode.py {pythonCode}")
        print(stderr)
        stdin, stdout, stderr = self.executeCommand(f"python3 /ssd/xyp/remoteRunPythonCode.py")
        print(stderr)



    def copyToLocal(self, remoteFolder,localFolder,filterBySuffix=None):
        s=lambda x: f'''
import os
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
                filePaths.append(os.path.join(currentFolderDirs, sfn))
    return filePaths
fileAbsPaths = {x}
print(fileAbsPaths)
        '''
        stdin, stdout, stderr = self.executeCommand(f"touch /ssd/xyp/a.py")
        stdin, stdout, stderr = self.executeCommand(f"chmod 777 /ssd/xyp/a.py")
        txt=s(f"findFiles('{remoteFolder}',{filterBySuffix}, mode=0)")
        stdin, stdout, stderr = self.executeCommand(f"cat << EOF > /ssd/xyp/a.py {txt}")
        stdin, stdout, stderr = self.executeCommand(f"python3 /ssd/xyp/a.py")
        # 创建远程目标目录
        fileAbsPaths =   eval(stdout)

        txt = s(f"findFiles('{remoteFolder}',{filterBySuffix}, mode=2)")
        stdin, stdout, stderr = self.executeCommand(f"cat << EOF > /ssd/xyp/a.py {txt}")
        stdin, stdout, stderr = self.executeCommand(f"python3 /ssd/xyp/a.py")
        fileRelatPaths = eval(stdout)
        for remoteFileAbsPath, remoteFileRelatPath in zip(fileAbsPaths, fileRelatPaths):
            localFileAbsPath = os.path.join(localFolder, remoteFileRelatPath).replace("\\","/")
            self.sftpGet(remoteFileAbsPath, localFileAbsPath)
        print('copyToLocal：done!')


if __name__ == "__main__":
    # ssh = SSH("10.8.4.208", "22", "tvt", "TDDPc5kc4WnYcy", 1)
    # / ssd / alarmpic / alarmFrame / 2024 - 04 - 18 /
    ssh = SSH("192.168.90.41", "22", "tvt", "TDDPc5kc4WnYcy", 3)
    ssh.copyToLocal("/ssd/alarmpic/alarmFrame/2024-04-18/",r"D:\xyp\guardData\0426")

    # stdout.read().decode()



    # ssh.sftpPut("./a.py","/ssd/xyp1/xyp3/a.b")
    # ssh.sftpPut("./Xiphos_Universal_guard_exe_Release_V1.23.08.18_EN_xyp.zip","/ssd/xyp1/xyp3/a.c")
    # ssh.copyToRemote("./.idea","/ssd/xyp1/xyp3/a")

