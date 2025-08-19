import ctypes
import datetime
import json
import os.path
import platform
import threading
import time
import traceback
from ctypes import *
from queue import Queue

from common_FireTimer import FireTimer


class Save_Pic_by_Infer:
    def __init__(self, pic_timeSpan_min=5, max_file_num=1000, max_file_size=2000 * pow(10, 6),
                 sudo_pw="king", pic_folder="/ssd/alarmpic/alarmFrame"):
        self.task_thread = None
        self.pic_timeSpan_min = pic_timeSpan_min
        self.save_pic_dll = ctypes.CDLL('/usr/bin/zipx/zj-guard-so/libclient.so')
        if "Windows" in platform.platform():
            self.pic_folder_list = [
                r"D:\FTP\pic_test\nearcamera_alarmpic",
                r"D:\FTP\pic_test\farcamera_alarmpic",
                r"D:\FTP\pic_test\alarmFrame"
            ]
        else:
            self.pic_folder_list = [
                pic_folder.replace("alarmFrame", "nearcamera_alarmpic"),
                pic_folder.replace("alarmFrame", "farcamera_alarmpic"),
                pic_folder
            ]
        # 每个timeStamp -5确保第一次调用有足够的时间间隔
        self.timeStamp_save_operation_dict = {1: time.time() - 5, 2: time.time() - 5, 3: time.time() - 5,
                                              4: time.time() - 5, 5: time.time() - 5}
        self.jpg_path_list_dict = {0: "", 1: ""}
        self.timer_for_saver=FireTimer()
        # self.pic_deleter_near = LOG_DELETER(self.pic_folder_list[0], 50, 100, period_minutes=1, sudo_pw=sudo_pw)
        # self.pic_deleter_near.thread_start('pic_deleter_near')
        # self.pic_deleter_far = LOG_DELETER(self.pic_folder_list[1], 50, 100, period_minutes=1, sudo_pw=sudo_pw)
        # self.pic_deleter_far.thread_start('pic_deleter_far')
        # self.pic_deleter_3 = LOG_DELETER(self.pic_folder_list[2], max_file_num, max_file_size, period_minutes=1, sudo_pw=sudo_pw)
        # self.pic_deleter_3.thread_start('pic_deleter_3')

        self.task_queue = Queue(maxsize=20)
        self.task_start()

    def saveAlarmPicture_task_enQueue(self, camera_id, file_path, bbox_list=[[100, 100, 100, 100]], timestamp=0):
        save_operation = 2 if camera_id == 0 else 1
        if len(bbox_list)==0:
            bbox_list=[[200, 100, 400, 300]]
        self.task_queue.put((camera_id, file_path, bbox_list, timestamp))
        qsize=self.task_queue.qsize()
        self.timeStamp_put = time.time()
        time.sleep(0.2)
        return 0

    def save_c01_radar_pic(self, operation, c01_radar_pic_path, bbox_list=[[100, 100, 100, 100]], timestamp=0, radar_pic_path=None,flag=0):
        # 调用dll存储c01和radar的拼接图片
        print("已进入/usr/bin/zipx/zj-guard-so/libclient.so的调用")
        bbox_list_str = json.dumps(bbox_list).replace(" ", "")
        bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
        p2_bbox_list_str = c_char_p(bbox_list_str_1)
        timestamp_ = c_long(timestamp)
        str_r = bytes(c01_radar_pic_path, 'utf-8')
        p1_new_camera_pic_path = c_char_p(str_r)
        if radar_pic_path is None:
            if self.save_pic_dll is not None:
                self.save_pic_dll.MesOfAlarmpic_andRadarpic_AccodingTimestamp(operation, p1_new_camera_pic_path, p2_bbox_list_str, timestamp_)
        else:
            str_radar = bytes(radar_pic_path, 'utf-8')
            p3_radar_img = c_char_p(str_radar)
            if self.save_pic_dll is not None:
                print(f"已经运行到调用dll合并雷达图和相机图了,即将传入的参数为:{operation, p1_new_camera_pic_path, p2_bbox_list_str, timestamp_, p3_radar_img,flag}")
                self.save_pic_dll.MesOfAlarmpic_andRadarpic_AccodingTimestamp(operation, p1_new_camera_pic_path, p2_bbox_list_str, timestamp_, p3_radar_img,flag)
                print("合并完了")


    def task_start(self):
        if self.task_thread is None:
            # 运行数据接收线程
            self.task_thread = threading.Thread(target=self.task_rcv_fun, daemon=True,name='self.task_thread ')
            self.task_thread.start()

    def task_rcv_fun(self):
        while True:
            try:
                queue_task_number=self.task_queue.qsize()
                if queue_task_number > 0:
                    task_infor = self.task_queue.get()
                    camera_id, file_path, bbox_list, timestamp = task_infor
                    save_result = self.saveAlarmJpgMp4(camera_id, file_path, bbox_list, timestamp)
                else:
                    time.sleep(0.002)
            except:
                traceback.print_exc()
                time.sleep(10) #延迟，避免巨量打印信息

    def saveAlarmJpgMp4(self, camera_id=0, file_path="/ssd/alarmpic/alarmFrame_20230518_090000_0.jpg",
                        bbox_list=[[100, 100, 100, 100]], timestamp=0):
        """
        :param save_type_0jpg_1mp4: 0 存图片，1 存mp4视频
        :param camera_id: 0 近焦相机，1 远焦相机
        :param file_path: 文件保存路径,必须以mp4或者jpg结尾，
        :param bbox_list: 存图片时候的xywh标注框列表，例如[[100, 100, 100, 100]]
        :return:
        """
        file_tail= file_path[-3:]
        if "jpg" in file_tail:
            save_type_0jpg_1mp4 = 0
        elif "mp4" in file_tail:
            save_type_0jpg_1mp4 = 1
        else:
            return
        operation_convert_dict={
            0: 2 if camera_id <= 0 else 1,  # 存jpg
            1: 5 if camera_id <= 0 else 4,  # 存mp4
        }
        save_operation = operation_convert_dict[save_type_0jpg_1mp4]
        try:
            # save_operation:
            # 1 save far img
            # 2 save near img
            # 3 save far && near img
            # 4 save far  video
            # 5 save near video
            # /ssd/alarmpic/ 下有两个文件夹
            # 一个farcamera_alarmpic放远焦报警图片，一个 nearcamera_alarmpic 放近焦图片

            if not os.path.exists("/ssd") or False:
                return
            file_folder = os.path.dirname(file_path)
            if not os.path.exists(file_folder):
                os.makedirs(file_folder)

            # lib
            lib_client_path = '/usr/bin/zipx/zj-guard-so/libclient.so'
            if os.path.exists(lib_client_path):
                # bbox_list 的分辨率转换。bbox为800*450，存图分辨率1920*1080
                if len(bbox_list) == 0 or bbox_list is None:
                    bbox_list = [[10, 10, 10, 10]]  # xywh
                x_coef, y_coef = 1920 / 800, 1080 / 450
                bbox_1920_1080_list=[]
                for bbox in bbox_list:
                    x, y, w, h = bbox
                    if save_operation==3:
                        bbox_1920_1080 = [int(x * x_coef), int(1080 * camera_id + y * y_coef),int(w * x_coef), int(h * y_coef)]
                    else:
                        bbox_1920_1080 = [int(x * x_coef), int(y * y_coef), int(w * x_coef), int(h * y_coef)]
                    bbox_1920_1080_list.append(bbox_1920_1080)
                bbox_list_str = json.dumps(bbox_1920_1080_list).replace(" ", "")
                bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
                bbox_list_p = ctypes.c_char_p(bbox_list_str_1)

                timestamp_c_long = ctypes.c_long(timestamp)

                # 存图操作，
                # time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # if 1 <= save_operation <= 3:
                #     path_jpg_str = f"{pic_folder_path}/{time_str}_alarm_frame_" + f"{camera_id}_{save_operation}" + ".jpg"
                #     path_jpg_bytes = bytes(path_jpg_str, 'utf-8')
                #     path_jpg_p = ctypes.c_char_p(path_jpg_bytes)
                #     time_span = time.time() - self.timeStamp_save_operation_dict[save_operation]
                #     if time_span >= self.pic_timeSpan_min:
                #         print(f"saveAlarmPicture,save_operation={save_operation},path_jpg_str={path_jpg_str}")
                #         self.jpg_path_list_dict[camera_id] = path_jpg_str
                #         save_pic_dll.start(save_operation, path_jpg_p, bbox_list_p)
                #         self.timeStamp_save_operation_dict[save_operation] = time.time()
                # 存图存视频操作
                file_path_bytes = bytes(file_path, 'utf-8')
                path_mp4_p = ctypes.c_char_p(file_path_bytes)
                if 1 <= save_operation <= 2:
                    # 存图时，需要捆绑保存视频
                    # save_pic_dll.start(save_operation, path_mp4_p, bbox_list_p)
                    self.save_pic_dll.start_new(save_operation, path_mp4_p, bbox_list_p, timestamp_c_long)
                    return file_path
                elif 4 <= save_operation <= 5:
                    self.save_pic_dll.start(save_operation, path_mp4_p, bbox_list_p)
                    return file_path
                else:
                    return 0
            else:
                # 旧版存图
                client_path = '/usr/bin/zipx/zj-guard-so/client.so'
                dll_saveAlarmPicture = ctypes.CDLL(client_path)
                dll_saveAlarmPicture.start(save_operation)
                return 0

        except:
            return 0

    def new_test(self, save_alarm_pic):
        self.save_pic_dll = ctypes.CDLL('/usr/bin/zipx/zj-guard-so/libclient.so')
        str_res = "./20230232_192308_alarm_frame.jpg"
        str_r = bytes(str_res, 'utf-8')
        p1 = ctypes.c_char_p(str_r)

        bbox_list = [[50, 50, 100, 100], [250, 250, 100, 100]]  # xywh
        bbox_list_str = json.dumps(bbox_list).replace(" ", "")
        bbox_list_str_1 = bytes(bbox_list_str, 'utf-8')
        p2 = ctypes.c_char_p(bbox_list_str_1)
        self.save_pic_dll.start(save_alarm_pic, p1, p2)

    def save_pic_windows(self, operation=3):
        from PIL import Image
        path = r"D:\新板子_DataSet\20210303 床铺动作测试\床头右侧\床头右侧.jpg"  # 图片路径
        img = Image.open(path)  # 打开图片
        if operation == 3:
            img.save(os.path.join(self.pic_folder_list[0], f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"))
            img.save(os.path.join(self.pic_folder_list[1], f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"))
        elif operation == 1:
            img.save(os.path.join(self.pic_folder_list[1], f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"))
        elif operation == 2:
            img.save(os.path.join(self.pic_folder_list[0], f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"))

    def exit(self):
        # self.pic_deleter_far.thread_exit()
        # self.pic_deleter_near.thread_exit()
        # self.pic_deleter_3.thread_exit()
        print(f"{datetime.datetime.now()},Save_Pic_by_Infer exit")

    def test_longTime_jpg_mp4_save(self, index_loop=1000, little_span=2, big_span=10, ):
        index_big_span = 0
        while index_loop > 0:
            index_loop -= 1
            for index in range(3):
                time.sleep(little_span)
            time.sleep(big_span)

    def test_saveAlarmJpgMp4(self):
        file_folder = f"/ssd/alarmpic/test"
        for index in range(5):
            time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            camera_id = 0
            self.saveAlarmJpgMp4(camera_id=camera_id, file_path=f"{file_folder}/{time_str}_test_{camera_id}.jpg",
                                 bbox_list=[[100, 100, 55, 55]])
            camera_id = 1
            self.saveAlarmJpgMp4(camera_id=camera_id, file_path=f"{file_folder}/{time_str}_test_{camera_id}.jpg",
                                 bbox_list=[[100, 100, 55, 55]])
            time.sleep(3)

        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        for index in range(5):
            camera_id = 0
            self.saveAlarmJpgMp4(camera_id=camera_id, file_path=f"{file_folder}/{time_str}_test_{camera_id}.mp4",
                                 bbox_list=[[200, 200, 55, 55]])
            camera_id = 1
            self.saveAlarmJpgMp4(camera_id=camera_id, file_path=f"{file_folder}/{time_str}_test_{camera_id}.mp4",
                                 bbox_list=[[200, 200, 55, 55]])
            time.sleep(3)


if __name__ == "__main__":
    saver = Save_Pic_by_Infer(pic_timeSpan_min=0.1)
    nowTime = int(time.time() * 1000) #当前时间
    print('--------------------------------')
    print(f"此时传入的时间戳为：{nowTime}")
    print('--------------------------------')
    saver.save_c01_radar_pic(3, "/ssd/alarmpic/alarmFrame/2025-08-16/2025-08-16_05-31-26_i000015_d217.6_a3_w1_s1.jpg", 
                            [[100, 100, 100, 100]], nowTime,
                            "/ssd/alarmpic/alarmFrame/2025-08-16/2025-08-16_05-31-26_i000015_d217.6_a3_w1_s1_radar.jpg",1)
    # saver.test_saveAlarmJpgMp4()
    saver.exit()
    # saveAlarmPicture(3)
