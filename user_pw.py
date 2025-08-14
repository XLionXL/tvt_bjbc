import datetime
import json
import os
import platform
import subprocess
import time


class User_PW:
    def __init__(self, config_path=os.path.join("config", "user_pw.json")):
        self.platform_str = platform.platform().lower()
        self.last_report_time=time.time()
        self.sudo_pw=None
        self.user=None
        self.config_path=os.path.abspath(config_path)
        self.get_user_pw()
        self.cmd_out_cnt = 0
        self.relay_last_value = 0.5

    def gpio_init_hi(self):
        # 启动时候，确保所有端口上电
        # self.gpio_name_list = ["GPIO_RD", "GPIO_AO", "GPIO_HB", "GPIO_RC", "GPIO_VC"]
        self.gpio_name_list = ["GPIO_RD", "GPIO_RC", "GPIO_VC"]
        for gpio_name in self.gpio_name_list:
            self.power_control_gpio(gpio_name=gpio_name, value="hi")
            # self.relay_control_gpio(1)

    def get_user_pw(self):
        # 由于sudo时效性，本函数只在第一次运行时能正确判断密码
        if self.user is None or self.sudo_pw is None:
            if "debian" in self.platform_str or "armv7l" in self.platform_str:
                self.subprocess_cmd(f"ls -la /dev/ttyS*")
            else:
                self.subprocess_cmd(f"ls -la /dev/ttyTHS*")
            pw_list = ["TDDPc5kc4WnYcy", "king", ""]
            for pw in pw_list:
                if "debian" in self.platform_str or "armv7l" in self.platform_str:
                    cmd = f"echo '{pw}'| sudo -S chmod 777 /dev/ttyS0"
                else:
                    #  "ubuntu" in self.platform_str
                    cmd=f"echo '{pw}'| sudo -S chmod 777 /dev/ttyTHS1"
                process=subprocess.Popen(cmd+"\n", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                result_stdout=process.stdout.readlines()
                result_stdout = str(result_stdout)
                if "password for" in result_stdout and "incorrect" not in result_stdout:
                    self.sudo_pw=pw
                    if "ck" in result_stdout:
                        self.user = "ck"
                    elif "tvt":
                        self.user = "tvt"
                    # 找到user和pw，退出for循环
                    self.save_json([self.user, self.sudo_pw])
                    break
            # 上述获取密码失败，读取文件中的密码
            if self.sudo_pw is None:
                data= self.load_json()
                if data is not None:
                    self.user,self.sudo_pw = data
            # 上述获取密码都失败，使用默认密码king
            if self.sudo_pw is None:
                self.sudo_pw = "king"

    def load_json(self):
        try:
            if not os.path.exists(self.config_path):
                ex=Exception(f"file not exist,{self.config_path}")
                raise ex
            with open(self.config_path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(e)
            return None

    def save_json(self, data):
        try:
            with open(self.config_path, "w+") as f:
                json.dump(data, f)
                f.flush()
                f.close()
            return True
        except Exception as e:
            print(e)
            return False

    def chmod_777(self, target):
        cmd=f"echo '{self.sudo_pw}' | sudo -S chmod 777 {target}"
        # os.system(cmd)
        self.subprocess_cmd(cmd)
        self.subprocess_cmd(f"ls -la {target}")

    def system_cmd(self, cmd):
        cmd_pw=f"echo '{self.sudo_pw}' | {cmd}"
        os.system(cmd_pw)

    def subprocess_cmd(self, cmd):
        # cmd = f"echo '{self.sudo_pw}'| {cmd}"
        process = subprocess.Popen(cmd + "\n", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result_stdout = process.stdout.readlines()
        try:
            print(f"cmd={cmd},result={[result.decode('UTF-8') for result in result_stdout]}")
        except:
            pass

    def power_control_gpio(self, gpio_name="GPIO_AO", value="low"):
        # sudo tvtgpio GPIO_RD hi
        # gpio_name ["GPIO_RD", "GPIO_AO", "GPIO_HB", "GPIO_RC", "GPIO_VC"]
        # value hi,low
        cmd = f"echo '{self.sudo_pw}' | sudo -S tvtgpio {gpio_name} {value}"
        # os.system(cmd)
        self.subprocess_cmd(cmd)
        # self.subprocess_cmd(f"ls -la {target}")

    def power_control_gpio_reset(self, gpio_name="GPIO_AO"):
        # 对应gpio置低后再置高
        self.power_control_gpio(gpio_name, "low")
        time.sleep(2)
        self.power_control_gpio(gpio_name, "hi")

    def relay_control_gpio(self, value=1):
        # sudo tvtgpio GPIO_RL hi
        # sudo tvtgpio GPIO_RL lo
        # gpio输出高或者低
        if self.relay_last_value != value:
            if value >= 1:
                self.power_control_gpio("GPIO_RL", "hi")
            else:
                self.power_control_gpio("GPIO_RL", "lo")
            self.relay_last_value = value

    def zipx_s_service_restart(self):
        # 重启zipx.s.service
        time.sleep(2)
        self.system_cmd("sudo systemctl restart zipx.s.service")

    def mv_syncNtpDate(self):
        # 移动syncNtpDate.py到 /usr/bin/zipx/ntp_face
        time.sleep(1)
        syncNtpDate_path_source="/usr/bin/zipx/zj-guard/syncNtpDate.py"
        syncNtpDate_path_destination="/usr/bin/zipx/ntp_face"
        if os.path.exists(syncNtpDate_path_source):
            self.system_cmd(f"sudo mv {syncNtpDate_path_source} {syncNtpDate_path_destination}")
            self.system_cmd(f"sudo ls -ln {syncNtpDate_path_destination}")
            self.system_cmd("sudo systemctl restart zipx.ntp1.service")

    def test(self):
        user_pw = User_PW()
        user_pw.chmod_777(r"/usr/bin/zipx/zj-guard/config/*")
        user_pw.subprocess_cmd(f"ls -ln /dev/ttyTHS*")
        user_pw.chmod_777(r"/dev/ttyTHS*")
        # user_pw.zipx_s_service_restart()
        gpio_name_list = ["GPIO_RD", "GPIO_AO", "GPIO_HB", "GPIO_RC", "GPIO_VC"]
        # gpio_name_list = ["GPIO_RD", "GPIO_AO", "GPIO_HB"]
        # gpio_name_list = ["GPIO_RD"]
        for index in range(30):
            # for gpio_name in gpio_name_list:
            # user_pw.power_control_gpio(gpio_name=gpio_name, value="hi")
            user_pw.relay_control_gpio(1)
            time.sleep(10)
            # for gpio_name in gpio_name_list:
            # user_pw.power_control_gpio(gpio_name=gpio_name, value="low")
            user_pw.relay_control_gpio(0)
            time.sleep(10)

    
if __name__ == "__main__":
    pass
    user_pw = User_PW()
    # user_pw.mv_syncNtpDate()
    user_pw.last_report_time = time.time() - 1200
    for index in range(300):
        # user_pw.list_mp4_jpg_download_url()
        time.sleep(1)
