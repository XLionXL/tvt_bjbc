


import cv2 as cv
import numpy as np

# 创建一个黑色的图像
s=0
for i in range(1,2):
    s=i*50
    image = np.zeros(( 600,1000, 3), dtype="uint8")
    cv.rectangle(image, (50+s, 50), (80+s, 100), (255, 255, 255), -1)
    # cv.rectangle(image, (50, 400), (500, 200), (255, 255, 255), -1)
    # cv.imwrite(f"./diffData/2/{i}.1.png", image)
    cv.imshow("Image", image)
    # cv.waitKey(0)

# 保存图像时不进行压缩
# cv.imwrite("./diffData/rectangle_no_compression.jpg", image)
# print(np.unique(cv.imread("./diffData/rectangle_no_compression.jpg")))

# 显示图像
cv.imshow("Image", image)
cv.waitKey(0)
