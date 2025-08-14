import datetime
import os
import paramiko
import re


def Add(a, b):
    return a + b;

def zip_with_pw(file_path_list,
                des_7z_path=os.path.join(".", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".7z"),
                password="tvt_0123456789_2018",
                ):
    import py7zr
    folder_abspath = os.path.abspath(des_7z_path)
    folder_folder = os.path.dirname(folder_abspath)
    if not os.path.exists(folder_folder):
        os.makedirs(folder_folder)
    z7z_file_path = os.path.abspath(des_7z_path)
    with py7zr.SevenZipFile(z7z_file_path, mode='w', password=password) as zf:
        zf.set_encrypted_header(True)
        for file_path in file_path_list:
            # zf.write(file_path, arcname=file_path)
            print(f"zip_with_pw add {os.path.abspath(file_path)}")
            if os.path.isdir(file_path):
                zf.writeall(file_path,)
            else:
                zf.write(file_path,)


class Pyinstaller_Build:
    def __init__(self, hostIP='192.168.1.200'):
        # 配置属性
        if ":" in hostIP:
            ip_port = hostIP.split(":")
            hostIP, port = ip_port[0:2]
            port = int(port)
        else:
            port=22
        self.config = {
                # 本地项目路径
                'local_path': os.path.abspath('.'),
                # 服务器项目路径
                # 'ssh_path': '/usr/bin/zipx/main_py',
                'ssh_path' : "/usr/bin/zipx/zj-guard",
                # 'ssh_path': '/ssd/xyp/xypTest',
                # 忽视列表
                'ignore_list': [".git"],
                # ssh地址、端口、用户名、密码
                'hostname':hostIP,
                'port': port,
                'username': 'tvt',
                'password': 'TDDPc5kc4WnYcy',
                # 是否强制更新
                'mandatory_update': True,
                # 更新完成后是否重启tomcat
                'restart_tomcat': False,
                # tomcat bin地址
                'tomcat_path': '',
            }
        self.ssh=None
        self.sftp=None

    def init_ssh(self):
        # ssh控制台
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.config['hostname'], port=self.config['port'], username=self.config['username'],
                         password=self.config['password'])
        print(f'{datetime.datetime.now()},ssh connect')

    def init_sftp(self):
        # sftp
        transport = paramiko.Transport((self.config['hostname'], self.config['port']))
        transport.connect(username=self.config['username'], password=self.config['password'])
        self.sftp = paramiko.SFTPClient.from_transport(transport)
        print(f'{datetime.datetime.now()},sftp connect')

    def exists_by_sftp(self, path='/path/to/folder'):
        if self.sftp is None:
            print(f"exists_by_sftp sftp is None,{path}")
            return False
        try:
            dir_stat = self.sftp.stat(path)
        except FileNotFoundError:
            return False
        return True

    def exit_ssh_sftp(self):
        if self.sftp is not None:
            self.sftp.close()
            print(f'{datetime.datetime.now()},sftp close')
        if self.ssh is not None:
            self.ssh.close()
            print(f'{datetime.datetime.now()},ssh close')

    # 检查文件夹是否存在，不存在则创建
    def check_and_creat_folder(self, path):
        stdin, stdout, stderr = self.ssh.exec_command('find ' + path)
        result = stdout.read().decode('utf-8')
        if len(result) == 0:
            print('目录 %s 不存在，创建目录' % path)
            self.ssh.exec_command('mkdir ' + path)
            print('%s 创建成功' % path)
            return 1
        else:
            print('目录 %s 已存在' % path)
            return 0

    def check_file(self, ssh_path):
        # 检查文件是否存在，不存在直接上传
        stdin, stdout, stderr = self.ssh.exec_command('find ' + ssh_path)
        result = stdout.read().decode('utf-8')
        if len(result) >= 10:
            print('%s 存在' % (ssh_path))
            return True
        return False

    # 检查文件是否存在，不存在直接上传，存在检查大小是否一样，不一样则上传
    def check_and_upload_file(self,local_path, ssh_path):
        # 检查文件是否存在，不存在直接上传
        path = '\'' + ssh_path + '\''
        stdin, stdout, stderr = self.ssh.exec_command('find ' + path)
        result = stdout.read().decode('utf-8')
        if len(result) == 0:
            self.sftp.put(local_path, ssh_path)
            print('%s 上传成功' % (ssh_path))
            os.remove(local_path)
            return 1
        else:
            # 存在则比较文件大小
            # 本地文件大小
            lf_size = os.path.getsize(local_path)
            # 目标文件大小
            stdin, stdout, stderr = self.ssh.exec_command('du -b ' + path)
            result = stdout.read().decode('utf-8')
            tf_size = int(result.split('\t')[0])
            print('本地文件大小为：%s，远程文件大小为：%s' % (lf_size, tf_size))
            if lf_size == tf_size:
                print('%s 大小与本地文件相同，不更新' % (ssh_path))
                os.remove(local_path)
                return 0
            else:
                self.sftp.put(local_path, ssh_path)
                print('%s 更新成功' % (ssh_path))
                os.remove(local_path)
                return 1

    def find_PyFiles(self, local_path, ignore_list):
        """
        本地查找并返回local_path下的文件和文件夹
        :param local_path:
        :param ignore_list:
        :return:
        """
        py_file_list = []
        files_and_folders=os.listdir(local_path)
        # 文件列表
        for filename in files_and_folders:
            if ignore_list.count(filename) == 0:
                p = os.path.join(local_path, filename)
                p = p[len(local_path):]
                p = p.replace('\\', '/')
                py_file_list.append(p)
        py_file_list=[x for x in py_file_list if (".py" in x and ".pyc" not in x) or (".spec" in x) ]
        print(py_file_list)
        return py_file_list, []


    def upload_files(self,  file_name_list):
        begin = datetime.datetime.now()
        update_file_num = 0
        for file_name in file_name_list:
            if True:
                local_file_path = self.config['local_path'] + file_name

                target_file_path = self.config['ssh_path'] + file_name
                stdin, stdout, stderr = self.ssh.exec_command(f'mkdir -p {os.path.dirname(target_file_path)}')
                stdout.channel.recv_exit_status() # 等待目录创建完成
                if self.config['mandatory_update']:
                    print(local_file_path,target_file_path)
                    self.sftp.put(local_file_path, target_file_path)
                    print('%s 强制更新成功' % (target_file_path))
                    update_file_num = update_file_num + 1
                else:
                    update_file_num = update_file_num + check_and_upload_file(local_file_path, target_file_path)
            else:
                print('%s 在被忽略文件类型中，所以被忽略' % file_name)
        end = datetime.datetime.now()
        print('本次上传结束：更新文件%s个，耗时：%s' % (update_file_num, end - begin))
        return update_file_num


