# Nano接口文档

安装好依赖后，可使用如下命令启动程序：

```bash
python python3_main_py.py
```

目前Nano端启动时，会自动开启一个TCP服务器，端口在8888，同时，默认会监听雷达数据（17000端口），相机数据（10001端口），可通过在启动时添加参数修改这些端口：

```bash
usage: python3_main_py.py [-h] [-t TCP_PORT] [-r RADAR_PORT] [-c CAMERA_PORT]

开启TCP服务

optional arguments:
  -h, --help            show this help message and exit
  -t TCP_PORT, --tcp_port TCP_PORT
                        设置 tcp 服务器端口
  -r RADAR_PORT, --radar_port RADAR_PORT
                        设置 radar 广播监听端口
  -c CAMERA_PORT, --camera_port CAMERA_PORT
                        设置 camera 广播监听端口
```



## 数据结构说明

由于是直接使用TCP，无论是请求还是响应，直接用JSON封装对象，结构如下：

- 请求

一般请求最重要的标志是code，如果有上传数据的，可以将数据写入到data属性中

```json
{
    "code": 100
}
```

- 响应

code要和请求的code一致，将返回结果放到data中

```json
{
    "code": 100, 
    "msg": "success", 
    "data": {...}
}
```



## 长期数据

### 相机数据

- 请求

无需请求，Nano端会实时将数据发送过来

- 响应

```json
{
	'code': 200,
	'msg': 'camera_data',
	'data': {
		'list': [{
			'id': 0,
			'timestamp': 1625802036376,
			'data': [{
				'confidence': 0.751524806,
				'class': 0,
				'bbox': [431, 138, 44, 68],
				'in_area': 1,
				'xyz': [7.411804962158203, 0, 27.2838134765625]
			}, {
				'confidence': 0.747727633,
				'class': 0,
				'bbox': [382, 159, 49, 58],
				'in_area': 1,
				'xyz': [5.922253799438477, 0, 25.588775634765625]
			}, {
				'confidence': 0.33292225,
				'class': 0,
				'bbox': [681, 345, 14, 26],
				'in_area': 0
			}]
		}],
		'stamp': 1625802036.3857338
	}
}
```



### 雷达数据

- 请求

无需请求，Nano端会实时将数据发送过来

- 响应

```json
{
	'code': 201,
	'msg': 'radar_data',
	'data': {
		'stamp': 1625802407.9870877,
		'list': [{
			'id': 0,
			'data': [{
				'in_area': 1,
				'dto': [1, -0.019455403089523315, 38.217559814453125, 0.16321370005607605, 10.0],
				'radar': [
					[168.13125, -103.55555555555554],
					[-0.218829575630334, -2.264426267729732, 38.0672618786729],
					[
						[97.409375, -262.22222222222223],
						[239.29791666666665, 55.11111111111111]
					],
					[-0.019455403089523315, 38.217559814453125]
				]
			}, {
				'in_area': 1,
				'dto': [1, -0.10360273718833923, 17.861072540283203, 0.228499174118042, 8.0],
				'radar': [
					[125.87604166666667, 109.33333333333333],
					[-0.19677946168978444, -0.5256378129164716, 17.785009095807798],
					[
						[-26.242708333333333, -229.77777777777777],
						[277.99479166666663, 448.4444444444444]
					],
					[-0.10360273718833923, 17.861072540283203]
				]
			}]
		}, {
			'id': 1,
			'data': []
		}]
	}
}
```



## 请求返回数据

### 相机ROI区域

`REQ_CAMERA_ROI = 100`

- 请求

```json
{'code': 100}
```

- 响应

```json
{
	'code': 100,
	'msg': 'success',
	'data': {
		'0': [
			[192, 712, 0.0, 0.0, 0.0],
			[357, 116, 0.0, 0.0, 0.0],
			[632, 109, 0.0, 0.0, 0.0],
			[1015, 716, 0.0, 0.0, 0.0]
		],
		'1': [
			[292, 711, 0.0, 0.0, 0.0],
			[307, 175, 0.0, 0.0, 0.0],
			[749, 174, 0.0, 0.0, 0.0],
			[1264, 715, 0.0, 0.0, 0.0]
		]
	}
}
```



