import os
import math
import datetime
import platform
import subprocess
import time
import traceback
from enum import unique, Enum
from xml.etree.ElementTree import ElementTree

from Camera_Train_Icr import Camera_Train_Icr
from DebugUDPSender import DebugUDPSender
from comm_decoder_radar import Decoder_Radar
from comm_net_transceiver import Udp_Camera_With_Reconnect
from comm_radar_driver_shibian import RadarDriver_COM, RadarDriver_UDP
from comm_tcp_server_main import MainTcpServer
from common_FireTimer import FireTimer_WithCounter, FireTimer_withCounter_InSpan
from common_hysteresis_threshold import EDGE_DETECT
from config_manager import ConfigManager, MainEngine_Config
from moniter_trace_false_alarm_list import CameraFalseAlarmFilter
# from pika_sftp import Rabbitmq_Config
from rtsp_from_ps import NANO_RTSP
from xypAutoCalibVanishPoint import calibVanishPoint
from xypTool.debug import xypLog

from xypMoniter import MonitorTrace, THRESHOLD_NEAR_FAR
from pronounce import PronounceConsumerThread
from alarm_pic_saver import Save_Pic_by_Infer
from comm_serialMCU import SerialMCU, HeartBeat_frame
from tvt_http_file_server import File_Server
from user_pw import User_PW
from videoCalibration_LineDetect import Common_Function
from xypTool.common import xypFileTool
from xypPikaSftp import DeviceControlForBeiJing
@unique
class GuardMode(Enum):
    CAMERA_MODE = 1  # 纯相机模式
    RADAR_MODE = 2  # 纯雷达模式
    CAMERA_RADAR_MODE = 4  # 混合模式
    MIX_MODE = CAMERA_MODE | RADAR_MODE | CAMERA_RADAR_MODE  # 自动模式


