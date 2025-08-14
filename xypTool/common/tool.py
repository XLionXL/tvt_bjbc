import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches

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
class DynamicCanvas():
    # 用法示例：
    # 第一步：创建类的实例d
    # 第二步：d.addData(1.2,"weight")，添加数据
    # 第三步：d.display 绘制内容并显示
    # 第四步：双击可以聚焦当前位置，再次双击可结束聚焦
    # 不建议指定名字为数字的画布，因为指定为字符串时也会默认按序号给予一个数字名字，可能会冲突
    def __init__(self, figName, maxHistoryNum=None):
        # 创建画布
        self.figName =figName
        self.blockFlag = False
        self.maxHistoryNum =maxHistoryNum
        self.fig = plt.figure(figsize=(4, 3), num=self.figName )
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
    def display(self, key=None):
        '''
        key：指定要画的数据
        '''
        plt.figure(self.figName)
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
    不建议指定名字为数字的画布，因为指定为字符串时也会默认按序号给予一个数字名字，可能会冲突
    '''
    def __init__(self,):
        self.blockFlag = True
        self.currentCanvas = None
        self.figName = [] # 记录当前创建的画布
        self.fistTimeDisplay= False


    def setCurrentCanvas(self,canvasName):
        self.fig = plt.figure(canvasName) # 创建或更换当前画布
        if canvasName not in self.figName: #防止重复操作
            # button_release_event 预定义事件类型，表示鼠标按钮点击事件
            self.fig.canvas.mpl_connect('button_press_event', self.buttonPressCallback) # 前面字符串是固定的
            self.figName.append(canvasName)  # 记录当前创建的画布
            self.fistTimeDisplay = True

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
            if self.fistTimeDisplay:
                plt.pause(0.001)
                self.fistTimeDisplay=False
            else:
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
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
