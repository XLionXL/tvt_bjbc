import datetime
import os
import site
import subprocess
import traceback


def list_all_folders(directory):
    folder_list = []
    # 遍历目录下的所有文件和文件夹
    for root, dirs, files in os.walk(directory):
        # 如果当前目录下有子文件夹，则将其绝对路径加入列表
        if dirs:
            for folder in dirs:
                folder_list.append(os.path.abspath(os.path.join(root, folder)))
    return folder_list
print(list_all_folders(os.path.abspath(".")))
print(site.getsitepackages())
objectFolder=site.getsitepackages()[0] # 这个目录才是sitepackages的目录
# objectFolder=sys.path[0]
def linuxCmdExecute(cmd, pwd=None):
    try:
        if pwd is not None:  # 有密码，执行管理员命令
            cmd = f"sudo -S {cmd}"
            pwdCmd = (pwd + "\n").encode('utf-8')
        else:  # 密码为空
            pwdCmd = pwd

        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate(input=pwdCmd)  # 等待执行完并返回输出
        output = output.decode('utf8').strip()
        error = error.decode('utf8').strip()
        print("*****************************************",
              "===============cmd=================",
              f"{datetime.datetime.now()}, cmd:{cmd}",
              "==============output==============",
              output if output else "None",
              "==============error===============",
              error if error else "None",
              "*****************************************\n", sep="\n")
        return True, output, error
    except Exception as e:
        error = f"{datetime.datetime.now()} windowCmdExecute cmd {cmd} error: {e} {traceback.format_exc()}"
        print(error)
        return False, '', error
pkgName = os.path.basename(os.path.dirname(__file__))

pthFile=os.path.join(objectFolder,pkgName+".pth")
pwd="TDDPc5kc4WnYcy"
if not  os.path.exists(pthFile):
    linuxCmdExecute(f"touch {pthFile}", pwd)
    linuxCmdExecute(f"chmod -R 777 {objectFolder}", pwd)

import sys
print(sys.path)
# with open(pthFile,"wt") as f:
#     f.write(f"import sys;roads={list_all_folders(os.path.abspath('.'))};sys.path.extend([i for i in roads]);"
# )
pkgFolder=os.path.abspath(".")
with open(pthFile,"wt") as f:
    for i in list_all_folders(os.path.abspath(".")):
        f.write(i+"\n")
    f.write(pkgFolder+"\n")
    f.write(os.path.dirname(pkgFolder)+"\n")
    print(os.path.dirname(pkgFolder))