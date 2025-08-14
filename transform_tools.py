import math
import numpy as np

import commdef


# 根据相机内参进行三维->二维坐标转换


def isRotationMatrix(R):
    Rt = np.transpose(R)
    shouldBeIdentity = np.dot(Rt, R)
    I = np.identity(3, dtype=R.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6


def rotationMatrixToEulerAngles(R):
    assert (isRotationMatrix(R))

    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])

    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    return np.array([x, y, z])


def eulerAnglesToRotationMatrix(theta):
    R_x = np.array([[1, 0, 0],
                    [0, math.cos(theta[0]), -math.sin(theta[0])],
                    [0, math.sin(theta[0]), math.cos(theta[0])]
                    ])

    R_y = np.array([[math.cos(theta[1]), 0, math.sin(theta[1])],
                    [0, 1, 0],
                    [-math.sin(theta[1]), 0, math.cos(theta[1])]
                    ])

    R_z = np.array([[math.cos(theta[2]), -math.sin(theta[2]), 0],
                    [math.sin(theta[2]), math.cos(theta[2]), 0],
                    [0, 0, 1]
                    ])

    R = np.dot(R_z, np.dot(R_y, R_x))

    return R


def xyzrpy2matrix(data, is_degrees=True):
    rpy = data[3:]
    if is_degrees:
        rpy = np.deg2rad(rpy)
    R_matrix = eulerAnglesToRotationMatrix(rpy)
    T_matrix = np.eye(4, dtype=np.float32)
    T_matrix[:3, :3] = R_matrix
    T_matrix[:3, 3] = data[:3]
    return T_matrix


def convert_to_2d(p3d, mtx):
    """
    将三维坐标通过相机内参矩阵转成二维坐标
    :param p3d:
    :param mtx:
    :return: 二维坐标
    """
    if mtx is not None:
        fx, fy = mtx[0, 0], mtx[1, 1]
        cx, cy = mtx[0, 2], mtx[1, 2]
        x, y, z = p3d[0], p3d[1], p3d[2]
        u = int(round((x * fx) / z + cx))
        v = int(round((y * fy) / z + cy))
    else:
        u, v=100,100
    return u, v


def radar_pos_to_camera(radar_target_pos, radar2camera, camera_in_params=None):
    """
    :param radar_target_pos:  雷达坐标系下目标的坐标
    :param radar2camera:  预制的xyz、rpy（雷达外参cTr）
    :param camera_in: 相机内参
    :return: 雷达坐标在相机坐标系下的像素uv坐标+三维坐标
    """

    # 转成齐次形式 4x1
    radar_target_pos.append(1.)
    radar_target_pos = np.array([radar_target_pos]).T

    # 转成齐次变换矩阵 4x4
    radar_matrix = xyzrpy2matrix(radar2camera)

    # 矩阵相乘得到目标在相机下的坐标
    target_in_camera = radar_matrix @ radar_target_pos

    # print(radar_target_pos)
    # print(radar_matrix)
    # print(target_in_camera.ravel())

    # 将3d坐标转成2d图像坐标
    target_in_camera = list(target_in_camera.ravel()[:3])
    uv_in_camera = convert_to_2d(target_in_camera, camera_in_params)
    # print(uv_in_camera)
    return uv_in_camera, target_in_camera


person_h = 1.697
person_radio = 0.4  # width/height = 0.4 / 1
person_w = person_h * person_radio


def generate_2d_box(p3d, mtx):
    """
    根据距离z及相机内参生成人体包容盒
    :param distance_z: 距离
    :param mtx: 相机内参
    :param target_real_shape: 人体尺寸
    :return: 包容盒 [x1, y1, x2, y2]
    """
    x, y, z = p3d[0], p3d[1], p3d[2]

    h, w = person_h, person_w

    top_left = (x - w / 2.0, y - h / 2.0, z)
    bottom_right = (x + w / 2.0, y + h / 2.0, z)

    return convert_to_2d(top_left, mtx), convert_to_2d(bottom_right, mtx)


# ---------------------------------------------------------------------------

