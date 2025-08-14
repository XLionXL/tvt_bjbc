import datetime
import json
import math
import re
import time
import traceback


class AutoFov:
    def __init__(self):
        self.calibration_result_list_c01=[]
        self.calibration_result_dict01={}

    def autoFov_fromLog(self, file_path_list, ):
        result_radar_camera=[]
        time_start = time.time()
        pattern_input_ = r'input_'
        result_radar = []
        result_camera = []
        cnt_consecutive = 0
        cnt_no_consecutive = 0
        cnt_radar_frame = 0
        cnt_camera_frame = 0
        try:
            self.calibration_result_list_c01=[]
            for file_path in file_path_list:
                print(f"autoFov_fromLog file_path={file_path}")
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        if re.search(pattern_input_, line):
                            cnt_consecutive += 1
                            if "input_radar" in line:
                                match = re.search(r"input_radar\s*(.*)", line.strip())
                                if match:
                                    cnt_camera_frame = 0
                                    cnt_radar_frame += 1
                                    matched_content = match.group(1)
                                    radar_frame_timestamp_objs = get_radar_obj_list(matched_content)
                                    if len(radar_frame_timestamp_objs)>1:
                                        result_radar.append(radar_frame_timestamp_objs)
                                    if cnt_radar_frame>=200:
                                        result_camera=[]
                            elif "input_camera" in line:
                                match = re.search(r"input_camera\s*(.*)", line.strip())
                                if match:
                                    cnt_camera_frame += 1
                                    cnt_radar_frame = 0
                                    matched_content = match.group(1)
                                    camera_frame_timestamp_obj01 = get_camera_obj_list(matched_content)
                                    # camera_frame_timestamp_obj01 格式是[时间戳,obj_list_c01]
                                    if len(camera_frame_timestamp_obj01[1])>0:
                                        result_camera.append(camera_frame_timestamp_obj01)
                                    if cnt_camera_frame>=200:
                                        result_radar=[]
                            cnt_no_consecutive = 0
                        else:
                            cnt_no_consecutive += 1
                        # 一段时间没有雷达和相机输入，中断日志
                        if cnt_no_consecutive >= 10 or cnt_camera_frame >= 100 or cnt_radar_frame >= 100:
                            if len(result_camera) > 200 and len(result_radar) > 200:
                                result_radar_camera.append([result_radar, result_camera])
                                self.get_fov_from_list(result_radar, result_camera)
                                result_radar = []
                                result_camera = []
                            cnt_consecutive = 0


                    # # 文件最后，需要处理残留的数据
                    # if len(result_camera) > 50 and len(result_radar) > 100:
                    #     result_radar_camera.append([result_radar, result_camera])
                    #     get_fov_from_list(result_radar, result_camera)

        except IOError:
            print(f"find_lines_with_pattern open file error: {file_path_list},{traceback.format_exc()}")
        if len(self.calibration_result_list_c01) > 0:
            calibration_result_c0 = [result for result in self.calibration_result_list_c01 if result[0] == 0]
            if len(calibration_result_c0) > 0:
                best_result_c0 = min(calibration_result_c0, key=lambda x: x[1][0][2])
                self.calibration_result_dict01[0] = best_result_c0[1]
                print(f"calibration_result_dict01 0: {self.calibration_result_dict01[0]}")
            calibration_result_c1 = [result for result in self.calibration_result_list_c01 if result[0] == 1]
            if len(calibration_result_c1) > 0:
                best_result_c1 = min(calibration_result_c1, key=lambda x: x[1][0][2])
                self.calibration_result_dict01[1] = best_result_c1[1]
                print(f"calibration_result_dict01 1: {self.calibration_result_dict01[1]}")
        print(f"time_of_run={time.time() - time_start} {file_path_list}")
        return result_radar_camera

    def get_fov_from_list(self, radar_list, camera_list):
        camera_dictTime, radar_dictY = get_fov_preprocess(radar_list, camera_list)
        # 根据雷达距离，进行校准计算
        camera_id = 0
        calibration_data_dict = get_fov_findDataByRadarDistance(radar_dictY, camera_dictTime, camera_id, [25, 40])
        if calibration_data_dict is not None :
            bestResult0 = get_fov_dict2result(calibration_data_dict)
            # [[deg_fov_v, vanishing_pixel, dist_h_coef], [radar_y0, radar_y1, camera_obj0, camera_obj1]]
            self.calibration_result_list_c01.append([camera_id, bestResult0])
        camera_id = 1
        calibration_data_dict = get_fov_findDataByRadarDistance(radar_dictY, camera_dictTime, camera_id, [65, 130])
        if calibration_data_dict is not None:
            bestResult1 = get_fov_dict2result(calibration_data_dict)
            self.calibration_result_list_c01.append([camera_id, bestResult1])


