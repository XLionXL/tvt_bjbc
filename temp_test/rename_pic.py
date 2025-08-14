import datetime
import os


def rename_pic_in_folder(folder=r"/ssd/alarmpic/farcamera_alarmpic", discard_str=":", replace_str=""):
    file_names = os.listdir(folder)
    print(f"{datetime.datetime.now()},rename_pic_in_folder,{folder},{discard_str}>>>{replace_str}")
    for old_name in file_names:
        new_name = old_name.replace(discard_str,replace_str)
        new_path = os.path.join(folder, new_name)
        old_path = os.path.join(folder, old_name)
        print(f"{old_path}>>>{new_path}")
        os.rename(old_path, new_path)


rename_pic_in_folder(r"/ssd/alarmpic/farcamera_alarmpic")
rename_pic_in_folder(r"/ssd/alarmpic/nearcamera_alarmpic")
