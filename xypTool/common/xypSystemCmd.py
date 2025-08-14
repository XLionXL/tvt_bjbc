import datetime
import platform
import subprocess
import traceback

globPwd="TDDPc5kc4WnYcy"
def windowCmdExecute(cmd, pwd=None,isPrint=True):
    try:
        if pwd is not None:  # 有密码，执行管理员命令
            cmd = f'powershell -Command Start-Process powershell  -WindowStyle Hidden -Verb RunAs -ArgumentList """{cmd}"""' # 三个"""不能少
            pwdCmd = (pwd + "\n").encode('utf-8')
        elif globPwd is not None:  # 密码为空
            cmd = f'powershell -Command Start-Process powershell  -WindowStyle Hidden -Verb RunAs -ArgumentList """{cmd}"""' # 三个"""不能少
            pwdCmd = (globPwd + "\n").encode('utf-8')
        else:
            pwdCmd = pwd
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        o, e = p.communicate(input=pwdCmd)  # 等待执行完并返回输出
        try:
            output = o.decode('utf-8').split("\x1b")[0].strip()
            error = e.decode('utf-8').split("\x1b")[0].strip()
        except:
            output = o.decode('gbk').split("\x1b")[0].strip()
            error = e.decode('gbk').split("\x1b")[0].strip()
        if isPrint:
            print("*****************************************",
                  "===============cmd=================",
                  f"{datetime.datetime.now()}, cmd:{cmd}",
                  "==============output==============",
                  output if output else "None",
                  "==============error===============",
                  error if error else "None",
                  "*****************************************\n",sep="\n")
            return True, output, error
    except Exception as e:
        error =f"{datetime.datetime.now()} windowCmdExecute cmd {cmd} error: {e} {traceback.format_exc()}"
        print(error)
        return False, '', error

def linuxCmdExecute(cmd, pwd=None,isPrint=True):
    try:
        if pwd is not None:  # 有密码，执行管理员命令
            cmd = f"sudo -S {cmd}"
            pwdCmd = (pwd + "\n").encode('utf-8')
        elif globPwd is not None:  # 密码为空
            cmd = f"sudo -S {cmd}"
            pwdCmd = (globPwd + "\n").encode('utf-8')
        else:
            pwdCmd = pwd

        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate(input=pwdCmd)  # 等待执行完并返回输出
        output = output.decode('utf8').strip()
        error = error.decode('utf8').strip()
        if isPrint:
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
def systemCmdExecute(cmd, pwd=None,isPrint=True):
    # 返回：执行是否成功标识符，运行输出，错误输出
    systemName = platform.system()
    if systemName == "Windows":
        return windowCmdExecute(cmd,pwd,isPrint)
    elif systemName == "Linux":
        return linuxCmdExecute(cmd, pwd,isPrint)
    else:
        print(f"{datetime.datetime.now()} systemCmdExecute error: unknown {systemName}")
        return False,None,None

if __name__=="__main__":
    systemName = platform.system()
    if systemName == "Windows":
        systemCmdExecute("dir")
    elif systemName == "Linux":
        systemCmdExecute("ls")