def get_fov_preprocess(radar_list, camera_list):

    # 根据时间交集，提纯list
    time_start = max(radar_list[0][0], camera_list[0][0])
    time_end = min(radar_list[-1][0], camera_list[-1][0])
    time_start_obj = datetime.datetime.fromtimestamp(time_start)
    time_end_obj = datetime.datetime.fromtimestamp(time_end)
    print(f"time_start={time_start_obj}>>>>> time_end={time_end_obj} ")
    radar_list = [frame for frame in radar_list if time_start <= frame[0] <= time_end]
    camera_list = [frame for frame in camera_list if time_start <= frame[0] <= time_end]
    # 打印信息
    len_str = f"radar_len={len(radar_list)},camera_len={len(camera_list)}"
    print(f"get_fov_preprocess start_end_camera index= {len_str} ")
    print(f"radar_list {radar_list[0]} >>>>>>> {radar_list[-1]}")
    print(f"camera_list {camera_list[0]} >>>>>>> \n {camera_list[-1]}")
    # 转换为dict，方便查找处理
    radar_dictY = radar_list2dict(radar_list)
    camera_dictTime = camera_list2dict(camera_list)
    return camera_dictTime, radar_dictY


def get_fov_dict2result(calibration_data_dict):
    # calibration_data_dict = {20: {'camera': [{'confidence': 0.83702451, 'class': 0, 'bbox': [235, 230, 50, 96],
    #                                          'dto': [9998, -2.7576227324744202, 21.437995015288042, 0, 0], 'in_area': 1,
    #                                          'id': 0}],
    #                               'radar': [4563, -3.1, 20.3, 0.0, 1695608504.4316454]},
    #                          45: {'camera': [{'confidence': 0.83912003, 'class': 0, 'bbox': [373, 225, 17, 40],
    #                                          'dto': [9998, -0.7729366105802417, 45.34877238216016, 0, 0], 'in_area': 1,
    #                                          'id': 0}],
    #                               'radar': [4563, -1.3, 45.0, 0.0, 1695608529.9164352]}
    #                          }
    key_list = list(calibration_data_dict.keys())
    key_list.sort()
    if len(key_list) >= 2:
        key0, key1 = key_list[0], key_list[1]
        calibration_result_list=[]
        for camera_obj0 in calibration_data_dict[key0]['camera']:
            for camera_obj1 in calibration_data_dict[key1]['camera']:
                try:
                    bbox0 = camera_obj0['bbox']
                    radar_y0 = calibration_data_dict[key0]['radar'][2]
                    bbox1 = camera_obj1['bbox']
                    radar_y1 = calibration_data_dict[key1]['radar'][2]
                    deg_fov_v, vanishing_pixel, dist_h_coef= get_fov_bbox2fov(bbox0, radar_y0, bbox1, radar_y1, camera_H=2.4)
                    calibration_result_list.append([[deg_fov_v, vanishing_pixel, dist_h_coef], [radar_y0, radar_y1, camera_obj0, camera_obj1]])
                except:
                    print(f"get_fov_dict2result error {traceback.format_exc()}")
    best_result = min(calibration_result_list, key=lambda result: result[0][2])
    print(f"get_fov_dict2result best_result={best_result}")
    return best_result


