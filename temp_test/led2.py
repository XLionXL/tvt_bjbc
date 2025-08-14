import datetime
import os.path
import platform
import time

camera_data = {
    "id": 2, "timestamp": 1616575744964,
    "data": [{"confidence": 0.828893244, "class": 0, "bbox": [306, 172, 25, 64]},
             {"confidence": 0.689129949, "class": 0, "bbox": [310, 157, 12, 26]},
             {"confidence": 0.789129949, "class": 0, "bbox": [310, 157, 12, 26]}
             ]
}


def so_add_test():
    import ctypes
    if "Windows" not in platform.platform():
        so_path = os.path.abspath(os.path.join("/home/pi/work", "raspberry-test.so"))
        if os.path.exists(so_path):
            print(f"{datetime.datetime.now()},so_add_test start {so_path} ")
            # so_face = ctypes.CDLL(so_path)
            # so_face.StartImgBase64Send(6055)
            so_face = ctypes.cdll.LoadLibrary(so_path)
            sum = so_face.add_test(2, 5525)
            print(f"add_test(2, 5525) sum= {sum}")
    else:
        print(f"{datetime.datetime.now()},so_add_test skipped")
    time.sleep(1)


def so_htra_test():
    import ctypes
    if "Windows" not in platform.platform():
        so_path = os.path.abspath(os.path.join("/usr/lib", "libhtraapi.so"))
        if os.path.exists(so_path):
            print(f"{datetime.datetime.now()},so_htra_test start {so_path} ")
            # so_face = ctypes.CDLL(so_path)
            # so_face.StartImgBase64Send(6055)
            so_face = ctypes.cdll.LoadLibrary(so_path)
            # sum = so_face.add_test(2, 5525)
            # print(f"add_test(2, 5525) sum= {sum}")
    else:
        print(f"{datetime.datetime.now()},so_htra_test skipped")
    time.sleep(1)

# 程序入口
if __name__ == "__main__":
    print(camera_data)
    confi_list = camera_data["data"]
    print("after")
    confi_list.sort(key=lambda obj: obj["confidence"], reverse=True)
    print(confi_list)
    path="/usr/lib/libhtraapi.so"
    print(f"path exist={os.path.exists(path)}")
    so_add_test()
    so_htra_test()

