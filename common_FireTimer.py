# -*- coding: utf-8 -*-
import datetime
import time


class FireTimer:
    # 周期定时节拍器，每次超过指定fireTime时间，返回True
    def __init__(self):
        self.startTime = time.time()

    def isFireTime(self, fireTime, ):
        if time.time() - self.startTime >= fireTime:
            self.startTime = time.time()
            return True
        else:
            return False

    def update_Timer(self):
        self.startTime = time.time()


class FireTimer_WithCounter(FireTimer):
    # 周期定时节拍器，每次超过指定fireTime时间，返回True
    def __init__(self, fire_number=3):
        super(FireTimer_WithCounter, self).__init__()
        self.fire_cnt = 0
        self.fire_number = fire_number

    def isFireTime(self, fireTime):
        if time.time() - self.startTime >= fireTime and self.fire_cnt < self.fire_number:
            self.startTime = time.time()
            self.fire_cnt += 1
            return True
        else:
            return False

    def reset_fire_cnt(self):
        self.fire_cnt = 0


class FireTimer_withCounter_InSpan:
    # 周期定时节拍器，每次超过指定fireTime时间，返回True
    def __init__(self, max_time_span_s=3600, max_fire_times=3):
        self.start_Time = None
        self.fire_time_last = None
        self.fire_cnt = None
        self.max_time_span_s = max_time_span_s  # 所有触发的最大时间间隔，-1表示无时间跨度限制
        self.max_fire_times = max_fire_times    # 所有触发的最大次数,-1表示无次数限制

    def isFireTime(self, fireTime, is_first_fire=False):
        # 第一次调用，reset，开始计时
        if self.start_Time is None:
            self.__reset()
        time_now = time.time()
        is_fire = False

        # 第一次fire
        if self.fire_cnt <= 0 and (time_now - self.start_Time > fireTime or is_first_fire):
            is_fire = True
            self.fire_time_last = time.time()
            self.start_Time = time.time()
            self.fire_cnt = 1
        # 不是第一次fire，满足次数、总时间跨度、时间间隔的要求
        elif 0 < self.fire_cnt \
                and (self.max_fire_times < 0 or self.fire_cnt < self.max_fire_times) \
                and (self.max_time_span_s < 0 or time_now - self.start_Time < self.max_time_span_s) \
                and (self.fire_time_last is not None and time_now - self.fire_time_last >= fireTime):
            is_fire = True
            self.fire_time_last = time_now
            self.fire_cnt += 1

        if self.max_time_span_s > 0 and self.fire_cnt > 0 and (time_now - self.start_Time > self.max_time_span_s):
            self.__reset()

        return is_fire

    def __reset(self):
        self.fire_time_last = None
        self.fire_cnt = 0
        self.start_Time = time.time()


def test_fireTimer_withCounter():
    fireTimer_withCounter = FireTimer_WithCounter(2)
    for index in range(60):
        time.sleep(1)
        if fireTimer_withCounter.isFireTime(3):
            print(f"{datetime.datetime.now()},is fire time{fireTimer_withCounter.fire_cnt}/{fireTimer_withCounter.fire_number}")
        else:
            print(f"{datetime.datetime.now()} not fire")
        if index == 40:
            fireTimer_withCounter.reset_fire_cnt()


def test_FireTimer_withCounter_InSpan(max_time_span_s, max_fire_times,is_first_fire=False):
    fireTimer_withCounter = FireTimer_withCounter_InSpan(max_time_span_s, max_fire_times)
    for index in range(60):
        time.sleep(1)
        if fireTimer_withCounter.isFireTime(3,is_first_fire):
            counter_str=f"{fireTimer_withCounter.fire_cnt}/{fireTimer_withCounter.max_fire_times}"
            print(f"{datetime.datetime.now()},{index},is fire time{counter_str}")
        else:
            print(f"{datetime.datetime.now()},{index},not fire")


if __name__ == "__main__":
    # test_fireTimer_withCounter()
    test_FireTimer_withCounter_InSpan(20, 3, is_first_fire=True)
    test_FireTimer_withCounter_InSpan(-1, 3, is_first_fire=True)
    test_FireTimer_withCounter_InSpan(-1, -1, is_first_fire=True)
    test_FireTimer_withCounter_InSpan(20, 3)
    test_FireTimer_withCounter_InSpan(-1, 3)
    test_FireTimer_withCounter_InSpan(-1, -1)
