import datetime
import os
import time

from common_FileLoadSave import File_Saver_Loader_json


class FalseAlarmCounter_minute:
    def __init__(self, name, reset_period_minute=60 * 30, threshold=600, callback=None):
        self.name = name
        self.reset_period_minute = reset_period_minute
        self.count = {}
        self.update_timeStamp = time.time()
        self.callback_of_overcount_threshold = threshold  # 计数门限值
        self.callback_of_overcount = callback  # 计数超过门限值的回调
        self.camera_key = Camera_Key()

    def count_add(self, key_xywh):
        # 根据距离更新计数器
        if isinstance(key_xywh, list):  # 相机数据
            index_x, index_y, index_wh = key_xywh
            if index_x not in self.count:
                self.count[index_x] = {}
            if index_y not in self.count[index_x]:
                self.count[index_x][index_y] = {}
            if index_wh not in self.count[index_x][index_y]:
                self.count[index_x][index_y][index_wh] = 0
            self.count[index_x][index_y][index_wh] += 1.0
        else:
            key = str(key_xywh)
            if key not in self.count:
                self.count[key] = 0.0
            self.count[key] += 1.0

    def update_count(self, key=None):
        """
        根据key值更新count_dict，
        根据当前时间和update_timeStamp的时间间隔决定是否重置count_dict
        """
        if key is not None:
            self.count_add(key)
            # print(f"{datetime.datetime.now()},update_count {self.count}")

        if time.time() - self.update_timeStamp >= self.reset_period_minute * 60:
            if self.reset_period_minute >= 10:  # 只有10分钟以上的计时器打印
                print(f"{datetime.datetime.now()},update_count count={self.count}")
            # 如果计数达到阈值，则调用callback函数,使上级计数器+1
            if isinstance(key, list):
                for index_x in self.count:
                    for index_y in self.count[index_x]:
                        for index_wh in self.count[index_x][index_y]:
                            if self.count[index_x][index_y][index_wh]> self.callback_of_overcount_threshold \
                                    and self.callback_of_overcount is not None:
                                self.callback_of_overcount([index_x, index_y, index_wh])
            else:
                for key_ in self.count:
                    if self.count[key_] >= self.callback_of_overcount_threshold and self.callback_of_overcount is not None:
                        self.callback_of_overcount(key_)
            # 重置count
            self.update_timeStamp = time.time()
            self.count = {}


