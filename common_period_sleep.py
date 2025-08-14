# -*- coding: utf-8 -*-
import datetime
import time


class Period_Sleep:
    # 周期定时节拍器，每次超过指定fireTime时间，返回True
    def __init__(self):
        self.lastTime = time.time()

    def period_sleep(self, period_s=2):
        time_escape=time.time() - self.lastTime
        self.lastTime = time.time()
        if time_escape < period_s:
            time.sleep(period_s-time_escape)


if __name__=="__main__":
    period_sleep=Period_Sleep()
    for i in range(10):
        period_sleep.period_sleep(2)
        print(f"{datetime.datetime.now()},{i}")
