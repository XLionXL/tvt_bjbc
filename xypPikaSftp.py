import datetime
import json
import os.path
import cv2 as cv
from xypTool.debug import xypLog
from io import BytesIO

defenceData = {
    "algorithmCode": "111",
    "areaState": 1,
    "sendTime": "2025-02-25 15:40:28"
}
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
# xypRemoteByPycharm = True  # 在远程调试环境配置失败时可用
# if xypRemoteByPycharm:
#     result = subprocess.check_output(['python3', '-m', 'site']).decode('utf-8')
#     # subprocess.check_output(['cp', '/usr/bin/zipx/zj-guard/config', '/ssd/xyp/xypTest/config'])
#     siteList = re.findall(r"'.*'", result)
#     for site in siteList:
#         xypLog.xypDebug(site[1:-1])
#         sys.path.append(site[1:-1])
import paramiko
import pika
import threading
import time
import traceback
import io
import cv2 as cv
import requests
import os
import mimetypes  # 正确导入mimetypes模块



def upload_file(file_path, company_name="tvt", url = "http://10.29.3.3:10010/minIo/uploadToMinIo"):
    try:
        with open(file_path, 'rb') as file:
            # 获取基础文件名
            filename = os.path.basename(file_path)

            # 自动检测MIME类型
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'  # 设置默认类型

            # 构建文件参数（包含检测到的MIME类型）
            files = {
                'file': (filename, file, mime_type)
            }
            data = {'company': company_name, 'date':datetime.datetime.now().strftime('%Y%m%d')}

            # 发送请求
            response = requests.post(url, files=files, data=data)

            # 处理响应
            if response.status_code == 200:
                return True
            else:
                return False

    except requests.exceptions.RequestException as e:
        return False
    except Exception as e:
        return False

from common_FileLoadSave import File_Saver_Loader_json
# from minio import Minio
#
#
# class MINIO():
#     def __init__(self, contentType, MaxRetransmission=3, ):
#         self.contentType = contentType
#         self.MaxRetransmission = MaxRetransmission
#         self.errorNum = 0
#         # 设置MinIO服务器的连接信息
#
#         self.client = Minio(
#             "10.29.3.3:19000",
#             access_key="briXF4NLf850dKii",
#             secret_key="x7DPW8exf6enLbBTzvVfOhHSjzue7bpZ",
#             secure=False  # 如果MinIO服务器启用了TLS/SSL，将此选项设置为True
#         )
#
#     def minioPut(self, localFilePath, remoteFilePath, *args, **kwargs):
#         xypLog.xypDebug(f"minioPut start {localFilePath} >>> {remoteFilePath}", self.contentType)
#         for idx in range(self.MaxRetransmission):  # 重传次数
#             try:
#                 if "image" in self.contentType:
#                     img = cv.imread(localFilePath)
#                     # 将OpenCV的图像数组转换为PIL图像对象
#                     img = Image.fromarray(img)
#                     img = img.resize((1920, 1080))
#                     # 添加文字
#                     font = ImageFont.truetype(r"./config/SIMSUN.ttf", 60)
#                     draw = ImageDraw.Draw(img)
#                     draw.text((10, 1010), "周界入侵报警系统", fill=(255, 255, 255), font=font)
#                     _, encoded_image = cv.imencode(".jpg", np.array(img))
#                     imageData = encoded_image.tobytes()
#                     self.client.put_object(
#                         "zj-test",
#                         remoteFilePath,
#                         io.BytesIO(imageData),
#                         len(imageData),  # 指定处理后的图像文件大小
#                         content_type=self.contentType
#                         # 设置内容类型，确保正确识别图片格式
#                     )
#                 else:
#                     self.client.fput_object(
#                         "zj-test",
#                         remoteFilePath,
#                         localFilePath,
#                         content_type=self.contentType  # 设置内容类型，确保正确识别图片格式
#                     )
#                 xypLog.xypDebug(f"minioPut done {localFilePath} >>> {remoteFilePath}")
#                 self.errorNum = 0
#                 return True
#             except Exception as e:
#                 xypLog.xypError(
#                     f"minioPut error {idx} {localFilePath} >>> {remoteFilePath},exception:{e}\ntraceback:{traceback.format_exc()}")
#         xypLog.xypDebug(f"minioPut error {localFilePath} >>> {remoteFilePath}, retransmission exceed limit")
#         self.errorNum += 1
#         if self.errorNum > 5:
#             self.errorNum = 0
#             try:
#                 self.client = Minio(
#                     "10.29.3.3:19000",
#                     access_key="briXF4NLf850dKii",
#                     secret_key="x7DPW8exf6enLbBTzvVfOhHSjzue7bpZ",
#                     secure=False  # 如果MinIO服务器启用了TLS/SSL，将此选项设置为True
#                 )
#                 xypLog.xypDebug("minio error , restart minio ")
#             except Exception as e:
#                 xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
#         return False


