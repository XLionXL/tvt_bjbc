"""
开启TCP服务器

连接成功时，返回客户端配置文件信息
"""

from buffer_queue import BufferQueue
from comm_tcp_server import *
from config_manager import *

REQ_CAMERA_ROI = 100  # 相机ROI
REQ_CAMERA_IN_PARAMS = 101  # 相机内参
REQ_CAMERA_EX_PARAMS = 102  # 相机外参
REQ_CAMERA_RADAR_CONFIG = 103  # 雷达相机
REQ_RAIL_RADAR_CONFIG = 104  # 雷达铁路
REQ_CAMERA_CALIBRATION_CONFIG = 105  # 相机标定结果
REQ_CAMERA_SETUP_CALIBRATION = 106  # 相机安装标定结果
REQ_AUDIO_TALK = 107  # 远程喊话
REQ_CAMERA_SETUP_VANISH_POINT_CAMERA_HEIGHT = 108  # 相机参考点设置
REQ_CAMERA_DISTANCE_TEST = 109  # 相机距离测试
REQ_CAMERA_BLOCK_LIST = 110  # 相机 blocklist
REQ_MAIN_CONFIG = 111  # main_config
REQ_RADAR_AREA = 112  # radar_area
REQ_AUTO_CALIBRATION = 113  # auto_calibration

REQ_CAMERA_SOURCE_LIST = 120 # 相机地址列表
REQ_CAMERA_SOURCE_OUT_LIST = 121 # 相机对外流地址列表

RESP_CAMERA_DATA = 200  # 相机包容盒
RESP_RADAR_DATA = 201  # 雷达信息
RESP_ALARM_EVENT = 202  # 报警事件信息
RESP_MERGE_DATA = 301  # 融合后目标信息
RESP_URL_DATA = 401  # 图片和视频下载链接
CONFIG_DATA = 303  # 配置设定
REMOTE_CALL_ACOUSTO_OPTIC = 305  # 远程喊话声光报警器电源控制

RESP_COMMON_SUCCESS = 1
RESP_COMMON_FAILURE = 0
NATIVE_ERROR = 500
MCU_DATA = 202  # MCU消息
# from xypConfig import xypConfig

