import datetime
import json
import time

from common_hysteresis_threshold import EDGE_DETECT


class Monitor_alarm_Event:
    def __init__(self):
        self.edger = EDGE_DETECT(False)
        self.pic_list = []
        self.start_time = datetime.datetime.now()
        self.end_time = datetime.datetime.now()
        self.report_event_callback = None
        self.alarm_type = 1
        self.alarm_list=[]
        self.is_edge_rise = False
        self.is_edge_fall = False
        print(f"{datetime.datetime.now()},Monitor_alarm_Event, init")

    def update_alarm_state(self, alarm_type=0):
        isAlarm = alarm_type>0
        if self.edger.is_Edge(isAlarm):
            if isAlarm:
                self.start_time = datetime.datetime.now()
                self.alarm_type = alarm_type
                self.is_edge_rise = True
                self.is_edge_fall = False
            else:
                self.end_time = datetime.datetime.now()
                report_json = self.gen_report_json()
                print(f"{datetime.datetime.now()},Monitor_alarm_Event, report={json.dumps(report_json)}")
                self.is_edge_rise = False
                self.is_edge_fall = True
                return report_json
        else:
            self.is_edge = False
        return None

    def gen_report_json(self):
        """
        
        :return: 
        """
        alarm_this = {
            "start_time": self.start_time.strftime("%Y%m%d_%H%M%S"),
            "end_time": self.end_time.strftime("%Y%m%d_%H%M%S"),
            "alarm_type": self._get_alarm_type()
        }
        alarm_report_out = {
            "alarm_this": alarm_this,
            "alarm_list": self.alarm_list,
        }
        self.alarm_list.append(alarm_this)
        if len(self.alarm_list) > 20:
            self.alarm_list.pop(0)
        return alarm_report_out

    def _get_alarm_type(self):
        if self.alarm_type>=4:
            return "joint_alarm"
        elif self.alarm_type==3:
            return "camera_radar_alarm"
        elif self.alarm_type==2:
            return "radar_alarm"
        elif self.alarm_type==1:
            return "camera_alarm"


if __name__ == "__main__":
    alarm_event = Monitor_alarm_Event()
    alarm_event.report_event_callback = print
    for i in range(30):
        time.sleep(1)
        alarm_event.update_alarm_state(10 <= i <= 20)