class DeviceControlForBeiJing():
    # 机制应该用self.deviceInfo存储所有信息，修改或者读取时都从中读写
    def __init__(self, imageAreaHandle, radarDataHandle, infer, heart):
        self.deviceInfoLock = threading.Lock()
        self.imageAreaHandle = imageAreaHandle
        self.infer = infer
        self.radarDataHandle = radarDataHandle
        self.heart = heart

        self.deviceInfo = {
            "companyCode": "203",
            "lineInfo": "L201",  # 线路信息
            "cameraChannelId": "43000000001310000052",  # 摄像机通道号
            "cameraDeviceId": "43000000001110000002",  # 摄像机设备编号
            "deviceId": "122",  # 字符串设备ID(uuid)
            "position": "K8+",  # 报警位置k 公里标 + 米
        }

        self.lastSetDefenceStatus = None  # 防止多次接收
        self.mq_config = Rabbitmq_Config(config_file_path=os.path.join(".", "config", "rabbitmq_config.json"))
        self.alarmEnable = self.mq_config.alarmEnable
        xypLog.xypDebug(f"self.mq_config {self.mq_config.data_dict}")

        # rabbitmq配置
        credentials = pika.PlainCredentials(self.mq_config.mq_user, self.mq_config.mq_pw)  # mq用户名和密码
        # 虚拟队列需要指定参数 virtual_host，如果是默认的可以不填。
        self.connection_parameters = pika.ConnectionParameters(host=self.mq_config.mq_ip,
                                                               port=self.mq_config.mq_port,
                                                               virtual_host='/', credentials=credentials)


        # rabbitmq监听初始化
        self.listenStateRes = None
        self.listenAlarmRes = None
        self.listenCommandRes = None
        # 心跳上报相关
        threading.Thread(target=self.createListen, args=("EQUIPMENT_STATUS_CONFIRM_EXCHANGE", "TVT_EQUIPMENT_STATUS_QUEUE", self.listenCallback), name="TVT_EQUIPMENT_STATUS_QUEUE").start()
        # 布撤防指令下发相关
        threading.Thread(target=self.createListen, args=("SIMULATION_COMMAND_EXCHANGE", "TVT_COMMAND_QUEUE", self.listenCallback), name="TVT_COMMAND_QUEUE").start()
        # 报警消息确认回执相关
        threading.Thread(target=self.createListen, args=("SIMULATION_ALARM_CONFIRM_EXCHANGE", "TVT_ALARM_CONFIRM_QUEUE", self.listenCallback), name="TVT_ALARM_CONFIRM_QUEUE").start()

        # sftp 初始化
        self.imageTask = []
        self.videoTask = []

        # self.imageTaskHandle = MINIO("image/jpeg")
        # self.videoTaskHandle = MINIO("video/mp4")


        threading.Thread(target=self.imageTaskThread, daemon=True, name='imageTaskThread').start()
        threading.Thread(target=self.videoTaskThread, daemon=True, name='videoTaskThread').start()
        # threading.Thread(target=self.sendDeviceStatus, daemon=True, name='sendDeviceThread').start()

        self.alarmInfoRecord = {}  # 断电闭环，即之前发了12必须有3
        self.msgTask = self.safetySend()  # 断电重启检查,记录报警未发送成功的数据
        self.msgTask = []
        threading.Thread(target=self.sendInfoThread, daemon=True, name='sendInfoThread').start()



    def safetySend(self):
        # 发送成功删除
        try:
            alarmSafetySendQueue = []
            with open('./config/safetySend.txt', 'r') as f:
                txt = f.read()
                if txt:
                    data = eval(txt)
                    for alarmInfo in data.values():
                        if alarmInfo["alarmStatus"] != "3":
                            nowTime= datetime.datetime.now()  # 上传时间
                            outagePath = f"/usr/bin/zipx/zj-guard/config/outage.jpg"
                            newOutageName= f"{nowTime.strftime('%Y-%m-%d_%H-%M-%S')}_outage.jpg"
                            remotePath = f"{os.path.dirname(alarmInfo['pvList'][0]['url'])}/{newOutageName}"
                            alarmInfo["alarmStatus"] = "3"
                            alarmInfo["callTime"] =nowTime.strftime('%Y-%m-%d %H:%M:%S')
                            alarmInfo["id"]= f"sbtx_hmbld_event_{nowTime.strftime('%Y%m%d%H%M%S')}",  # 报警消息id
                            alarmInfo["pvList"][0]["url"] = remotePath
                            alarmInfo["pvList"][0]["alarmVideo"] = ''
                            alarmSafetySendQueue.append(("alarm",alarmInfo))
                            self.addTask(outagePath,"/".join(remotePath.split("/")[-4:]))
                            print(f"outagePath:{outagePath}")
            xypLog.xypDebug(f"safetySend load done: {alarmSafetySendQueue}")
            with open('./config/safetySend.txt', 'w') as f:
                pass
            return alarmSafetySendQueue
        except:
            xypLog.xypDebug(f"safetySend error: {traceback.format_exc()}")
            # with open('./config/safetySend.txt', 'w') as f:
            #     pass
            return []



    def listenCallback(self, channel, deliver, properties, body):
        # xypLog.xypDebug(channel,"\n")
        # xypLog.xypDebug(deliver, "\n")
        # xypLog.xypDebug(properties, "\n")
        # xypLog.xypDebug(body.decode())
        # xypLog.xypDebug("=====================")
        # pass
        msg = None
        try:
            exchange = deliver.exchange
            msg = json.loads(body.decode())
            if exchange == "EQUIPMENT_STATUS_CONFIRM_EXCHANGE":
                if msg["algorithmCode"] == "116":
                    xypLog.xypDebug(channel, "\n")
                    xypLog.xypDebug(deliver, "\n")
                    xypLog.xypDebug(properties, "\n")
                    xypLog.xypDebug("listen EQUIPMENT_STATUS_CONFIRM_EXCHANGE", msg)
                    self.listenStateRes = msg
                    channel.basic_ack(delivery_tag=deliver.delivery_tag)
            elif exchange == "SIMULATION_ALARM_CONFIRM_EXCHANGE":
                if msg["alarmId"][:4] == "sbtx":
                    xypLog.xypDebug(channel, "\n")
                    xypLog.xypDebug(deliver, "\n")
                    xypLog.xypDebug(properties, "\n")
                    xypLog.xypDebug("listen SIMULATION_ALARM_CONFIRM_EXCHANGE", msg)
                    self.listenAlarmRes = msg
                    channel.basic_ack(delivery_tag=deliver.delivery_tag)
            elif exchange == "SIMULATION_COMMAND_EXCHANGE":
                if msg["algorithmCode"] == "116":
                    xypLog.xypDebug(channel, "\n")
                    xypLog.xypDebug(deliver, "\n")
                    xypLog.xypDebug(properties, "\n")
                    xypLog.xypDebug("listen SIMULATION_COMMAND_EXCHANGE", msg)
                    """
                    {
                    "algorithmCode":"116",
                    "areaState":1,
                    "sendTime":"2025-02-25 15:40:28"
                    }"""
                    self.listenCommandRes = msg
                    self.setDefenceStatus(msg)
                    channel.basic_ack(delivery_tag=deliver.delivery_tag)
        except:
            xypLog.xypDebug(f"listenCallback error {msg}")
            traceback.print_exc()

    def createListen(self, exchange, queue, callback):
        while True:  # 因为是广播的形式，如果其他消费者没ack导致ack超时，该部分30min会被杀一次，所有要while True。
            try:
                # pika不是线程安全的，每个线程里都应该有个connection
                connection = pika.BlockingConnection(self.connection_parameters)
                channel = connection.channel()
                channel.exchange_declare(exchange=exchange, exchange_type='fanout', durable=True)
                channel.queue_declare(queue=queue, durable=True)
                channel.queue_bind(exchange=exchange, queue=queue)
                channel.queue_purge(queue)
                channel.basic_consume(queue, callback)
                channel.start_consuming()
            except:
                # xypLog.xypDebug(f"listen error:{traceback.format_exc()}")
                time.sleep(1)

    def setDefenceStatus(self, data):  # 防区布防撤防
        # {
        # "algorithmCode":"111",
        # "areaState":1,
        # "sendTime":"2025-02-25 15:40:28"
        # }
        if self.lastSetDefenceStatus is not None and self.lastSetDefenceStatus["algorithmCode"] == data["algorithmCode"] and \
                self.lastSetDefenceStatus["areaState"] == data["areaState"]:  # 防止重复设置
            # 回复
            data["sendTime"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # msg = json.dumps(data).encode('utf-8')
        else:
            # 使防区失活
            self.lastSetDefenceStatus = data
            imageAreaData = self.imageAreaHandle.imageAreaData
            # if data["areaCode"] == "0":
            for area in imageAreaData:
                area["enable"] = data["areaState"]
            # else:
            #     for area in imageAreaData:
            #         # if int(data["areaCode"]) == area["areaId"]:
            #         area["enable"] = data["areaState"]
            self.imageAreaHandle.areaSet(imageAreaData)
            
            self.radarDataHandle.radarAreaEnable=data["areaState"]
            # 仅不发送报警给rabbitmq
            self.alarmEnable = data["areaState"]
            self.mq_config.data_dict["alarmEnable"] = data["areaState"]
            self.mq_config.config_file_handler.save_to_file(self.mq_config.data_dict)
            data["sendTime"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # msg = json.dumps(data).encode('utf-8')
        self.msgTask.append(("defence",data))




    def sendDeviceStatus(self):
        
        # data={
        #     "algorithmCode": "111",
        #     "algorithmState": 0,
        #     "failureCause": "雷达故障",
        #     "sendTime": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #     }

        # imageAreaData = self.imageAreaHandle.imageAreaData
        # sendData = []
        # for area in imageAreaData:
        #     sendData.append({"areaCode": area["areaId"], "areaState": area["enable"]})
        # data = {"companyCode": self.deviceInfo["companyCode"],  # 厂家编码
        #         "deviceId": self.deviceInfo["deviceId"],  # 字符串        设备ID(uuid)
        #         "deviceState": 1,  # 离线和在线。

        #         "failureCause": "0" if (self.infer.is_infer_online() and self.heart.check_radar_isOk()) else "1", # 耗时慢
        #         "failureCause": "0",
        #         # 离线和在线。

        #         "area": sendData,  # 1 为布防，0 为撤防。
        #         "sendTime": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # 发送时间字符串
        #         }
        # while True:
        data={
            "algorithmCode": "116",
            "algorithmState": 1,
            "failureCause": "" if (self.infer.is_infer_online() and self.heart.check_radar_isOk()) else "雷达故障",
            "sendTime": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        self.msgTask.append(("status", data))  # 添加发送的数据
            # time.sleep(60)


    def getRemotePath(self, dataPath):
        if ".jpg" in dataPath:
            return f"file-server/tvt/image/{os.path.basename(os.path.dirname(dataPath)).replace('-','')}/{os.path.basename(dataPath)}"
        else:
            return f"file-server/tvt/video/{os.path.basename(os.path.dirname(dataPath)).replace('-','')}/{os.path.basename(dataPath)}"
        # return f"http://10.29.3.3:19001/zj-test/{os.path.basename(dataPath)}"

    def sendAlarmInfo(self, areaId, alarmLevel, alarmState, alarmType, imagePath, videoPath, alarmSrcFile, position):
        if self.alarmEnable:
            less = [(40, 45), (90, 95), (140, 145), (190, 195)]
            more = [(55, 60), (105, 110), (155, 160), (205, 210)]
            for l, m in zip(less, more):
                if l[0] <= position <= l[1]:
                    position = l[1]
                    break
                elif m[0] <= position <= m[1]:
                    position = m[0]
                    break

            nowTime = datetime.datetime.now()
            if alarmState == 1:
                self.lastAlarmId = nowTime
            # alarmInfo = {
            #     "alarmEventId": f"sbtx_hmbld_alarm_{self.lastAlarmId.strftime('%Y%m%d%H%M%S')}",  # 报警事件id
            #     "alarmStatus": str(alarmState),  # 报警状态 1开始 2进行中 3结束
            #     "boxId": self.deviceInfo["deviceId"],  # 对应设备ID
            #     "callAlgo": self.deviceInfo["companyCode"],  # 对应厂家ID
            #     "callTime": nowTime.strftime('%Y-%m-%d %H:%M:%S'),  # 报警时间
            #     "callType": "201",  # 报警类别 201人员、202大型动物、203落石、204泥石流、205水漫、206其他
            #     "id": f"sbtx_hmbld_event_{nowTime.strftime('%Y%m%d%H%M%S')}",  # 报警消息id
            #     "position": self.deviceInfo["position"] + str(int(position)),  # 报警位置k公里标 + 米
            #     "callContent": f"sbtx_{self.deviceInfo['position'] + str(int(position))}_201",
            #     # 报警内容 什么设备  于什么位置发生了什么类型的入侵

            #     "lineInfo": self.deviceInfo["lineInfo"],  # 线路信息

            #     "callEvent": "1",  # 报警事件
            #     "callLevel": str(alarmLevel),  # 报警级别
            #     "callSource": "2",  # 报警来源
            #     "callState": "0",  # 报警状态 0未确认 1已确认 2误报 5关联预警
            #     "channelId": self.deviceInfo["cameraChannelId"],  # 摄像机通道号
            #     "deviceId": self.deviceInfo["cameraDeviceId"],  # 摄像机设备编号
            #     "zone": str(areaId),  # 防区位置
            #     "type": "alarm",

            #     "cloudMessage": [  # 云端异物坐标
            #         {"boxMessage": [{"box": "909,744,909,772,951,744,951,772",  # 矩形框，每个按照左上左下右上右下排列
            #                          "category": "1",  # 1 - 落石，2 - 人员，3 - 水漫、4 - 泥土、5 - 大型动物、6 - 过车
            #                          "confidence": "0.99935669"  # 可信度
            #                          }],
            #          "code": "91",  # 颜色
            #          "colour": "(37,176,186)",  # 云端算法厂商名称
            #          "name": "时变通讯"  # 云端算法厂商编码
            #          }],

            #     "pvList": [
            #         {
            #             "alarmVideo": "http://10.29.3.3:19000/zj-test/" + self.getRemotePath(videoPath),  # 视频地址
            #             "alarmSrcFile": "",  # 点云地址
            #             "image": None,  # 原始图片地址
            #             "saveImage": None,  # 原始图片地址
            #             "type": "0",  # 传输类型  0是图片
            #             "url": "http://10.29.3.3:19000/zj-test/" + self.getRemotePath(imagePath)  # 图片地址
            #         }],

            #     "uploadMessage": [
            #         {"box": None,  # 矩形框，每个按照左上左下右上右下排列
            #          "category": "201",  # 报警类别
            #          "confidence": None  # 可信度

            #          }
            #     ]
            # }
            alarmInfo = {
                        "companyCode": "106",
                        "algorithmCode": "116",
                        "alarmState": int(alarmState),
                        "alarmId": f"sbtx_alarm_{self.lastAlarmId.strftime('%Y%m%d%H%M%S')}",  # 报警事件id,
                        "alarmEventId": f"sbtx_event_{self.lastAlarmId.strftime('%Y%m%d%H%M%S')}",
                        "position": self.deviceInfo["position"] + str(int(position)),
                        "alarmLevel": int(alarmLevel),
                        "alarmType": "人员",
                        "alarmTime": str(nowTime.strftime('%Y-%m-%d %H:%M:%S')),
                        "alarmVideo": "http://10.29.3.3:19000/" + self.getRemotePath(videoPath),
                #http://10.29.3.3:19000/file-server/tvt/image/20250324/2025-03-24_14-33-26_i000008_d176.6_a4_w1_s2.jpg
                        "alarmImage": "http://10.29.3.3:19000/" + self.getRemotePath(imagePath),

                        }
            self.msgTask.append(("alarm", alarmInfo))  # 添加发送的数据


    def sendInfoThread(self):
        while True:
            try:
                connection = pika.BlockingConnection(self.connection_parameters)

                # 心跳上报
                areaChannel = connection.channel()
                areaChannel.queue_declare(queue='SIMULATION_EQUIPMENT_STATUS_QUEUE', durable=True)
                areaChannel.queue_purge('SIMULATION_EQUIPMENT_STATUS_QUEUE')
                areaChannel.queue_bind(queue="SIMULATION_EQUIPMENT_STATUS_QUEUE", exchange="SIMULATION_EXCHANGE",
                                    routing_key="SIMULATION_EQUIPMENT_STATUS_ROUTINGKEY")
                areaChannel.confirm_delivery()  # 检测是否发送成功
                # 布撤防上报
                stateChannel = connection.channel()
                stateChannel.queue_declare(queue='SIMULATION_COMMAND_CONFIRM_QUEUE', durable=True)
                stateChannel.queue_purge('SIMULATION_COMMAND_CONFIRM_QUEUE')
                stateChannel.queue_bind(queue="SIMULATION_COMMAND_CONFIRM_QUEUE", exchange="SIMULATION_EXCHANGE",
                                        routing_key="SIMULATION_COMMAND_CONFIRM_ROUTINGKEY")
                stateChannel.confirm_delivery()  # 检测是否发送成功
                # 报警信息上报
                alarmChannel = connection.channel()
                alarmChannel.queue_declare(queue='SIMULATION_ALARM_QUEUE', durable=True)
                alarmChannel.queue_purge('SIMULATION_ALARM_QUEUE')
                alarmChannel.queue_bind(queue="SIMULATION_ALARM_QUEUE", exchange="SIMULATION_EXCHANGE",
                                        routing_key="SIMULATION_ALARM_ROUTINGKEY")
                alarmChannel.confirm_delivery()  # 检测是否发送成功

                waitNum = 0
                while True:
                    taskNum = len(self.msgTask)
                    # print(f"---------------{taskNum}---------------------")
                    if taskNum > 1000:
                        self.msgTask = []  # 断网过长，重置
                        xypLog.xypDebug(f"network error too long ,clear alarmInfoTask")
                    elif taskNum == 0:
                        waitNum += 1
                        waitNum = min(waitNum, 10)
                        time.sleep(0.1 * waitNum)
                    else:
                        waitNum = 0

                        for msgIdx in range(taskNum):
                            msgType, msg = self.msgTask[0]
                            msgBytes = json.dumps(msg).encode('utf-8')
                            xypLog.xypDebug(f"rabbitmq send {msgType} {msgIdx}: {msg}")
                            if msgType == "alarm":
                                alarmChannel.basic_publish(exchange='SIMULATION_EXCHANGE',
                                                                routing_key='SIMULATION_ALARM_ROUTINGKEY',
                                                                body=msgBytes)
                                self.msgTask.pop(0)  # 发送成功删除
                                evenId = msg["alarmEventId"]
                                self.alarmInfoRecord[evenId] = msg  # 记录事件evenId发送的历史
                                if self.alarmInfoRecord[evenId]["alarmState"] == "3":  # 事件evenId发送到了3的话
                                    self.alarmInfoRecord.pop(evenId)
                                with open('./config/safetySend.txt', 'w') as f:
                                    f.write(str(self.alarmInfoRecord))
                            elif msgType == "status":
                                stateChannel.basic_publish(exchange='SIMULATION_EXCHANGE',
                                                                routing_key='SIMULATION_EQUIPMENT_STATUS_ROUTINGKEY',
                                                                body=msgBytes)
                                self.msgTask.pop(0)  # 发送成功删除
                            elif  msgType == "defence":
                                areaChannel.basic_publish(exchange='SIMULATION_EXCHANGE',
                                                               routing_key='SIMULATION_COMMAND_CONFIRM_ROUTINGKEY',
                                                               body=msgBytes)
                                self.msgTask.pop(0)  # 发送成功删除
                            xypLog.xypDebug(f"rabbitmq send {msgType} {msgIdx} done")
                            time.sleep(0.2)  # 缓解cpu压力
            except Exception as e:
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")


    def addTask(self, dataPath,remotePath=None):
        if dataPath.endswith(".jpg"):
            if remotePath is not None:
                self.imageTask.append((time.monotonic(), dataPath,remotePath))
            else:
                self.imageTask.append((time.monotonic(), dataPath, self.getRemotePath(dataPath)))
            xypLog.xypDebug(f"imageTask add: {len(self.imageTask)}")
        else:
            self.videoTask.append((time.monotonic(), dataPath, self.getRemotePath(dataPath)))
            xypLog.xypDebug(f"videoTask add: {len(self.videoTask)}")

    def imageTaskThread(self):
        xypLog.xypDebug(f"imageTaskThread start")
        while True:
            try:
                if len(self.imageTask) == 0:
                    time.sleep(1)
                else:
                    startTime = time.monotonic()
                    timeStamp, localFilePath, remoteFilePath = self.imageTask[0]
                    # 等待文件创建3s+等待写入完毕3s，一个文件最多等待6s
                    # 因为写入程序和该程序是不同的进程，time.sleep(max(3 - pastTime, 0))，是对imageTask的所有文件生效的，因此该逻辑是稳健的
                    if startTime - timeStamp < 3600 * 24:  # 24小时的文件
                        # 等待文件创建
                        while time.monotonic() - startTime < 3:
                            if not os.path.exists(localFilePath):
                                time.sleep(0.1)
                            else:
                                break

                        if not os.path.exists(localFilePath):  # 文件生成失败
                            self.imageTask.pop(0)
                            xypLog.xypDebug(
                                f"imageTaskThread error, not such file: {localFilePath}, spend time:{time.monotonic() - startTime}")
                        else:
                            # 等待文件写入完毕
                            pastTime = time.time() - os.path.getmtime(localFilePath)
                            time.sleep(min(max(3 - pastTime, 0),3)) # min 防止异常
                            # 上传到远程位置
                            res = upload_file(localFilePath)
                            if res:  # 文件传输成功
                                self.imageTask.pop(0)
                                # with open("log.txt", "a") as f:
                                #     f.write(f"{localFilePath}上传成功\n")
                            # else:
                            #     with open("log.txt", "a") as f:
                            #         f.write(f"{localFilePath},网络断开,没有上传成功\n")
                                # print(f"{localFilePath},网络断开,没有上传成功")
                    else:
                        self.imageTask.pop(0)  # 文件超时
                        xypLog.xypDebug(f"imageTaskThread delete task: {localFilePath} >>> {remoteFilePath}")
            except Exception as e:
                xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
                time.sleep(2)

    def videoTaskThread(self):
        xypLog.xypDebug(f"videoTaskThread start")
        while True:
            # try:
            if len(self.videoTask) == 0:
                time.sleep(1)
            else:
                startTime = time.monotonic()
                timeStamp, localFilePath, remoteFilePath = self.videoTask[0]
                # 等待文件创建5s+等待写入完毕10s，一个文件最多等待15s
                # 因为写入程序和该程序是不同的进程，time.sleep(max(10 - pastTime, 0))，是对videoTask的所有文件生效的，因此该逻辑是稳健的
                if startTime - timeStamp < 3600 * 24:
                    # 等待文件创建
                    while time.monotonic() - startTime < 5:
                        if not os.path.exists(localFilePath):
                            time.sleep(0.1)
                        else:
                            break
                    if not os.path.exists(localFilePath):  # 文件生成失败
                        self.videoTask.pop(0)
                        xypLog.xypDebug(
                            f"sftp error, not such file: {localFilePath}, spend time:{time.monotonic() - startTime}")
                    else:
                        # 等待文件写入完毕
                        pastTime = time.time() - os.path.getmtime(localFilePath)
                        time.sleep(min(max(10 - pastTime, 0),10))# min 防止异常
                        # 上传到sftp远程位置
                        res = upload_file(localFilePath)
                        if res:  # 文件传输成功
                            self.videoTask.pop(0)


                else:
                    self.videoTask.pop(0)  # 文件超时
                    xypLog.xypDebug(f"videoTaskThread delete task: {localFilePath} >>> {remoteFilePath}")
            # except Exception as e:
            #     xypLog.xypError(f"exception:{e}\ntraceback:{traceback.format_exc()}")
            #     time.sleep(2)


class Rabbitmq_Config:
    def __init__(self, config_file_path=os.path.join(".", "config", "rabbitmq_config.json")):
        self.data_dict = {
            "companyCode": "203",
            "deviceId": "10220801162200",
            "algorithmCode": "122",
            "areaCode": "47",
            "area_enable": 1,
            "companyAlarmId": "123",  # 生成唯一id
            "position": "K8+",  # 报警位置k 公里标 + 米
            "companyAlarmDate": "2022-04-15 15:49:00",  # 按这个格式传时间
            "alarmVideo": "/bjjw/20220801/bjjw_101_31_20220801162200.mp4",  # 视频保存为h264编码，要求不带红框，根据文件名具体变化。
            "alarmImage": "/bjjw/20220801/bjjw_101_31_2022080116220100.jpg",  # 报警图片要求带红框，根据文件名具体变化
            "alarmSrcFile": "",
            "mq_ip": "10.29.3.3",
            "mq_port": 5672,
            "mq_user": 'admin',
            "mq_pw": 'tky3306!@#',
            "ftp_ip": '10.29.3.3',
            "ftp_port": 6522,
            "ftp_user": 'bjjd',
            "ftp_pw": 'Bjtu212.',
            "ftp_rootFolder": "/home",
            "mp4_upload_enable": 1,
            "jpg_upload_enable": 1,
            "alarmEnable": 1
        }
        self.config_file_handler = File_Saver_Loader_json(config_file_path)
        self.load_from_config_file()
        # s2
        self.mq_ip = self.data_dict["mq_ip"]
        self.mq_port = self.data_dict["mq_port"]
        self.mq_user = self.data_dict["mq_user"]
        self.mq_pw = self.data_dict["mq_pw"]
        self.ftp_ip = self.data_dict["ftp_ip"]
        self.ftp_port = self.data_dict["ftp_port"]
        self.ftp_user = self.data_dict["ftp_user"]
        self.ftp_pw = self.data_dict["ftp_pw"]
        self.ftp_rootFolder = self.data_dict["ftp_rootFolder"]
        self.companyCode = self.data_dict["companyCode"]
        self.deviceId = self.data_dict["deviceId"]
        self.algorithmCode = self.data_dict["algorithmCode"]
        self.areaCode = self.data_dict["areaCode"]
        self.companyAlarmId = self.data_dict["companyAlarmId"]
        self.position = self.data_dict["position"]
        self.companyAlarmDate = self.data_dict["companyAlarmDate"]
        self.alarmVideo = self.data_dict["alarmVideo"]
        self.alarmImage = self.data_dict["alarmImage"]
        self.alarmSrcFile = self.data_dict["alarmSrcFile"]
        self.mp4_upload_enable = self.data_dict["mp4_upload_enable"]
        self.jpg_upload_enable = self.data_dict["jpg_upload_enable"]
        self.area_enable = self.data_dict["area_enable"]
        self.basic_message = self.init_basic_message()
        self.alarmEnable = self.data_dict["alarmEnable"]
        # 开发过程中，在self.data_dict中添加了数据则需要保存
        # self.config_file_handler.save_to_file(self.data_dict)

    def init_basic_message(self, ):
        key_list = ["companyCode", "algorithmCode", "areaCode", "companyAlarmId", "position"]
        message_dict_basic = {}
        for key in key_list:
            message_dict_basic[key] = self.data_dict[key]
        return message_dict_basic

    def load_from_config_file(self):
        data_dict = self.config_file_handler.load_from_file()
        xypLog.xypDebug(f"{datetime.datetime.now()}, load_from_config_file, data_dict={data_dict}")
        if data_dict is not None:
            for key in data_dict:
                self.data_dict[key] = data_dict[key]


if __name__ == "__main__":

    nowTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    alarmInfo = {
                "companyCode": "106",
                "algorithmCode": "116",
                "alarmState": 2,
                "alarmId": "sbtx_alarm_202502021122510",
                "alarmEventId": "sbtx_event_202502021122510",
                "position": "K0+142",
                "alarmLevel": 1,
                "alarmType": "人员",
                "alarmTime": "2025-03-12 16:17:51",
                "alarmVideo": "/bjjw/video/20250225/tky_1712710571.2311444.mp4",
                "alarmImage": "/bjjw/image/20250225/2024-04-10/ZJ20250210090150.570200.jpg",
                "alarmSrcFile": "/bjjw/other/20250225/1712650386.4652252.csv"
                }
    heartBeat={
            "algorithmCode": "116",
            "algorithmState": 0,
            "failureCause": "雷达故障",
            "sendTime": "2025-02-25 08:48:50"
            }
    defenseStatus = {
        "algorithmCode":"116",
        "areaState":1,
        "sendTime":"2025-02-25 15:40:28"
        }
    a = DeviceControlForBeiJing(None, None, None, None)
    statusQueue = ["alarm","status","defence"]
    for index,s in enumerate([alarmInfo,heartBeat,defenseStatus]):
        # a.sendAlarmInfo(1, 1, 1, "人员,石块", "/ssd/alarmpic/alarmFrame/2024-05-07/2024-05-07_14-03-47_i000064_d134.3_a1_w1_s2.jpg", "/ssd/alarmpic/alarmFrame/2024-05-07/2024-05-07_14-02-22_i000063_c1.mp4", None,
        #                 1)
        # a.msgTask.append(("alarm",{'alarmEventId': 'sbtx_hmbld_alarm_20240612115529', 'alarmStatus': '1', 'boxId': '122', 'callAlgo': '203', 'callTime': '2024-06-12 11:55:29', 'callType': '201', 'id': 'sbtx_hmbld_event_20240612115529', 'position': 'K8+1', 'callContent': 'sbtx_K8+1_201', 'lineInfo': 'L201', 'callEvent': '1', 'callLevel': '1', 'callSource': '2', 'callState': '0', 'channelId': '43000000001310000052', 'deviceId': '43000000001110000002', 'zone': '1', 'type': 'alarm', 'cloudMessage': [{'boxMessage': [{'box': '909,744,909,772,951,744,951,772', 'category': '1', 'confidence': '0.99935669'}], 'code': '91', 'colour': '(37,176,186)', 'name': '时变通讯'}], 'pvList': [{'alarmVideo': 'http://10.29.3.3:19000/zj-test/video/sbtx/2024-05-07/2024-05-07_14-02-22_i000063_c1.mp4', 'alarmSrcFile': '', 'image': None, 'saveImage': None, 'type': '0', 'url': 'http://10.29.3.3:19000/zj-test/image/sbtx/2024-05-07/2024-05-07_14-03-47_i000064_d134.3_a1_w1_s2.jpg'}], 'uploadMessage': [{'box': None, 'category': '201', 'confidence': None}]}))
        a.msgTask.append((statusQueue[index],s))
        time.sleep(2)

    time.sleep(5555)
    # nowTime = datetime.datetime.now()
    while 1:
        xypLog.xypDebug(datetime.datetime.now(), "===============================================")
        time.sleep(1001)
    # a.test_sftp_chengdu()
    time.sleep(5555)
