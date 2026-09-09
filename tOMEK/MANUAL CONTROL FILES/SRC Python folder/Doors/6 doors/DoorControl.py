import time

import nidaqmx
import numpy as np

from src.Python.Loger.Loger import Loger
from src.Python.Settings import Settings


class DoorControl(Loger):

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
        return (door_names.index(name))

    def _getDoorIndex(self, name):
        return (DoorControl.getDoorIndex(name, self.door_names))

    def setLamps(self):
        self.task1 = nidaqmx.Task()
        for l in range(4):
            self.task1.do_channels.add_do_chan("Dev1/port1/line%d" % l)
        self.task1.start()

    def setDoors(self):
        for i in range(self.nr_of_doors):
            door_name = self.door_names[i]
            # print (Settings.doors)
            ch_id = Settings.doors[door_name]
            # print ("Opening Dev1/port0/%s"%ch_id,door_name,ch_id)
            self.task.do_channels.add_do_chan("Dev1/port0/%s" % ch_id)
        self.task.start()
        self.setLamps()
        val = []
        for i in range(self.nr_of_doors):
            door_name = self.door_names[i]
            self.door_status[i] = Settings.initDoorsPos[door_name]
            self.loger("inital setting for ", door_name, Settings.initDoorsPos[door_name])
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
                self.loger(self.door_names[i])
                if (self.door_names[i]) not in ["L1", "L2"]:
                    if self.door_status[i] == 1:
                        self.loger("Opening doors=", self.door_names[i])
                    if self.door_status[i] == 0:
                        self.loger("Closing doors=", self.door_names[i])
                else:
                    self.loger("Opening doors=", self.door_names[i])
                    self.sendStatus()
                    if self.door_names[i] == "L1":
                        time.sleep(Settings.LTime1)
                    if self.door_names[i] == "L2":
                        time.sleep(Settings.LTime2)
                    self.door_status[i] = 0
                    self.loger("Closing doors=", self.door_names[i])
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
