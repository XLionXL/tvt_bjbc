import os
import platform
if platform.system() == "Windows":
    matplotlibDeBugFlag = True
    opencvDeBugFlag     = True
    printDeBugFlag      = True
    logDeBugFlag        = True
    xypLogPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),"log")
else:
    matplotlibDeBugFlag = False
    opencvDeBugFlag = False
    printDeBugFlag = False
    logDeBugFlag = False
    xypLogPath = "/ssd/xyp/xypLog"