class RadarFalseAlarmFilter:
    def __init__(self, config_folder=os.path.join("..", "config"), file_name="false_alarm_count.json"):
        self.isFilterRadarObj = False
        self.top_count_dict = {}
        self.count_360_minute = FalseAlarmCounter_minute("count_360_minute", 120, 30, self.top_count_dict_add)  # 120分钟内有30分钟有目标出现
        self.count_2_minute = FalseAlarmCounter_minute("count_2_minute", 2, 2, self.count_360_minute.update_count)  # 每2分钟内达到2次报警
        self.decrese_count_period_s = 3600 * 24 * 0.25  # 0.25天自减一次
        self.decrese_coefficent = 0.85  # 每次自减乘以0.85
        self.inFalseAlarm_threshold = 1.0  #
        self.count_min_to_display = 0.2 * self.inFalseAlarm_threshold  # 只显示超过一定数量的falseAlarm
        self.decrease_count_timestamp = time.time() - self.decrese_count_period_s
        # load_from_file false_alarm_file
        self.filepath_false_alarm_count = os.path.join(config_folder, file_name)
        self.file_saver_loader = File_Saver_Loader_json(self.filepath_false_alarm_count)
        if not os.path.exists(self.filepath_false_alarm_count):  # 文件不存在，则新建文件
            self.file_saver_loader.save_to_file(self.top_count_dict)
        self.top_count_dict = self.file_saver_loader.load_from_file()
        print(f"{datetime.datetime.now()},RadarFalseAlarmFilter, load false_alarm_list={self.top_count_dict}")

        self.falseAlarm_status_string = ""
        self.update_falseAlarm_status_string()

    def top_count_dict_add(self, key):
        # 根据距离更新计数器
        key = str(key)
        if key not in self.top_count_dict:
            self.top_count_dict[key] = 0.0
        self.top_count_dict[key] += 1.0
        self.update_falseAlarm_status_string()

    def get_coefficient_of_falseAlarm(self, key):
        # 根据是否在false_alarm_list，返回不同的权重系数
        key_int = str(int(key))
        if key_int in self.top_count_dict and self.top_count_dict[key_int] > self.inFalseAlarm_threshold:
            return 0.5
        else:
            return 1.0

    def update_falseAlarmList(self, radar_obj_frame=None):
        # 根据雷达目标更新false_alarm_list
        # radar_obj_frame=\
        #     {'stamp': 1637304901.2296166,
        #      'list': [{'id': 0,
        #                'data': [    {'in_area': 1,
        #                              'dto': [1, 3.116259813308716, 71.10643005371094, 0.0032951277680695057, 0.0],
        #                              }
        #                         ]},
        #               {'id': 1,
        #                'data': [ {'in_area': 1,
        #                           'dto': [1, -3.8796603679656982, 147.57652282714844, -0.003955674823373556, 0.0],
        #                           }]
        #                }]
        #      }

        # {'stamp': 1637304901.2296166,
        #  'list': []
        #  "status":"ok","error1","error2",
        #   }
        if radar_obj_frame is not None:
            for index, radarobjs_in_frame in enumerate(radar_obj_frame["list"]):
                for a_radar_obj_dict_in_frame in radarobjs_in_frame["data"]:
                    # 雷达X位置不能太靠边(避免隔壁轨道）
                    if self.isInFalseAlarmList(a_radar_obj_dict_in_frame) and self.isFilterRadarObj == True:
                        radar_obj_frame['list'][index]["data"] = []
        self.decrease_count_dict_by_time()

    def update_falseAlarm_status_string(self):
        # 更新用于对外显示false_alarm状态的字符串，
        falseAlarm_status_list = []
        for key in self.top_count_dict:
            if self.top_count_dict[key] >= self.count_min_to_display:  # 只显示超过一定数量的falseAlarm
                falseAlarm_status_list.append(f"{key}:{self.top_count_dict[key]:.2f}")
        self.falseAlarm_status_string = ", ".join(falseAlarm_status_list) + f" ,/{self.inFalseAlarm_threshold}"

    def decrease_count_dict_by_time(self):
        # 周期性减少各距离报警计数器
        if time.time() - self.decrease_count_timestamp >= self.decrese_count_period_s:
            delete_keys = []
            for key in self.top_count_dict:
                self.top_count_dict[key] = self.top_count_dict[key] * self.decrese_coefficent
                if self.top_count_dict[key] <= 0.5:
                    delete_keys.append(key)
            for key in delete_keys:
                self.top_count_dict.pop(key)  # 删除过小的值 20220812
            self.decrease_count_timestamp = time.time()
            print(f"{datetime.datetime.now()},decrease_count_dict save {self.file_saver_loader.file_path},false_alarm_list=", self.top_count_dict)
            self.file_saver_loader.save_to_file(self.top_count_dict)

    def isInFalseAlarmList(self, a_radar_obj_dict_in_frame):
        # 根据Y值判断是否在虚警列表中
        """
        [   {'in_area': 1,
            'dto': [1, -2.1313729286193848, 45.44459915161133, 0.0035258529242128134, 0.0],
             }
        ]
        """
        isInFalseAlarm = False
        if len(a_radar_obj_dict_in_frame) > 0 and len(a_radar_obj_dict_in_frame['dto']) > 3:
            # 获得xy坐标
            obj_x, obj_y = a_radar_obj_dict_in_frame['dto'][1:3]
            # 根据目标距离更新count_dict
            obj_y_int = int(obj_y)
            # 根据计数判断是否在FalseAlarmList
            if obj_y_int in self.top_count_dict and self.top_count_dict[obj_y_int] >= self.inFalseAlarm_threshold:
                isInFalseAlarm = True
            # 更新count
            self.count_2_minute.update_count(obj_y_int)

        return isInFalseAlarm


class Camera_Key:
    def __init__(self):
        # self.camera_grid_step = [40, 30, 10]
        self.camera_grid_step = [80, 45, 20]    # 10*10格子

    def get_index(self, key):
        index_x = key[0] // self.camera_grid_step[0]
        index_y = key[1] // self.camera_grid_step[1]
        index_wh = key[2] // self.camera_grid_step[2]
        return str(index_x), str(index_y), str(index_wh)


