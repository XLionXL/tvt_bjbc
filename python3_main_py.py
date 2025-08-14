#encoding: utf-8
import xypLinuxStartInit # 初始化

# 导入官方库
import os
import time

# 导入自己的库
from main_engine import MainEngine



if __name__ == '__main__':
    mainFolder =  "/ssd/lss/guard_tvt-BJCOMP2025/"
    engine = MainEngine(main_folder=mainFolder, xml_path=os.path.join("..", "zj-general-constant.xml"))
    engine.run()
    while True:
        startTime =  time.monotonic()
        engine.update()
        spendTime =  time.monotonic()-startTime
        time.sleep(max(1-spendTime,0))