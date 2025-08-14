import cv2 as cv
import numpy as np

img = np.zeros((450, 800, 3), np.uint8)  # ⽣成⼀个空灰度图像
print(img.shape)  # 输出：(480, 480, 3)

a_point_list=[(157, 128), (157, 245), (197, 245), (197, 128)]
b_point_list=[(13, 445), (11, 400), (418, 219), (564, 216), (540, 447)]

point_size = 1
point_color = (0, 255, 0)  # BGR
thickness = 4  # 可以为 0 、4、8

fontFace = cv.FONT_HERSHEY_PLAIN
fontScale = 0.5
thickness_text = 1
lineType = 4
bottomLeftOrigin = 1
# 要画的点的坐标
for point in a_point_list:
    cv.circle(img, point, point_size, point_color, thickness)
    org = [point[0], point[1] - 10, ]
    cv.putText(img, f"{point}", org, fontFace, fontScale, point_color, thickness_text, lineType)

point_color = (0, 0, 255)  # BGR
# 要画的点的坐标
for point in b_point_list:
    cv.circle(img, point, point_size, point_color, thickness)
    org = [point[0], point[1] - 10, ]
    cv.putText(img, f"{point}", org, fontFace, fontScale, point_color, thickness_text, lineType)


    # 画圆，圆⼼为：(160, 160)，半径为：60，颜⾊为：point_color，实⼼线
cv.namedWindow("image")
cv.imshow('image', img)
cv.waitKey(20000)  # 显⽰ 10000 ms 即 10s 后消失
cv.destroyAllWindows()
