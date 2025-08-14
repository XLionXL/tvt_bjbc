import os
import paramiko
import threading
import time
from xypFileTool import findFiles





class SSH(paramiko.SSHClient):
    def __init__(self,ip,port,user,pwd,maxRepeat=3):
        super().__init__()
        self.ip=ip
        self.port=port
        self.user=user
        self.pwd = pwd
        self.cmd = lambda x: f"echo '{self.pwd}' | sudo -S {x}"
        self.maxRepeat = maxRepeat
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.isOpen = False
        self.open()
        # threading.Thread(target=self.open).start()

    def open(self,):
        i=0
        while True:
            try:
                self.connect(hostname=self.ip ,port=self.port,username=self.user,password=self.pwd)
                self.sftp = self.open_sftp()
                print(f"open ssh done,ssh={(self.ip,self.port)}")
                self.isOpen = True
                break
            except Exception as e:
                time.sleep(0.5)
                i+=1
                print(f"open ssh error:{e},ssh={(self.ip,self.port)},try again {i}...")

    def rm(self,path):
        self.executeCommand(f"rm -rf {path}")

    def executeCommand(self,cmd):
        stdin, stdout, stderr= self.exec_command(self.cmd(cmd))
        return stdin,stdout,stderr


    # 安全上传文件
    def sftpPut(self,localFilePath,remoteFilePath):
        try:
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
        except:
            print(f"sftpPut error {idx}, trying restart ssh ...")
            self.open()

    # 将某个目录内的结构完整打发送到目的目录
    def copyToRemote(self,localFolder, remoteFolder,filterBySuffix=None):
        # 创建远程目标目录
        fileAbsPaths = findFiles(localFolder,filterBySuffix, mode=0)
        fileRelatPaths = findFiles(localFolder,filterBySuffix, mode=2)
        for localFileAbsPath, localFileRelatPath in zip(fileAbsPaths, fileRelatPaths):
            remoteFileAbsPath = os.path.join(remoteFolder, localFileRelatPath).replace("\\","/")
            self.sftpPut(localFileAbsPath, remoteFileAbsPath)
        print('copyToRemote：done!')





if __name__ == "__main__":
    # ssh = SSH("10.8.4.208", "22", "tvt", "TDDPc5kc4WnYcy", 1)

    ssh = SSH("58.20.230.32", "10080", "tvt", "TDDPc5kc4WnYcy", 1)
    # ssh.sftpPut("./a.py","/ssd/xyp1/xyp3/a.b")
    # ssh.sftpPut("./Xiphos_Universal_guard_exe_Release_V1.23.08.18_EN_xyp.zip","/ssd/xyp1/xyp3/a.c")
    ssh.copyToRemote("./.idea","/ssd/xyp1/xyp3/a")

