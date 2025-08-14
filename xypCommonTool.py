try:
    import os
    import time
    import torch
    import inspect
    import cv2 as cv
    import matplotlib
    import numpy as np
    import matplotlib.pyplot as plt
except:
    importCmd = [
        "import os",
        "import time",
        "import torch",
        "import inspect",
        "import cv2 as cv",
        "import matplotlib",
        "import numpy as np",
        "import matplotlib.pyplot as plt"
    ]
    for cmd in importCmd:
        print(cmd)
        try:
            exec(cmd)
        except Exception as e:
            print(f"{__file__}: {cmd} fail: {e}")


# 计时
class ReckonTime():
    def __init__(self,flag =""):
        self.mainFlag = str(flag)
        self.startTime = time.time()
        self.lastTime = time.time()
    def reckon(self,flag =""):
        nowTime = time.time()
        if self.mainFlag != '' and flag !="":
            flags =f' "{self.mainFlag} {flag}"'
        elif self.mainFlag != '':
            flags =f' "{self.mainFlag}"'
        elif flag != '':
            flags =f' "{flag}"'
        else:
            flags = ''

        print("since last time{}:{}s".format(flags, nowTime - self.lastTime))
        print("total time{}:{}s\n".format(flags,nowTime- self.startTime ))
        self.lastTime = nowTime

# 函数计时装饰器
def costTime(func):  # 接收被封装函数
    def wrapper(*args, **kwargs):  # 接收被封装函数的参数
        start = time.time()
        print('{} 函数开始运行'.format(func.__name__))
        # 真正执行被封装函数的地方。
        func(*args, **kwargs)
        print('{} 函数运行结束，耗时{}s'.format(func.__name__,time.time() - start))
    return wrapper
# 用于函数运行失败重新运行的装饰器，使用该装饰器的函数返回值为(flag,res)格式
# flag:true继续运行，flase结束运行; res:返回值
def repeatRunFunc(reconnectNum= 8): # 接收装饰器参数，运行次数
    def decorator(func):  # 接收被封装函数
        def wrapper(*args, **kwargs):  # 接收被封装函数的参数
            for i in range(0, reconnectNum + 1):
                if i != 0:
                    print(f"{func.__name__}正在重新运行：{i}/{reconnectNum}")
                flag,res = func(*args, **kwargs)  # 真正执行被封装函数的地方。
                # data第一个是运行是否成功的标志
                if flag:
                    if i == reconnectNum:
                        return res
                else:
                    return res
        return wrapper
    return decorator
# 该方法用于实现matplotlib版的cv.waitKey(0)，采用双击解除阻塞
class MatplotlibWaitKey():
    '''
    因为matplotlib的show函数必需要关掉窗口才能继续运行，用pasue函数结合cv.waitKey(0)又会导致matplotlib窗口
    一移动就报错。所以洋鹏创建了matplotlib堵塞类，用于实现将matplotlib的show变成类似于opencv里面的waitKey函
    数值为0时的情况，从而实现显示图像的想暂停暂停，想继续继续。

    原理：
    通过该类创建的画布figure都加了一个双击操作的监听函数buttonPressCallback，相当cv.waitKey(0)去监听空格
    同时通过block函数循环实现堵塞，而监听函数通过改变blockFlag变量值退出堵塞。

    用法示例：
    第一步：创建类的实例m
    第二步：m.setCurrentCanvas(0)，等价于 plt.figure(0)
    第三步：绘制内容
    第四步：m.display()显示
    '''
    def __init__(self,):
        self.blockFlag = True
        self.currentCanvas = None
        self.figName = [] # 记录当前创建的画布

    def setCurrentCanvas(self,canvasName):
        self.fig = plt.figure(canvasName) # 创建或更换当前画布
        if canvasName not in self.figName: #防止重复操作
            # button_release_event 预定义事件类型，表示鼠标按钮点击事件
            self.fig.canvas.mpl_connect('button_press_event', self.buttonPressCallback) # 前面字符串是固定的
            self.figName.append(canvasName)  # 记录当前创建的画布

    def buttonPressCallback(self,event): # 鼠标按下回调函数
        if event.dblclick: # 如果是双击，取消阻塞
            self.blockFlag = False

    def display(self,block=0.001,clf=False):# 只有传入True时为阻塞，否则为普通plt.pause
        '''
        Args:
            block: float:阻塞block秒，bool:True 阻塞
            clf: str:清除str画布,bool:清除或者不清除所有画布,序列:清除列表中指定画布
        Returns:
        '''
        if not isinstance(block,bool):
            plt.pause(block)
        elif isinstance(block,bool):
            self.blockFlag = block
            plt.pause(0.001)  # 不阻塞则默认显示0.001秒,第一次显示到顶层界面
            while self.blockFlag: # 如果阻塞
                # 不是一次显示则可以后台显示，防止多个画布反复相互覆盖
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
        else:
            raise "block value error"

        if isinstance(clf, str):  # 清空指定的一个画布
            self.fig = plt.figure(clf)
            self.fig.clf()
        elif isinstance(clf, (list, tuple, set)): # 清空指定的一组画布
            for i in clf:
                self.fig = plt.figure(i)  # 清空指定的一个画布
                self.fig.clf()
        elif isinstance(clf, bool) and clf: # 清空所有画布
            for i in self.figName:
                self.fig = plt.figure(i)  # 更换当前画布
                self.fig.clf()



