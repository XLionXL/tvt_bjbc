#!/bin/bash
time=$(date "+%Y%m%d-%H%M%S")
cd /usr/bin/zipx/zj-guard
cd /usr/bin/zipx/zj-guard
#/usr/bin/python3 /usr/bin/zipx/zj-guard/python3_main_py.py
python3 main.py >/usr/bin/zipx/log/guard-"${time}".log
