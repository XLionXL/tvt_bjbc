"""
配置管理中心
"""
import datetime
import json
import numpy as np
import os
import platform
from blinker import signal
from os import path

import transform_tools
from autoMendRadarOffset import amendRadarOffset
from comm_Polygon import Polygon_zzl
from commdef import *
from common_FileLoadSave import File_Saver_Loader_SN
from common_FileLoadSave import File_Saver_Loader_json
from config_file_json import CONFIG_FILE
from configs import BaseConfig
from videoCalibration_LineDetect import Convertor_pkl_json


class JsonObjEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, CameraConfig):
            return obj.__str__()
        elif isinstance(obj, AreaConfig):
            return obj.data_list
        elif isinstance(obj, RadarConfig):
            return obj.pose_dict
        elif isinstance(obj, BaseConfig):
            return obj.data
        return json.JSONEncoder.default(self, obj)


class AreaConfig(object):

    def __init__(self, area_file_path="", real_length=-1, pix_real_ratio=-1):
        self.area_file_path = area_file_path

        self.data_list = None

        self.transform_M = None
        self.real_length = real_length
        self.pix_real_ratio = pix_real_ratio
        # self.alarmLevel = 1  # 1(low),2,3(high)

        if not os.path.exists(self.area_file_path):
            return

        with open(self.area_file_path, "r") as f:
            # [[u,v,x,y,z],[]...]
            self.data_list = json.load(f)
            self._init_roi()

    def _init_roi(self):
        # 转换到统一的显示分辨率下
        self.camera_roi_json_obj = [
            (transform_tools.scale_xy(p[:2], (dst_width, dst_height), (calib_width, calib_height)))
            for p in self.data_list]

        if self.real_length != -1 and self.pix_real_ratio != -1:
            self._init_transform_matrix(self.real_length, self.pix_real_ratio)

    def _init_transform_matrix(self, real_length=70, pix_real_ratio=40):
        """
        初始化2D与3D坐标的转换关系矩阵
        :param real_length:     相机观测的最远距离，单位为m
        :param pix_real_ratio:  像素和物理尺寸的放大比例(避免物理尺寸较小，映射到像素int空间导致的精度丢失问题)
        :return:
        """
        self.q_point_list = [
            [transform_tools.scale_xy(p[:2], (dst_width, dst_height), (calib_width, calib_height)), *p[2:]]
            for p in self.data_list]

        if len(self.q_point_list) < 4:
            print("-----------------3D转换矩阵初始化失败，请确保标定点至少有四个")
            return

        # 640x360分辨率 point = [(u,v),x,y,z]
        src2d = [(point[0][0], point[0][1]) for point in self.q_point_list]
        src3d = [(point[1], real_length - point[2]) for point in self.q_point_list]

        pts_src = np.array(src2d, dtype=np.float32)
        pts_dst = np.array(src3d, dtype=np.float32) * pix_real_ratio
        # self.transform_M = cv2.getPerspectiveTransform(pts_src, pts_dst)

        """
        self.real_length = 60.0  # 距离m
        self.pix_real_ratio = 40.0  # 像素和实际尺寸的放大比例(避免物理尺寸较小，映射到像素int空间导致的精度丢失问题)

        # 这里是反向推算相机前方一个矩形区域在2D画面上的四个点（长60m,宽7m, ）
        self.transform_M_transpose = np.linalg.inv(self.transform_M)
        real_min_x = min(src3d, key=lambda x: x[0])[0] - 0.5
        real_max_x = real_min_x + 6.5
        org_3d = np.array([
            [real_min_x, self.real_length - 3], [real_min_x, 0], [real_max_x, 0], [real_max_x, self.real_length - 3]
        ], dtype=np.float32) * self.pix_real_ratio

        calib_2d_points = cv2.perspectiveTransform(org_3d.reshape(-1, 1, 2), self.transform_M_transpose)
        calib_2d_points = calib_2d_points.reshape(-1, 2)
        self.calib_2d_points = [QPoint(int(point[0]), int(point[1])) for point in calib_2d_points]
        self.calib_2d_q_polygon = QPolygon(self.calib_2d_points)
        """

    def load_from_json(self, json_list):
        # self.data_list = json.loads(json_str)
        self.data_list = json_list
        self._init_roi()

    def get_transform_matrix(self):
        return self.transform_M

    def __repr__(self):
        return str(self.data_list)

    def __str__(self):
        return str(self.data_list)

    def points(self):
        return self.camera_roi_json_obj

    def save(self):
        with open(self.area_file_path, "w") as f:
            json.dump(self.data_list, f)