class ColorMap():
    def __init__(self,dataNum,colorSet='Paired'):
        self.dataNum=dataNum
        # https://zhuanlan.zhihu.com/p/158871093 颜色组预览，这里用Paired
        try:
            self.colorMap = matplotlib.colormaps.get_cmap(colorSet)
        except: # 适应老版本
            self.colorMap =  plt.cm.get_cmap(colorSet)
    def __call__(self, key):
       return self.colorMap(key/self.dataNum)
    def getColor(self,):
          return np.arange(self.dataNum)/self.dataNum

# 用于在一个画布上动态实时获取数据
class DynamicCanvas():
    # 用法示例：
    # 第一步：创建类的实例d
    # 第二步：d.addData(1.2,"weight)，添加数据
    # 第三步：d.display 绘制内容并显示
    # 第四步：双击可以聚焦当前位置
    def __init__(self, figName, maxHistoryNum=None):
        # 创建画布
        self.figName =figName
        self.blockFlag = False
        self.maxHistoryNum =maxHistoryNum
        self.fig = plt.figure(figsize=(4, 3), num=figName)
        self.fig.canvas.mpl_connect('button_press_event', self.buttonPressCallback)
        self.ax = plt.subplot()
        self.dataHistory = {}  # 历史数据
        self.fistTimeDisplay =True


    def addData(self, data, dataName):
        if dataName not in self.dataHistory.keys():
            self.dataHistory[dataName] = [data]
        else:
            if self.maxHistoryNum is not None and len( self.dataHistory[dataName])>self.maxHistoryNum:
                self.dataHistory[dataName] =  self.dataHistory[dataName][1:]
            self.dataHistory[dataName].append(data)
        self.colorMap = ColorMap(len(self.dataHistory))

    def buttonPressCallback(self, event):  # 鼠标按下回调函数
        if event.dblclick:  # 如果是双击，取消阻塞
            self.blockFlag = not self.blockFlag

    # 输入数组，画折线图
    def display(self, key=None,method=None):
        '''
        key：指定要画的数据
        '''
        plt.figure(figsize=(4, 3), num=self.figName)
        if key is None: # 不指定则默认全部绘制
            key = self.dataHistory.keys()
        elements = []
        for idx,k in enumerate(key):
            line, = self.ax.plot(self.dataHistory[k],c= self.colorMap(idx),label=f"{k}:{self.dataHistory[k][-1]:.3f}")
            elements.append(line)

        self.ax.legend(loc='upper right')
        if self.fistTimeDisplay:# 第一次显示到顶层界面
            self.fistTimeDisplay = False
            plt.pause(0.001)
        else:# 不是一次显示则可以后台显示，防止多个画布反复相互覆盖
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

        if self.blockFlag:
            self.ax.set_xlim(None)  # 固定xlim
            self.ax.set_ylim(None)  # 固定ylim
            for e in elements: # 移除当前画布内容
                e.remove()
        else:
            self.ax.cla() # 重置子图

    def clearTemp(self):
        self.dataHistory = {}

def normalize(data, min=0, max=255):
    if isinstance(data,torch.Tensor):
        data = data.type(torch.float32)
        if torch.max(data) == torch.min(data):
            return data * 0 + min
        else:
            return (max - min) * (data - torch.min(data)) / (torch.max(data) - torch.min(data)) + min
    if isinstance(data, (np.ndarray,list,set,tuple)):
        data = np.array(data,dtype=np.float64)
        if np.max(data) == np.min(data):
            return data * 0 +min
        else:
            return (max - min) * (data - np.min(data)) / (np.max(data) - np.min(data)) + min

class XypError(Exception):
    def __init__(self, msg):
        lastStack = inspect.stack()[1]  # 获取调用栈的上一层
        print(f"{lastStack.filename}--{lastStack.lineno}: {msg}")
