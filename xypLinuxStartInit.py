import time
import socket
import psutil
import datetime
import traceback
import subprocess

globPwd="TDDPc5kc4WnYcy"
def linuxCmdExecute(cmd, pwd=None):
    try:
        if pwd is not None:  # 有密码，执行管理员命令
            cmd = f"echo '{pwd}' | sudo -S {cmd}"
        elif globPwd is not None:  # 密码为空
            cmd = f"echo '{globPwd}' | sudo -S {cmd}"

        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()  # 等待执行完并返回输出
        output = output.decode('utf8').strip()
        error = error.decode('utf8').strip()
        return True, output, error
    except Exception as e:
        error = f"{datetime.datetime.now()} windowCmdExecute cmd {cmd} error: {e} {traceback.format_exc()}"
        print(error)
        return False, '', error

# 等待对时服务启动
def waitNtp():
    startTime = time.time()
    while True:
        try:
            flag, output, error = linuxCmdExecute(f"ps aux|grep ntp")
            if "syncNtpDate" in output:
                print(f"waitNtp: ntp service init done")
                break
            else:
                print(f"waitNtp: ntp service init fail")
                time.sleep(0.5)
        except Exception as e:
            print(f"waitNtp: exception:{e}\ntraceback:{traceback.format_exc()}")
    print(f"waitNtp: ntp service init done, spend time {time.time() - startTime}")

# 等待硬件初始化
def waitSystemInit():
    startTime = time.time()
    obj = [("0.0.0.0", 5542), ("0.0.0.0", 5541)]
    while obj:
        ip, port = obj[-1]
        try:
            # 创建socket对象
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置超时时间为1秒
            s.settimeout(1)
            # 尝试连接指定主机和端口
            s.connect((ip, port))
            # 如果连接成功，则端口可达
            print(f"waitSystemInit: {ip}:{port} init success")
            obj.pop(-1)
        except:
            # 如果连接失败，则端口不可达
            print(f"waitSystemInit: {ip}:{port} init fail")
        finally:
            # 关闭socket连接
            s.close()
        time.sleep(0.5)
    print(f"waitSystemInit: init success done,spend time {time.time() - startTime}")

def waitCpuUseRate():
    cpuUseRate = 100
    startTime = time.time()
    while cpuUseRate > 50:
        try:
            cpuUseRate = psutil.cpu_percent(interval=2, percpu=False)
            print(f"waitCpuUseRate: cpu use rate too high: {cpuUseRate}")
        except Exception as e:
            print(f"exception:{e}\ntraceback:{traceback.format_exc()}")
    print(f"waitCpuUseRate: cpu use rate ok: {cpuUseRate},spend time {time.time() - startTime}")
    return cpuUseRate







waitNtp() # 等待对时服务启动
waitSystemInit() # 等待硬件初始化
waitCpuUseRate() # 断电重启很多服务会启动，等待其他服务启动完毕








