# Create time : 2024/1/20 and 21:09

"""
explain:

"""
import threading
import time

from xypALoneData import ALoneData

xypServerData={}
# 发布者 订阅者 多对多
# 发布的内容不应该在发布后内容还发生改变
# 在整个通信过程中，要注意通信数据是共享的，read后要注意如果是修改对象的本身，可能需要用到深拷贝等策略
class Subscribe():
    def __init__(self, subscribeName,channelName):
        if channelName not in xypServerData:
            self.channel = Channel(channelName)
            xypServerData[channelName] = self.channel
        else:
            self.channel = xypServerData[channelName]
        self.channel.subscribe[subscribeName] = self
        self.subscribeName = subscribeName
        self.subscribeChannel = []
        self.lastReadTime = time.time()
        threading.Thread(target=self.protectThread).start()

    def protectThread(self):
        while True:
            if time.time() > self.lastReadTime + 3600:  # 一个小时没有read数据，订阅者出现问题
                self.subscribeChannel = []
            time.sleep(360)

    def read(self, ):
        nowTime = time.time()
        self.lastReadTime = nowTime
        for data in self.subscribeChannel:
            if nowTime > data["outTime"]:  # 应用局部变量nowtime而不是self.lastReadTime
                self.subscribeChannel.pop(0)
            else:
                return self.subscribeChannel.pop(0)
        return None


class Publish():
    def __init__(self, publishName,channelName):
        if channelName not in xypServerData:
            self.channel=Channel(channelName)
            xypServerData[channelName]= self.channel
        else:
            self.channel =xypServerData[channelName]
        self.channelName = channelName

        self.channel.publish[publishName] = self
        self.publishName = publishName
        self.channelLock = self.channel.channelLock
        self.subscribe =  self.channel.subscribe

    def publish(self, data, copyFlag=False, outTime=3600):
        # outTime,消息超时没有接受删除的时间，单位s
        with self.channelLock:
            data =  {"publishName": self.publishName, "channel": self.channelName,"publishData":  data, "outTime": time.time() + outTime}
            # print(data)
            for client in self.subscribe.values():
                client.subscribeChannel.append(data)





class Channel():
    def __init__(self,channelName ):
        self.channelName=channelName
        self.publish = {}  # 记录发布者
        self.subscribe = {}  # 记录订阅者
        self.channelLock = ALoneData(None) # 对于一个通道，同一时刻只有一个发布者，且发布的时候不能更改发布者和订阅者对象

    def createPublish(self, publishName):
        with self.channelLock:
            p = Publish(publishName, self.channelName)

            return p

    def createSubscribe(self, subscribeName):
        with self.channelLock:
            s = Subscribe(subscribeName,self.channelName)
            return s

    def removePublish(self, publishName):
        with self.channelLock:
            self.publish.pop(publishName)

    def removeSubscribe(self, subscribeName):
        with self.channelLock:
            self.subscribe.pop(subscribeName)


class Server():
    def createChannel(self,channelName):
        c= Channel(channelName)
        xypServerData[channelName] = c
        return c

if __name__ == "__main__":
    s = Server()
    # c = s.createChannel("dar")
    p1 = Publish("p1","dar")
    s1 = Subscribe("s1","dar")


    # time.sleep(1)
    print(s1.read(),"22")
    p1.publish("1")
    print(s1.read(),"22")

    p1.publish("2")
    print(s1.read(),"22")

    #
    # c.p():
    #
    # s = a.subscribe("name")
    #
    #
    # if s.read():
    #     xxx