### 相机内参

`REQ_CAMERA_IN_PARAMS = 101`

- 请求

```json
{'code': 101}
```

- 响应

```json
{
	'code': 101,
	'msg': 'success',
	'data': {
		'0': '%YAML:1.0\n---\nimage_width: 1920\nimage_height: 1080\ncamera_name: narrow_stereo\ncamera_matrix: !!opencv-matrix\n  rows: 3\n  cols: 3\n  dt: d\n  data: [17908.65575,     0.     ,   481.34968,\n             0.     , 15996.73682,   718.54338,\n             0.     ,     0.     ,     1.     ]\ndistortion_model: plumb_bob\ndistortion_coefficients: !!opencv-matrix\n  rows: 1\n  cols: 5\n  dt: d\n  data: [-28.409467, 1282.423080, -0.271868, 0.636307, 0.000000]\nrectification_matrix: !!opencv-matrix\n  rows: 3\n  cols: 3\n  dt: d\n  data: [1., 0., 0.,\n         0., 1., 0.,\n         0., 0., 1.]\nprojection_matrix: !!opencv-matrix\n  rows: 3\n  cols: 4\n  dt: d\n  data: [18082.16602,     0.     ,   526.97395,     0.     ,\n             0.     , 16144.84277,   706.34979,     0.     ,\n             0.     ,     0.     ,     1.     ,     0.     ]\n',
		'1': '%YAML:1.0\n---\nimage_width: 1920\nimage_height: 1080\ncamera_name: narrow_stereo\ncamera_matrix: !!opencv-matrix\n  rows: 3\n  cols: 3\n  dt: d\n  data: [44336.99278,     0.     ,  1004.24865,\n             0.     , 47489.02056,  -432.4263 ,\n             0.     ,     0.     ,     1.     ]\ndistortion_model: plumb_bob\ndistortion_coefficients: !!opencv-matrix\n  rows: 1\n  cols: 5\n  dt: d\n  data: [37.079428, -12753.108988, -0.354298, 0.074203, 0.000000]\nrectification_matrix: !!opencv-matrix\n  rows: 3\n  cols: 3\n  dt: d\n  data: [1., 0., 0.,\n         0., 1., 0.,\n         0., 0., 1.]\nprojection_matrix: !!opencv-matrix\n  rows: 3\n  cols: 4\n  dt: d\n  data: [44759.88281,     0.     ,  1008.12971,     0.     ,\n             0.     , 47250.41406,  -436.85489,     0.     ,\n             0.     ,     0.     ,     1.     ,     0.     ]\n'
	}
}
```



### 相机外参

`REQ_CAMERA_EX_PARAMS = 102`

- 请求

```json
{'code': 102}
```

- 响应

```json
{
	'code': 102,
	'msg': 'success',
	'data': {
		'0': [
			[193, 709, -0.75, 0.0, 0.0],
			[351, 128, -0.75, 51.0, 0.0],
			[494, 125, 3.25, 51.0, 0.0],
			[461, 715, 3.25, 0.0, 0.0]
		],
		'1': [
			[280, 712, -0.75, 0.0, 0.0],
			[314, 182, -0.75, 210.0, 0.0],
			[701, 179, 6.45, 210.0, 0.0],
			[715, 713, 6.45, 0.0, 0.0]
		]
	}
}
```



## 错误信息

当请求数据格式无法解析，或code不识别时，会返回如下信息

```json
{'code': -1, 'msg': '请求失败，请求体中需包含有效code字段，并保证json格式正确'}
```



|              | 便捷性 | 精确性 | 通用性 |
| ------------ | ------ | ------ | ------ |
| 4点现场标定  | ★      | ★★★    | ★★★    |
| 铁轨远程标定 | ★★     | ★★★    | ★      |
| 陀螺仪标定   | ★★★    | ★★     | ★★★    |
| 无标定       | ★★★    | ★      | ★★★    |

