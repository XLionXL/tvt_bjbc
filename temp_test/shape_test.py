import time
from comm_Polygon import Polygon_zzl
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

point = Point(0.5, 0.5)
polygon1_pointList = [(0, 0), (0, 1), (1, 1), (1, 0)]
polygon1 = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])

polygon2_pointList = [(0.3, 0.3), (0, 1), (1, 1), (0.8, 0)]
polygon2 = Polygon([(0.3, 0.3), (0, 1), (1, 1), (0.8, 0)])

time.sleep(0.1)

start = time.time()
for i in range(1000):
    polygon1.contains(point)
end = time.time()

print("duration1: ", end - start)


start = time.time()
for i in range(1000):
    polygon1.intersects(polygon2)
end = time.time()
print("duration2: ", end - start)


start = time.time()
for i in range(1000):
    Polygon_zzl.intersects(polygon2_pointList, polygon1_pointList)
end = time.time()
print("duration3: ", end - start)