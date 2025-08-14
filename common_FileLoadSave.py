# coding:utf-8
import datetime
import json
import os
import traceback


class File_Saver_Loader_SN:
    def __init__(self, file_path=os.path.join("service", "sn")):
        self.file_path = os.path.abspath(file_path)
        self.class_name = "File_Saver_Loader_SN"
        print(f"File_Saver_Loader_SN file_path={self.file_path}")

    def save_to_file(self, data):
        print(f"{datetime.datetime.now()},File_Saver_Loader_SN,save_to_file,{self.file_path}")
        with open(self.file_path, "w") as f:
            f.write(data)

    def load_from_file(self, ):
        print(f"{datetime.datetime.now()},File_Saver_Loader_SN,load_from_file,{self.file_path}")
        with open(self.file_path, "rt") as f:
            data = f.read()
        return data


class File_Saver_Loader_pkl:
    def __init__(self, file_path=os.path.join("service", "default.pkl")):
        self.file_path = os.path.abspath(file_path)
        self.class_name = "File_Saver_Loader_pkl"
        print(f"File_Saver_Loader_pkl file_path={self.file_path}")

    def save_to_file(self, data):
        import pickle
        print(f"{datetime.datetime.now()},File_Saver_Loader_pkl,save_to_file,{self.file_path}")
        with open(self.file_path, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    def load_from_file(self, ):
        import pickle
        print(f"{datetime.datetime.now()},File_Saver_Loader_pkl,load_from_file,{self.file_path}")
        with open(self.file_path, 'rb') as f:
            return pickle.load(f)


class File_Saver_Loader_npy():
    def __init__(self, file_path=os.path.join("service", "default.npy")):
        self.file_path = os.path.abspath(file_path)
        self.class_name = "File_Saver_Loader_npy"
        print(f"File_Saver_Loader_npy file_path={self.file_path}")

    def save_to_file(self, data):
        import numpy as np
        print(f"{datetime.datetime.now()},File_Saver_Loader_npy,save_to_file,{self.file_path}")
        np.save(self.file_path, data)

    def load_from_file(self, ):
        import numpy as np
        print(f"{datetime.datetime.now()},File_Saver_Loader_npy,load_from_file,{self.file_path}")
        return np.load(self.file_path, allow_pickle=True)


class File_Saver_Loader_json:
    def __init__(self, file_path=os.path.join("service", "sn")):
        self.file_path = os.path.abspath(file_path)
        self.class_name = "File_Saver_Loader_json"
        print(f"File_Saver_Loader_json file_path={self.file_path}")

    def save_to_file(self, data):
        print(f"{datetime.datetime.now()},File_Saver_Loader_json,save_to_file,{self.file_path}")
        with open(self.file_path, "wt") as file:
            json.dump(data, file)

    def load_from_file(self):
        print(f"{datetime.datetime.now()},File_Saver_Loader_json,load_from_file,{self.file_path}")
        if not os.path.exists(self.file_path):
            print(f"{datetime.datetime.now()},File_Saver_Loader_json,path error, not exist path={self.file_path}")
            return None
        try:
            with open(self.file_path, "rt") as file:
                data = json.load(file)
        except Exception as err:
            print(f"load_from_file error, path={self.file_path},{err}")
            traceback.print_exc()
            return None
        return data


def test_sn():
    sn_file_path = os.path.join(os.path.dirname(os.path.abspath("")), "sn")
    print(sn_file_path)
    if os.path.exists(sn_file_path):
        sn_reader = File_Saver_Loader_SN(sn_file_path)
        print(f"sn={sn_reader.load_from_file()}")


def test_json():
    json_file_path = os.path.join(os.path.dirname(os.path.abspath("")), "test.json")
    print(f"json_file_path={json_file_path}")
    json_reader = File_Saver_Loader_json(json_file_path)
    data_save = {
        1: "12",
        2: "2",
        3: "3",
        # "sdfsa": "fsdt"
    }
    json_reader.save_to_file(data_save)
    if os.path.exists(json_file_path):
        data_load=json_reader.load_from_file()
        print(f"load_from_file={data_load}")


if __name__ == "__main__":
    test_json()