class CameraFalseAlarmFilter:

    def __init__(self, config_folder=os.path.join("..", "config")):
        self.isFilteObj = False
        self.top_count_dict = {}
        self.count_360_minute = FalseAlarmCounter_minute("count_360_minute", 60, 20, self.top_count_dict_add)  # 60分钟内有30分钟有目标出现
        self.count_2_minute = FalseAlarmCounter_minute("count_2_minute", 1, 3, self.count_360_minute.update_count)  # 每分钟内达到3次报警
        self.decrease_count_period_s = 3600 * 24 * 0.25  # 0.25天自减一次
        self.decrease_coefficent = 0.85  # 每次自减乘以0.7
        self.inFalseAlarm_threshold = 1.0  #
        self.count_min_to_display = 0.5 * self.inFalseAlarm_threshold  # 只显示超过一定数量的falseAlarm
        self.decrease_count_timestamp = time.time() - self.decrease_count_period_s
        self.filepath_false_alarm_count = os.path.join(config_folder, "camera_false_alarm_list.json")
        self.file_saver_loader = File_Saver_Loader_json(self.filepath_false_alarm_count)
        # 文件不存在，则新建文件
        if not os.path.exists(self.filepath_false_alarm_count):
            self.file_saver_loader.save_to_file(self.top_count_dict)
        self.top_count_dict = self.file_saver_loader.load_from_file()
        # 20221208 文件为空错误处理：为空则保存一次
        if self.top_count_dict is None:
            self.top_count_dict={}
            self.file_saver_loader.save_to_file(self.top_count_dict)

        print(f"{datetime.datetime.now()},CameraFalseAlarmFilter, load camera_false_alarm_list={self.top_count_dict}")

        self.falseAlarm_status_string = ""
        self.update_falseAlarm_status_string()

    def get_coefficient_of_falseAlarm(self, key):
        # 根据是否在false_alarm_list，返回不同的权重系数
        key_int = str(int(key))
        if key_int in self.top_count_dict and self.top_count_dict[key_int] > self.inFalseAlarm_threshold:
            return 0.5
        else:
            return 1.0

    # def update_falseAlarmList(self, camera_obj_frame=None):
        # 根据雷达目标更新false_alarm_list
        # {
        #     "camerastatus": [{"nearcameraocclude": 0, "farcameraocclude": 0, "deflection": 0, "nighttrainlight": 0}],
        #     "list": [
        #         {
        #             "id": 0,
        #             "timestamp": 1660298132776,
        #             "data": [
        #                 {"confidence": 0.496109813, "class": 0, "bbox": [268, 231, 52, 18], "in_area": 2, "xyz": [3.1049219131469727, 0, 19.20555419921875]},
        #                 {"confidence": 0.267849267, "class": 0, "bbox": [215, 238, 45, 20], "in_area": 2, "xyz": [1.3487207412719726, 0, 18.17421875]}
        #             ]
        #          }
        #              ],
        #  "stamp": 1660298132.7826412
        #  }
        # if camera_obj_frame is not None:
        #     for index_camera, objs_in_frame in enumerate(camera_obj_frame["list"]):
        #         index_list_for_delete=[]
        #         for index_obj, a_obj_dict_in_frame in enumerate(objs_in_frame["data"]):
        #             if self.isInFalseAlarmList_by_bbox(a_obj_dict_in_frame["bbox"]):
        #                 if self.isFilteObj:
        #                     index_list_for_delete.append(index_obj)
        #         # 对列表删除多个元素，需要反向pop，否则错误。
        #         for index_for_delete in index_list_for_delete[::-1]:
        #             camera_obj_frame['list'][index_camera]["data"].pop(index_for_delete)
        # pass

    def update_falseAlarm_status_string(self):
        # 更新用于对外显示false_alarm状态的字符串，
        falseAlarm_status_list = []
        for index_x in self.top_count_dict:
            for index_y in self.top_count_dict[index_x]:
                for index_wh in self.top_count_dict[index_x][index_y]:
                    if self.top_count_dict[index_x][index_y][index_wh] >= self.count_min_to_display:  # 只显示超过一定数量的falseAlarm
                        falseAlarm_status_list.append(f"{index_x}_{index_y}_{index_wh}:{self.top_count_dict[index_x][index_y][index_wh]}")
        self.falseAlarm_status_string = ", ".join(falseAlarm_status_list) + f" ,/{self.inFalseAlarm_threshold}"

    def top_count_dict_decrease_operation(self):
        # top_count减少和删除键值操作
        delete_keys = []
        for index_x in self.top_count_dict:
            for index_y in self.top_count_dict[index_x]:
                for index_wh in self.top_count_dict[index_x][index_y]:
                    self.top_count_dict[index_x][index_y][index_wh]*=self.decrease_coefficent
                    if self.top_count_dict[index_x][index_y][index_wh] <= 0.5:
                        delete_keys.append([index_x, index_y, index_wh])
        for index_list in delete_keys:
            index_x, index_y, index_wh=index_list
            self.top_count_dict[index_x][index_y].pop(index_wh)  # 删除过小的值 20220812
            if index_y in self.top_count_dict[index_x] and len(self.top_count_dict[index_x][index_y])==0:
                self.top_count_dict[index_x].pop(index_y)
            if index_x in self.top_count_dict and len(self.top_count_dict[index_x])==0:
                self.top_count_dict.pop(index_x)

    def top_count_dict_add(self, key_xywh):
        # 根据距离更新计数器
        # 相机数据
        # index_x, index_y, index_wh = self.count_2_minute.camera_key.get_index(key_xywh)
        index_x, index_y, index_wh = key_xywh
        if index_x not in self.top_count_dict:
            self.top_count_dict[index_x] = {}
        if index_y not in self.top_count_dict[index_x]:
            self.top_count_dict[index_x][index_y] = {}
        if index_wh not in self.top_count_dict[index_x][index_y]:
            self.top_count_dict[index_x][index_y][index_wh] = 0
        self.top_count_dict[index_x][index_y][index_wh] += 1.0
        print(f"{datetime.datetime.now()},CameraFalseAlarmFilter top_count_dict_add,{self.top_count_dict}")
        self.update_falseAlarm_status_string()
        self.file_saver_loader.save_to_file(self.top_count_dict)

    def top_count_dict_decrease(self,):
        # 周期性减少各距离报警计数器
        if time.time() - self.decrease_count_timestamp >= self.decrease_count_period_s:
            self.top_count_dict_decrease_operation()
            self.decrease_count_timestamp = time.time()
            print(f"{datetime.datetime.now()},CameraFalseAlarmFilter top_count_dict_decrease {self.top_count_dict}")
            self.file_saver_loader.save_to_file(self.top_count_dict)

    def isInFalseAlarmList_by_bbox(self, bbox, update_count=True):
        # 根据Y值判断是否在虚警列表中
        """
        {
            "camerastatus": [{"nearcameraocclude": 0, "farcameraocclude": 0, "deflection": 0, "nighttrainlight": 0}],
            "list": [
                {
                    "id": 0,
                    "timestamp": 1660298132776,
                    "data": [
                        {"confidence": 0.496109813, "class": 0, "bbox": [268, 231, 52, 18], "in_area": 2, "xyz": [3.1049219131469727, 0, 19.20555419921875]},
                        {"confidence": 0.267849267, "class": 0, "bbox": [215, 238, 45, 20], "in_area": 2, "xyz": [1.3487207412719726, 0, 18.17421875]}
                    ]
                 }
                     ],
         "stamp": 1660298132.7826412
         }
        """
        isInFalseAlarm = False
        index_x, index_y, index_wh = self.count_2_minute.camera_key.get_index([bbox[0], bbox[1], bbox[2] + bbox[3]])
        # print(f"isInFalseAlarmList ={[index_x, index_y, index_wh]},{self.top_count_dict.keys()}")
        if index_x in self.top_count_dict:
            if index_y in self.top_count_dict[index_x]:
                if index_wh in self.top_count_dict[index_x][index_y]:
                    # 根据计数判断是否在FalseAlarmList
                    if self.top_count_dict[index_x][index_y][index_wh] >= self.inFalseAlarm_threshold:
                        isInFalseAlarm = True
        # 更新count
        if update_count:
            self.count_2_minute.update_count([index_x, index_y, index_wh])

        self.top_count_dict_decrease()

        return isInFalseAlarm