class RadarConfig():

    def __init__(self, radar_config_path):
        # self.current_dir = path.dirname(path.abspath(__file__))
        self.radar_config_path = radar_config_path

        self.pose_dict = None

        self.xyz_rpy = [
            0.0,  # x
            0.0,  # y
            0.0,  # z
            0.0,  # roll  翻滚
            0.0,  # pitch 俯仰
            0.0  # yaw   偏航
        ]

        self.load_config()

    def save_config(self, data_dict: dict = None):

        if data_dict is not None:
            self.update_pose(data_dict)

        with open(self.radar_config_path, encoding="utf-8", mode="w") as f:
            json.dump(self.pose_dict, f)
            print("RadarConfig 配置文件保存成功：", self.radar_config_path)

    def load_config(self):
        if not path.exists(self.radar_config_path):
            print("RadarConfig 配置文件不存在：", self.radar_config_path)
            return

        with open(self.radar_config_path, encoding="utf-8", mode="r") as f:
            data = json.load(f)
            if data is None or len(data) != 6:
                print("RadarConfig 加载配置文件失败，数据有误：", data)
                return

            # print("加载雷达配置文件成功：", data)
            self.update_pose(data)

    def update_pose(self, data):
        self.pose_dict = data
        self.xyz_rpy = [
            self.pose_dict["x"],
            self.pose_dict["y"],
            self.pose_dict["z"],
            self.pose_dict["_r"],
            self.pose_dict["_p"],
            self.pose_dict["_y"],
        ]

    def __str__(self):
        return str(self.pose_dict)

    def get_radar_ex_params(self):
        # 这里要根据索引取对应的雷达外参
        return self.xyz_rpy


class CameraConfig():

    def __init__(self, camera_intrinsic_path):
        self.is_remap = True

        self.camera_intrinsic_path = camera_intrinsic_path

        self.content = None
        self.cameraMatrix = None
        self.distCoeffs = None
        self.image_size = None
        self.rectify_map1 = None
        self.rectify_map2 = None

        # self.load_config()

    # def load_config(self):
    #     if not os.path.exists(self.camera_intrinsic_path):
    #         return
    #
    #     with open(self.camera_intrinsic_path, "r") as file:
    #         self.content = file.read()
    #
    #     fs = cv2.FileStorage(self.camera_intrinsic_path, cv2.FileStorage_READ)
    #     print("---------------------------->", type(fs))
    #     self.cameraMatrix = fs.getNode("camera_matrix").mat()
    #     self.distCoeffs = fs.getNode("distortion_coefficients").mat()
    #     self.image_size = (int(fs.getNode("image_width").real()), int(fs.getNode("image_height").real()))
    #     print("cameraMatrix: \n", self.cameraMatrix)
    #     # print("distCoeffs: \n", self.distCoeffs)
    #     # print("image_size: \n", self.image_size)
    #     fs.release()
    #     # 初始化图像去畸变纠正Map
    #     self.rectify_map1, self.rectify_map2 = cv2.initUndistortRectifyMap(self.cameraMatrix, self.distCoeffs,
    #                                                                        None, self.cameraMatrix,
    #                                                                        self.image_size, cv2.CV_16SC2)

    def __str__(self):
        return self.content

    def get_camera_in_params(self):
        # 这里要根据索引取对应的相机内参
        return self.cameraMatrix

    def save(self, content):
        with open(self.camera_intrinsic_path, "w") as f:
            f.write(content)