def grep_obj_log_by_timeStamp(nanoIP, time_stamp_str="2018-01-29 00:21:46", dest_folder="D:\FTP\log", line_number=100):
    """
    根据时间戳，使用grep命令，获得nano上的时间戳前后的融合目标日志。
    :param nanoIP:
    :param time_stamp_str:时间戳
    :param dest_folder:日志存放的本地文件夹
    :param line_number:时间戳前后行数
    :return:
    """
    # 初始化连接
    py_installer = Pyinstaller_Build(nanoIP)
    py_installer.init_ssh()
    py_installer.init_sftp()
    # log保存路径
    log_name = time_stamp_str.replace(":", "").replace(" ", "_").replace("-", "")
    if py_installer.exists_by_sftp("/ssd/zipx"):
        log_folder="/ssd/zipx"
    else:
        log_folder = "/usr/bin/zipx/zj-guard/log"
    log_path = f"{log_folder}/{nanoIP}_{log_name}.log"
    # 执行grep命令生成文件
    cmd_grep = f"grep \"{time_stamp_str}\" -C {line_number} {log_folder}/system_* >{log_path}"
    print(f"{datetime.datetime.now()},cmd_grep={cmd_grep}")
    stdin, stdout, stderr = py_installer.ssh.exec_command(cmd_grep)  #
    print(f"{datetime.datetime.now()},cmd_grep stdout={stdout.read().decode()},stderr={stderr.read().decode()}")
    # 下载到本地目录
    dest_folder = os.path.join(dest_folder, datetime.datetime.now().strftime("%Y%m%d"))
    dest_path = os.path.join(dest_folder, nanoIP + "_grep_" + log_name + ".log")
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if py_installer.sftp is not None:
        print(f"{datetime.datetime.now()},{log_path} >>> {dest_path}")
        py_installer.sftp.get(log_path, dest_path)
        py_installer.sftp.remove(log_path)
    else:
        print(f"{datetime.datetime.now()},{log_path} sftp none skip >>>{dest_folder}")
    py_installer.exit_ssh_sftp()
    return dest_path

