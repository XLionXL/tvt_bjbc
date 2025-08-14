'''用于保证某个数据同一时刻只能有一个线程使用
使用方法：
c = ALoneData(data)
with c as d:
    print(d)
或者
c = ALoneData(data)
d=c.occupy()
print(d)
c.release()
注意该类是互斥锁结构，同一线程不能重复调用，不然会出现死锁
多个锁的时候要注意顺序：
with a:
    with b:
别的地方用锁要注意
也是
with a:
    with b:
而不是
with b:
    with a:
注意：该方法只浅保护

c = ALoneData([[1],[2]])
with c as d:
在使用c的时候别的地方[2]，变成了[3]
c也是被改的

因此正确的用法是：对于数据d，以及内部的子元素
都应只在with c as d:下修改

当然，考虑上计算问题本类不支持真正意义上的保护，只是一种约定写法
with xxx，表示占用了xxx资源，其他地方不可调用

然后通用用get 和 set获取与设置xxx
为了防止get set的误用，假如了applyKey
当然如果有信心，可以直接用+=之类的处理而不是用set，一般情况下，最好用set，+=的处理该类没有监测机制，可能会有风险


'''
import inspect
import threading
import time


class ALoneData():
    def __init__(self,data,dataName = None):
        self.data = data
        self.dataName = dataName
        self.dataLock = True
        self.applyDataTask = [] # 数据申请使用的队列
        self.getData = None # 以变量形式，在没有occupy时使用了的话可以报错起到提醒作用
        self.setData = None # 以变量形式，在没有occupy时使用了的话可以报错起到提醒作用
    def _getData(self):
        return self.data
    def _setData(self,data):
        self.data=data

    def __enter__(self,):
        return self.occupy()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def occupy(self,):
        applyTime = time.time()
        applyKey = str(applyTime) + str(threading.current_thread().ident)  # 唯一调用秘钥
        self.applyDataTask.append(applyKey)
        while True:
            if self.dataLock:  # 解锁
                if  self.applyDataTask[0] == applyKey:  # 唯一调用id
                    self.dataLock = False  # 先关锁
                    self.applyDataTask.pop(0)  # 再移除
                    self.applyKey = applyKey
                    # try:
                    #     callerFrame = inspect.currentframe().f_back
                    #     fileName = inspect.getframeinfo(callerFrame).filename
                    #     lineno = inspect.getframeinfo(callerFrame).lineno
                    #     if "xypALoneData" in fileName : #__enter__调用的
                    #         callerFrame = inspect.currentframe().f_back.f_back
                    #         fileName = inspect.getframeinfo(callerFrame).filename
                    #         lineno = inspect.getframeinfo(callerFrame).lineno
                    #     print(f"最新占用数据 {self.dataName} 的对象: {fileName} {lineno}")
                    # except Exception as e:
                    #     print(e)

                    self.getData = self._getData
                    self.setData = self._setData
                    return   self
            time.sleep(0.1)
            if time.time() - applyTime > 10:
                try:
                    callerFrame = inspect.currentframe().f_back
                    fileName = inspect.getframeinfo(callerFrame).filename
                    lineno = inspect.getframeinfo(callerFrame).lineno
                    if "xypALoneData" in fileName:  # __enter__调用的
                        callerFrame = inspect.currentframe().f_back.f_back
                        fileName = inspect.getframeinfo(callerFrame).filename
                        lineno = inspect.getframeinfo(callerFrame).lineno
                    print(f"occupy data error, 长时间未占用到数据, 死锁可能产生, 等待占用数据 {self.dataName} 的对象: {fileName} {lineno}")
                except Exception as e:
                    print(e)
                # 等待过长时间，可能死锁产生，可将上面注释掉的代码取消注释，找到最近一次调用的地方进行debug

    def release(self,):
        if self.dataLock:  # 释放锁时锁是开着的，说明程序有问题
            print("release data error, dataName {self.dataName}")
        else:
            self.getData = None
            self.setData = None
            self.dataLock = True  # 解锁



if __name__=="__main__":
    def t1():
        while True:
            with a as d:
                data = d.getData()
                data.append("X")
                time.sleep(0.1)


    def t2():
        while True:
            with a as d:
                data = d.getData()
                for i in range(1, 10):
                    data.append(i)


    def t3():
        while True:
            d = a.occupy()
            print(d.getData())
            a.release()
    data=[1,2,3]
    a = ALoneData(data)
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()
    threading.Thread(target=t3).start()
    time.sleep(33332)


