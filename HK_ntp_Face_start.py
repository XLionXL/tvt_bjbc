import datetime
import os
import platform
import threading
import time


class HK_ntp_Face_start:
    def __init__(self):
        self.so_folder='/usr/bin/zipx/zj-guard-so'
        pass

    def hk_ntp_face_process_start(self, ):
        print(f"{datetime.datetime.now()},hk_ntp_face_process_start")

        thread_ntp = threading.Thread(target=self.hk_ntp_process_task, daemon=False,name=   "x5")
        thread_ntp.start()

        thread_face = threading.Thread(target=self.face_process_task, daemon=False,name=   "x6")
        thread_face.start()

    def hk_ntp_process_task(self):
        import ctypes
        if "Windows" not in platform.platform():
            so_path = os.path.abspath(os.path.join(self.so_folder, 'libNtpSetCameratime.so'))
            if os.path.exists(so_path):
                print(f"{datetime.datetime.now()},hk_ntp_process_task start {so_path} ")
                so_ntp = ctypes.CDLL(so_path)
                so_ntp.NtptimetoCamera(30)
            else:
                print(f"{datetime.datetime.now()},{so_path} not exists,error")
        else:
            print(f"{datetime.datetime.now()},hk_ntp_process_task skipped")
        time.sleep(1)

    def face_process_task(self):
        import ctypes
        if "Windows" not in platform.platform():
            so_path = os.path.abspath(os.path.join(self.so_folder, "libImgBase64Send.so"))
            if os.path.exists(so_path):
                print(f"{datetime.datetime.now()},face_process_task start {so_path} ")
                # so_face = ctypes.CDLL(so_path)
                # so_face.StartImgBase64Send(6055)
                so_face = ctypes.cdll.LoadLibrary(so_path)
                nanoip = os.path.join(self.so_folder,"nanoip.xml")
                strs = bytes(nanoip, 'utf-8')
                so_face.StartImgBase64Send(ctypes.c_char_p(strs), 5525)
        else:
            print(f"{datetime.datetime.now()},face_process_task skipped")
        time.sleep(1)


if __name__=="__main__":

    hk_ntp = HK_ntp_Face_start()
    hk_ntp.hk_ntp_face_process_start()
