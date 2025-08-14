
from enum import Enum, unique

@unique
class GuardMode(Enum):
    CAMERA_MODE = 1 # 纯相机模式
    RADAR_MODE = 2 # 纯雷达模式
    CAMERA_RADAR_MODE = 4 # 纯混合模式
    MIX_MODE = CAMERA_MODE | RADAR_MODE | CAMERA_RADAR_MODE # 自动模式

current_cuard_mode = GuardMode.MIX_MODE

print(current_cuard_mode._value_)

print("-------------------------------")

print(current_cuard_mode._value_ & GuardMode.CAMERA_MODE.value)
print(current_cuard_mode._value_ & GuardMode.RADAR_MODE.value)
print(current_cuard_mode._value_ & GuardMode.CAMERA_RADAR_MODE.value)

print(GuardMode.RADAR_MODE.value & GuardMode.CAMERA_MODE.value)
print(GuardMode.RADAR_MODE.value & GuardMode.RADAR_MODE.value)
print(GuardMode.RADAR_MODE.value & GuardMode.CAMERA_RADAR_MODE.value)

