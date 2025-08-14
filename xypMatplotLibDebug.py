from xypDebugConfig import matplotlibDeBugFlag
if matplotlibDeBugFlag:
    from pylab import mpl
    import matplotlib.pyplot as plt
    mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # matpotlib显示中文字体

def matScatter(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.scatter(*args, **kwargs)
def matPlot(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.plot(*args, **kwargs)
def matLegend(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.legend(*args, **kwargs)
def matFigure(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.figure(*args, **kwargs)

def matSubplot(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.subplot(*args, **kwargs)

def matSubplots(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.subplots(*args, **kwargs)

def xypMatSubplots(*args, **kwargs): # 多了个figName的参数
    if matplotlibDeBugFlag:
        if "figName" in kwargs.keys():
            figName = kwargs.pop("figName")
            fig,ax =  plt.subplots(*args, **kwargs)
            figManager = plt.get_current_fig_manager()
            figManager.set_window_title(figName)
            return (fig,ax)
        else:
            return plt.subplots(*args, **kwargs)

def xypMatClf(figName): # 按名字清除画布
    if matplotlibDeBugFlag:
        if isinstance(figName,(str,int)):
            plt.figure(figName)
            plt.clf()
        elif isinstance(figName, (list,set,tuple)):
            for n in figName:
                plt.figure(n)
                plt.clf()

def xypMatClose(figName):  # 按名字关闭画布
    if matplotlibDeBugFlag:
        if isinstance(figName, (str, int)):
            plt.figure(figName)
            plt.close()
        elif isinstance(figName, (list, set, tuple)):
            for n in figName:
                plt.figure(n)
                plt.close()

def matPause(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.pause(*args, **kwargs)

def matClf(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.clf(*args, **kwargs)
def matShow(*args, **kwargs):
    if matplotlibDeBugFlag:
        return plt.show(*args, **kwargs)

if __name__ == "__main__":
    pass
