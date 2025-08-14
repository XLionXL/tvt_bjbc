import datetime
import json
import os
import os.path


class CONFIG_FILE:
    def __init__(self, file_folder=".", file_name='config.txt'):
        self.class_name="CONFIG_FILE"
        self.file_folder=file_folder
        self.file_name=file_name
        file_path = os.path.join(self.file_folder, self.file_name)
        self.config = None
        if os.path.exists(file_path):
            self.load()

    def save(self):
        if not os.path.exists(self.file_folder):
            os.makedirs(self.file_folder)
        file_path = os.path.join(self.file_folder, self.file_name)
        with open(file_path, 'a', encoding='utf8') as f:
            f.write(json.dumps(self.config))

    def load(self):
        file_path = os.path.join(self.file_folder, self.file_name)
        if not os.path.exists(file_path):
            print(f"{datetime.datetime.now()},{self.class_name},file not exist error,file_path={file_path}")
            return None
        with open(file_path, 'r', encoding='utf8') as f:
            config_str=f.read()
            self.config=json.loads(config_str)
        print(f"{datetime.datetime.now()},{self.class_name},config load from,file_path={file_path}")
        return self.config


if __name__ == "__main__":
    debug_config = CONFIG_FILE("service", "debug_config.ini")
    debug_config.load()
    print(f"debug_config.config={debug_config.config}",)
    # debug_config.save()