def convert_bbox(bbox, target_pix=None, req_2_point_mode = False):
    """
    1. 将640x640图像内的包容盒根据目标尺寸进行缩放800x800
    2. 将800x800的图像内的包容盒去黑边，变成800x450图像下
    :param bbox:
    :param target_pix:
    :return:
    """
    if target_pix is None:
        target_pix = (commdef.dst_width, commdef.dst_height)

    infer_width, infer_height = commdef.infer_width, commdef.infer_height

    dst_width, dst_height = target_pix # 800x450
    scale_ratio = 1
    if dst_width > dst_height:
        scale_ratio = infer_width / dst_width # 640 / 800
    else:
        scale_ratio = infer_height / dst_height

    scaled_width, scaled_height = infer_width, infer_height # 640x640

    new_bbox = list(bbox)
    if abs(scale_ratio - 1) > 0.0001:
        # 将坐标等比例缩放
        new_bbox = [value / scale_ratio for value in new_bbox]
        # 得到缩放后的图像尺寸 640x640
        scaled_width, scaled_height = infer_width / scale_ratio, infer_height / scale_ratio # 800x800

    lefttop_x, lefttop_y, width, height = new_bbox
    # print(f"s: {scale_ratio}, {lefttop_x, lefttop_y, width, height}")

    # 800x800 -> 800x450
    lefttop_x = lefttop_x - (scaled_width - dst_width) / 2.0   # x - (800 - 800) / 2
    lefttop_y = lefttop_y - (scaled_height - dst_height) / 2.0 # y - (800 - 450) / 2

    if req_2_point_mode:
        return int(lefttop_x), int(lefttop_y), int(lefttop_x + width), int(lefttop_y + height)

    return int(lefttop_x), int(lefttop_y), int(width), int(height)


def convert_bbox2(bbox, bbox_pix=[1920, 1280], target_pix=[800, 450], req_2_point_mode=False):
    """
    将图像内的包容盒bbox根据目标尺寸进行缩放
    :param bbox:包容盒,[x,y,w,h]
    :param bbox_pix:包容盒像素分辨率,(1920, 1280)
    :param target_pix:(800, 450)
    :return:
    """
    scale_ratio = (target_pix[0] / bbox_pix[0], target_pix[1] / bbox_pix[1])
    leftTop_x, leftTop_y, width, height = [bbox[0] * scale_ratio[0], bbox[1] * scale_ratio[1], bbox[2] * scale_ratio[0], bbox[3] * scale_ratio[1]]

    if req_2_point_mode:
        return int(leftTop_x), int(leftTop_y), int(leftTop_x + width), int(leftTop_y + height)

    return int(leftTop_x), int(leftTop_y), int(width), int(height)

# def camera_radar_fusion_test():
#     radar_target_pos = [1.2, 2.4, 0.8]
#     radar2camera = [1, 2, 3, 0, 0, 30]
#     # camera_params_path = "./conf/calibration_in_params_hk.yml"
#     # 1. 加载相机内参矩阵、畸变系数
#     fs = cv2.FileStorage("../conf/calibration_in_params_hik.yml", cv2.FileStorage_READ)
#     cameraMatrix = fs.getNode("camera_matrix").mat()
#     distCoeffs = fs.getNode("distortion_coefficients").mat()
#     print("cameraMatrix: \n", cameraMatrix)
#     print("distCoeffs: \n", distCoeffs)
#     fs.release()
#     radar_pos_to_camera(radar_target_pos, radar2camera, cameraMatrix)


if __name__ == '__main__':
    # print(xyzrpy2matrix([1, 2, 3, 0, 0, 30]))
    bbox = [0, 280, 400, 200]

    rst = convert_bbox(bbox) # [0, 0, 200, 100]
    print(rst)

    org_camera_pix = (1920, 1080)
    bbox_one = convert_bbox(bbox, target_pix=org_camera_pix, req_2_point_mode=True)

    print(bbox_one)


def scale_xy(src, target_wh, org_wh):
    """
    缩放坐标值
    :param src: 原点坐标(x, y)
    :param target_wh: 目标图像宽高
    :param org_wh:    原始图像宽高
    :return:
    """
    widget_w, widget_h = target_wh
    org_w, org_h = org_wh
    scale_x = widget_w / org_w
    scale_y = widget_h / org_h
    new_x, new_y = src
    if abs(scale_x - 1.0) > 0.001:
        new_x *= scale_x
    if abs(scale_x - 1.0) > 0.001:
        new_y *= scale_y
    return new_x, new_y


if __name__ == '__main__':
    xywh1 = convert_bbox([243, 305, 13, 14])
    xywh2 = convert_bbox2([243, 305, 13, 14], bbox_pix=[640, 640])
    print(f"xywh1={xywh1},xywh2={xywh2}")
# (0, 175, 500, 250)
# (0, 420, 1200, 1020)
# xywh1=(303, 206, 16, 17),xywh2=(303, 214, 16, 9)