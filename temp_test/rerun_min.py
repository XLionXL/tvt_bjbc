#!/usr/bin/env python3

"""Demonstrates the most barebone usage of the Rerun SDK."""
import math
import numpy as np
import rerun as rr  # pip install rerun-sdk
import time

_, unknown = __import__("argparse").ArgumentParser().parse_known_args()
[__import__("logging").warning(f"unknown arg: {arg}") for arg in unknown]

rr.init("minimal2", spawn=True)

positions = np.vstack([xyz.ravel() for xyz in np.mgrid[3 * [slice(-10, 10, 10j)]]]).T
colors = np.vstack([rgb.ravel() for rgb in np.mgrid[3 * [slice(0, 255, 10j)]]]).astype(np.uint8).T
rr.log_points("my_points", positions=positions, colors=colors, radii=0.5)
#
radar_points=[]
camera_points=[]
for index in range(100):
    radar_point = [index, 10 * math.sin(0.1 * index), 0]
    camera_point = [index * 2, 10 * math.cos(0.2 * index), 1]
    radar_points.append(radar_point)
    camera_point.append(camera_points)
# rr.set_time_seconds("sim_time", 1)
rr.log_points("radar_points", positions=radar_points, radii=0.2)
time.sleep(1)
# rr.set_time_seconds("sim_time", 2)
rr.log_points("camera_points", positions=camera_points, radii=0.2)
time.sleep(1)
rr.log_points("camera_points2", positions=camera_points, radii=0.2)