def get_fov_findDataByRadarDistance(radar_dictY, camera_dictTime, camera_id=0, cali_distances=[25, 40]):
    calibration_distances_key = [int(y) for y in cali_distances]
    calibration_data_dict={}
    # 找到每个距离对应的雷达目标和相机目标
    for distance_key in calibration_distances_key:
        radar_camera_dict = {}
        if distance_key not in radar_dictY:
            return
        for obj_radar in radar_dictY[distance_key]:
            obj_time = obj_radar[-1]
            camera_objs_inTime = get_camra_objs_inTime(camera_dictTime, obj_time)
            camera_objs_inTime = [obj for obj in camera_objs_inTime if obj['id'] == camera_id]
            if len(camera_objs_inTime) > 0:
                # 选取一个目标用于校准
                # camera_obj_for_cal = camera_objs_inTime[0]  # 暂时直接取第一个
                # camera_obj_for_cal = max(camera_objs_inTime, key=lambda objs: objs.get("confidence", 0))
                # {'confidence': 0.83702451, 'class': 0, 'bbox': [235, 230, 50, 96], 'dto': [9998, -2.7576227324744202, 21.437995015288042, 0, 0], 'in_area': 1, 'id': 0}
                radar_camera_dict["camera"] = camera_objs_inTime
                radar_camera_dict["radar"] = obj_radar
                break
        calibration_data_dict[distance_key] = radar_camera_dict
    key_len_list=[1 for x in calibration_data_dict.values() if len(x)>0]
    if len(key_len_list)>=2:
        return calibration_data_dict
    else:
        return None


def get_camra_objs_inTime(camera_dictTime, obj_time, max_time_span=2):
    time_offset_list = [0, 1, -1, 2, -2]
    for time_offset in time_offset_list:
        time_key = math.floor(obj_time) + time_offset
        if time_key in camera_dictTime:
            camera_objs_inTime = camera_dictTime[time_key]
            return camera_objs_inTime
    else:
        return []


def radar_list2dict(radar_list):
    # 找到radar_list 中对应距离的雷达目标
    radar_dictY = {}
    for radar_frame in radar_list:
        time_stamp, objs_list = radar_frame
        for obj in objs_list:
            id, x, y = obj[0:3]
            key_y = math.floor(y)
            obj[4] = time_stamp  # 借用obj[4]存储时间戳
            if key_y not in radar_dictY:
                radar_dictY[key_y] = [obj]
            else:
                radar_dictY[key_y].append(obj)
    return radar_dictY
                

def camera_list2dict(camera_list):
    # 找到camera_list 中对应距离的雷达目标
    camera_dictTime = {}
    for camera_frame in camera_list:
        time_stamp, objs_list = camera_frame
        for obj in objs_list:
            key_y = math.floor(time_stamp)
            if key_y not in camera_dictTime:
                camera_dictTime[key_y] = [obj]
            else:
                camera_dictTime[key_y].append(obj)
    return camera_dictTime


def get_radar_obj_list(matched_content):
    matched_content = matched_content.replace("\'", "\"").replace("(", "[").replace(")", "]")
    json_camera = json.loads(matched_content)
    # json_camera =[1695763757.490538, [[5072, 1.8, 99.1, 0.0, 0.0]]]
    return json_camera


def get_camera_obj_list(matched_content):
    # json_camera = {'camerastatus': [{'nearcameraocclude': '-1', 'farcameraocclude': '-1', 'deflection': '-1', 'nighttrainlight': '-1'}],
    #                'list': [{'id': 1, 'timestamp': 1695763544637,
    #                          'data': [{'confidence': 0.29144457, 'class': 0, 'bbox': [297, 0, 45, 20], 'dto': [9998, 9999.9999, 9999.9999, 0, 0],'in_area': 0}]
    #                          }],
    #                'stamp': 1695763544.6414816}
    matched_content = matched_content.replace("\'", "\"").replace("(", "[").replace(")", "]")
    json_camera = json.loads(matched_content)
    obj_list_c01 = []
    for c01_dict in json_camera["list"]:
        # c01_dict = {'id': 0, 'timestamp': 1695763544751, 'data': [
        #     {'confidence': 0.391460359, 'class': 0, 'bbox': [295, 0, 48, 20],
        #      'dto': [9998, 9999.9999, 9999.9999, 0, 0], 'in_area': 0}]}
        # 只保留置信概率大于0.5的目标
        obj_list_id = [x for x in c01_dict["data"] if x['confidence'] > 0.6]
        for index in range(len(obj_list_id)):
            obj_list_id[index]["id"] = c01_dict["id"]
        obj_list_c01.extend(obj_list_id)
    # 返回值[时间戳,obj_list_c01]
    return [json_camera['stamp'], obj_list_c01]