class XML_Version:
    """
    融合程序版本信息管理类，负责定义版本号，并提供写入xml文件的api
    """

    def __init__(self, xml_path=os.path.join("", "zj-general-constant.xml")):
        """
        nano 的guard软件版本。
        :param xml_path:
        """
        # 0607 远程喊话声光报警器电源控制
        # 0608 修改火车识别概率大于0.7, log_deleter配置修改
        # 0608C 修改火车识别概率大于0.75, 打开相机控制,优化相机未连接不能启动问题
        # 0609 优化接自研相机ntp获取时间不成功问题
        # 0610 优化远程喊话中间，声光报警器掉电问题。关闭报警延时增加1s,测试保存图片
        # 0611 报警图像保存，10s间隔
        # 0614 火车屏蔽报警60s
        # 0615 火车消失90s后 icr自动
        # 0615C 报警事件开始结束信息，202 报警事件信息,无火车灯光屏蔽报警
        # 0616 火车灯光屏蔽报警debug
        # 0617 自动icr后，20s内忽略火车灯光报警，sn号读取并在心跳包中发送
        # 0620 优化融合误报，缩小融合时间1.5s和距离范围0.15，根据相机框概率计算权重>0.65,火车检测最小概率0.8修改为0.73
        # 0621 Monitor_alarm_Event中发送最近二十次报警事件,火车关灯后150s开灯
        # 0622 火车屏蔽报警和关灯分别处理，屏蔽时间180s
        # 0622 提高融合报警门限到80，以减少误报
        # 0704 雷达检测火车，并屏蔽报警3分钟
        # 0705 相机目标计算雷达xy
        # 0706 整理屏蔽报警和关灯逻辑
        # 0707 调试gpio控制相机红外灯，丢弃230米以外雷达目标，提高融合报警门限到150,删除融合、雷达报警时候的雷达虚拟目标
        # 0708 调整虚拟目标alarmojbs，初步OK; 8B雷达数据转发初步ok，需要添加控制命令
        # 0712 添加雷达转发模式命令，及配置处理函数,修改false_alarm_count
        # 0713 转发模式基本调试通过，false_alarm debug调试
        # 0714 新开线程发送声光报警器上电下电命令
        # 0715 调整ssd nano存储图片数量和容量
        # 0716 优化虚拟出的雷达目标过多。udp发送固定为30000端口，罗琛更新syncNtpDate.py, udp发送sn
        # 0718 相机红外控制debug
        # 0719 0720 漏报debug，udp发子网255和192.168.8.255
        # 0721 漏报debug，提高 isTrainObj 门限到1.1，以避免block,优化add_alarm0bj_virtual_radarXYZ代码
        # 0722 优化udp端口重连，优化整理Decoder_Radar类
        # 0725 和web一起优化调试雷达虚拟目标显示
        # 0726 优化monitor_trace中alarmojbs目标漏掉虚拟目标,优化蹲下报警取消问题,tts声音调试屏蔽火车灯光。
        # 0727 radar_false_alarm.json保存,comm_serialMCU中发读radar_false_alarm命令。
        # 0728 confidence_min:0.65>>>0.55。
        # 0802 郑州无报警debug。
        # 0809 雷达命令端口5分钟reconnect,远焦相机防区计算xy坐标。
        # 0810 远焦相机防区计算雷达防区上方两点xy坐标，近焦相机防区计算雷达防区下方两点x坐标。
        # 0811 优化雷达虚拟目标，先从雷达列表中查找目标，如果没有则使用相机虚拟目标
        # 0812 优化传输中的数值位数，在心跳帧中添加nano_time字段
        # 0816 添加相机虚警列表功能
        # 0822 添加参考点&相机高度设置功能
        # 0822C 设置防区和读取防区解码
        # 0823 debug灭点设置
        # 0824 保存图片功能恢复，相机虚警列表确认,更新requirements
        # 0825 相机虚警列表debug，infer推理cpu低于25则重启，每小时最多重启3次
        # 0826 减少send_cmd_acousto_optic_power_task打印内容，调整camera_grid_step
        # 0830 调整相机虚拟雷达目标逻辑
        # 0831 标定设置相机灭点和高度调试完成，相机虚拟雷达目标逻辑调试,
        # 0831B 相机距离测试接口 REQ_CAMERA_DISTANCE_TEST,
        # 0901 cpu_min_to_restart_infer修改为20，避免简单场景下重启infer_main,debug,添加mcu相关帧id到Radar_Frame_Code
        # 0902 添加journalctl_vaccum_size，第一次就触发，每6小时执行一次,最大3000M日志
        # 0906 pyinstaller修改，解决冲突
        # 0909 标定文件pkl改为json格式
        # 0913 升级zip_codes操作
        # 0928 防区分辨率debug
        # 0929 增加支持串口雷达升级
        # 0930 调试雷达无声音问题
        # 1008 调试不能存图问题，合并dev分支的修改
        # 1009 debug不能存图问题，debug mcu数据无雷达相机掉线报警问题,
        # 1010 提高读Mcu版本号的成功率
        # 1011 提高读Mcu版本号,gps的成功率,添加pronounce_english配置
        # 1013 使用web音量控制，web喊话优于声音报警，调整speak_config部分代码
        # 1013 串口打开错误时修改权限 listen_comm_open_error_callback
        # 1019 如果没有读到雷达、mcu版本号，则反复读，get_edition_firer
        # 1026 防摔雷达串口输出忽略CRC check_crc, debian系统 0 MCU数据 ,1 radar串口,防摔雷达解码待补充decode_radar_objs
        # 1026 无MCU工控板的gpio控制 listen_power_control_gpio_set
        # 1027 定时重启功能避免久了假死 zipx_s_service_restart,解码防摔雷达 decode_radar_objs,改进读取mcu雷达版本
        # 1028 debug web没有异常报警 camera_near.update_status
        # 1101 60米视觉框适配 decode_radar_objs 默认不重启 zipx_s_service_restart_time_s
        # 1102 60米雷视匹配串口名字
        # 1106 罗琛更新 syncTime 函数
        # 1116 debug __isRayInSegment 函数
        # 1117 handle_config_msg 60米雷视一体机远焦防区解决报错
        # 1118 handle_config_msg 60米雷视一体机雷达防区固定为 30 60(注释掉),雷达防区设置发2遍
        # 1123 handle_radar_data 通过视觉防区判断雷达是否在防区内
        # 1124 class Common_Function 添加判断方法
        # 1213 调试雷达无数据后通过power_control_gpio_reset函数控制GPIO_RD重启
        # 0104 继电器调试relay_control_gpio
        # 0114 debug视觉虚警列表不起作用，原因是get_index函数中key类型不是str
        # 0202 handle_radar_data 修改视觉防区判断方法，原判断方法针对特定顺序图形有误
        # 0203 handle_radar_data 视觉虚拟雷达目标处理
        # 0207 调用so文件存图后，指定图片路径 saveAlarmPicture，图片最多保存500张/500M,存储图片报警框 bbox_list_dict
        # 0214 File_Server http port 8008,http_file_port
        # 0216 saveAlarmPicture debug
        # 0220 get_serialName_from_ls_cmd debug,mp4路径
        # 0221 getCameraTime_Near getCameraTime_Far timeout=2  upgrade_fusion.sh
        # 0222 list_mp4_jpg_download_url
        # 0223 Udp_Camera_With_Reconnect _run_receive power_control_gpio by mcu_enable
        # 0224 get_mp4_path_callback upgrade_fusion.sh
        # 0225 update tvtupgrade
        # 0227 main_config.max_file_num main_config.max_file_size
        # 0227c 存图10s,视频调用间隔4s
        # 0228 main_config.pic_timeSpan_min main_config.mp4_timeSpan_min 注释掉401 send_url_data_callback
        # 0228 如果pic_timeSpan_min或者mp4_timeSpan_min <0,则不启用存图和存视频功能
        # 0229B Save_Pic_by_Infer task_rcv_fun,"pic_timeSpan_min": 5, "mp4_timeSpan_min": 4,
        # 0303 print debug infor,decode_radar_objs Repeat_Obj,handle_radar_data
        # 0308 MainEngine_Config cpu_min_to_restart_infer
        # 0309 TcpServer reStart_guard_callback
        # 0309 ConfigManager update_defence_area_list
        # 0330 pika_sftp
        # 0331 radar24G decoder
        # 0403 TieKeYuan rabbitMQ sftp调试
        # 0407 debug decode radar_objs
        # 0505 get_radar_score_by_distance2
        # 0506 max_client 32,pika rabbitmq_config,get_radar_score_by_dict
        # 0508 max_client 128
        # 0509 dto from get_axis_xy [9998, dto_x, dto_y, 0, 0]
        # 0509B tx_tieKeYuan_rabbitmq_process Pika_Queue
        # 0510 get_radar_score_by_dict
        # 0511 tx_tieKeYuan_rabbitmq_callback
        # 0512 socket send,get_alarm_id_cnt,tx_tieKeYuan_rabbitmq_callback
        # 0513 sftp_close
        # 0515 thread_start_sftp_put joint_alarm_score
        # 0516 thread_start_sftp_put
        # 0517R tx_tieKeYuan_rabbitmq_callback tx_tieKeYuan_rabbitmq_process
        # 0517R3 tx_tieKeYuan_rabbitmq_deQueue get_pixel_xywh
        # 0518R1 saveAlarmPicture_task_enQueue saveAlarmJpgMp4
        # 0519R1 mp4_upload_enable jpg_upload_enable get_radar_score_by_dict get_joint_detection_score complex
        # 0520R1 Block_list gen_pic_of_block_list
        # 0522R3 get_radar_score_by_dict camera_radar_h_offset_rad
        # 0524R1 get_radar_score_by_dict +THRESHOLD_NEAR_FAR tx_tieKeYuan_rabbitmq_callback
        # 0524R2 get_camera_score_by_confidence ,y,self.confidence_min,301 dto
        # 0524R4 ip_change_update_rtsp_callback 940 rtsp,position
        # 0525R1 get_joint_detection_score get_radar_distance_sum
        # 0530 get_radar_score
        # 0531 MainEngine_Config confidence_min
        # 0601 syncNtpDate Camera_Http_940 zip_log
        # 0602 get_log_by_cmd zip_tvtupdate
        # 0605 mp4 filename i{self.alarm_id}
        # 0607 _recv_json_data alarm_rising_edge
        # 0607C block_list update to alarm_area
        # 0608 box['confidence'] *= 0.75 sftp rm /usr/bin/zipx/zj-guard/*.py
        # 0614 _handle_msg_send recvQ_ipPort;get_log_by_cmd using_7z
        # 0615 get_make_pic_folder check_tcp_close_deadClient close_consumer_thread _handle_msg_send block_level
        # 0625 60m in debug
        # 0627 fix bug in add_alarmojbs
        # 0703 60m longRun
        # 0707 block_list convert_area_resolution
        # 0707 ntp 1s
        # 0711 merge rv1126_60m and optimized_performance
        # 0724 rv1126_60m indebug
        # 0725 Upgrade_radar_mcu in debug
        # 0725 decode_radar_heartBeat_A66A A66A5E11
        # 0726 handle_radar_data log, add tcp_monitor.vi
        # 0811 handle_calibration_update_callback
        # 0822 merger branch by zzl
        # 0823 main_config REQ_MAIN_CONFIG
        # 0823 REQ_RADAR_AREA
        # 0825 zip_exe upgrade_fusion.sh
        # 0831 timeout_for_reconnect=50
        # 0904 radar_area auto_calibration
        # 0919 trace offline to restart zipx.s.service
        # 0920 update tcp_monitor,rm *.zip in upgrade_fusion.sh
        # 0922 get_alarm_distance alarm_distance_final
        # 0926 fog_coef_near
        # 1009 fog_coef_near1.05 autoFov_fromLog
        # 1012 get_fog_coef_nightTime

        # self.guard_version = "V2.0.0.0.20240703"
        self.guard_version = "V2.0.0.0.202503272030"

        self.Debug_Beta_Release = "Release"
        self.Rail_Universal = "Universal200"
        self.xml_path = os.path.abspath(xml_path)
        if "Windows" not in platform.platform():
            self.save_key_value_to_xml(key='guard_version', value=self.guard_version)

    def save_key_value_to_xml(self, key=None, value=None):
        """
        保存模块版本信息到xml文件，路径为self.xml_path
        :param key:  "mcu_version","radar_version",
        :param value:
        :return:
        """
        if os.path.exists(self.xml_path) and key is not None and value is not None:
            print(f"write key={key},value={value},xml_path={self.xml_path}")
            tree = ElementTree(file=self.xml_path)
            root = tree.getroot()
            key_value = root.findall(key)
            if key_value is not None and len(key_value) > 0:
                if value != key_value[0].text:
                    print(f"{datetime.datetime.now()},save_key_value_to_xml,{key},{key_value[0].text}>>>{value}")
                    key_value[0].text = value
                    tree.write(self.xml_path, encoding='utf-8')


