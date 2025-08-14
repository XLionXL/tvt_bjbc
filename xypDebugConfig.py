import os
import platform
if platform.system() == "Windows":
    matplotlibDeBugFlag = True
    opencvDeBugFlag     = True
    printDeBugFlag      = True
    logDeBugFlag        = True
    xypTestSwitch = False
    xypLogPath = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),"testData/log"))
else:
    matplotlibDeBugFlag = False
    opencvDeBugFlag = False
    printDeBugFlag = False
    logDeBugFlag = False
    xypTestSwitch = False
    xypLogPath = "/ssd/xyp/xypLog"