def xypPrint(*data):
    '''printI用于美化输出'''
    # 打开调用该函数的文件
    lastStack = inspect.stack()[1]
    f = open(lastStack.filename, "r", encoding='utf8')
    fileData = f.readlines()
    f.close()
    # 获取调用该函数xypPrint内容
    leftParenthesesNum = 0 #统计左括号数
    xypPrintTxt = ''
    lineOffset = -1
    print(f"{lastStack.filename}--{lastStack.lineno}")
    while True:
        xypPrintTxt =xypPrintTxt + fileData[lastStack.lineno +lineOffset].strip()
        for i in xypPrintTxt:
            if i == '(':
                leftParenthesesNum+=1
            if i == ")":
                leftParenthesesNum -=1
        if leftParenthesesNum==0:
            break
        else:
            leftParenthesesNum = 0
            lineOffset +=1
    xypPrintTxt=xypPrintTxt[9:-1] # 去掉xypPrint()
    # 获取每个输出对象
    objectList = [i.strip() for i in xypPrintTxt.split(',')]
    for idx,i in enumerate(data):
        print(f"{objectList[idx]}: {i}")

def xypImgShow(*data):
    '''xypImgShow用于快捷显示多个图片'''
    # 打开调用该函数的文件
    lastStack = inspect.stack()[1]
    f = open(lastStack.filename, "r", encoding='utf8')
    fileData = f.readlines()
    f.close()
    # 获取调用该函数xypPrint内容
    leftParenthesesNum = 0 #统计左括号数
    xypPrintTxt = ''
    lineOffset = -1
    while True:
        xypPrintTxt =xypPrintTxt + fileData[lastStack.lineno +lineOffset].strip()
        for i in xypPrintTxt:
            if i == '(':
                leftParenthesesNum+=1
            if i == ")":
                leftParenthesesNum -=1
        if leftParenthesesNum==0:
            break
        else:
            leftParenthesesNum = 0
            lineOffset +=1
    xypPrintTxt=xypPrintTxt[11:-1] # 去掉xypPrint()
    # 获取每个输出对象
    objectList = [i.strip() for i in xypPrintTxt.split(',')]
    for idx,i in enumerate(data):
        cv.namedWindow(objectList[idx], cv.WINDOW_NORMAL)
        cv.imshow(objectList[idx], i)
        cv.waitKey(1)


class GetImagePos():
    def __init__(self,imgName, img):
        self.pos = []
        self.imgName = imgName
        self.img = img
        self.imgDraw =  self.img.copy()

    def getMousePosCallback(self, event, x, y, flags, param):
        if event == cv.EVENT_FLAG_LBUTTON:
            self.pos.append((x, y))
            print(f"{self.imgName} 鼠标位置(x,y)：({x}, {y})")
            return x, y
        if event == cv.EVENT_MOUSEMOVE and flags == cv.EVENT_FLAG_LBUTTON:
            # 当鼠标移动且左键按下时，获取鼠标位置
            self.pos.append((x, y))
            self.imgDraw[y,x] *= 0
            cv.imshow(self.imgName, self.imgDraw)
            print(f"{self.imgName} 鼠标位置(x,y)：({x}, {y})")
            return x, y
        if event == cv.EVENT_FLAG_RBUTTON:
            self.pos =[]
            self.imgDraw = self.img.copy()
            cv.imshow(self.imgName, self.imgDraw)
            print(f"{self.imgName} 重置")



    def getMousePos(self, ):
        cv.namedWindow(self.imgName, cv.WINDOW_NORMAL)
        if not isinstance(self.img, bool):
            cv.imshow(self.imgName,  self.img)
        cv.setMouseCallback(self.imgName, self.getMousePosCallback, )
def findFiles(searchPath, filterBySuffix=('.py'), mode=0):
    # mode:0 返回绝对路径，1 返回带一层searchPath的相对路径，2 返回不带searchPath的相对路径
    searchPath = os.path.abspath(searchPath)  # 转绝对路径以适应./..等符号
    if mode == 0:
        n = 0
    elif mode == 1:
        n = len(searchPath) - len(os.path.basename(searchPath))
    elif mode == 2:
        n = len(searchPath) + 1
    else:
        raise ValueError("mode error!")
    folderStructure = os.walk(searchPath)  # 获取目录结构
    filePaths = []
    for i in folderStructure:
        currentFolderDirs, sonFolderNames, sonFileNames = i
        currentFolderDirs = currentFolderDirs[n:]
        for sfn in sonFileNames:
            if os.path.splitext(sfn)[1] in filterBySuffix:
                filePaths.append(os.path.join(currentFolderDirs, sfn).replace("\\", "/"))
    return filePaths



