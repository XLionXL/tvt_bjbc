import datetime
import os
import platform
import time

from main_engine import XML_Version
from zip_log import zip_with_pw, Pyinstaller_Build


def build_exe_pyinstaller(hostIP):
    py_installer = Pyinstaller_Build(hostIP)
    py_installer.init_ssh()
    py_installer.init_sftp()

    # 文件列表
    file_list, folder_list = py_installer.find_PyFiles(py_installer.config["local_path"],
                                                       py_installer.config['ignore_list'])

    # copyToRemote(py_installer.config["hostname"],py_installer.config["port"],py_installer.config["username"],
    #              py_installer.config["password"],py_installer.config["ssh_path"],)
    print('共有文件夹%s个，文件%s个' % (len(file_list), len(folder_list)))

    # 上传文件
    ssh_path = py_installer.config['ssh_path']
    py_installer.upload_files(file_list)

    # 在目标平台编译dependentFiles文件
    # cmd_pyinstaller = f"python3 /usr/bin/zipx/main_py/dependent/build.py"
    # stdin, stdout, stderr = py_installer.ssh.exec_command(cmd_pyinstaller)
    # print(f"cmd_pyinstaller stdout={stdout.read().decode()},stderr={stderr.read().decode()}")
    # raise
    # 按/python3_main_py.spec配置build python3_main_py
    # cmd_pyinstaller = f"/home/tvt/.local/bin/pyinstaller {ssh_path + '/python3_main_py.spec'} --distpath {ssh_path} --exclude-module pydoc"
    # 解決shapely庫打包，後面考慮替代shapely
    #北京公司和现场设备
    cmd_pyinstaller = f"/home/tvt/.local/bin/pyinstaller -F {ssh_path + '/python3_main_py.py'} --add-data   '/usr/lib/aarch64-linux-gnu/libgeos_c.so':'./shapely/.libs/'  --add-data   '/usr/lib/aarch64-linux-gnu/libgeos_c.so.1':'./shapely/.libs/' --distpath {ssh_path}  --paths=/usr/lib/python3.6/dist-packages/cv2/python-3.6 --exclude-module pydoc"
    # 北京酒店设备
    # cmd_pyinstaller = f"pyinstaller -F {ssh_path + '/python3_main_py.py'} --add-data   '/usr/lib/aarch64-linux-gnu/libgeos_c.so':'./shapely/.libs/'  --add-data   '/usr/lib/aarch64-linux-gnu/libgeos_c.so.1':'./shapely/.libs/' --distpath {ssh_path}  --paths=/usr/lib/python3.6/dist-packages/cv2/python-3.6 --exclude-module pydoc"


    # cmd_pyinstaller = f"/home/tvt/.local/bin/pyinstaller -F {'/home/tvt/a.py'}  --distpath {'/home/tvt/'}  --paths=/usr/lib/python3.6/dist-packages/cv2/python-3.6/ --exclude-module pydoc"

    #

    print(f"cmd_pyinstaller={cmd_pyinstaller}")

    # 删除多余文件
    py_installer.ssh.exec_command(f'rm -rf /home/tvt/build/*')
    stdin, stdout, stderr = py_installer.ssh.exec_command(cmd_pyinstaller)
    print(f"cmd_pyinstaller stdout={stdout.read().decode()},stderr={stderr.read().decode()}")

    # 下载exe文件
    remotepath = ssh_path + '/python3_main_py'
    localpath = os.path.join(py_installer.config['local_path'], 'python3_main_py')
    if py_installer.check_file(remotepath):
        py_installer.sftp.get(remotepath, localpath)
        # 列出远程dependent目录下的所有文件
        # stdin, stdout, stderr = py_installer.ssh.exec_command('ls /usr/bin/zipx/main_py/dependent/')
        # output = stdout.read().decode('utf-8').split("\n")[:-1]
        # # 设置dependent下载保存的位置
        # dependentPath = os.path.join(py_installer.config['local_path'], 'dependent/')
        # if not os.path.exists(dependentPath):
        #     os.makedirs(dependentPath)
        # for i in output: # 远程dependent目录下的所有文件
        #     dependentFile = os.path.join(dependentPath,i)
        #     if not os.path.isfile(dependentFile):
        #         py_installer.sftp.get(f'/usr/bin/zipx/main_py/dependent/{i}', dependentFile)
        print(f"get {remotepath}>>>{localpath}")
    else:
        print(f"no {remotepath}***{localpath}")
        return False

    # 删除ssh_path下的py文件
    py_installer.ssh.exec_command(f'rm {ssh_path}/*.py')

    # 关闭连接
    py_installer.exit_ssh_sftp()
    # time
    return True


