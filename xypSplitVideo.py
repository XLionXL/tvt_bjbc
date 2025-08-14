
import os
import ffmpeg


def split_video_by_minute(input_file, output_dir):
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 使用ffmpeg获取视频时长
    probe = ffmpeg.probe(input_file)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    duration = float(video_info['duration'])
    print(duration)
    t=2*60
    # 分割视频
    for i in range(max(int(duration / t),1)):
        start_time = i * t
        end_time = min((i + 1) * t, duration)
        print(start_time,end_time)
        ffmpeg.input(input_file, ss=start_time, to=end_time).output(os.path.join(output_dir, f'part_{i + 1}.mp4')).run()


# 示例用法
input_file = r"D:\新建文件夹\940北京原视频(1)\11.mp4" # 输入文件路径
output_dir = './video/1'  # 输出目录路径
from xypTool.common import xypFileTool
xypFileTool.checkPath(output_dir)
split_video_by_minute(input_file, output_dir)