def get_log_by_cmd(nanoIP, cmd="journalctl -u zipx.s.service -n 10000", dest_folder="D:\FTP\log", using_7z=True):
    """
    使用journalctl命令，获得nano上的日志。
    :param nanoIP:
    :param cmd: 生成日志的命令
    :param dest_folder: 日志存放的本地文件夹
    :return:
    """
    print(f"get_log_by_cmd nanoIP={nanoIP} cmd={cmd} dest_folder{dest_folder}")
    dest_folder = os.path.join(dest_folder, datetime.datetime.now().strftime("%Y%m%d"))
    dest_folder = os.path.abspath(dest_folder)
    # 初始化连接
    py_installer = Pyinstaller_Build(nanoIP)
    py_installer.init_ssh()
    py_installer.init_sftp()
    # log保存路径
    time_stamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cmd_replaced = re.sub('[\/:*?"<>| ]', '_', cmd)
    log_name = f"{time_stamp_str}_{cmd_replaced}"

    # if os.path.exists("/ssd/zipx"):
    if py_installer.exists_by_sftp("/ssd/zipx"):
        log_folder="/ssd/zipx"
    else:
        log_folder = "/usr/bin/zipx/zj-guard"
    log_path = f"{log_folder}/{nanoIP}_{log_name}.log"
    log_path = log_path.replace(":", "_")
    # 执行grep命令生成文件
    cmd_journalctl = f"{cmd} > {log_path}"
    print(f"{datetime.datetime.now()},cmd_journalctl={cmd_journalctl}")
    stdin, stdout, stderr = py_installer.ssh.exec_command(cmd_journalctl)  #
    print(f"{datetime.datetime.now()},cmd_journalctl stdout={stdout.read().decode()},stderr={stderr.read().decode()}")
    nanoIP_str=nanoIP.replace(":", "_")
    if using_7z:
        # 加密压缩log文件
        zip_filePath=f"{log_path}.7z"
        cmd_7z=f"7z a -pTDDPc5kc4WnYcy -mhe=on {zip_filePath} {log_path}"
        print(f"{datetime.datetime.now()},cmd_7z {log_path}")
        stdin, stdout, stderr = py_installer.ssh.exec_command(cmd_7z)  #
        print(f"{datetime.datetime.now()},cmd_7z stdout={stdout.read().decode()},stderr={stderr.read().decode()}")
        if py_installer.sftp is not None:
            print(f"{datetime.datetime.now()},get_log_by_cmd remove {log_path}")
            py_installer.sftp.remove(log_path)
        dest_path = os.path.join(dest_folder, nanoIP_str + "_cmd_" + log_name + ".7z")
        log_path = f"{zip_filePath}"
    else:
        dest_path = os.path.join(dest_folder, nanoIP_str + "_cmd_" + log_name + ".log")

    # 下载到本地目录
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if py_installer.sftp is not None:
        print(f"{datetime.datetime.now()},{log_path} >>> {dest_path}")
        py_installer.sftp.get(log_path, dest_path)
        print(f"{datetime.datetime.now()},get_log_by_cmd remove {log_path}")
        py_installer.sftp.remove(log_path)
    else:
        print(f"{datetime.datetime.now()},{log_path} sftp none skip >>>{dest_folder}")
    py_installer.exit_ssh_sftp()
    return dest_path



# if __name__=="__main__":
#     time_start = time.time()
#     dest_folder = os.path.join(".", "log")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-01 20:41:56")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-02 10:13:48", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="58.20.230.32:10090", time_stamp_str="2023-06-02 10:13:48", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.15", cmd="journalctl -u zipx.s.service -b", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.15", cmd="journalctl -u zipx.s.service -n 10000", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.15", cmd="journalctl -u zipx.ntp1.service -b", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.4.224", cmd="journalctl -u zipx.ntp1.service -b", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.253", cmd="journalctl -u zipx.s.service |grep boot -C 2", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-02 19:58:21", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-02 19:58:33", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-02 19:58:52", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="10.8.2.15", time_stamp_str="2023-06-02 19:59:13", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.11", cmd="journalctl -u zipx.s.service -n 20000", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="10.8.2.14", cmd="journalctl -u zipx.s.service", dest_folder="D:\FTP\log")
    # get_log_by_cmd(nanoIP="58.20.230.32:10090", cmd="journalctl -u zipx.s.service -n 40000", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="58.20.230.32:10090", time_stamp_str="2023-06-07 23:06:09", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="58.20.230.32:10090", time_stamp_str="2023-06-08 01:47:15", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="58.20.230.32:10090", time_stamp_str="2023-06-08 05:45:47", dest_folder="D:\FTP\log")
    # grep_obj_log_by_timeStamp(nanoIP="58.20.230.32:10090", time_stamp_str="2023-06-08 05:46:20", dest_folder="D:\FTP\log")
    # dest_path=get_log_by_cmd(nanoIP="10.8.2.11", cmd="journalctl -u zipx.s.service -n 40000", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.10", cmd="journalctl -u zipx.s.service -n 80000|grep _handle_msg_send", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.11", cmd="journalctl -u zipx.s.service -n 80000|grep _handle_msg_send", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.10", cmd="journalctl -u zipx.s.service |grep tcp_server", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.11", cmd="journalctl -u zipx.s.service |grep tcp_server", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.12", cmd="journalctl -u zipx.s.service |grep tcp_server", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.13", cmd="journalctl -u zipx.s.service", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="58.20.230.32:10080", cmd="journalctl -u zipx.s.service -n 10000", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.13", cmd="journalctl -u zipx.s.service |grep tcp_server", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.14", cmd="journalctl -u zipx.s.service |grep tcp_server", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="192.168.1.203", cmd="journalctl -u zipx.s.service", dest_folder=dest_folder, using_7z=True)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.13", cmd="journalctl -u zipx.s.service -n 80000|grep _handle_msg_send", dest_folder=dest_folder, using_7z=False)
    # dest_path = get_log_by_cmd(nanoIP="10.8.2.14", cmd="journalctl -u zipx.s.service -n 80000|grep _handle_msg_send", dest_folder=dest_folder, using_7z=False)
    # dest_path = grep_obj_log_by_timeStamp(nanoIP="10.8.2.13", time_stamp_str="2023-07-04 15:00:00", line_number=1000,dest_folder=dest_folder)
    # os.system(f'explorer {os.path.abspath(os.path.dirname(dest_path))}')
