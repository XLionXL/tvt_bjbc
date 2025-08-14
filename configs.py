import datetime
import json
import os
import time
import yaml

default_modified_time = "00-00 00:00:00"


def get_modified_time(file_path):
    if not os.path.exists(file_path):
        return default_modified_time

    modified_time = time.localtime(os.path.getmtime(file_path))
    # print(modified_time)
    # return time.strftime('%Y-%m-%d %H:%M:%S', modified_time)
    return time.strftime('%m-%d %H:%M:%S', modified_time)


class BaseConfig(object):

    def __init__(self, config_path, config_desc=None):
        self.config_path: str = config_path
        self.config_desc = config_desc
        self.data = None
        self.modified_time = default_modified_time
        self.load()

    def load(self):
        if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
            self.load_yaml()
        else:
            self.load_json()
        self.modified_time = get_modified_time(self.config_path)
        if self.config_desc is not None:
            print(f"{self.config_desc} Load:{str(self)}")

    def load_yaml(self):
        try:
            with open(self.config_path, "r") as f:
                self.data = yaml.load(f, Loader=yaml.FullLoader)
            return True
        except Exception as e:
            print(e)
            return False

    def save(self, data):
        try:
            self.data = data
            if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
                return self.save_yaml(data)
            else:
                return self.save_json(data)
        finally:
            self.modified_time = get_modified_time(self.config_path)

    def save_yaml(self, data):
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(data, f)
                f.flush()
                f.close()
            return True
        except Exception as e:
            print(e)
            return False

    def load_json(self):
        try:
            if not os.path.exists(self.config_path):
                print(f"error! file not exists,{self.config_path}")
                ex=Exception(f"file not exist,{self.config_path}")
                raise ex
            with open(self.config_path, "r") as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(e)
            return False

    def save_json(self, data):
        try:
            with open(self.config_path, "w+") as f:
                json.dump(data, f)
                f.flush()
                f.close()
            print(f"{datetime.datetime.now()},save_json,file_path={self.config_path}")
            return True
        except Exception as e:
            print(e)
            return False

    def __str__(self):
        if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
            return yaml.safe_dump(self.data)
        else:
            return json.dumps(self.data,  ensure_ascii=False)

    def save_from_str(self, data_str):
        new_data = None
        try:
            if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
                new_data = yaml.safe_load(data_str)
            else:
                new_data = json.loads(data_str)
        except Exception as e:
            print(e)

        if new_data is None:
            return

        self.save(new_data)