class MainEngine:
    """
    nano程序的主要模块
    """


    def __init__(self, main_folder, xml_path=None):
        """
        MainEngine初始化函数，
        :param xml_path:nano上记录版本信息的xml文件路径。本模块将雷达版本、mcu版本、guard融合程序版本写入xml文件
        """
        xypLogSpaceManage = xypFileTool.FileSpaceManage("/ssd/alarmpic/alarmFrame",["100GB"] ,"1d")

        from handleCameraData import ImageAreaHandle, CameraVanishHandle,HandleCameraData
        from handleRadarData import RadarAreaHandle,HandleRadarData
        self.vanishHandle = CameraVanishHandle()
        self.imageAreaHandle = ImageAreaHandle(os.path.join(".", "config", "imageArea.json"), self.vanishHandle, "./aa")
        self.radarAreaHandle = RadarAreaHandle(os.path.join(".", "config", "radarArea.json"),self.vanishHandle, "./aa")

        self.imageAreaHandle.imageAreaSetRadarArea(self.radarAreaHandle)
        self.x = HandleCameraData(self.imageAreaHandle,self.vanishHandle,True, self)
        self.y = HandleRadarData(self.radarAreaHandle,self.vanishHandle,self)

        self.fog_coef_cnt = 0
        self.radar_obj_simulator=[[2922, 1, 1, 0.0, 0.0], [2993, -1, 1, 0.0, 0.0]]
        self.false_alarm_cnt = 0
        self.camera_data_print_cnt = 0
        self.print_cnt_camera_data = 0
        self.print_cnt_handle_radar_data=0
        self.debug_firer = FireTimer_withCounter_InSpan(max_time_span_s=-1, max_fire_times=-1)
        self.platform_str = platform.platform().lower()
        self.debug_print_callback = None
        self.className = "MainEngine"
        self.camera_occlude_update_to_heartbeat_callback = None
        self.isWindows = "Windows" in platform.platform()
        self.main_folder = main_folder
        self.config_folder = os.path.join(self.main_folder, "config")
        self.main_config = MainEngine_Config(os.path.join(self.config_folder, "main_config.json"))
        self.radar_decoder = Decoder_Radar(self.main_config.radar_decode_head)
        self.user_pw = User_PW()

        if not self.main_config.mcu_enable:
            self.user_pw.gpio_init_hi()

        self.pnpoly = Common_Function()
        if "ubuntu" in self.platform_str:
            self.user_pw.subprocess_cmd(f"ls -la /dev/ttyTHS*")
        elif "debian" in self.platform_str:
            self.user_pw.subprocess_cmd(f"ls -la /dev/ttyS[01234]")
        for index_chmod in range(3):
            self.user_pw.chmod_777(f"{self.main_folder}/config/*")
            # self.user_pw.chmod_777(r"/dev/ttyTHS*")
        self.error_print_fire = FireTimer_WithCounter(10)
        self.debug_udp_sender = DebugUDPSender()

        if self.main_config.infer_enable:
            self.nano_infer = NANO_RTSP(self.user_pw, self.main_config.cpu_min_to_restart_infer)
            # 循环使用ps命令，扫描得到rtsp url
            check_cycle = 3
            for index in range(int(600 / check_cycle)):
                self.camera_rtsp = self.nano_infer.get_rtsp_from_ps_infer_main()
                if len(self.camera_rtsp) > 0:
                    break
                else:
                    print(f"{datetime.datetime.now()},{self.className} __init__, no infer in ps,index={index},wait {check_cycle}s and recheck")
                    time.sleep(check_cycle)
        else:
            self.nano_infer=None
            if self.debug_udp_sender.out_ip is not None and isinstance(self.debug_udp_sender.out_ip, str):
                out_ip=self.debug_udp_sender.out_ip
            else:
                out_ip="10.8.4.170"
            # 单相机流地址
            self.camera_rtsp = [f"rtsp://admin:123456@{out_ip}:554/ch01.264"]
        print(f"{datetime.datetime.now()},{self.className} __init__, self.camera_rtsp={self.camera_rtsp}")
        # self.super_mv_syncNtpDate()

        if self.isWindows:
            # windows调试
            self.camera_type = "window_debug"
        elif "Streaming/Channels" in str(self.camera_rtsp):
            # 海康相机
            self.camera_type = "hk"
        else:
            # 自研相机
            self.camera_type = "zy"

        self.xml_handle = XML_Version(xml_path)
        print(f"guard version={self.xml_handle.guard_version}")

        # 各种配置文件
        self.config_manager = ConfigManager(self.camera_rtsp, self.config_folder, self.main_config)
        # 测试代码,确认相机框转换雷达距离是否准确
        # x, y, w, h = 333, 226, 47, 88
        # self.config_manager.camera_diameter_dict[0].get_axis_xy([x + 0.5 * w, y + h], resolution_old=[800, 450], )
        # x, y, w, h = 296, 222, 76, 158
        # self.config_manager.camera_diameter_dict[1].get_axis_xy([x + 0.5 * w, y + h], resolution_old=[800, 450], )

        # 雷达或相机持续出现目标的时间，单位s
        self.time_care_in_seconds = 3
        # 推理端口IP
        self.ip_port = None
        self.camera_decoder = Decoder_Radar(self.main_config.radar_decode_head)
        self.camera_driver = Udp_Camera_With_Reconnect(self.camera_decoder, bind_port=self.main_config.camera_udp_port)  # 支持重连的udp类
        self.camera_driver.timeout_for_reconnect = 60

        self.ttyTH_list = get_serialName_from_ls_cmd()

        # 警戒模式
        self.current_guard_mode = GuardMode.MIX_MODE
        self.current_guard_mode_value = self.current_guard_mode._value_

        # 打开雷达通讯
        self.radar_driver = None
        comm_test_time = 4
        if self.main_config.radar_decode_head=="AAAA5555":
            self.radar_decoder_cmd = Decoder_Radar(self.main_config.radar_decode_head)
            self.radar_driver_udp_cmd = RadarDriver_UDP(self.radar_decoder_cmd, local_port=15000,
                                                        get_edition=self.main_config.radar_get_edition_enable)
            self.radar_driver_udp_cmd.timeout_for_reconnect = 300
        else:
            self.radar_driver_udp_cmd = None

        radar_port = self.main_config.radar_udp_port    # 17000是雷达数据端口
        if "Windows" in platform.platform():
            port = "COM2"
            print(f"Windows open serial radar,com_port={port}", __file__)
            if "COM" in port:
                self.radar_driver = RadarDriver_COM(port, self.user_pw.sudo_pw, self.radar_decoder,
                                                    self.main_config.radar_get_edition_enable)
                self.radar_driver.start()
            else:
                # xyp雷达a66a
                self.radar_driver = RadarDriver_UDP(self.radar_decoder, int(port))
        elif len(self.ttyTH_list) >= 2 and True:
            # 打开串口，测试是否能够读取到数据
            print(f"open serial radar,com_port={self.ttyTH_list[1]}", __file__)
            self.radar_driver = RadarDriver_COM(self.ttyTH_list[1], self.user_pw.sudo_pw, self.radar_decoder,
                                                self.main_config.radar_get_edition_enable)
            if "debian" in self.platform_str:
                self.radar_driver.decoder.check_crc = False
            print(f"{datetime.datetime.now()},{self.platform_str} check_crc={self.radar_driver.decoder.check_crc}")
            self.radar_driver.listen_comm_open_error_callback(self.user_pw.chmod_777)
            self.radar_driver.start()
            time.sleep(comm_test_time)
            self.radar_driver.comm_send(self.radar_decoder.get_radar_edition_cmd(), showDataHex=True)
            last_data_time_stamp_radar = time.time() - self.radar_driver.latest_data_stamp
            print(f"radar_driver.latest_data_stamp20230731 ={last_data_time_stamp_radar}")
            # 如果读不到数据，使用udp雷达
            is_use_udp_radar = (isinstance(radar_port, int) and 0 < radar_port and last_data_time_stamp_radar >= comm_test_time * 0.8)
            if is_use_udp_radar:
                self.radar_driver.exit()
                print(f"open udp radar, radar_port={radar_port}", __file__)
                # 从数据端口读取雷达目标
                self.radar_driver = RadarDriver_UDP(self.radar_decoder, local_port=radar_port, get_edition=False)
                # 从命令端口读取版本号
                if self.main_config.radar_get_edition_enable:
                    if self.radar_driver_udp_cmd is not None:
                        edition_str=self.radar_driver_udp_cmd.get_radar_mcu_edition()
                    else:
                        edition_str=self.radar_driver.get_radar_mcu_edition()
                    if isinstance(edition_str, str):
                        self.xml_handle.save_key_value_to_xml("radar_version", edition_str)
                else:
                    print(f"{self.className},radar_get_edition_enable skiped",)

            else:
                # 使用串口雷达时，读取版本号，更新xml文件
                if self.main_config.radar_get_edition_enable:
                    self.radar_driver.get_radar_mcu_edition()
                else:
                    print(f"{self.className},radar_get_edition_enable skiped",)
                if self.radar_driver.decoder.edition_str is not None:
                    self.xml_handle.save_key_value_to_xml("radar_version", self.radar_driver.decoder.edition_str)
                pass
        else:
            print(datetime.datetime.now(), f" {self.className} ttyTH_list={self.ttyTH_list},radar_port={radar_port}")
            print("exit")
            return
        # 定义udp调试类，获得外部ip，并更新外部流地址
        # self.debug_udp_sender = DebugUDPSender()
        self.ip_change_update_rtsp_callback()

        # 轨迹参数
        self.config_manager.source_list = self.camera_rtsp
        self.trace = MonitorTrace(self.config_manager, self.main_config,self.imageAreaHandle,radarDriver=self.radar_driver)



        if not self.main_config.mcu_enable:
            self.trace.gpio_alarm_relay_callback = self.user_pw.relay_control_gpio

        self.thread_pronounce = PronounceConsumerThread(self.main_folder, self.user_pw, self.main_config.pronounce_english)
        self.thread_pronounce.start()
        self.thread_pronounce.get_volume_callback = self.get_speak_config_data

        # 登录相机http控制
        self.block_alarm_edge = EDGE_DETECT()
        self.block_icr_edge = EDGE_DETECT()
        self.block_time = 10  # 开机关灯时间
        self.block_count = 0    # self.block_count=0对应程序启动时候第一次block_time为10s，之后block_time为180
        self.handle_camera_get_icr_control_handle()

        self.camera_targets_dict = {0: [], 1: []}
        self.radar_targets_dict = {0: [], 1: []}

        # mcu
        if self.main_config.mcu_enable:
            self.mcu = SerialMCU(self.ttyTH_list[0], get_edition=self.main_config.mcu_get_edition_enable)  # MCU数据
            self.mcu.listen_comm_open_error_callback(self.user_pw.chmod_777)
            # self.mcu.get_radar_mcu_edition()
            print(f"{datetime.datetime.now()},mcu_edition={self.mcu.decoder.edition_str}")
            if self.mcu.decoder.edition_str is not None:
                self.xml_handle.save_key_value_to_xml("mcu_version", self.mcu.decoder.edition_str)
            self.mcu.start()
        else:
            self.mcu = None

        # if self.main_config.ntp_enable:
        #     self.ntp_start()
        # else:
        #     print(f"{datetime.datetime.now()},ntp_enable={self.main_config.ntp_enable}")

        # TCP&UDP通讯
        self.tcp_server = MainTcpServer(self.main_config.tcp_server_port, self.config_manager)
        self.imageAreaHandle.imageAreaSetRadarArea(self.radarAreaHandle)
        self.tcp_server.vanishHandle = self.vanishHandle
        self.tcp_server.imageAreaHandle = self.imageAreaHandle
        self.tcp_server.radarAreaHandle = self.radarAreaHandle
        self.trace.cameraDataHandle = self.x
        self.trace.radarDataHandle = self.y

        if self.main_config.infer_enable:
            self.tcp_server.reStart_guard_callback = self.nano_infer.restart_guard # 重启融合函数
        self.tcp_server.run_forever(is_block=False)

        self.heart_beat_thread = HeartBeat_frame(self.mcu, self.tcp_server, self.radar_driver, self)#雷达\推理掉线在这里
        if self.main_config.pika_rabbitmq_enable:
            self.deviceControlForBeiJing = DeviceControlForBeiJing(self.imageAreaHandle,self.y, self.nano_infer,self.heart_beat_thread)
            self.trace.deviceControlForBeiJing = self.deviceControlForBeiJing

        self.heart_beat_thread.zipx_s_service_restart_callback = self.user_pw.zipx_s_service_restart
        # if self.mcu is None: #20221213
        self.heart_beat_thread.listen_power_control_gpio_set(self.user_pw.power_control_gpio, self.user_pw.power_control_gpio_reset)
        self.heart_beat_thread.start()
        print(f"{datetime.datetime.now()},heart_beat_thread start")
        self.heart_beat_thread.update_camera_rtsp_callback = self.update_camera_rtsp

        # self.radar_driver.decoder.listen_radar_data_handler(self.handle_radar_data) # 赋值回调函数
        #qs
        if False:
            from xypVirtualInput import VirtualInput
            self.virtualInput=VirtualInput("/ssd/xyp/2024-06-04 13-47.log",self.y.handleRadarData,self.x.handleCameraData)

            self.trace.engine =self
            def awe(b):
                pass
            self.radar_driver.decoder.listen_radar_data_handler(awe) # 赋值雷达回调函数
            self.camera_driver.listen_radar_data_handler(awe)
        else:
            self.radar_driver.decoder.listen_radar_data_handler(self.y.handleRadarData) # 赋值雷达回调函数
            self.camera_driver.listen_radar_data_handler(self.x.handleCameraData)

        self.camera_false_alarm_list=CameraFalseAlarmFilter(config_folder=self.config_manager.config_folder)



        # self.camera_driver.listen_radar_data_handler(self.handle_camera_data)


        self.tcp_server.set_config_callback = self.handle_config_callback
        self.tcp_server.handle_auto_calibration_callback = self.handle_auto_calibration_callback
        self.tcp_server.handle_main_config_callback = self.handle_main_config_callback




        if self.isWindows:
            from Audio_Receiver import audio_receiver_test
            self.tcp_server.handle_audio_talk_callback = audio_receiver_test
        self.trace.acousto_optic_alarm_callback = self.heart_beat_thread.set_acousto_optic_power
        self.trace.send_alarm_event_callback = self.tcp_server.send_alarm_event
        if self.mcu is not None:
            self.camera_occlude_update_to_heartbeat_callback = self.mcu.decoder.component_status.camera_status_update
        self.tcp_server.handle_remote_call_acousto_optic_power_callback = self.heart_beat_thread.handle_remote_call_acousto_optic_power

        # 报警图像保存，5s存图间隔，最多2天
        self.alarmPic_save = Save_Pic_by_Infer(pic_timeSpan_min=self.main_config.pic_timeSpan_min,
                                               max_file_num=self.main_config.max_file_num,
                                               max_file_size=self.main_config.max_file_size,
                                               sudo_pw=self.user_pw.sudo_pw,
                                               pic_folder=self.config_manager.pic_folder)
        self.trace.saveAlarmPicture_task_enQueue = self.alarmPic_save.saveAlarmPicture_task_enQueue
        self.trace.save_c01_radar_pic_callback = self.alarmPic_save.save_c01_radar_pic

        # debug config
        self.debug_settings()
        self.device_settings()
        self.update_camera_rtsp()
        # 程序启动时，先置于有火车状态,关闭红外灯。
        self.handle_camera_data_block_alarm_icr(True, True, None)

        if "UDP" in self.radar_driver.className:
            if self.radar_driver_udp_cmd is not None:
                self.config_manager.set_radar_defence_area_callback=self.radar_driver_udp_cmd.set_radar_defence_area    # udp需要从15000命令端口发送
                self.radar_driver_udp_cmd.listen_radar_objArea_update_callback(self.config_manager.update_defence_area_list)
            else:
                self.config_manager.set_radar_defence_area_callback = self.radar_driver.set_radar_defence_area
                self.radar_driver.listen_radar_objArea_update_callback(self.config_manager.update_defence_area_list)
        else:
            self.config_manager.set_radar_defence_area_callback = self.radar_driver.set_radar_defence_area
            self.radar_driver.listen_radar_objArea_update_callback(self.config_manager.update_defence_area_list)

        # 启动文件传输端口
        if self.main_config.http_file_port > 0:
            directory = '/ssd/alarmpic/'
            if not os.path.exists(directory):
                directory ='/home/tvt/back_camera/'
            self.file_server = File_Server(server_ip=self.config_manager.out_ip, server_port=self.main_config.http_file_port, directory=directory)
            self.file_server.server_start("x8")

        if self.main_config.pika_rabbitmq_enable:
            self.rabbitmq_config = self.trace.deviceControlForBeiJing.mq_config
            self.trace.deviceControlForBeiJing.message_for_tx = self.rabbitmq_config.data_dict
        else:
            self.rabbitmq_config = None
        print(f"{datetime.datetime.now()},MainEngine init finish")

    def super_mv_syncNtpDate(self):
        print(f"{datetime.datetime.now()},super_mv_syncNtpDate ")
        if self.user_pw.user is not None and self.debug_udp_sender.out_ip is not None:
            cmd_ssh_mv = f"ssh {self.user_pw.user}@{self.debug_udp_sender.out_ip} -Y 'python3 /usr/bin/zipx/zj-guard/user_pw.py' "
            print(f"super_mv_syncNtpDate {cmd_ssh_mv}")
            os.system(cmd_ssh_mv)

    def handle_camera_get_icr_control_handle(self):
        if "debug" in self.camera_type:
            # windows调试不需要控制相机icr
            camera_http_icr = False
        elif "hk" in self.camera_type:
            # 海康相机不需要控制icr
            camera_http_icr = False
        elif ":8554/0" in "".join(self.camera_rtsp):
            # 940相机，不用控制icr
            camera_http_icr = False
        else:
            # 自研相机，火车来时需要关闭红外灯
            camera_http_icr = True

        if camera_http_icr and self.main_config.camera_remote_enable:
            # 控制icr 火车来时需要关闭红外灯
            print(f"{datetime.datetime.now()},camera_http_icr enable")
            self.camera_http_icr = Camera_Train_Icr()
        else:
            print(f"{datetime.datetime.now()},camera_http_icr disable")
            self.camera_http_icr = None

    def debug_settings(self):
        """
        根据config_manager中读到debug_config.ini中的配置开关参数，确定udp广播哪些调试信息
        :return:
        """

        debug_config = self.config_manager.debug_config
        print(f"debug_path={os.path.join(debug_config.file_folder, debug_config.file_name)},debug_config={debug_config.config}")
        if debug_config.config is not None:
            if "debug_score" in debug_config.config.keys() and debug_config.config["debug_score"] > 0:
                self.trace.udp_debug_callback = self.debug_udp_sender.udp_send  # 调试Score分数
            if "debug_tcp_client" in debug_config.config.keys() and debug_config.config["debug_tcp_client"] > 0:
                self.tcp_server.udp_debug_callback = self.debug_udp_sender.udp_send  # 调试TCP已有连接
            if "debug_mcu" in debug_config.config.keys() and debug_config.config["debug_mcu"] > 0:
                self.mcu.decoder.udp_debug_callback = self.debug_udp_sender.udp_send  # 调试MCU decoder
            if "debug_radar" in debug_config.config.keys() and debug_config.config["debug_radar"] > 0:
                self.radar_driver.decoder.udp_debug_callback = self.debug_udp_sender.udp_send  # 调试雷达decoder
            self.debug_print_callback = self.debug_udp_sender.udp_send  # 调试雷达或者相机目标列表信息

    def device_settings(self):
        """
        根据config_manager中读到device_config.ini中的配置，确定声光报警器是否常开
        :return:
        """

        device_config_path = os.path.join(self.config_manager.device_config.file_folder,
                                          self.config_manager.device_config.file_name)
        print(f"device_config_path={device_config_path},device_config={self.config_manager.device_config.config}")
        if self.config_manager.device_config.config is not None:
            if 'is_voice_normally_open' in self.config_manager.device_config.config.keys():
                # 如果是支持喊话和语音播报的喇叭，则一直打开供电
                self.heart_beat_thread.always_power_on = self.config_manager.device_config.config["is_voice_normally_open"]

    def get_speak_config_data(self):
        """
        根据config_manager中读到speak_config.json中的配置，确定声光报警器开关和音量
        :return:
        """
        on_off = self.config_manager.speak_config.on_off
        volume = self.config_manager.speak_config.volume
        return on_off, volume



    def update_camera_rtsp(self):
        """
        通过与外部ip的socket连接获得对外ip地址,
        一次尝试连接的远端ip地址，connect_ip_list = ['8.8.8.8', '192.168.1.1']
        此函数可能有点问题
        :return:
        """
        connect_ip_list = ['8.8.8.8', '192.168.1.1']
        for connect_ip in connect_ip_list:
            my_ip = self.debug_udp_sender.get_out_ip(connect_ip, ip_change_callback=self.ip_change_update_rtsp_callback)
            if my_ip is not None:
                break

    def ip_change_update_rtsp_callback(self):
        """
        根据 self.udp_sender.out_ip 和相机视频流地址更新对外url
        有"Streaming/Channels"的是海康相机
        :return:
        """
        # 先默认发送内部RTSP流地址
        if "Streaming/Channels" in "".join(self.camera_rtsp):
            # HK相机
            self.config_manager.camera_url_out = ["rtsp://admin:Admin123@192.168.8.12/Streaming/Channels/101",
                                                  "rtsp://admin:Admin123@192.168.8.11/Streaming/Channels/101"]
        else:
            # 自研相机
            self.config_manager.camera_url_out = ["rtsp://admin:Admin123@192.168.8.12:554/ch01.264",
                                                  "rtsp://admin:Admin123@192.168.8.11/live/0/MAIN"]
        # 如果有外部ip则改写为外部rtsp流地址
        if self.debug_udp_sender.out_ip is not None and len(self.debug_udp_sender.out_ip) >= 6:
            self.config_manager.out_ip = self.debug_udp_sender.out_ip
            if not self.main_config.camera_remote_enable:
                if "rv1126" in self.config_manager.cpu_platform:
                    self.config_manager.camera_url_out = [f"rtsp://admin:Admin123@{self.config_manager.out_ip}:5542/ch01.264", ""]
                else:
                    # 60m 原型机
                    self.config_manager.camera_url_out = self.camera_rtsp
            elif "Streaming/Channels" in "".join(self.camera_rtsp):
                # HK相机 rtsp://admin:Admin123@192.168.8.200:5542/ch01.264  rtsp://admin:Admin123@192.168.8.200:5541/live/0/MAIN
                self.config_manager.camera_url_out = [
                    f"rtsp://admin:Admin123@{self.config_manager.out_ip}:5542/Streaming/Channels/101",
                    f"rtsp://admin:Admin123@{self.config_manager.out_ip}:5541/Streaming/Channels/101"]
            elif ":8554" in "".join(self.camera_rtsp):
                # 940相机 'rtsp://admin:Admin123@192.168.8.12:8554/0' 'rtsp://admin:Admin123@192.168.8.11:8554/0
                self.config_manager.camera_url_out = [
                    f"rtsp://admin:Admin123@58.20.230.32:10083/0",
                    f"rtsp://admin:Admin123@58.20.230.32:10082/0"]
            else:
                # 850 相机
                self.config_manager.camera_url_out = [
                    f"rtsp://admin:Admin123@{self.config_manager.out_ip}:5542/ch01.264",
                    f"rtsp://admin:Admin123@{self.config_manager.out_ip}:5541/live/0/MAIN"]
        print(f"camera_url_out={self.config_manager.camera_url_out}")

    def debug_callback_function(self, data):
        """
        用于调试打印的函数，自动判断debug_print_callback是否为空，避免每个调用的地方重复写判空语句
        :param data:
        :return:
        """
        if self.debug_print_callback is not None:
            self.debug_print_callback(data)

    def handle_config_callback(self, json_obj):
        """
        处理网页或者上位机传过来的参数配置请求
        :param json_obj:tcp客户端传过来的配置参数
        :return:
        """
        respon = {}
        print(f"{datetime.datetime.now()},handle_config_callback,{json_obj}")
        if 'speak_config' in json_obj["data"] or "status" in json_obj["data"]:
            respon = self.config_manager.speak_config.set_volume(json_obj["data"])
        if 'transfer_config' in json_obj["data"]:
            transfer_config = json_obj["data"]["transfer_config"]
            respon = self.radar_driver.transfer_handle.set_transfer_mode(transfer_config)
        return respon


    def handle_main_config_callback(self, json_obj):
        """
        处理网页或者上位机传过来的main_config参数配置请求
        :param json_obj:tcp客户端传过来的配置参数
        :return:
        """
        try:
            json_dict = json_obj["data"]
            self.config_manager.main_config.load_from_dict(data_dict=json_dict)
            json_dict["radar_alarm_score"] = self.config_manager.main_config.camera_alarm_score
            json_dict["camera_alarm_score"] = self.config_manager.main_config.radar_alarm_score
            json_dict["joint_alarm_score"] = self.config_manager.main_config.joint_alarm_score
            self.config_manager.main_config.update_rotationMatrix()
            self.config_manager.main_config.data_dict = json_dict
            self.config_manager.main_config.config_file_handler.save_to_file(json_dict)
            print(f"handle_main_config_callback data_dict={self.config_manager.main_config.data_dict}")
        except:
            print(f"handle_main_config_callback {traceback.format_exc()}")


    def handle_auto_calibration_callback(self, json_obj):
        try:
            print(f"self.camera_rtsp={self.camera_rtsp}")
            xypDebug(f"self.camera_rtsp={self.camera_rtsp}")
            # 是否是第一次创建
            if not hasattr(self.config_manager, 'auto_calibration_result'):
                self.config_manager.auto_calibration_result = {}
            cameraConfig = [None,None]
            # 适配铁道设备
            for idx, url in enumerate(self.camera_rtsp, 1):
                if "8.12" in url:
                    cameraConfig[0] = self.config_manager.calibrationloader.calibration_dict[url]
                elif "8.11" in url:
                    cameraConfig[1] = self.config_manager.calibrationloader.calibration_dict[url]
            cameraConfig = calibVanishPoint('/ssd/zipx/log/',cameraConfig)
            self.config_manager.auto_calibration_result[0] = cameraConfig[0]
            self.config_manager.auto_calibration_result[1] = cameraConfig[1]
            print(self.config_manager.auto_calibration_result,"self.config_manager.auto_calibration_result")
            xypDebug(f"self.camera_rtsp={self.config_manager.auto_calibration_result}")
        except:
            xypDebug(f"handle_auto_calibration_callback {traceback.format_exc()}")
            print(f"handle_auto_calibration_callback {traceback.format_exc()}")



    def run(self):
        """
        启动相关通信模块
        :return:
        """
        if self.camera_driver is not None:
            self.camera_driver.start()
            print(f"{self.className},run,self.camera_driver start")
        else:
            print(f"{self.className},run,self.camera_driver is None")
        if self.radar_driver is not None:
            self.radar_driver.start()
            print(f"{self.className},run,self.radar_driver start")
        else:
            print(f"{self.className},run,self.radar_driver is None")

        if self.radar_driver_udp_cmd is not None and "UDP" in self.radar_driver_udp_cmd.className:
            self.radar_driver_udp_cmd.start()
            print(f"{self.className},run,self.radar_driver_udp_cmd start")
        else:
            print(f"{self.className},run,self.radar_driver_udp_cmd not start")

    def update(self):
        # try:
            # while 1:
            #     self.trace.is_alarm_by_score2(None, None,
            #                                  send_merge_data_callback=self.tcp_server.send_merge_data,
            #                                  pronounce_queue=self.thread_pronounce.pronounce_alarm_type_queue0,
            #                                  remote_call_power_on=self.config_manager.remote_call_power_on,
            #                                  send_url_data_callback=self.tcp_server.send_url_data)
        self.trace.moniter(None, None, send_merge_data_callback=self.tcp_server.send_merge_data,
                                        pronounce_queue=self.thread_pronounce.pronounce_alarm_type_queue0,
                                        remote_call_power_on=self.config_manager.remote_call_power_on,
                                        send_url_data_callback=self.tcp_server.send_url_data)
        # except Exception as e:
        #     xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
    def process_each_area(self, current_stamp, recent_lst):
        """
        最近的3秒内每秒都至少有一个信号
        当前代码中未调用，准备弃用 ---zzl 20220525
        :param current_stamp:
        :param recent_lst:
        :return:
        """
        last_empty_index = -1
        rst_set = set()
        for index in range(len(recent_lst) - 1, -1, -1):
            stamp, data = recent_lst[index]
            duration = current_stamp - stamp
            rst_set.add(math.floor(duration))

            if duration > self.time_care_in_seconds:
                last_empty_index = index
                break

        return rst_set.issuperset(range(self.time_care_in_seconds)), last_empty_index, rst_set




    def get_fog_coef_zhaoJin(self,camera_fogStrings):
        # 有雾的时候返回0.5
        # 无雾的时候返回0.95
        # '101.12,100.49,95.20,98.59,95.17,96.78,94.85,93.51,93.34,103.75,94.47,94.61,93.81,102.29,101.57,105.32,110.50,115.15,130.31,130.59,118.23,146.41,142.59,130.90,124.13,107.15,88.91,79.97,90.41,107.03,0',
        fog_coef=0.95
        return fog_coef

    def get_fog_coef(self, camera_fogStrings):
        # {
        #     'farcamerafog': '100.37,100.52,105.63,105.84,102.02,107.17,104.40,104.74,111.15,110.23,'
        #                     '120.53,131.63,135.06,131.61,126.97,123.15,113.17,116.50,115.03,110.43,'
        #                     '107.21,106.42,100.06,96.48,95.21,89.02,91.72,89.67,87.59,85.93,0'}
        if self.main_config.fog_enable:
            isDayTime = True
            if camera_fogStrings[-1] in ["0", "1"]:
                isDayTime = int(camera_fogStrings[-1])
                camera_fogStrings = camera_fogStrings[0:-1]
            # print(f"get_fog_coef isDayTime={isDayTime} fogStrings={camera_fogStrings}")
            camera_fogValues = [float(val) for val in camera_fogStrings]
            if isDayTime:
                # 白天，彩色模式
                fog_coef = self.get_fog_coef_dayTime(camera_fogValues)
            else:
                # 晚上，黑白模式
                fog_coef = self.get_fog_coef_nightTime(camera_fogValues)
        else:
            fog_coef = 1.0
        return fog_coef

    def get_fog_coef_dayTime(self, camera_fogValues):
        # 分成3组，以最小的一组为准
        fogValues_len = len(camera_fogValues)
        group_len = int(fogValues_len / 3)
        fogGroup = [camera_fogValues[0:group_len], camera_fogValues[group_len:2 * group_len],
                    camera_fogValues[group_len * 2:3 * group_len]]
        fogSum = [sum(group) for group in fogGroup]
        min_index = fogSum.index(min(fogSum))
        camera_fogValues_min = fogGroup[min_index]
        fog_values_len = len([x for x in camera_fogValues_min if x > 15])
        fog_coef = 0.8 if fog_values_len >= 4 else 0.5  # 相机视野良好，雷达分数乘以小系数，减少雷达误报
        if self.fog_coef_cnt <= 30:
            self.fog_coef_cnt += 1
        return fog_coef

    def get_fog_coef_nightTime(self, camera_fogValues):
        # 确定递增计数，
        # "nearcamerafog": "69.61,70.68,60.71,65.07,57.18,59.92,53.21,50.52,45.43,46.57,
        #                   40.16,38.05,35.49,41.77,40.25,45.28,40.98,54.66,57.69,65.19,
        #                   18.70,26.25,28.50,22.14,30.03,28.92,34.71,24.76,36.20,18.63,1",
        camera_fogValues_len=len(camera_fogValues)
        # 20231016
        consecutive_cnt =self.find_max_consecutive_length(camera_fogValues)
        if consecutive_cnt >= 0.4 * camera_fogValues_len:
            # 有雾，雷达分数接近1
            fog_coef = 0.8
        else:
            # 相机视野良好，雷达分数乘以小系数，减少雷达误报
            fog_coef = 0.5
        print(f"get_fog_coef_nightTime fog_coef={fog_coef},consecutive_cnt={consecutive_cnt},camera_fogValues_len={camera_fogValues_len}"
              f"camera_fogValues={camera_fogValues}")
        if self.fog_coef_cnt <= 30:
            print(f"get_fog_coef_nightTime fog_coef={fog_coef} increase_cnt={consecutive_cnt}<<<{camera_fogValues}")
            self.fog_coef_cnt += 1
        return fog_coef

    def find_max_consecutive_length(self,nums):
        if not nums:
            return 0

        max_inc_length = 1
        max_dec_length = 1
        current_increase_length = 1
        current_decrease_length = 1

        for i in range(1, len(nums)):
            if nums[i] > nums[i - 1]:
                current_increase_length += 1
            else:
                max_inc_length = max(max_inc_length, current_increase_length)
                current_increase_length = 1
            if nums[i] < nums[i - 1]:
                current_decrease_length += 1
            else:
                max_dec_length = max(max_dec_length, current_decrease_length)
                current_decrease_length = 1
        return max(max_inc_length, max_dec_length, current_increase_length, current_decrease_length)


    def handle_camera_data_false_alarm_decrease_confidence(self, bbox, target):
        if self.camera_false_alarm_list.isInFalseAlarmList_by_bbox(bbox):
            confidence_pre = target["confidence"]
            target["confidence"] *= 0.4
            confidence_after = target["confidence"]
            if self.false_alarm_cnt < 20:
                print(f"{datetime.datetime.now()},{bbox},handle_camera_data_false_alarm_decrease_confidence, {round(confidence_pre,3)}>>{round(confidence_after,3)}")
                # print(f"top_count_dict={self.camera_false_alarm_list.top_count_dict}")
                print(f"count_2_minute.count={self.camera_false_alarm_list.count_2_minute.count}")
                self.false_alarm_cnt += 1

    def handle_camera_data_block_alarm_icr(self, isTrainLight, isTrainObj, target_bbox):
        """
        火车灯光上升沿，关灯，屏蔽报警block_time。
        有火车目标，屏蔽报警block_time
        block_time 秒后开灯，解除报警屏蔽
        :param isTrainLight:
        :param isTrainObj:
        :param target_bbox:
        :return:
        """
        # 火车灯光、火车目标、雷达检测到火车，均可屏蔽报警
        is_block_alarm_Edge = self.block_alarm_edge.is_Edge(isTrainLight or isTrainObj or self.radar_driver.is_train_by_radar_edge.lastValue)
        # 火车灯光\雷达检测到火车，可关闭红外灯
        is_block_icr_edge = self.block_icr_edge.is_Edge(isTrainLight or self.radar_driver.is_train_by_radar_edge.lastValue)

        # 报警屏蔽
        if is_block_alarm_Edge and self.block_alarm_edge.lastValue:
            self.trace.is_train_block_alarm = 1
            # 有train_in_view 打印信息
            print(f"{datetime.datetime.now()},is_block_alarm_Edge={self.block_alarm_edge.lastValue}, target_bbox={target_bbox}")
        # 火车灯光上升沿，关灯
        if is_block_icr_edge and self.block_icr_edge.lastValue:
            print(f"{datetime.datetime.now()},is_block_icr_edge={self.block_icr_edge.lastValue}")
            if self.camera_http_icr is not None:
                self.camera_http_icr.set_camera_icr_by_train(True)  # 关灯

        # 报警屏蔽达到指定时间，解除报警屏蔽
        if time.time() - self.block_alarm_edge.last_rising_timestamp >= self.block_time and not self.block_alarm_edge.lastValue:
            # 如果之前是block状态，则打印信息
            if self.trace.is_train_block_alarm:
                print(f"{datetime.datetime.now()},is_train_block_alarm=0,")
            self.trace.is_train_block_alarm = 0
        # 关闭红外达到指定时间并且当前没有火车灯光，打开红外
        if time.time() - self.block_icr_edge.last_rising_timestamp >= self.block_time and not self.block_icr_edge.lastValue:
            # 之前是屏蔽红外状态，则控制
            if self.camera_http_icr is not None and self.camera_http_icr.isTrainInView:
                self.camera_http_icr.set_camera_icr_by_train(False)  # 开灯
                self.block_count += 1

        # self.block_count=0对应程序启动时候第一次block_time为10s，之后block_time为180
        if self.block_count == 1 and self.block_time <= 10:
            print(f"{datetime.datetime.now()},block_time=180")
            self.block_time = 180  # 屏蔽报警和关灯恢复时间



    def handler_radar_virtualObj2jsonData(self, camera_virtual_radar_obj_xyv_list):
        """
        根据虚拟目标列表，生成虚拟目标报文
        :param camera_virtual_radar_obj_xyv_list:[[ID, x, y, vx, vy],...] example [[65, 66, 67, 68, 69],[80, 81, 82, 83, 84]]
        :return:
        """
        last_stamp = time.time()

        # 根据Y坐标，将雷达目标归到不同的ixyv_list
        ixyv_list_0 = []    # 近端雷达目标
        ixyv_list_1 = []    # 远端雷达目标
        for index in range(len(camera_virtual_radar_obj_xyv_list)):
            ixyv = camera_virtual_radar_obj_xyv_list[index]
            if ixyv[2] <= THRESHOLD_NEAR_FAR:
                ixyv_list_0.append(ixyv)
            else:
                ixyv_list_1.append(ixyv)

        # 处理 ixyv_list_0 近端雷达目标
        obj_dict_list = []
        for index, ixyv in enumerate(ixyv_list_0):
            obj_dict = {"in_area": 1, "dto": ixyv, }
            obj_dict_list.append(obj_dict)
        dto_dict_0 = {"id": 0, "data": obj_dict_list}

        # 处理 ixyv_list_1 远端雷达目标
        obj_dict_list_1 = []
        for index, ixyv in enumerate(ixyv_list_1):
            obj_dict = {"in_area": 1, "dto": ixyv, }
            obj_dict_list_1.append(obj_dict)
        dto_dict_1 = {"id": 1, "data": obj_dict_list_1}

        json_obj = {
            "stamp": last_stamp,
            "list": [dto_dict_0, dto_dict_1]
        }
        return json_obj
        # print(f"handler_radar_virtual_obj, json_obj={json.dumps(json_obj)}")
        # print(f"handler_radar_virtual_obj, json_obj={json_obj}")
        # {"stamp": 1661481976.3627234, "list": [{"id": 0, "data": []},
        #                                        {"id": 1,"data": [{"in_area": 1,"dto": [2649,-1.775,25.452,-0.005,0.075]}]}
        #                                        ]}