def get_fov_bbox2fov(obj1_bbox, radar_y1, obj2_bbox, radar_y2, camera_H=2.4):
    try:
        bottom_pixel1 = obj1_bbox[1] + obj1_bbox[3]
        bottom_pixel2 = obj2_bbox[1] + obj2_bbox[3]
        theta1 = math.atan(camera_H / radar_y1)
        theta2 = math.atan(camera_H / radar_y2)
        rad_delta = theta1 - theta2
        rad_per_pixel = abs(rad_delta / (bottom_pixel1 - bottom_pixel2))
        rad_fov_v = rad_per_pixel * 450
        deg_fov_v = rad_fov_v * 180 / math.pi
        vanishing_pixel = bottom_pixel2 - theta2 / rad_per_pixel
        dist_h_1 = radar_y1 * obj1_bbox[3]
        dist_h_2 = radar_y2 * obj2_bbox[3]
        dist_h_coef = max(dist_h_2, dist_h_1) / min(dist_h_2, dist_h_1)
        # print(f"get_fov_bbox2fov deg_fov_v={deg_fov_v:.2f},vanishing_pixel={vanishing_pixel:.2f} dist_h_coef={dist_h_coef:.4f}")
        return [deg_fov_v, vanishing_pixel, dist_h_coef]
    except:
        print(f"get_fov_bbox2fov error {traceback.format_exc()}")
        return [99.99, 99.99, 99.99]


def test_c0_get_fov():
    obj1_bbox = [207, 235, 61, 91]
    obj1_radar = [4563, -2.5, 20.7, 0.0, 0.0]
    obj2_bbox = [387, 221, 16, 35]
    obj2_radar = [4563, -1.1, 50.7, 0.0, 0.0]
    get_fov_bbox2fov(obj1_bbox, obj1_radar[2], obj2_bbox, obj2_radar[2])


def test_c1_get_fov():
    obj1_bbox = [358, 215, 68, 165]
    obj1_radar = [4563, -1.1, 50.7, 0.0, 0.0]
    obj2_bbox = [480, 188, 40, 90]
    obj2_radar = [4563, 0.3, 91.4, 0.0, 0.0]
    get_fov_bbox2fov(obj1_bbox, obj1_radar[2], obj2_bbox, obj2_radar[2])


if __name__ == "__main__":
    autoFov = AutoFov()
    # test_c0_get_fov()
    # test_c1_get_fov()
    # file_path = r"D:\project\tvtEye\guard_tvt\tools\log\system_20230926_1525.log.2023-09-27_05"
    # file_path1 = r"D:\FTP\log\20230908\system_20180128_2358.log.2023-10-07_10"
    # file_path2 = r"D:\FTP\log\20230908\system_20180128_2358.log.2023-10-07_11"
    # file_path3 = r"D:\FTP\log\20230908\system_20180128_2358.log.2023-10-07_12"
    # results = autoFov.autoFov_fromLog([file_path1, file_path2, file_path3], )
    # results = autoFov.autoFov_fromLog([r"D:\FTP\log\20230908\system_20231010_1124.log.2023-10-10_15",
    #                                    r"D:\FTP\log\20230908\system_20231010_1124.log",
    #                                    ], )
    results = autoFov.autoFov_fromLog([r"D:\FTP\log\20230908\system_20231010_1655.log.2023-10-10_16",
                                       r"D:\FTP\log\20230908\system_20231010_1655.log",
                                       ], )
    # file_path1 = r"D:\project\tvtEye\guard_tvt\tools\log\system_20180128_2358.log.2023-09-25_09"
    # file_path2 = r"D:\project\tvtEye\guard_tvt\tools\log\system_20180128_2358.log.2023-09-25_10"
    # results = autoFov.autoFov_fromLog([file_path1, file_path2],)

    # print(results)
