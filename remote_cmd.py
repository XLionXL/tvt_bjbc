# -*- coding:utf-8 -*-
from enum import Enum

# #上位机linux命令
# path="/home"
# cmd="sudo systemctl restart zipx.service"
# nano_cmd_json={
# "code": 311,
#  "msg": "nano_cmd",
#  "data":{"path":path,
#          "cmd":cmd,
#          }
# }
# #上位机mcu命令
# mcu_cmd_json={
# "code": 312,
#  "msg": "mcu_cmd",
#  "data":{"operation":0,#0,无操作,1,雷达断电重启 2,近端相机断电重启,3,远端相机断电重启,4,nano断电重启,5,MCU重启,6,交换机/路由器断电重启,7,整机重启
#          }
# }

class Mcu_cmd_operation(Enum):
    # operation
    # 0, 无操作, 1, 雷达断电重启 2, 近端相机断电重启, 3, 远端相机断电重启,
    # 4, nano断电重启, 5, MCU重启, 6, 交换机 / 路由器断电重启, 7, 整机重启
    NO_OPERATION=0
    RADAR_RESTART = 1
    CAMERA_NEAR_RESTART = 2
    CAMERA_REMOTE_RESTART = 3
    NANO_RESTART = 4
    MCU_RESTART=5
    SWITCH_ROUTER_RESTART=6
    ALL_RESTART=7

class Nano_remote_cmd():
    def __init__(self):
        pass

    def gen_nano_linux_cmd_frame(self,path:str,cmd:str):
        # 上位机发送到nano的linux命令,方便测试人员执行相关操作，远程升级也可能需要用到
        # 目前至少需要支持如下命令
        # 启动推理：sudo systemctl start zipx.service
        # 停止推理：sudo systemctl stop zipx.service
        # 重启推理：sudo systemctl restart zipx.service
        nano_linux_cmd_frame={
        "code": 311,
         "msg": "nano_cmd",
         "data":{"path":path, "cmd":cmd, }  #在path目录下执行cmd命令
        }
        return nano_linux_cmd_frame

    def execute_nano_linux_cmd(self,nano_linux_cmd_frame:dict):
        # 请孙克完成并调试
        # 执行发送到nano的linux命令,方便测试人员执行相关操作，远程升级也可能需要用到
        # 目前至少需要支持如下命令
        # 启动推理：sudo systemctl start zipx.service
        # 停止推理：sudo systemctl stop zipx.service
        # 重启推理：sudo systemctl restart zipx.service
        # 数据包内容参考gen_nano_linux_cmd_frame函数
        pass

    def gen_mcu_cmd_frame(self,operation:Mcu_cmd_operation):
        #上位机或者浏览器发给nano需要mcu执行的操作/命令
        # operation 0,无操作,1,雷达断电重启 2,近端相机断电重启,3,远端相机断电重启,4,nano断电重启,5,MCU重启,6,交换机/路由器断电重启,7,整机重启
        mcu_cmd_frame={
        "code": 312,
         "msg": "mcu_cmd",
         "data":{"operation":operation.value,
                 }
        }
        return mcu_cmd_frame

    def execute_mcu_cmd(self,mcu_cmd_frame:dict):
        # 请镇畅完成并调试
        # 协议翻译并转发到MCU执行相关操作
        # 可能的操作包括
        # 0,无操作,1,雷达断电重启 2,近端相机断电重启,3,远端相机断电重启,4,nano断电重启,5,MCU重启,6,交换机/路由器断电重启,7,整机重启
        # 数据包内容参考gen_mcu_cmd_frame函数

        pass

remote_cmd_executor=Nano_remote_cmd()

if __name__=="__main__":
    print(remote_cmd_executor.gen_nano_linux_cmd_frame("/home","sudo systemctl restart zipx.service"))
    print(remote_cmd_executor.gen_mcu_cmd_frame(Mcu_cmd_operation.MCU_RESTART))
    print(Mcu_cmd_operation(5))
