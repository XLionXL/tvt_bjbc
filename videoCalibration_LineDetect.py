# -*- coding: utf-8 -*-
import datetime
import math
import numpy as np
import os

import common_cross_point
from common_FileLoadSave import File_Saver_Loader_json, File_Saver_Loader_pkl


class CalibrationResult():
    def __init__(self, url="", ):
        self.result = {"fov_V_deg": 1,
                       "fov_H_deg": 1,
                       "vanishingPoint": [1, 1],
                       "camera_height": 1.0,
                       'rad_per_pixel': 1.0
                       }
        self.url = url
        self.default_resolution = [800, 450]

    def calc_FOV_V_degree(self, resolution, obj_span_pixel, distance, height):
        rad_per_pixel = math.atan(height / distance) / obj_span_pixel
        rad_fov = rad_per_pixel * resolution
        self.result['fov_V_deg'] = rad_fov * 180 / math.pi
        self.result['rad_per_pixel'] = rad_fov / resolution

    def get_axis_y(self, obj_bottom_xy, ):
        """
        根据目标脚部像素坐标和校准结果计算目标距离
        """
        x_pixel, y_pixel = obj_bottom_xy
        x_vanishing, y_vanishing = self.result["vanishingPoint"]
        # 计算目标底部在相机看过去的下倾角
        foot_angle_rad = 0.5 * math.pi - self.result["rad_per_pixel"] * (y_pixel - y_vanishing)
        if y_pixel - y_vanishing <= 0:
            return 999
        # 计算距离
        y_axis = self.result["camera_height"] * math.tan(foot_angle_rad)
        return y_axis

    def get_axis_xy(self, obj_xy, resolution_old=[1280, 720], resolution_new=[800, 450]):
        """
        根据目标脚部像素坐标和校准结果计算目标XY坐标
        """
        # 画防区分辨率是[1280, 720]，标定分辨率是[800, 450]
        obj_xy_new = self.point_transfer_of_resolution(obj_xy, resolution_old, resolution_new)
        x_pixel, y_pixel = obj_xy_new

        x_vanishing, y_vanishing = self.result["vanishingPoint"]
        # 计算目标底部在相机看过去的下倾角
        foot_angle_rad = 0.5 * math.pi - self.result["rad_per_pixel"] * (y_pixel - y_vanishing)
        if y_pixel - y_vanishing <= 0:
            return (9999.9999, 9999.9999)
        # 计算距离
        y_axis = self.result["camera_height"] * math.tan(foot_angle_rad)

        # 计算水平方向X位置，右侧为X正，左侧为X负，灭点的x为0，根据灭点位置和相机水平方向角度分辨率、纵向距离计算x坐标
        x_res_per_pixel = self.result["rad_per_pixel"]
        # line_of_vanishingPoint = [resolution_new[0] * 0.5, resolution_new[1], x_vanishing, y_vanishing]
        line_of_x0 = [resolution_new[0] * 0.5, resolution_new[1], resolution_new[0] * 0.5, 0]  # 中间垂直线
        line_of_click_horizon = [0, y_pixel, resolution_new[0], y_pixel]
        cross_point = common_cross_point.get_cross_point(line_of_x0, line_of_click_horizon)
        # print(f"cross_point={cross_point}")
        if cross_point is not None:
            x_axis = y_axis * math.sin(x_res_per_pixel * (x_pixel - cross_point[0]))
            # print(f"axis={x_axis},{y_axis}")
            if resolution_new[1] * 0.97 < y_pixel and resolution_old[0] >= 1000: # 画防区分辨率是[1280, 720]
                # 靠近底部，y置为0
                return (x_axis, 0)
            else:
                return (x_axis, y_axis)
        else:
            return (9999.9999, 9999.9999)

    def get_pixel_xywh(self, radar_xy, resolution=[800, 450]):
        """
        # 将雷达坐标转换为相机目标框
        :param radar_xy:
        :param resolution:
        :return:
        """
        # for debug
        # "dto": [3458, -0.682, 83.122, 0.008, -0.978]>>> "xywh_800_450": [104, -187, 76, 143]}
        # self.result = {"fov_V_deg": 25.017006056708457, "fov_H_deg": 1, "vanishingPoint": [402, 192],
        #                "camera_height": 2.2, "rad_per_pixel": 0.0009702869437353906}
        # self.result = {"fov_V_deg": 3.6614114505309927, "fov_H_deg": 1, "vanishingPoint": [440, 170],
        #                "camera_height": 2.2, "rad_per_pixel": 0.0001420081890710829}
        # radar_xy = -1.389, 54.061

        pixel_x_vanishing, pixel_y_vanishing = self.result["vanishingPoint"]
        radar_x, radar_y = radar_xy
        # 计算 foot_angle_rad
        foot_angle_rad = math.atan(self.result["camera_height"] / radar_y)
        pixel_y_foot = foot_angle_rad / self.result["rad_per_pixel"] + pixel_y_vanishing
        # 计算 pixel xy
        angle_x_rad = math.atan(radar_x / radar_y)
        pixel_x_foot = angle_x_rad / self.result["rad_per_pixel"] + 0.5 * resolution[0]
        # 假定目标高和宽分别为 (1.7,0.9)
        obj_h, obj_w = 1.7, 0.9
        pixel_h = math.atan(obj_h / radar_y) / self.result["rad_per_pixel"]
        pixel_w = math.atan(obj_w / radar_y) / self.result["rad_per_pixel"]
        pixel_xywh_float = [pixel_x_foot - 0.5 * pixel_w, pixel_y_foot - pixel_h, pixel_w, pixel_h]
        pixel_xywh = [int(pixel) for pixel in pixel_xywh_float]
        return pixel_xywh

    def point_transfer_of_resolution(self, point_old, resolution_old=[1280, 720], resolution_new=[800, 450]):
        # 不同分辨率下坐标转换
        point_new = []
        for index in range(min(len(point_old), len(resolution_old), len(resolution_new))):
            point_new.append(point_old[index] * resolution_new[index] / resolution_old[index])
        return point_new

    def get_corsssection_ofObj(self, xywhList):
        """
        根据目标像素坐标和校准结果计算目标截面积
        """
        x_pixel, y_pixel, w_pixel, h_pixel = xywhList
        # 计算纵向距离
        distance = self.get_axis_y([x_pixel + 0.5 * w_pixel, y_pixel + h_pixel])
        # 距离*tan，计算宽和高，计算面积
        rad_per_pixel = self.result["rad_per_pixel"]
        w_meter = distance * math.tan(w_pixel * rad_per_pixel)
        h_meter = distance * math.tan(h_pixel * rad_per_pixel)
        corsssection = w_meter * h_meter

        # 判断是否正常截面积
        corsssection_ref = 0.5 * 1.5  # 标准参考人体尺寸 宽度和高度
        corss_coef_min, corss_coef_max = 0.4, 2.0
        corsssection_coef = corsssection / corsssection_ref
        isNormCrossSection = corss_coef_min <= corsssection_coef and corsssection_coef <= corss_coef_max
        # corsssection_min = 0.35 * 1.2    #最小宽度*最小高度
        # corsssection_max = 1.1 * 2.2    #最大宽度*最大高度
        # isNormCrossSection=(corsssection_min <=corsssection and corsssection <= corsssection_max)

        return [corsssection, w_meter, h_meter, corsssection_coef], isNormCrossSection


