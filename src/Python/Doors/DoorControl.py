import time

import nidaqmx
import numpy as np

from src.Python.Settings import Settings


class DoorControl:

    def __init__(self, door_status, light_status, finishFlag):
        self.step_nr = 0
        self.door_status = door_status
        self.light_status = light_status
        self.last_status = np.array(door_status)
        self.nr_of_doors = len(Settings.doors)
        self.door_names = DoorControl.getDoorNames()
        self.task = nidaqmx.Task()
        self.task1 = None
        self.finishFlag = finishFlag
        self.setDoors()
        self.MainLoop()

    @staticmethod
    def getDoorNames():
        return sorted(Settings.doors.keys())

    @staticmethod
    def getDoorIndex(name, door_names):
        return door_names.index(name)

    def _getDoorIndex(self, name):
        return DoorControl.getDoorIndex(name, self.door_names)

    def setLamps(self):
        self.task1 = nidaqmx.Task()
        for l in range(4):
            self.task1.do_channels.add_do_chan("Dev1/port1/line%d" % l)
        self.task1.start()

    def setDoors(self):
        # CODE VERSION FOR 6 DOORS:
        for i in range(self.nr_of_doors):
            door_name = self.door_names[i]
            # print (Settings.doors)
            ch_id = Settings.doors[door_name]
            # print ("Opening Dev1/port0/%s"%ch_id,door_name,ch_id)
            self.task.do_channels.add_do_chan("Dev1/port0/%s" % ch_id)
        self.task.start()

        # CODE VERSION FOR 7 DOORS
        # for i in range(self.nr_of_doors):
        # if door_name in Settings.doors:
        # ch_info = Settings.doors[door_name]
        # if 'channel' in ch_info and 'type' in ch_info:
        # ch_id = ch_info['channel']

        # elif door_name == "D7" and ch_info['type'] == 'DO':
        # self.task.do_channels.add_do_chan("Dev1/port2/%s" % ch_id)
        # if ch_info['type'] == 'DO': #here depending whether you use condition in line 59. If you use line 59 then conditional is "elif", but if you do not use line 49 it the conditinal should be "if"
        # self.task.do_channels.add_do_chan("Dev1/port0/%s" % ch_id)
        # else:
        # print(f"Invalid channel type '{ch_info['type']}' for door {door_name}. Skipping...")
        # Else:
        # print(f"Channel information incomplete for door {door_name}. Skipping...")
        # else:
        # print(f"Door name {door_name} not found in doors dictionary. Skipping...")
        # self.task.start()

        self.setLamps()
        val = []
        for i in range(self.nr_of_doors):
            door_name = self.door_names[i]
            self.door_status[i] = Settings.initDoorsPos[door_name]
            print("Initial setting for ", door_name, Settings.initDoorsPos[door_name])

        for i in range(4):
            self.light_status[i] = 0

    def MainLoop(self):
        while True:
            time.sleep(Settings.DCntrlTime)
            self.CheckStatusChange()
            self.sendStatus()
            self.step_nr = self.step_nr + 1
            if self.finishFlag.is_set():
                break

    def CheckStatusChange(self):
        for i in range(self.nr_of_doors):
            if self.last_status[i] != self.door_status[i]:
                print(self.door_names[i])
                if (self.door_names[i]) not in ["L1", "L2"]:
                    if self.door_status[i] == 1:
                        print("Opening doors=", self.door_names[i])
                    if self.door_status[i] == 0:
                        print("Closing doors=", self.door_names[i])
                else:
                    print("Opening doors=", self.door_names[i])
                    self.sendStatus()
                    if self.door_names[i] == "L1":
                        time.sleep(Settings.LTime1)
                    if self.door_names[i] == "L2":
                        time.sleep(Settings.LTime2)
                    self.door_status[i] = 0
                    print("Closing doors=", self.door_names[i])
                    self.sendStatus()

            self.last_status[i] = self.door_status[i]

    def sendStatus(self):
        if Settings.lightFlash == True:
            lightFlag = (int(self.step_nr / Settings.lightFlash_step) % 2)
        else:
            lightFlag = 1
        val = []
        for i in range(self.nr_of_doors):
            val.append(bool(self.door_status[i]))
        self.task.write(val)

        val = []
        for i in range(4):
            if ((i + 1) not in Settings.lightFlashEXC):
                val.append(bool(self.light_status[i] * lightFlag))
            else:
                val.append(bool(self.light_status[i]))
        self.task1.write(val)
