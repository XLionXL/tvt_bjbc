import os
import paramiko
import py7zr

from xypPrintDebug import xypPrint


def findFiles(searchPath, filterBySuffix=('.py'), mode=0):
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
            if os.path.splitext(sfn)[1] in filterBySuffix:
                filePaths.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
    return filePaths

def copyToRemote(remoteIp,remotePort,remoteUsername,remotePassword,remoteFolder):
    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 连接到远程服务器
    ssh.connect(hostname=remoteIp, port=remotePort, username=remoteUsername,password=remotePassword)
    # 创建SFTP客户端
    sftp= ssh.open_sftp()
    # 创建远程目标目录
    fileAbsPaths = findFiles(os.path.dirname(__file__), mode=0)
    fileRelatPaths = findFiles(os.path.dirname(__file__), mode=1)
    for localFileAbsPath,localFileRelatPath in zip(fileAbsPaths,fileRelatPaths):
        if ".git" in localFileAbsPath:
            continue
        remoteFilePath = os.path.join(remoteFolder, localFileRelatPath).replace("\\", "/")
        ssh.exec_command('mkdir -p {}'.format(os.path.dirname(remoteFilePath)))
        sftp.put(localFileAbsPath, remoteFilePath)
        xypPrint('{} >>> {}'.format(localFileAbsPath, remoteFilePath))
    xypPrint('copyToRemote：done!')
    sftp.close()
    ssh.close()


def copyTo7Z(zipOutputPath,password=None):
    if not os.path.exists(zipOutputPath):
        os.mkdir(zipOutputPath)
    zipName = os.path.join(zipOutputPath,os.path.basename(os.path.dirname(__file__))+".7z").replace("\\","/")
    fileAbsPaths = findFiles(os.path.dirname(__file__), mode=0)
    fileRelatPaths = findFiles(os.path.dirname(__file__), mode=2)
    with py7zr.SevenZipFile(zipName, 'w', password=password) as f:
        for absFile, relatFile in zip(fileAbsPaths, fileRelatPaths):
            f.write(absFile, arcname=relatFile)

def mergeTo7Z(mergeZip,password=''):
    fileAbsPaths = findFiles(os.path.dirname(__file__), mode=0)
    fileRelatPaths = findFiles(os.path.dirname(__file__), mode=1)
    with py7zr.SevenZipFile(mergeZip, 'a', password= password) as f:
        for absFile, relatFile in zip(fileAbsPaths, fileRelatPaths):
            f.write(absFile, arcname=relatFile)

if __name__ == "__main__":
    copyTo7Z("./test","123")
    mergeTo7Z("./test/xypDebugTool.7z")
    copyToRemote("58.20.230.32","10080" , 'tvt','TDDPc5kc4WnYcy','/ssd/xyp/xypTest/test')
    print(findFiles(".", mode=0))
    print(findFiles(".", mode=1))
    print(findFiles(".", mode=2))