class Common_Function():
    def is_point_in_image(self, crossPoint, imagesize_H_V=[800, 450]):
        if len(crossPoint) < 2:
            return False
        return 0 <= crossPoint[0] and crossPoint[0] < imagesize_H_V[0] and \
               0 <= crossPoint[1] and crossPoint[1] < imagesize_H_V[1]

    def overlap_y(self, lines_i, lines_j):
        """
        计算两条直线，在Y方向重叠的像素数量
        """
        line_i_y_max, line_i_y_min = max(lines_i[0][1], lines_i[0][3]), min(lines_i[0][1], lines_i[0][3])
        line_j_y_max, line_j_y_min = max(lines_j[0][1], lines_j[0][3]), min(lines_j[0][1], lines_j[0][3])
        delta_Y = min(line_i_y_max, line_j_y_max) - max(line_i_y_min, line_j_y_min)
        return delta_Y

    def angle_line(self, line_this):
        """
        根据直线上两点像素坐标，使用复数方法计算复数的线，线长，辐角(度)。
        """
        point1, point2 = complex(line_this[0][0], line_this[0][1]), complex(line_this[0][2], line_this[0][3])
        line_complex = point1 - point2
        line_length = abs(line_complex)
        line_angle_deg = np.angle(line_complex, deg=True) % 180
        return line_complex, line_length, line_angle_deg

    def pnpoly(self, vertices, testp):
        """
            判断点是否在不规则的多边形内
        """
        n = len(vertices)
        j = n - 1
        res = False
        for i in range(n):
            if (vertices[i][1]) > testp[1] != (vertices[j][1] > testp[1]) and \
                    testp[0] < (vertices[j][0] - vertices[i][0]) * (testp[1] - vertices[i][1]) / (
                    vertices[j][1] - vertices[i][1]) + vertices[i][0]:
                res = not res
            j = i
        return res

    # 向量叉乘
    def crossMul(self, v1, v2):
        return v1[0] * v2[1] - v1[1] * v2[0]

    # 判断两条线段是否相交
    def checkCross(self, p1, p2, p3, p4):
        v1 = [p1[0] - p3[0], p1[1] - p3[1]]
        v2 = [p2[0] - p3[0], p2[1] - p3[1]]
        v3 = [p4[0] - p3[0], p4[1] - p3[1]]
        v = self.crossMul(v1, v3) * self.crossMul(v2, v3)
        v1 = [p3[0] - p1[0], p3[1] - p1[1]]
        v2 = [p4[0] - p1[0], p4[1] - p1[1]]
        v3 = [p2[0] - p1[0], p2[1] - p1[1]]
        if v <= 0 and self.crossMul(v1, v3) * self.crossMul(v2, v3) <= 0:
            return True
        else:
            return False

    # 判断点是否在多边形内
    def checkPP(self, point, polygon):
        try:
            p1 = point
            p2 = [-1000000000, point[1]]
            count = 0
            for i in range(len(polygon) - 1):
                p3 = polygon[i]
                p4 = polygon[i + 1]
                if self.checkCross(p1, p2, p3, p4):
                    count += 1
            p3 = polygon[len(polygon) - 1]
            p4 = polygon[0]
            if self.checkCross(p1, p2, p3, p4):
                count += 1
            # print(f"checkPP {count}") # 交点
            if count % 2 == 0:
                return False
            else:
                return True
        except:
            print(f"checkPP error point={point},polygon={polygon}")

    # def addLines_in_image(self,img_rail,lines):
    #     """
    #     在图像上画出各条直线
    #     """
    #     try:
    #         if lines==None:
    #             return []
    #     except:
    #         pass
    #     if len(lines)>0:
    #         color_seed=150
    #         for line_this in lines:
    #             x1, y1, x2, y2=line_this[0][0],line_this[0][1],line_this[0][2],line_this[0][3]
    #             # print(line_this)
    #             # 每次点击，都是一种 新颜色
    #             cv2.line(img_rail, (x1, y1), (x2, y2),  (0, 0, color_seed), 2)
    #             color_seed+=30

    def getCrossPoint(self, Line1, Line2):
        """
        函数功能：求两条直线交点
        输入：两条直线
        返回：两条直线交点坐标[x,y]
        """
        LineA = Line1[0]
        LineB = Line2[0]
        crossPoint = [0, 0]
        if abs(LineA[2] - LineA[0]) == 0:
            ka = 999999
        if abs(LineB[2] - LineB[0]) == 0:
            kb = 999999
        if abs(LineA[2] - LineA[0]) > 0 and abs(LineB[2] - LineB[0]) > 0:
            # //求出LineA斜率，//求出LineB斜率
            ka = (LineA[3] - LineA[1]) / (LineA[2] - LineA[0]);
            kb = (LineB[3] - LineB[1]) / (LineB[2] - LineB[0]);
        if ka == kb:
            return []
        else:
            crossPoint[0] = (ka * LineA[0] - LineA[1] - kb * LineB[0] + LineB[1]) / (ka - kb);
            crossPoint[1] = (ka * kb * (LineA[0] - LineB[0]) + ka * LineB[1] - kb * LineA[1]) / (ka - kb);
            return crossPoint