def test_radar_false_alarm_list():
    my_RadarFalseAlarmFilter = RadarFalseAlarmFilter()
    my_sorted = sorted(my_RadarFalseAlarmFilter.top_count_dict.items(), key=lambda item: int(item[0]))
    print(my_sorted)
    my_RadarFalseAlarmFilter.decrease_count_dict_by_time()


def test_camera_false_alarm_list():
    # config_folder = os.path.join("..", "config")
    my_cameraFalseAlarmFilter = CameraFalseAlarmFilter()
    frame={
            "camerastatus": [{"nearcameraocclude": 0, "farcameraocclude": 0, "deflection": 0, "nighttrainlight": 0}],
            "list": [
                {
                    "id": 0,
                    "timestamp": 1660298132776,
                    "data": [
                        {"confidence": 0.496109813, "class": 0, "bbox": [268, 231, 52, 18], "in_area": 2, "xyz": [3.1049219131469727, 0, 19.20555419921875]},
                        {"confidence": 0.267849267, "class": 0, "bbox": [215, 238, 45, 20], "in_area": 2, "xyz": [1.3487207412719726, 0, 18.17421875]}
                    ]
                 }
            ],
        "stamp": 1660298132.7826412
         }
    for index in range(1200):
        my_cameraFalseAlarmFilter.update_falseAlarmList(frame)
        time.sleep(1)

    my_cameraFalseAlarmFilter.file_saver_loader.save_to_file(my_cameraFalseAlarmFilter.top_count_dict)




if __name__ == "__main__":
    # test_radar_false_alarm_list()
    # test_camera_false_alarm_list()
    pass

