# coding:utf-8
import datetime
import os
import platform
import serial
import time

from comm_decoder_radar import Decoder_Radar


def serial_test(portName="/dev/ttyTHS2", time_s=60):
    print(f"serial test at {portName},time_s={time_s}")
    if "Windows" not in platform.platform():
        os.system(f"echo 'king' | sudo -S chmod 777 {portName}")
    serial_handle = serial.Serial(port=portName, baudrate=115200,
                                 bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE, )
    print(f"serial open {portName} ", __file__)
    time_start = time.time()
    send_time_stamp=None
    decoder=Decoder_Radar()
    while time.time() - time_start <= time_s:
        time.sleep(0.1)
        data_bytes=serial_handle.read_all()
        if isinstance(data_bytes, bytes) and len(data_bytes) > 0:
            print(datetime.datetime.now(), portName,"".join(['%02X' % x for x in data_bytes]))
        if send_time_stamp is None or time.time()-send_time_stamp>10:
            data_write=decoder.gen_frame(b'\x00\x42\x00\x00\x00\x04\x00\x00\x00\x00', "little")
            serial_handle.write(data_write)
            serial_handle.write(data_write)
            serial_handle.write(data_write)
            data_write_str="".join(['%02X' % x for x in data_write])
            print(datetime.datetime.now(), portName, f"data_write_str={data_write_str}")
            send_time_stamp=time.time()
    serial_handle.close()

if __name__=="__main__":
    # portName="/dev/ttyTHS2" #雷达
    # serial_test(portName)

    if "Windows" in platform.platform():
        portName = "COM1"  # MCU
    else:
        portName = "/dev/ttyTHS1"  # MCU
        portName = "/dev/ttyTHS2"  # Radar

    serial_test(portName)
