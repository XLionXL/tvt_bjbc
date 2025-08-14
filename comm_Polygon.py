# from shapely.geometry import Polygon
import os
import platform
import time
import traceback
from ctypes import CDLL, c_int, c_float, c_bool, POINTER


class Polygon_zzl:
    print_cnt = 0
    inside = None

    @staticmethod
    def init_inside_so():
        if Polygon_zzl.inside is None:
            platform_str = platform.platform()[0:15]
            inside_path = os.path.join(".", "/lss/guard_tvt-BJCOMP2025","dependent", f'inside_{platform_str}.so')
            # inside_path = os.path.join(".", "dependent", f'inside_Linux-4.9.201-t.so')
            inside_path_abs = os.path.abspath(inside_path)
            inside_path_abs = "/ssd/lss/guard_tvt-BJCOMP2025/dependent/inside_Linux-4.9.201-t.so"
            print(f"Polygon_zzl inside_path={inside_path_abs}")
            Polygon_zzl.inside = CDLL(inside_path_abs).inside  # 加载inside.so
            Polygon_zzl.inside.argtypes = [c_float, c_float, c_int, POINTER(c_float * 2)]
            Polygon_zzl.inside.restype = c_bool

    @staticmethod
    def intersects(a_point_list, b_point_list):
        try:
            result = False
            for point in a_point_list:
                if Polygon_zzl.isPointIntersectPoly_by_so(point, b_point_list):
                    result = True
                    break
            for point in b_point_list:
                if Polygon_zzl.isPointIntersectPoly_by_so(point, a_point_list):
                    result = True
                    break
            if result and Polygon_zzl.print_cnt < 20:
                print(f"intersects {Polygon_zzl.print_cnt}/20,a={a_point_list}, b={b_point_list},result={result}")
                Polygon_zzl.print_cnt += 1
            return result
        except:
            print(f"Polygon_zzl intersects error,a_point_list={a_point_list},b_point_list={b_point_list} {traceback.format_exc()}")

    @classmethod
    def isPointIntersectPoly_by_so(self, point, polygon):
        polyNum = len(polygon)
        point_xy_list = [(xy[0], xy[1]) for xy in polygon]
        # 将python列表结构转换为c语言下的数组
        egde = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in point_xy_list))
        return Polygon_zzl.inside(float(point[0]), float(point[1]), polyNum, egde)


    @staticmethod
    def __isRayInSegment(poi, start_poi, end_poi):
        # 输入：判断点，边起点，边终点，都是[lng,lat]格式数组
        #
        # https://cloud.tencent.com/developer/article/1515808
        poi_x, poi_y = poi
        ray_end = (9e100, poi_y)
        if start_poi[1] == end_poi[1]:  # 排除与射线平行、重合，线段首尾端点重合的情况
            return False
        if start_poi[1] > poi[1] and end_poi[1] > poi[1]:  # 线段在射线上边
            return False
        if start_poi[1] < poi[1] and end_poi[1] < poi[1]:  # 线段在射线下边
            return False
        if start_poi[1] == poi[1] and end_poi[1] > poi[1]:  # 交点为下端点，对应start_point
            return False
        if end_poi[1] == poi[1] and start_poi[1] > poi[1]:  # 交点为下端点，对应end_point
            return False
        if start_poi[0] < poi[0] and end_poi[0] < poi[0]:  # 线段在射线左边
            return False
        xseg = end_poi[0] - (end_poi[1] - poi[1]) * (end_poi[0] - start_poi[0]) / (end_poi[1] - start_poi[1])  # 求交
        if xseg < poi[0]:  # 交点在射线起点的左侧,不算
            return False
        return True  # 排除上述情况之后

    @staticmethod
    def isPointIntersectPoly(poi, poly):
        # 输入：点，多边形
        # poly=[[x1,y1],[x2,y2],...,[xn,yn]] 点列表
        in_cnt = 0  # 交点个数
        length_of_poly=len(poly)
        for index, start_point in enumerate(poly):  # 循环每条边的曲线->each polygon 是二维数组[[x1,y1],…[xn,yn]]
            end_point = poly[(index + 1) % length_of_poly]
            if Polygon_zzl.__isRayInSegment(poi, start_point, end_point):
                in_cnt += 1  # 有交点就加1
        return True if in_cnt % 2 == 1 else False


def test_intersects(a_point_list, b_point_list, num=1):
    start = time.time()
    for i in range(num):
        Polygon_zzl.intersects(a_point_list, b_point_list)
    end = time.time()
    print("duration3: ", end - start)
    # 20230711 临时调试
    for a_point in a_point_list:
        Polygon_zzl.isPointIntersectPoly_by_so(a_point, b_point_list)


def inside_so_polygon_test():
    print(f"platform={platform.platform()}")
    Polygon_zzl.init_inside_so()
    polygon = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    polyNum = len(polygon)
    # 将python列表结构转换为c语言下的数组
    polygon_c = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in polygon))
    for index_in in range(20):
        x, y = -0.5 + index_in * 0.1, 0.5
        is_inside = 1 if Polygon_zzl.inside(x, y, polyNum, polygon_c) else 0
        print(f"{is_inside}", end=" ")
    print(f"inside_so_polygon_test end")
    for index_in in range(20):
        point_xy = -0.5 + index_in * 0.1, 0.5
        is_inside = 1 if Polygon_zzl.isPointIntersectPoly(point_xy,  polygon) else 0
        print(f"{is_inside}", end=" ")
    print(f"polygon_test end")


def inside_so_polygon_speed_test(num_cnt=10000):
    # 使用so方法的速度测试
    start = time.time()
    Polygon_zzl.init_inside_so()
    polygon = [(0, 0), (0, 1), (1, 1), (1, 0)]
    polyNum = len(polygon)
    # 将python列表结构转换为c语言下的数组
    polygon_c = (c_float * 2 * polyNum)(*(tuple(j for j in i) for i in polygon))
    for index in range(num_cnt):
        for index_in in range(20):
            x, y = -0.5 + index_in * 0.1, 0.5
            is_inside = 1 if Polygon_zzl.inside(x, y, polyNum, polygon_c) else 0
    end = time.time()
    print("inside_so_polygon_speed_test by inside_so: ", end - start)
    # 不使用so方法的速度测试
    start = time.time()
    polygon = [(0, 0), (0, 1), (1, 1), (1, 0)]
    for index in range(num_cnt):
        for index_in in range(20):
            point_xy = -0.5 + index_in * 0.1, 0.5
            is_inside = 1 if Polygon_zzl.isPointIntersectPoly(point_xy,  polygon) else 0
    end = time.time()
    print("inside_so_polygon_speed_test no so: ", end - start)


if __name__ == "__main__":
    inside_so_polygon_test()
    inside_so_polygon_speed_test(num_cnt=10000)

    polygon1_pointList = [(0, 0), (0, 1), (1, 1), (1, 0)]
    polygon2_pointList = [(0.3, 0.3), (0, 1), (1, 1), (0.8, 0)]
    test_intersects(polygon1_pointList, polygon2_pointList, )

    a_point_list = [(157, 128), (157, 245), (197, 245), (197, 128)]
    b_point_list = [(13, 445), (11, 400), (418, 219), (564, 216), (540, 447)]
    test_intersects(a_point_list, b_point_list, )

    a_point_list = [(157, 128), (157, 245), (197, 400), (197, 128)]
    b_point_list = [(13, 445), (11, 400), (418, 219), (564, 216), (540, 447)]
    test_intersects(a_point_list, b_point_list, )