class Speak_Config:
    def __init__(self, config_file_path=os.path.join(".", "config", "speak_config.json")):
        self.data_dict = {
            "on_off": 0,
            "volume": 0.5
        }
        self.config_file_handler=File_Saver_Loader_json(config_file_path)
        self.load_from_config_file()
        self.on_off=self.data_dict["on_off"]
        self.volume=self.data_dict["volume"]
        # 开发过程中，在self.data_dict中添加了数据则需要保存
        self.config_file_handler.save_to_file(self.data_dict)

    def load_from_config_file(self):
        data_dict=self.config_file_handler.load_from_file()
        print(f"{datetime.datetime.now()}, Speak_Config load_from_config_file, data_dict={data_dict}")
        if data_dict is not None:
            for key in data_dict:
                self.data_dict[key]=data_dict[key]

    def set_volume(self, config_data_in):
        # config_data_in={'status': '0'}
        # config_data_in={'status': '0',"volume":0.5}
        # print(datetime.datetime.now(), f"set_volume config_data_in={config_data_in}")
        if 'status' in config_data_in:
            self.on_off= int(config_data_in['status'])
            self.data_dict['on_off'] = int(config_data_in['status'])
        if 'volume' in config_data_in:
            self.volume = config_data_in['volume']
            self.data_dict["volume"] = config_data_in['volume']
        if 'speak_config' in config_data_in and 'volume' in config_data_in['speak_config']:
            self.on_off = int(config_data_in['speak_config']['status'])
            self.volume = config_data_in['speak_config']['volume']
            self.data_dict["volume"] = config_data_in['speak_config']['volume']
        response= {
            'status': self.data_dict['on_off'],
            'volume': self.data_dict["volume"]
        }
        self.config_file_handler.save_to_file(self.data_dict)
        print(datetime.datetime.now(), f"Speak_Config set_volume data_dict={self.data_dict}")
        return response


