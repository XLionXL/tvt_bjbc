# 推理时用到的分辨率 16/9
# infer_width, infer_height = 1280, 1280
infer_width, infer_height = 640, 640

# 显示用的分辨率 16/9 （用于显示）
dst_width, dst_height = 800, 450
# dst_width, dst_height = 854, 480
# dst_width, dst_height = 640, 360

# 标定时的图像分辨率 16/9 (用于将标定的坐标点进行等比例缩放)
calib_width, calib_height = 1280, 720

# 原始图像的分辨率 (用于通过内参进行目标位置估算)
org_camera_pix = 1920, 1080
