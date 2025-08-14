# coding=gbk
import datetime
import platform
import subprocess
import time

from common_FireTimer import FireTimer_withCounter_InSpan
from common_hysteresis_threshold import EDGE_DETECT
from xypTool.debug import xypLog


class NANO_RTSP:
    def __init__(self, user_pw, cpu_min_to_restart_infer=16):
        self.user_pw = user_pw
        self.edge_infer_cpu_load = EDGE_DETECT()
        self.edge_infer_rtsp = EDGE_DETECT()
        self.cpu_of_infer = 0
        self.time_of_infer = 0
        self.cpu_min_to_restart_infer = cpu_min_to_restart_infer      # 低于该值达到一定时间则重启infer推理模块
        self.cpu_restart_infer_firer = FireTimer_withCounter_InSpan(max_time_span_s=3600, max_fire_times=3)  # 1小时最多重启3次
        self.journalctl_vaccum_size_firer = FireTimer_withCounter_InSpan(max_time_span_s=3600 * 24, max_fire_times=2)   # 1天最多2次
        print(f"NANO_RTSP init,cpu_min_to_restart_infer={self.cpu_min_to_restart_infer}")

    def get_rtsp_from_ps_infer_main(self, cmd="ps -aux|grep infer_main|grep rtsp", filterKey='rtsp', ):
        """
        在shell中通过ps命令获得当前系统中的推理流地址
        :param cmd:显示推理进程的ps命令
        :param filterKey:用于过滤的字符串
        :return:
        """
        rtsp_list = []
        if "Windows" not in platform.platform():
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            time.sleep(0.5)
            line_list=p.stdout.readlines()
            for index, line_byte in enumerate(line_list):
                line_str = str(line_byte, encoding='utf-8')
                if "rtsp" in line_str and "zipx" in line_str:
                    self.update_cpu_of_infer(line_str)
                    if self.cpu_of_infer < self.cpu_min_to_restart_infer:
                        if self.cpu_restart_infer_firer.isFireTime(10):
                            self.restart_infer(self.user_pw)
                text = str(line_byte, encoding='utf-8').split()
                # print(text)
                rtsp_list = [x.strip() for x in text if (filterKey in x and len(x)>20)]
                # print(rtsp_list)
                if len(rtsp_list)>0:
                    break
            p.kill()
            if self.edge_infer_rtsp.is_Edge(rtsp_list):
                print(f"{datetime.datetime.now()},get_rtsp_from_ps_infer_main, rtsp={rtsp_list}")

            if len(rtsp_list) > 0:
                # rtsp_list.reverse()
                return rtsp_list
            else:
                print(f"error in get_url_from_ps_infer_main line_list={line_list}")
                return []
        else:
            # return ["rtsp://admin:Admin123@10.8.4.31", "rtsp://admin:Admin123@10.8.4.32"]
            # return ["rtsp://admin:Admin123@192.168.1.12/ch01.264", "rtsp://admin:Admin123@192.168.1.11/live/0/MAIN"]
            return ["rtsp://admin:Admin123@192.168.8.12/Streaming/Channels/101", "rtsp://admin:Admin123@192.168.8.11/Streaming/Channels/101"]
            # return ["D:\\2022-03-02 18-56-43.mp4", "D:\\2022-03-02 18-49-03.mp4"]

    def update_cpu_of_infer(self, ps_string="root      4694 16.4 26.2 12300464 1066796 ?    Sl"):
        try:
            ps_str_list = ps_string.strip().split()
            self.cpu_of_infer = float(ps_str_list[2])
            if len(ps_str_list)>=10:
                self.time_of_infer = float(ps_str_list[9])
            if self.edge_infer_cpu_load.is_Edge(self.cpu_of_infer > 15):
                print(f"{datetime.datetime.now()},update_cpu_of_infer,cpu={self.cpu_of_infer},time={self.time_of_infer},{ps_string}")
        except:
            pass
            # return 999.999

    def is_infer_online(self, ):
        # 通过ps命令中是否包含rtsp，判断推理是否在线
        text = self.get_rtsp_from_ps_infer_main()
        if len(text) > 0 and 'rtsp' in text[-1]:
            # infer online
            is_online = True
        else:
            # infer Off
            is_online = False

        # 附加代码，清理日志
        if self.journalctl_vaccum_size_firer.isFireTime(3600 * 6, is_first_fire=True):  # 第一次就触发，每6小时执行一次
            self.journalctl_vaccum_size(size_M=1000)  # 最大1000M日志

        return is_online

    def restart_infer(self, user_pw=None):
        # infer restart
        command = 'sudo -S systemctl restart zipx.service'
        # os.system('echo %s | %s' % (self.main_engine.password, command))
        infor_str = f"{datetime.datetime.now()},NANO_RTSP restart_infer"
        print(infor_str)
        xypLog.xypError(infor_str)
        if user_pw is not None:
            user_pw.system_cmd(command)

    def restart_guard(self):
        # guard restart
        command = 'sudo -S systemctl restart zipx.s.service'
        # os.system('echo %s | %s' % (self.main_engine.password, command))
        infor_str = f"{datetime.datetime.now()},restart_guard"
        print(infor_str)
        xypLog.xypError(infor_str)
        if self.user_pw is not None:
            self.user_pw.system_cmd(command)

    def journalctl_vaccum_size(self, size_M=4000):
        # 清理过多日志，避免存储空间不够
        command = f'sudo -S journalctl --vacuum-size={size_M}M'
        infor_str = f"{datetime.datetime.now()}, journalctl_vaccum_size command={command}"
        print(infor_str)
        xypLog.xypError(infor_str)
        if self.user_pw is not None:
            self.user_pw.system_cmd(command)


if __name__=="__main__":
    # rtsp_list=get_rtsp_from_ps_infer_main()
    # print(f"get_url_from_ps_infer_main", rtsp_list)
    nano_rtps = NANO_RTSP(user_pw="TDDPc5kc4WnYcy")
    nano_rtps.get_rtsp_from_ps_infer_main()
    nano_rtps.update_cpu_of_infer()
    print(f"cpu_of_infer={nano_rtps.cpu_of_infer}")


