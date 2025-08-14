import datetime
import time
from user_pw import User_PW


def test_gpio_RadarReset():
    global user_pw
    user_pw = User_PW()
    print(f"GPIO_RD reset")
    user_pw.power_control_gpio_reset(gpio_name="GPIO_RD")
    print(f"time.sleep(5)")
    time.sleep(5)
    print(f"GPIO_HB reset")
    user_pw.power_control_gpio_reset(gpio_name="GPIO_HB")


def test_cameraFrame():
    global index
    camera_frame = list(range(10))
    print(f"camera_frame={camera_frame}")
    for obj in camera_frame[1:-1]:  # camera_frame[0]是时间戳
        print(obj)
    camera_fram = list(range(0, 10))
    camera_frame_len = len(camera_fram)
    for index in range(-1, -1 * camera_frame_len, -1):
        print(f"index={index},value={camera_fram[index]}")


def test_timedLoop():
    timeStamp_dict = {"0": datetime.datetime.now().strftime("%Y%m%d_%H%M%S.%f")}
    timeStamp_start = time.time()
    timeStamp_dict["1"] = time.time() - timeStamp_start
    timeStamp_dict["2"] = time.time() - timeStamp_start
    for key in timeStamp_dict:
        print(f"is_alarm_by_score timeStamp_dict={key}")
    timestamp_start = time.time()
    time.sleep(0.1)
    time_for_run_s = time.time() - timestamp_start
    if time_for_run_s < 0.5:
        print(f"sleep {0.5 - time_for_run_s}")
        time.sleep(0.5 - time_for_run_s)


def find_max_consecutive_length(nums):
    if not nums:
        return 0

    max_inc_length = 1
    max_dec_length = 1
    current_increase_length = 1
    current_decrease_length = 1

    for i in range(1, len(nums)):
        if nums[i] > nums[i-1]:
            current_increase_length += 1
        else:
            max_inc_length = max(max_inc_length, current_increase_length)
            current_increase_length = 1
        if nums[i] < nums[i-1]:
            current_decrease_length += 1
        else:
            max_dec_length = max(max_dec_length, current_decrease_length)
            current_decrease_length = 1
    print(f"max_inc_length, max_dec_length, current_increase_length, current_decrease_length="
          f"{max_inc_length, max_dec_length, current_increase_length, current_decrease_length}")
    return max(max_inc_length, max_dec_length, current_increase_length, current_decrease_length)


def get_fog_coef_nightTime(self, camera_fogValues):
    # 确定递增计数，
    camera_fogValues_len=len(camera_fogValues)
    increase_cnt=0
    for index in range(camera_fogValues_len-1):
        if camera_fogValues[index] > camera_fogValues[index + 1]:
            increase_cnt += 1

    fog_coef = 0.9 if increase_cnt >= 0.6 * camera_fogValues_len else 0.5  # 相机视野良好，雷达分数乘以小系数，减少雷达误报
    if self.fog_coef_cnt <= 30:
        print(f"get_fog_coef_nightTime fog_coef={fog_coef} increase_cnt={increase_cnt}<<<{camera_fogValues}")
        self.fog_coef_cnt += 1
    # 调试代码，可以删除
    print(f"get_fog_coef_nightTime max_consecutive_length={self.find_max_consecutive_length(camera_fogValues)}")

    return fog_coef


test_data = '101.12,100.49,95.20,98.59,95.17,96.78,94.85,93.51,93.34,103.75,' \
            '94.47,94.61,93.81,102.29,101.57,105.32,110.50,115.15,130.31,130.59,' \
            '118.23,146.41,142.59,130.90,124.13,107.15,88.91,79.97,90.41,107.03,0'
camera_fogStrings = test_data.split(",")
if camera_fogStrings[-1] in ["0", "1"]:
    isDayTime = int(camera_fogStrings[-1])
    camera_fogStrings = camera_fogStrings[0:-1]
print(f"get_fog_coef isDayTime={isDayTime} fogStrings={camera_fogStrings}")
camera_fogValues = [float(val) for val in camera_fogStrings]
max_consecutive_length = find_max_consecutive_length(camera_fogValues)
print(f"{camera_fogValues}连续递增的最大长度为:", max_consecutive_length)
camera_fogValues.reverse()
max_consecutive_length = find_max_consecutive_length(camera_fogValues)
print(f"{camera_fogValues}连续递增的最大长度为:", max_consecutive_length)

# test_gpio_RadarReset()
# test_cameraFrame()
# test_timedLoop()
def test_speed_inList_inDict():
    global data_dict, index
    data_list = list(range(100))
    data_dict = {x: x for x in data_list}
    time_start = time.time()
    in_cnt = 0
    for index in range(1000000):
        if index % 200 in data_list:
            in_cnt += 1
    print(f"time for data_list={time.time() - time_start} in_cnt={in_cnt}")
    time_start = time.time()
    in_cnt = 0
    for index in range(1000000):
        if index % 200 in data_dict:
            in_cnt += 1
    print(f"time for data_dict={time.time() - time_start} in_cnt={in_cnt}")


# point_list = [[9, 6, 3], [5, 2, 8], [7, 4, 1]]
# min_x=min([point[0] for point in point_list])

test_speed_inList_inDict()