import threading
# 防止多个线程对文件进行修改时冲突
class fileThreadManage():
    def __init__(self):
        self.fileThreadLock={}
    def readFile(self,filePath,mode="rt"):
        if filePath not in self.fileThreadLock:
            self.fileThreadLock[filePath]=threading.Lock()
        with self.fileThreadLock[filePath]:
            with open(filePath, mode) as file:
                return file.read()
    def writeFile(self,filePath,data,mode="wt"):
        if filePath not in self.fileThreadLock:
            self.fileThreadLock[filePath] = threading.Lock()
        with self.fileThreadLock[filePath]:
            with open(filePath, mode) as file:
                file.write(data)

















def calculateLineIntersection(self, m1, b1, m2, b2):
    '''
    m=None,直线方程为x=b
    m=0，直线方程为y=b，即y=0*x + b
    '''
    if m1 is None and m2 is None:  # 两条x=b的线
        if b1 == b2:  # 两条直线重合，有无穷多个交点
            return np.inf
        else:  # 两条直线平行且不重合，没有交点
            return None
    elif m1 is None:  # 第一条直线垂直于 x 轴，交点的 x 坐标为 b1
        x = b1
        y = m2 * x + b2
    elif m2 is None:  # 第二条直线垂直于 x 轴，交点的 x 坐标为 b2
        x = b2
        y = m1 * x + b1
    elif m1 == m2:
        if b1 == b2:  # 两条直线重合，有无穷多个交点
            return np.inf
        else:  # 两条直线平行且不重合，没有交点
            return None
    else:  # 一般情况下，解线性方程组得到交点坐标
        x = (b2 - b1) / (m1 - m2)
        y = m1 * x + b1
    return x, y

def splitPolygon(self, polygon, lineMB):
    m, b = lineMB
    # 将多边形的顶点添加到相应的部分
    # Ax + By + c = 0
    if m != None:
        f = lambda x, y: -y + m * x + b
    else:
        f = lambda x, y: x - b

    splitPolygon1 = []
    splitPolygon2 = []
    for i in range(len(polygon)):
        # 获取直线方程
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        # 不要等于
        if f(x1, y1) < 0:
            splitPolygon1.append((x1, y1))
        elif f(x1, y1) > 0:
            splitPolygon2.append((x1, y1))
        if x1 == x2:
            mm = None
            bb = x1
        else:
            mm = (y2 - y1) / (x2 - x1)
            bb = y1 - mm * x1
        intersection = self.calculateLineIntersection(m, b, mm, bb)

        # 检查边与直线的交点,并判断是否在线段上
        if intersection is not None and len(intersection) == 2:
            x, y = intersection
            if min(x1, x2) <= x and x <= max(x1, x2):
                # 将交点添加到两个部分
                splitPolygon1.append(intersection)
                splitPolygon2.append(intersection)

    return splitPolygon1, splitPolygon2
if __name__ == '__main__':
    @costTime
    def testMatplotlibWaitKey():
        import cv2 as cv
        img1 = cv.imread("../testData/1.jpg")
        img2 = cv.imread("../testData/2.jpg")
        m = MatplotlibWaitKey()
        m.setCurrentCanvas('testMatplotlibWaitKey')
        plt.imshow(img1)
        m.display(block=True)
        plt.imshow(img2)
        m.display(block=True)

    def testDynamicCanvas():
        d=DynamicCanvas("testDynamicCanvas")
        for i in range(100):
            d.addData(i * np.sin(i)*1, "height1")
            d.addData(i * np.sin(i)*2, "weight2")
            d.addData(i * np.sin(i)*3, "weight3")
            d.addData(i * np.sin(i)*4, "weight4")
            d.addData(i * np.sin(i)*5, "weight5")
            d.addData(i * np.sin(i)*6, "weight6")
            d.addData(i * np.sin(i)*7, "weight7")
            d.display()

    rt = ReckonTime("xyp")
    testMatplotlibWaitKey()
    rt.reckon()
    testDynamicCanvas()
    rt.reckon("py")

    print(normalize([1,2,3],0,1))
    t1=[1,2,3]
    t2 = [1, 2, 3]
    xypPrint(t1,t1,t2
             , t2 )
    xypPrint(t1, t1, t2
             ,1+1)

    XypError("XypError")

    img1 = cv.imread("../testData/1.jpg")
    img2 = cv.imread("../testData/2.jpg")

    xypImgShow(img1,
               img2
               )

    g = GetImagePos()
    black = np.zeros((500, 500), dtype=np.uint8)
    white = np.zeros((500, 500), dtype=np.uint8) + 255
    g.getMousePos("black", black)
    g.getMousePos("white", white)
    cv.waitKey()