def get_serialName_from_ls_cmd(cmd="ls -l /dev/ttyT*", filterKey='ttyTH', ):
    """
    在shell中通过ls命令获得当前系统中的串口列表
    :param cmd:用于列举串口的shell命令，默认为"ls -l /dev/ttyT*"命令
    :param filterKey:用于过滤结果的 串口名前缀字符串，默认为'ttyTH'
    :return:
    """
    if "Linux" in platform.platform():
        if "bian" in platform.platform():
            return ["/dev/ttyS0", "/dev/ttyS1", ]  # 20221026 debian系统 0 MCU数据 ,1 radar串口
        elif "armv7l" in platform.platform():
            return ["/dev/ttyS1", "/dev/ttyS0", ]  ## 20230626 60米雷视一体机  "/dev/ttyS1" radar串口, "/dev/ttyS1" 未使用
        else:
            p = subprocess.Popen(f'{cmd}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            text_list = []
            for stdoutLine in p.stdout.readlines():
                text_list.extend(str(stdoutLine, encoding='utf-8').split(" "))
            print(f"get_serialName_from_ls_cmd cmd={cmd}", text_list)
            ttyTH_list = [x.strip() for x in text_list if filterKey in x]
            if len(ttyTH_list) == 0:
                print(f"error in get_serialName_from_ls_cmd ttyTH_list=", ttyTH_list)
            else:
                pass
                # print(f"get_serialName_from_ls_cmd={cmd},filterKey={filterKey}\n", ttyTH_list)
            p.kill()
            return ttyTH_list
    elif "Windows" in platform.platform():
        return ["COM1", "COM2", ]


if __name__ == "__main__":
    # defence = [
    #     [-3.7483939446315917, 0],
    #     [-10.492263740617746, 28.796109566705628],
    #     [-10.434913289482123, 113.23762313573822],
    #     [0.05222912089276654, 107.12265534038852],
    #     [-0.8228577938721543, 0]]
    # radarData, camera0Data, camera1Data = analyseLog(
    #     r"C:\Users\admins\Desktop\20230809铁路晚上测试漏报图片.selection\新建文件夹\200839.log")
    # for radarFrame in radarData:
    #     for radarObj in radarFrame:
    #         x, y = radarObj["xy"]
    #         handle_radar_data([[1,x,y,0,0]])
            # print( radarObj["xy"])
            # print(Polygon_zzl.isPointIntersectPoly(radarObj["xy"], defence))
    pass