class LineDetect:
    def __init__(self):
        self.resolution_H = 800
        self.angle_ref = 145
        self.angle_threshold_merge = 4
        self.region_pts_list = []
        self.lineHistory = []
        self.lines = []
        self.minLineLength = 100
        self.maxLineGap = 100
        self.angle_theta = 0.6
        self.gray_threshold = 50
        self.delta_X_min = 30
        self.delta_Y_min = 30
        self.common_function = Common_Function()

    # def get_gray_contour_img(self, img_rail):
    #     start = time.time()
    #     # 二值化，并获得灰度图
    #     ddepth = -1
    #     img_rail_sobel = cv2.Sobel(img_rail, ddepth, 1, 0)
    #     t, img_rail_threshold = cv2.threshold(img_rail_sobel, 210, 255, cv2.THRESH_TOZERO)
    #     img_rail_gray = cv2.cvtColor(img_rail_threshold, cv2.COLOR_BGR2GRAY)
    #     ##复制灰度图
    #     # img_line0 = img_rail_gray.copy();
    #     #
    #     ##定义检测范围，找到最大连通区域的外轮廓
    #     # left_top=(int(self.cols_number*0.4),int(self.rows_number*0.45))
    #     # left_down=(int(self.cols_number*0.05),int(self.rows_number*0.99))
    #     # right_top=(int(self.cols_number*0.7),int(self.rows_number*0.45))
    #     # right_down=(int(self.cols_number*0.95),int(self.rows_number*0.99))
    #     # cv2.line(img_line0, left_top, right_top,255,1,cv2.LINE_AA);
    #     # cv2.line(img_line0, left_down, right_down, 255, 1,cv2.LINE_AA);
    #     # rio_contours=[left_top,right_top ,right_down,left_down]
    #     ##cv2.imshow("img_rail",img_line0)
    #     ##cv2.waitKey(0)
    #     # contours,heridency=cv2.findContours(img_line0,  cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE);
    #     ##过滤外轮廓
    #     # contours_large=[x for x in contours if x.size>=500  ]
    #
    #     ##过滤外轮廓
    #     # image_black = np.zeros([rows_number,cols_number,1], np.uint8)
    #     # img_contours = cv2.drawContours(image_black, contours_large, -1, 255, 6)
    #     # img_result=cv2.bitwise_and(img_rail_gray, img_contours)
    #
    #     end = time.time()
    #     # print(f'Running time: {end - start:.3f} Seconds')
    #     return img_rail_gray

    def mergerLines_by_angle(self, lines):
        angles_of_Line_dict = {}
        # 遍历每条线，如果有足够间距的新angle就用较长的直线替代原来的直线
        for line_this in lines:
            line_complex, line_length, line_angle_deg = self.common_function.angle_line(line_this)
            # 处理相近角度的直线
            angle_list_near = [x for x in angles_of_Line_dict.keys() if
                               abs(line_angle_deg - x) % 90 < self.angle_threshold_merge]
            if len(angles_of_Line_dict) == 0 or len(angle_list_near) == 0:
                # 没有角度相近的直线，添加
                angles_of_Line_dict[line_angle_deg] = [line_this, line_length]
            elif len(angle_list_near) > 0:
                # 有相近的角度，如果更长，则更新，否则跳过
                for angle in angle_list_near:
                    if line_length > angles_of_Line_dict[angle][1]:
                        angles_of_Line_dict.pop(angle)
                        angles_of_Line_dict[line_angle_deg] = [line_this, line_length]
        list_return = [angles_of_Line_dict[x][0] for x in angles_of_Line_dict.keys()]
        return list_return

    def filterLines_by_deltaXY(self, lines):
        try:
            return [x for x in lines if
                    abs(x[0][1] - x[0][3]) > self.delta_Y_min and abs(x[0][0] - x[0][2]) > self.delta_X_min]
        except:
            return []

    # def filterLines_by_region(self, lines, ):
    #     if len(lines) > 0 and len(self.region_pts_list) >= 3:
    #         region_pts_list_pixel = self.get_pixel()
    #         region_contour = np.array(region_pts_list_pixel, np.int32)
    #         lines_result = []
    #         for line in lines:
    #             retval_1 = cv2.pointPolygonTest(region_contour, (int(line[0][0]), int(line[0][1])),
    #                                             False);  # 需要用int()转换一下，不然报错
    #             retval_2 = cv2.pointPolygonTest(region_contour, (int(line[0][2]), int(line[0][3])),
    #                                             False);  # 需要用int()转换一下，不然报错
    #             if retval_1 >= 0 and retval_2 >= 0:
    #                 lines_result.append(line)
    #         return lines_result
    #         # retval_1=cv2.pointPolygonTest(region_contour, (150,150), False)
    #     elif len(self.region_pts_list) < 3:
    #         return lines
    #     else:
    #         return []

    def filterLines_history(self, lines):
        """
        缓存10次lines历史记录，选择最大重叠lines输出
        """
        if len(lines) >= 2:
            self.lineHistory.append(lines)
        if len(self.lineHistory) > 10:
            self.lineHistory.pop(0)
        if len(self.lineHistory) > 0:
            line_score_list = [self.common_function.overlap_y(line_couple[0], line_couple[1]) for line_couple in
                               self.lineHistory]
            lines_out = self.lineHistory[line_score_list.index(max(line_score_list))]
            return lines_out
        else:
            return []

    def get_pixel(self):
        region_pts_list_pixel = []
        for pts in self.region_pts_list:
            region_pts_list_pixel.append([int(pts[0]), int(pts[1])])
        return region_pts_list_pixel

    # def detect_line(self, img_rail):
    #     img_gray = self.get_gray_contour_img(img_rail)
    #     if len(self.region_pts_list) >= 4:
    #         region_pts_list_pixel = self.get_pixel()
    #         region_contour = np.array(region_pts_list_pixel, np.int32)
    #         im_zeros = np.zeros([img_rail.shape[0], img_rail.shape[1]], dtype=np.uint8)
    #         cv2.fillPoly(im_zeros, [region_contour], 255)
    #         img_gray = cv2.bitwise_and(img_gray, im_zeros)
    #     if __name__ == '__main__' or 1:
    #         # cv2.imshow("img_gray", img_gray)
    #         # cv2.waitKey(10)
    #         pass
    #     lines = cv2.HoughLinesP(img_gray, 1, self.angle_theta * np.pi / 180, self.gray_threshold,
    #                             minLineLength=self.minLineLength, maxLineGap=self.maxLineGap)
    #     lines = self.filterLines_by_deltaXY(lines)
    #     lines = self.filterLines_by_region(lines)
    #     lines = self.mergerLines_by_angle(lines)
    #     lines = self.filterLines_history(lines)
    #     self.lines = lines
    #
    #     vanishing_point_list=[]
    #     if len(self.lines) == 2:
    #         self.common_function.addLines_in_image(img_rail, self.lines)
    #         crossPoint = self.common_function.getCrossPoint(self.lines[0], self.lines[1])
    #         return (int(crossPoint[0]), int(crossPoint[1]))
    #
    #     return None