def zip_exe():
    exe_fileName_list=[
        "python3_main_py",
        "bridgeCOMUDP.py",
        "Upgrade_radar_mcu.py",
        "comm_crc16.py",
        "comm_radar_driver_shibian.py",
        "DebugUDPSender.py",
        "common_FireTimer.py",
        "common_hysteresis_threshold.py",
        "comm_decoder_radar.py",
        "common_FileLoadSave.py",
        "speak.py",
        "buffer_queue.py",
        "comm_serialMCU.py",
        "common_period_sleep.py",
        "Camera_Link.py",
        "comm_nano_heartbeat_frame.py",
        "user_pw.py",
        "HK_ntp_Face_start.py",
        "comm_serialMCU.py",
        "upgrade_fusion.sh",
        "tvtupdate.zip",
        "dependent", # 远程平台下编译后的文件
        # "tvtupdate\zipx.ntp1.service",
        # "tvtupdate\zj-guard-so\client.so",
        # "tvtupdate\zj-guard-so\libclient.so",
        # "tvtupdate\zj-guard-so\libNtpSetCameratime.so",
        # "tvtupdate\zj-guard-so\nanoip.xml",
    ]
    exe_filePath_list = [os.path.join(".", x) for x in exe_fileName_list]
    xml_version = XML_Version()
    product="Xiphos"
    print(f"zip_codes exe_filePath_list={exe_filePath_list}")
    time_str = datetime.datetime.now().strftime("%H%M%S")
    if "Windows" in platform.platform():
        zip_folder="D:\FTP\guard_versions"
    else:
        zip_folder = "."

    if "release" in xml_version.Debug_Beta_Release.lower():
        zip_name=f'{product}_{xml_version.Rail_Universal}_guard_exe_{xml_version.Debug_Beta_Release}_{xml_version.guard_version}_EN.zip'
    else:
        zip_name=f'{product}_{xml_version.Rail_Universal}_guard_exe_{xml_version.Debug_Beta_Release}_{xml_version.guard_version}_EN_{time_str}.zip'
    zip_path = os.path.join(zip_folder, zip_name)
    zip_with_pw(exe_filePath_list, zip_path)
    # mergeTo7Z(zip_path, password="tvt_0123456789_2018",)
    print(f"{datetime.datetime.now()},zip success! zip_path={zip_path}")
    os.system(f'explorer {os.path.dirname(zip_path)}')


def zip_tvtupdate():
    start_dir = os.path.abspath(os.path.join(".", "tvtupdate"))
    zip_path = os.path.abspath(os.path.join(".", "tvtupdate"))
    print(f"zip_tvtupdate {start_dir}>>>{zip_path}")
    import shutil
    shutil.make_archive(zip_path, "zip", start_dir,)


def gen_guard_zip():
    exe_ok = build_exe_pyinstaller(hostIP='10.29.3.32')  # 在nano板上 pyinstaller 生成exe
    # exe_ok = build_exe_pyinstaller(hostIP='58.20.230.32:10080')  # 在nano板上 pyinstaller 生成exe
    # exe_ok = build_exe_pyinstaller(hostIP='58.20.230.32:10090')  # 在nano板上 pyinstaller 生成exe
    # exe_ok = build_exe_pyinstaller(hostIP='121.62.22.121:47350')  # 在nano板上 pyinstaller 生成exe
    # exe_ok = build_exe_pyinstaller(hostIP='192.168.137.5')  # 在nano板上 pyinstaller 生成exe

    # exe_ok = build_exe_pyinstaller(hostIP='192.168.1.200')  # 在nano板上 pyinstaller 生成exe
    # exe_ok = build_exe_pyinstaller(hostIP='10.8.2.12')  # 在nano板上 pyinstaller 生成exe

    if exe_ok:
        print(f"build_exe_pyinstaller done")
        # zip_tvtupdate()  # 更新 tvtupdate.zip
        zip_exe()  # 生成升级包
        print(f"time spend ={time.time() - time_start}")


if __name__=="__main__":
    time_start = time.time()
    gen_guard_zip()
    # zip_exe()
    # mergeTo7Z("D:\FTP\guard_versions\Xiphos_Universal_guard_exe_Release_V1.23.06.27_EN.zip", password="tvt_0123456789_2018",)

#