class MainEngine_Config:
    def __init__(self, config_file_path=os.path.join(".", "config", "main_config.json")):
        self.data_dict={
            "device_type": "TXPL200-7/94L",
            "camera_udp_port": 10001,
            "radar_udp_port": 17000,
            "radar_decode_head": "AAAA5555",
            "tcp_server_port": 8888,
            "mcu_enable": 1,
            "ntp_enable": 0,
            "fog_enable": 0,
            "radar_get_edition_enable": 1,
            "mcu_get_edition_enable": 1,
            "infer_enable": 1,
            "cpu_min_to_restart_infer": 20,
            "camera_remote_enable": 1,
            "video_save": 3,  # 3 近焦远焦存到一起，4 存视频
            "pronounce_english": 0,  # 0:中文，1:英文
            # "zipx_s_service_restart_time_s": 3600 * 24 * 7,  # 小于0表示不重启
            "zipx_s_service_restart_time_s": -1,  # 小于0表示不重启 20221101
            "http_file_port": -1,  # 小于0表示不启用 20230214
            "max_file_num": 1000,  # 图片和视频文件数目，默认1000个
            "max_file_size": 2000*1000*1000,  # 图片和视频文件大小,默认2G，
            "pic_timeSpan_min": 5,  # 图片存储间隔，单位s
            "mp4_timeSpan_min": 4,  # mp4视频存储间隔，单位s
            "pika_rabbitmq_enable": 0,  # 铁科院rabbitmq发送报警json
            "pika_sftp_enable": 0,  # 铁科院sftp上传报警图片视频
            "radar_alarm_score": 45,
            "camera_alarm_score": 20,
            "joint_alarm_score": 150,
            "camera_radar_h_offset_rad": -0.01,  # 相机相对雷达的水平偏转弧度值,负值雷达框左移，正值雷达框右移
            "confidence_min": 0.55,  # 视觉框最小置信度，0.0-1.0
            # "radarOffset": 0.00516228442320362,
            # "autoMendRadarOffset": 0,
            "autoCalibration": 0,
            "sensitivity": 2,  # 报警灵敏度 2最难报警,1中等,0最容易报警,
            "scores_list": [[10, 25, 50, 3], [15, 35, 100, 6], [20, 45, 150, 10], ]  # 报警灵敏度对应的分支列表，依次是相机、雷达和融合报警阈值
        }

        self.config_file_handler=File_Saver_Loader_json(config_file_path)
        self.load_from_config_file()

        self.update_rotationMatrix()
        self.load_from_dict(data_dict=self.data_dict)
        # 开发过程中，在self.data_dict中添加了数据则需要保存
        self.config_file_handler.save_to_file(self.data_dict)

    def update_rotationMatrix(self):
        if "autoMendRadarOffset" in self.data_dict.keys() and self.data_dict["autoMendRadarOffset"]:
            angle = amendRadarOffset()
            if angle is not None:
                self.data_dict["radarOffset"] = angle
                self.rotationMatrix = np.array(
                    [[np.cos(angle), -np.sin(angle)],
                     [np.sin(angle), np.cos(angle)]])
            else:
                angle = self.data_dict["camera_radar_h_offset_rad"]
                self.rotationMatrix = np.array(
                    [[np.cos(angle), -np.sin(angle)],
                     [np.sin(angle), np.cos(angle)]])
        else:
            angle = self.data_dict["camera_radar_h_offset_rad"]
            self.rotationMatrix = np.array(
                [[np.cos(angle), -np.sin(angle)],
                 [np.sin(angle), np.cos(angle)]])

    def load_from_dict(self, data_dict):
        self.autoCalibration = data_dict["autoCalibration"]
        self.camera_udp_port = data_dict["camera_udp_port"]
        self.radar_udp_port = data_dict["radar_udp_port"]
        self.radar_decode_head = data_dict["radar_decode_head"]
        self.tcp_server_port = data_dict["tcp_server_port"]
        self.http_file_port = data_dict["http_file_port"]
        self.max_file_num = data_dict["max_file_num"]
        self.max_file_size = data_dict["max_file_size"]
        self.pic_timeSpan_min = data_dict["pic_timeSpan_min"]
        self.mp4_timeSpan_min = data_dict["mp4_timeSpan_min"]
        self.mcu_enable = data_dict["mcu_enable"]
        self.ntp_enable = data_dict["ntp_enable"]
        self.fog_enable = data_dict["fog_enable"]
        self.radar_get_edition_enable = data_dict["radar_get_edition_enable"]
        self.mcu_get_edition_enable = data_dict["mcu_get_edition_enable"]
        self.infer_enable = data_dict["infer_enable"]
        self.cpu_min_to_restart_infer = data_dict["cpu_min_to_restart_infer"]
        self.camera_remote_enable = data_dict["camera_remote_enable"]
        self.video_save = data_dict["video_save"]
        self.pronounce_english = data_dict["pronounce_english"]
        self.zipx_s_service_restart_time_s = data_dict["zipx_s_service_restart_time_s"]
        self.pika_rabbitmq_enable = data_dict["pika_rabbitmq_enable"]
        # self.pika_rabbitmq_enable = 0

        self.pika_sftp_enable = data_dict["pika_sftp_enable"]
        self.camera_radar_h_offset_rad = data_dict["camera_radar_h_offset_rad"]
        self.confidence_min = data_dict["confidence_min"]
        # "sensitivity": 0,
        # "scores_list": [[20, 45, 150, 10], [15, 35, 100, 6], [10, 25, 50, 3]]
        self.sensitivity = data_dict["sensitivity"]
        self.scores_list = data_dict["scores_list"]
        if 0 <= int(self.sensitivity) <= 2:
            scores = self.scores_list[int(self.sensitivity)]
            print(f"sensitivity scores={scores}")
            self.camera_alarm_score = scores[0]
            self.joint_alarm_score = scores[2]
            self.radar_alarm_score = scores[1]
        else:
            self.radar_alarm_score = data_dict["radar_alarm_score"]
            self.camera_alarm_score = data_dict["camera_alarm_score"]
            self.joint_alarm_score = data_dict["joint_alarm_score"]

    def load_from_config_file(self):
        data_dict=self.config_file_handler.load_from_file()
        print(f"{datetime.datetime.now()}, load_from_config_file, data_dict={data_dict}")
        if data_dict is not None:
            for key in data_dict:
                self.data_dict[key]=data_dict[key]
        self.data_dict["device_type"]="TXPL200-7/94L"

def get_list_element1(list_input):
    return list_input[1]


