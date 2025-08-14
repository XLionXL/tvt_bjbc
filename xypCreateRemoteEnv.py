# nano
from xypRemoteTool import SSH

# ssh = SSH("121.62.22.121", "47350", "tvt", "TDDPc5kc4WnYcy", 1)
ssh = SSH("192.168.137.5", "22", "tvt", "TDDPc5kc4WnYcy", 1)


ssh.executeCommand("timedatectl set-ntp true") # 先对时，不然可能安装失败
ssh.executeCommand("mkdir -p /ssd/xyp/xypTemp")
ssh.executeCommand("mkdir -p /ssd/xyp/xypTest")
ssh.executeCommand("mkdir -p /ssd/xyp/xypEnv")
ssh.executeCommand("mkdir -p /ssd/xyp/xypLog")
ssh.executeCommand("chmod 777 -R /ssd/xyp")
ssh.executeCommand("touch /ssd/xyp/sn")
# 安装python venv
# ssh.copyToRemote(r"C:\Users\admins\Desktop\env","/var/cache/apt/archives/")
a,b,c=ssh.executeCommand("apt install -y  python3.6-venv")
#ps aux | grep dpkg # 找到其他进程apt并杀掉

print(b.read().decode())
print(c.read().decode())
ssh.executeCommand("rm -rf /ssd/xyp/xypEnv/py36")
a,b,c=ssh.executeCommand("python3.6 -m venv --system-site-packages /ssd/xyp/xypEnv/py36")
print(b.read().decode())
print(c.read().decode())

# 确实py7rz的设备安装py7rz后执行
# ssh.executeCommand("rm /home/tvt/.local/lib/python3.6/site-packages/psutil/_psutil_linux.cpython-36m-aarch64-linux-gnu.so")
#source /ssd/xyp/xypEnv/py36/bin/activate