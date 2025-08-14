## 依赖安装：

```bash
# 多边形相交判断
sudo apt install libgeos-dev

# 语音依赖库
sudo apt install espeak

# 语音
pip3 install pyttsx3

# 多边形相交判断
pip3 install shapely

# 更新默认的yaml版本
pip3 install -U pyyaml

pip3 install blinker

pip3 install pyserial
pip3 install joblib


```

## 运行程序

```bash
# 前台运行
python python3_main_py.py

# 后台运行
nohup python python3_main_py.py > output.log 2>&1 &

```

## 远程警戒接口及服务

### 接口

- [x] 接收推理的结果数据（输入）
   - 相机1
   - 相机2
   - 雷达
- [x] 转发相机数据和雷达数据（输出）
- [ ] 获取、设置警戒区域/接收配置文件
  - 雷达报警区域
  - 摄像头报警区域（两个）
  - 相机内参
  - 相机外参
- [ ] 上传误报区域
- [ ] 获取、设置黑夜傍晚时间

### 服务

- 警戒区判定服务
  - 雷达和相机：
    - 雷达和相机距离判定在±5m以内，直接报警
    - 5m开外，走单雷达&单摄像头报警流程
  - 单摄像头报警：
    - 无雷达数据
    - 白天：持续出现在报警区域3s以上（无漏帧），报警后3s内最多允许漏2帧
    - 夜晚：持续出现在报警区域5s以上（无漏帧），报警后5s内最多允许漏3帧
  - 单雷达报警：
    - 无相机数据
    - 持续出现在报警区域3S以上（无漏帧）
- 调用声卡报警服务
- 心跳检测服务，每5秒发一个包