class ConfigManager:
    config_update_signal = signal('config_update')

    signal_roi = "roi_signal"
    signal_camera_in = "camera_in_signal"
    signal_camera_ex = "camera_ex_signal"
    signal_camera_radar = "camera_radar_signal"
    signal_rail_radar = "rail_radar_signal"
    signal_source_list = "source_list_signal"

    def __init__(self, camera_rtsp=None, config_folder=None, main_config:MainEngine_Config=None):

        """
        初始化配置信息，读取各项配置文件。
        :param camera_rtsp:相机流地址
        :param config_folder:配置文件存在的路径
        """
        self.cpu_platform="rv1126" if "armv7l" in platform.platform() else "nano"
        Polygon_zzl.init_inside_so()
        self.pic_folder = self.get_make_pic_folder()
        self.defence_area_list = None
        self.main_config = main_config
        self.out_ip = None
        self.remote_call_power_on = False  # 远程喊话声光报警器电源开关
        home_path = os.path.expanduser('~')
        if config_folder is None:
            if "Windows" in platform.platform():
                self.config_folder = os.path.abspath(os.path.join(".", "config"))
            else:
                self.config_folder = os.path.abspath(os.path.join(".", "config"))
        else:
            self.config_folder=config_folder
        print(f"{datetime.datetime.now()},config_folder={self.config_folder}")

        self.source_list_path = os.path.join(self.config_folder, "source_list.json")
        if camera_rtsp is not None:
            self.source_list = camera_rtsp
        else:
            self.source_list = ["", ""]
        self.camera_url_out=["", ""]
        # self.load_source_list()

        # 相机内参信息
        self.camera_in_dict = {
            0: CameraConfig(os.path.join(self.config_folder, "ost_17.yaml")),
            1: CameraConfig(os.path.join(self.config_folder, "ost_64.yaml"))
        }

        # 相机外参文件, 用于计算目标的位置
        self.camera_ex_dict = {
            0: AreaConfig(os.path.join(self.config_folder, "shibian_t1_17.json"), real_length=70, pix_real_ratio=40),
            1: AreaConfig(os.path.join(self.config_folder, "shibian_t1_64.json"), real_length=210, pix_real_ratio=40)
        }


        # 雷达在相机坐标系下的位姿
        self.radar_config_dict = {
            0: RadarConfig(os.path.join(self.config_folder, "radar2camera_17.json")),
            1: RadarConfig(os.path.join(self.config_folder, "radar2camera_64.json"))
        }

        # 雷达在世界坐标系下的位姿
        # self.rail_radar_dict = {
        #     0: BaseConfig(os.path.join(self.config_folder, "radar_config_0.yaml"), "铁轨-雷达0"),
        #     1: BaseConfig(os.path.join(self.config_folder, "radar_config_1.yaml"), "铁轨-雷达1")
        # }
        self.rail_radar_dict = {
            0: None,
            1: None
        }

        self.debug_config = CONFIG_FILE(self.config_folder, "debug_config.ini")
        self.device_config = CONFIG_FILE(self.config_folder, "device_config.ini")

        # 相机安装的校准结果
        calibration_pkl_path = os.path.join(self.config_folder, "calibration.pkl")
        calibration_json_path = os.path.join(self.config_folder, "calibration.json")
        if os.path.exists(calibration_pkl_path) and not os.path.exists(calibration_json_path):
            pkl_json = Convertor_pkl_json()
            # 为了兼容以前版本, 暂时不做calibration.pkl的删除操作
            pkl_json.convert_pkl2json(calibration_pkl_path, calibration_json_path, remove_source_file=False)

        # 声音开关和音量
        self.speak_config = Speak_Config(os.path.join(self.config_folder, "speak_config.json"))

        sn_folder = os.path.dirname(os.path.dirname(self.config_folder))
        self.sn_loader = File_Saver_Loader_SN(os.path.join(sn_folder+'/guard_tvt-BJCOMP2025', "sn"))
        self.sn=self.sn_loader.load_from_file().strip()
        print(f"load_from_file sn,filePath={self.sn_loader.file_path},sn={self.sn} ")
        self.set_radar_defence_area_callback = None
        self.radar_obj_area_saver = File_Saver_Loader_json(os.path.join(self.config_folder, "radar_defence_area.json"))

    def get_make_pic_folder(self):
        if os.path.exists("/ssd"):
            pic_folder = "/ssd/alarmpic/alarmFrame"
        else:
            pic_folder = "/usr/bin/zipx/zj-guard/alarmFrame"
        if not os.path.exists(pic_folder):
            os.makedirs(pic_folder)
        return pic_folder

    def load_source_list(self):
        if not path.exists(self.source_list_path):
            return

        with open(self.source_list_path, "r") as f:
            self.source_list = json.load(f)
            print("-----rtsp load_from_file-----")
            for source in self.source_list:
                print(source)
            print("------------------------")

    def save_source_list(self):
        with open(self.source_list_path, "w") as f:
            json.dump(self.source_list, f)

    def get_radar_config(self, index) -> RadarConfig:
        return self.radar_config_dict[index]

    def get_camera_in_config(self, index) -> CameraConfig:
        return self.camera_in_dict[index]

    def get_camera_ex_config(self, index) -> AreaConfig:
        return self.camera_ex_dict[index]

    def get_guard_area(self, index) -> AreaConfig:
        return self.guard_area_dict[index]

    def update_server_info(self, server_ip: str, server_port: int):
        print(f"new server: {server_ip}:{server_port}")

    def handle_config_msg(self, signal_code, json_obj):
        """
        {'code': 100, 'msg': 'success', 'data':
            {'0': [[192, 712, 0.0, 0.0, 0.0], [357, 116, 0.0, 0.0, 0.0], [632, 109, 0.0, 0.0, 0.0], [1015, 716, 0.0, 0.0, 0.0]],
             '1': [[292, 711, 0.0, 0.0, 0.0], [307, 175, 0.0, 0.0, 0.0], [749, 174, 0.0, 0.0, 0.0], [1264, 715, 0.0, 0.0, 0.0]]
             }
         }
        """

        if 'data' not in json_obj:
            print("客户端请求数据", json_obj['code'])
            return False

        json_data = json_obj['data']

        if json_data is None:
            print("请求data为None，获取数据", json_obj['code'])
            return False

        if signal_code == ConfigManager.signal_camera_ex:
            for key in self.camera_ex_dict.keys():
                # 保存最新配置信息到内存
                json_list = json_data[str(key)]
                self.camera_ex_dict[key].load_from_json(json_list)
                # 保存最新配置到文件
                self.camera_ex_dict[key].save()

        elif signal_code == ConfigManager.signal_camera_in:
            for key in self.camera_in_dict.keys():
                # 保存最新配置到文件
                self.camera_in_dict[key].save(json_data[str(key)])
                # 保存最新配置信息到内存
                # self.camera_in_dict[key].load_config()

        elif signal_code == ConfigManager.signal_camera_radar:
            for key in self.radar_config_dict.keys():
                # 保存最新配置到文件
                self.radar_config_dict[key].save_config(json_data[str(key)])

        elif signal_code == ConfigManager.signal_rail_radar:
            pass
            for key in self.rail_radar_dict.keys():
                # 保存最新配置到文件
                self.rail_radar_dict[key].save(json_data[str(key)])

        elif signal_code == ConfigManager.signal_source_list:
            # 保存到内存
            self.source_list = json_data
            # 保存到文件
            self.save_source_list()

        # 发信号给订阅者
        ConfigManager.config_update_signal.send(signal_code)

        return True

    def update_defence_area_list(self, json_load):
        # 加载防区
        # json_load = self.radar_obj_area_saver.load_from_file()
        if "area_point" in json_load:
            # 如果是202309以前的顶点列表格式
            # [[[3.346510731996906, 30.7714540514303], [4.632277640767955, 32.02100660197035],[4.840441775504251, 12.882338381449475], [4.063004336968363, 0], [3.0696532851801375, 0]],
            #  [[-2.8757163321996284, 0], [-1.919746167732102, 49.008879105782015], [3.230273626667291, 47.85676775561873],[2.8850532601240477, 0]],
            #  [[-2.3631315517521334, 0], [-0.8840850008102308, 101.0964076641026], [5.338795073696986, 98.18049041346012],[4.465843154076969, 68.84592159518336], [4.1915511645340695, 0]]]
            self.defence_area_list = [{"type": 1, "verteces": polygen} for polygen in json_load['area_point']]
            self.radar_obj_area_saver.save_to_file(self.defence_area_list)
        else:
            self.defence_area_list = json_load
            self.radar_obj_area_saver.save_to_file(self.defence_area_list)



# def save_areaconfig_list(areaconfig_list,filePath='new_json.json',):
#     areaconfig_list_str=json.dumps(areaconfig_list)
#     f2 = open(filePath, 'w')
#     f2.write(areaconfig_list_str)
#     f2.close()




def reset_vanishingPoint():

    pass


if __name__=="__main__":
    # test=AreaConfig(os.path.join(r"D:\project\tvtEye\guard\config", "shibian_t1_17_guard.json"))
    # print(test)
    # test.save()

    if 1:
        reset_vanishingPoint()
    elif 1:
        main_config=MainEngine_Config()
        main_config.save_to_config_file()