class MainTcpServer(TcpServer):

    def __init__(self, port, config_manager: ConfigManager):
        super(MainTcpServer, self).__init__(port)
        self.config_manager = config_manager
        self.queue = BufferQueue(1)
        self.handle_main_config_callback=None
        self.handle_radar_area_callback=None
        self.handle_auto_calibration_callback=None
        self.handle_audio_talk_callback=None
        self.set_config_callback=None
        self.handle_remote_call_acousto_optic_power_callback=None

    def on_client_connect(self, client_socket, client_key):
        # 先给客户端回复当前的配置信息
        self._send(self.gen_roi_response(), client_socket, client_key)
        self._send(self.gen_camera_in_response(), client_socket, client_key)
        self._send(self.gen_camera_ex_response(), client_socket, client_key)
        # self._send(self.gen_camera_radar_response(), client_socket, client_key)
        self._send(self.gen_rail_radar_response(), client_socket, client_key)
        self._send(self.gen_camera_source_response(), client_socket, client_key)
        self._send(self.gen_camera_source_out_response(), client_socket, client_key)
        self._send(self.gen_camera_calibration_out_response(), client_socket, client_key)
        self._send(self.gen_camera_block_list_response(), client_socket, client_key)
        self._send(self.gen_main_config_response(), client_socket, client_key)
        self._send(self.gen_radar_area_response(), client_socket, client_key)

    def handle_set_config(self,json_obj):
        pass

    def on_client_request(self, json_obj):
        """
        处理请求， 返回响应结果对象
        :param json_obj:
        :return:
        """
        code = json_obj["code"]

        if code == REQ_CAMERA_ROI:  # 100xyp相机
            if "data" in json_obj: # 无data是请求
                self.imageAreaHandle.areaSet(json_obj)
                if self.imageAreaHandle.imageAreaSetRadarArea(self.radarAreaHandle):# 是否设置成功
                    self.gen_radar_area_response()
                else:
                    self.gen_radar_area_response("radar_area")
            return self.gen_roi_response()
        elif code == REQ_CAMERA_IN_PARAMS:  # 101
            self.config_manager.handle_config_msg(ConfigManager.signal_camera_in, json_obj)
            return self.gen_camera_in_response()
        elif code == REQ_CAMERA_EX_PARAMS:  # 102
            self.config_manager.handle_config_msg(ConfigManager.signal_camera_ex, json_obj)
            return self.gen_camera_ex_response()
        elif code == REQ_CAMERA_RADAR_CONFIG:  # 103
            self.config_manager.handle_config_msg(ConfigManager.signal_camera_radar, json_obj)
            return self.gen_camera_radar_response()
        elif code == REQ_RAIL_RADAR_CONFIG:  # 104
            self.config_manager.handle_config_msg(ConfigManager.signal_rail_radar, json_obj)
            return self.gen_rail_radar_response()
        elif code == REQ_CAMERA_CALIBRATION_CONFIG or code== REQ_CAMERA_SETUP_CALIBRATION or code == REQ_CAMERA_SETUP_VANISH_POINT_CAMERA_HEIGHT:  # 105 106  108
            # xypConfig.cameraVanishConfig.setData(json_obj)
            self.vanishHandle.calibInfoSet(json_obj)
            self.imageAreaHandle.areaSet()
            self.imageAreaHandle.imageAreaSetRadarArea(self.radarAreaHandle)
            return self.gen_camera_calibration_out_response()
        elif code == REQ_CAMERA_DISTANCE_TEST:  # 109 xyp 点击web参考点设置界面，返回估计坐标
            return self.gen_distance_test_response(json_obj)
        elif code == REQ_CAMERA_BLOCK_LIST:  # 110  # xyp相机屏蔽区
            print(f"REQ_CAMERA_BLOCK_LIST={json_obj}")
            if "data" in json_obj:
                self.imageAreaHandle.areaSet(json_obj)
            return self.gen_camera_block_list_response()
        elif code == REQ_MAIN_CONFIG:  # 111  # main_config
            print(f"REQ_MAIN_CONFIG={json_obj}")
            if self.handle_main_config_callback is not None and "data" in json_obj:
                self.handle_main_config_callback(json_obj)
            return self.gen_main_config_response()
        elif code == REQ_RADAR_AREA:  # 112  #xyp雷达区域设置 radar_area
            if "data" in json_obj:
                if self.radarAreaHandle.areaSet(json_obj):
                    return self.gen_radar_area_response()
                else:
                    return self.gen_radar_area_response("radar_area")
            else:
                return self.gen_radar_area_response()
        elif code == REQ_AUTO_CALIBRATION:  # 113  # auto_calibration
            print(f"REQ_AUTO_CALIBRATION={json_obj}")
            if self.handle_auto_calibration_callback is not None and "data" in json_obj:
                self.handle_auto_calibration_callback(json_obj)
            return self.gen_auto_calibration_response()
        elif code == REQ_AUDIO_TALK:  # 107
            if self.handle_audio_talk_callback is not None:
                self.handle_audio_talk_callback(json_obj)
            print(f"REQ_AUDIO_TALK={json_obj}")
            return self.gen_audio_talk_response()
        elif code == REQ_CAMERA_SOURCE_LIST:  # 120
            self.config_manager.handle_config_msg(ConfigManager.signal_source_list, json_obj)
            a = self.gen_camera_source_response()
            return a
        elif code == REQ_CAMERA_SOURCE_OUT_LIST: # 121
            # self.config_manager.handle_config_msg(ConfigManager.signal_source_list, json_obj)
            return self.gen_camera_source_out_response()
        elif code == CONFIG_DATA: #303 参数配置
            if self.set_config_callback is not None :
                respon=self.set_config_callback(json_obj)
            else:
                respon={}
            print(f"{datetime.datetime.now()},CONFIG_DATA respon={respon}")
            return self.send_setting_data(respon)
        elif code == REMOTE_CALL_ACOUSTO_OPTIC: # 305 远程喊话声光报警器电源控制
            if self.handle_remote_call_acousto_optic_power_callback is not None:
                self.handle_remote_call_acousto_optic_power_callback(json_obj)
            return self.send_setting_data(None)
        else:
            return self.gen_default_response(code)

    # def gen_native_response(self):
    #     return self.response(NATIVE_ERROR,"success",{"ds-native":"算力故障.."})
    
    def gen_roi_response(self): # xyp发送给web
        return self.response(REQ_CAMERA_ROI, "success", self.imageAreaHandle.areaSendToWeb())

    def gen_camera_in_response(self):
        return self.response(REQ_CAMERA_IN_PARAMS, "success", self.config_manager.camera_in_dict)

    def gen_camera_ex_response(self):
        return self.response(REQ_CAMERA_EX_PARAMS, "success", self.config_manager.camera_ex_dict)

    def gen_camera_radar_response(self):
        return self.response(REQ_CAMERA_RADAR_CONFIG, "success", self.config_manager.radar_config_dict)

    def gen_rail_radar_response(self):
        return self.response(REQ_RAIL_RADAR_CONFIG, "success", self.config_manager.rail_radar_dict)

    def gen_camera_source_response(self):
        return self.response(REQ_CAMERA_SOURCE_LIST, "success", self.config_manager.source_list)

    def gen_camera_source_out_response(self):
        return self.response(REQ_CAMERA_SOURCE_OUT_LIST, "success", self.config_manager.camera_url_out)

    def gen_camera_calibration_out_response(self):
        return self.response(REQ_CAMERA_SETUP_CALIBRATION, "success", self.vanishHandle.calibInfoSendToWeb())

    def gen_camera_block_list_response(self): # 发送屏蔽区域
        return self.response(REQ_CAMERA_BLOCK_LIST, "success", self.imageAreaHandle.areaSendToWeb(True))

    def gen_main_config_response(self):
        return self.response(REQ_MAIN_CONFIG, "success", self.config_manager.main_config.data_dict)

    def gen_radar_area_response(self,msg = "success"):
        # block_list转换成
        # return self.response(REQ_RADAR_AREA, "radar_area", self.config_manager.defence_area_list)
        return self.response(REQ_RADAR_AREA, msg, self.radarAreaHandle.areaSendToWeb())

    def gen_auto_calibration_response(self):
        # auto_calibration的结果
        return self.response(REQ_AUTO_CALIBRATION, "auto_calibration", self.config_manager.auto_calibration_result)

    def gen_distance_test_response(self, json_obj):
        # 距离测试结果
        # rx:json_obj={"code": 109, "data": {"index": 0, "testPoint": [462, 310]}}
        # tx: {"code": 109, "data": {"index": 0, "testPoint": [462, 310], "XY": [2.25, 125.11]}}
        try:
            camId, testPoint = int(json_obj["data"]["index"]), json_obj["data"]["testPoint"]
            estimatePos = self.vanishHandle.estimateImageToRadar(testPoint, camId)
            response_dict = json_obj["data"]
            response_dict["XY"] = [round(estimatePos[0], 2), round(estimatePos[1], 2)]
            print(f"gen_distance_test_response response={response_dict}")
            return self.response(REQ_CAMERA_DISTANCE_TEST, "success", response_dict)
        except Exception as e:
            print(f"gen_distance_test_response error={str(e)},json_obj={json_obj}")

    def gen_audio_talk_response(self):
        # 校准结果camera_diameter_dict转换成
        if "Windows" in platform.platform() or False:
            from Audio_Receiver import CONFIGS_DICT
            return self.response(REQ_AUDIO_TALK, "success", CONFIGS_DICT)
        return None

    def send_setting_data(self, status):
        self._send(self.response(CONFIG_DATA,"success",status))

    def send_camera_data(self, target_bbox):
        """
        发送相机数据，如果这个函数被多个地方调用，要考虑使用消息队列的形式
        :param target_bbox:
        :return:
        """
        self._send(self.response(RESP_CAMERA_DATA, "camera_data", target_bbox))

    def send_merge_data(self, target_bbox: dict):
        """
         发送merge数据，如果这个函数被多个地方调用，要考虑使用消息队列的形式
         :param target_bbox:
         :return:
         """
        # target_bbox_exampleData = {
        #     "alarmojbs": [
        #         {"cameraid": 1, "score": 36.48844139999998, "alarmtype": 1, "bbox": [141, 2, 292, 441], "in_area": 2}
        #     ],
        #     "stamp": 1649839539.1522176,
        #     "report_cnt": "33/56"
        # }
        # data_out={
        #     "alarmojbs": [
        #         {"id": 0, "bboxs": [{"cameraid": 0,"score": 0.864645779,"alarmtype": 0,	"bbox": [176, 172, 26, 65],"in_area": 0}, ]},
        #         {"id": 1, "bboxs": [{ "cameraid": 1, "score": 0.328182846, "alarmtype": 0, "bbox": [506, 121, 7, 13], "in_area":0}]}
        #     ],
        #     "stamp": 1638512361.7311606
        # }
        self._send(self.response(RESP_MERGE_DATA, "merge_data", target_bbox))

    def send_url_data(self, url_dict: dict):
        """
         发送merge数据，如果这个函数被多个地方调用，要考虑使用消息队列的形式
         :param target_bbox:
         :return:
         """
        # target_bbox_exampleData = {
        #     "alarmojbs": [
        #         {"cameraid": 1, "score": 36.48844139999998, "alarmtype": 1, "bbox": [141, 2, 292, 441], "in_area": 2}
        #     ],
        #     "stamp": 1649839539.1522176,
        #     "report_cnt": "33/56"
        # }
        # data_out={
        #     "alarmojbs": [
        #         {"id": 0, "bboxs": [{"cameraid": 0,"score": 0.864645779,"alarmtype": 0,	"bbox": [176, 172, 26, 65],"in_area": 0}, ]},
        #         {"id": 1, "bboxs": [{ "cameraid": 1, "score": 0.328182846, "alarmtype": 0, "bbox": [506, 121, 7, 13], "in_area":0}]}
        #     ],
        #     "stamp": 1638512361.7311606
        # }
        self._send(self.response(RESP_URL_DATA, "url_data", url_dict))

    def send_radar_data(self, json_obj):

        self._send(self.response(RESP_RADAR_DATA, "radar_data", json_obj)) # 201 radar_data json_obj self.response就是将这些作为json

    def send_alarm_event(self, json_obj):
        self._send(self.response(RESP_ALARM_EVENT, "alarm_event", json_obj))
    
    # def send_native_error(self):
    #     self._send(self.response(NATIVE_ERROR, "ds-native", {"name":"算力故障..."}))
    def send_heartbeat_data(self, json_boj):
        self._send(json_boj)


def gen_block_list_request():
    pass


if __name__ == '__main__':
    config_folder = os.path.abspath(os.path.join("", "config"))
    main_config = MainEngine_Config(os.path.join(config_folder, "main_config.json"))
    config = ConfigManager(config_folder=config_folder,main_config=main_config)
    server = MainTcpServer(8888, config)
    json_str = json.dumps({"code": REQ_CAMERA_BLOCK_LIST, "msg": "request"}, ensure_ascii=False, cls=JsonObjEncoder)
    json_bytes = f"{json_str}\n".encode()
    send_data_str = f'{len(json_bytes)}\n'.encode() + json_bytes
    print(f"send_data_str={send_data_str}")
    server.run_forever(is_block=False)
    time.sleep(300)