class Convertor_pkl_json:
    def __init__(self):
        self.handler_pkl = None
        self.handler_json = None

    def convert_pkl2json(self, file_path_source=os.path.join("..", "config", "calibration.pkl"), file_path_des=None,
                         remove_source_file=False):
        # 读取数据，将pkl转化为json
        if file_path_source.endswith("pkl"):
            self.handler_pkl = File_Saver_Loader_pkl(file_path_source)
            data_dict = self.handler_pkl.load_from_file()
            # 转存为json文件
            if file_path_des is None:
                file_folder, file_name = os.path.split(file_path_source)
                file_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path_des = os.path.join(file_folder, file_name.replace("pkl", f"{file_time}.json"))
            print(f"convert_pkl2json {file_path_source}>>>{file_path_des}")
            self.handler_json = File_Saver_Loader_json(file_path_des)
            self.handler_json.save_to_file(data_dict)
        # 读取数据，将json转化为pkl
        elif file_path_source.endswith("json"):
            self.handler_json = File_Saver_Loader_json(file_path_source)
            data_dict = self.handler_json.load_from_file()
            # 转存为pkl文件
            if file_path_des is None:
                file_folder, file_name = os.path.split(file_path_source)
                file_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path_des = os.path.join(file_folder, file_name.replace("json", f"{file_time}.pkl"))
            print(f"convert_pkl2json {file_path_source}>>>{file_path_des}")
            self.handler_pkl = File_Saver_Loader_pkl(file_path_des)
            self.handler_pkl.save_to_file(data_dict)
        if remove_source_file:
            os.remove(file_path_source)
            print(f"{datetime.datetime.now()}, convert_pkl2json remove_file={file_path_source}")

def test_get_pixel_xywh():
    calibration_result = CalibrationResult()
    calibration_result.get_pixel_xywh([1, 1])


if __name__ == '__main__':
    """
     [[1.567434783401315, 0], [5.4872486615036635, 311.63197440629847], [9.439469165754913, 347.49156146051837], [3.363843397654081, 61.08160269395686], [2.884129473440093, 0]], 
    """
    test_get_pixel_xywh()
    aPoints = [[-2.821067250747054, 0], [-2.6696861594284447, 95.92831723613948],
               [3.6179264781951446, 96.27536761662577], [2.9001686622189324, 0]]
    # vTarget = [33.66478674809094, -876.3191697016006]
    vTarget = [0, 45]
    func = Common_Function()
    # result = IsPointInConvexSinglePolygon(aPoints, vTarget)
    result = func.checkPP(vTarget, aPoints)
    print(result)
