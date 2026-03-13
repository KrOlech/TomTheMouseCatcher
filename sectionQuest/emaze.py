import numpy as np
import multiprocessing
import cv2
from datetime import datetime
import time
import numpy
import random
import os
import Settings
from VideoCapture import VideoCapture
from Zones import Zones
from MainLoop_HabituationDD1 import MainLoop  # Line to choose the logic: from (insert logic name) import MainLoop
from DoorControl import DoorControl


class EMaze(MainLoop):
    def __init__(self):
        nr_of_zones = len(Settings.zones)
        nr_of_doors = len(Settings.doors)
        self.zone_activated = -1
        self.zone_deactivated = -1
        self.last_active_zone = -1
        self.which_logic_Set = multiprocessing.Value('i', 0)
        self.trial_nr = multiprocessing.Value('i', 0)
        self.active_zone = multiprocessing.Value('i', 0)
        self.zone_names = Zones(self.which_logic_Set, self.trial_nr).get_zone_names()
        self.door_names = DoorControl.getDoorNames()
        e = multiprocessing.Event()
        self.finishFlag = multiprocessing.Event()

        self.door_status = multiprocessing.Array('i', numpy.zeros(nr_of_doors, dtype=numpy.uint))
        self.light_status = multiprocessing.Array('i', numpy.zeros(4, dtype=numpy.uint))
        i = 0
        p = multiprocessing.Process(target=VideoCapture,
                                    args=(self.active_zone, e, self.finishFlag, self.which_logic_Set, self.trial_nr))
        p.start()
        dc = multiprocessing.Process(target=DoorControl, args=(self.door_status, self.light_status, self.finishFlag,))
        dc.start()
        self.MainLoop()

    def _getDoorIndex(self, door_name):
        return (DoorControl.getDoorIndex(door_name, self.door_names))

    def CloseDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 1

    def OpenDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 0

    def LightOn(self, ln):
        self.light_status[ln - 1] = 1
        print("Light %d turned on" % (ln))

    def LightOff(self, ln):
        self.light_status[ln - 1] = 0
        print("Light %d turned off" % (ln))

    def get_active_zone(self):
        zone_nr = self.active_zone.value
        if zone_nr > (-1):
            return (self.zone_names[zone_nr])
        else:
            return (None)

    def checkActivation(self):
        if self.active_zone.value != self.last_active_zone:
            self.zone_activated = self.active_zone.value
            self.zone_deactivated = self.last_active_zone
        else:
            self.zone_activated = -1
            self.zone_deactivated = -1
        self.last_active_zone = self.active_zone.value

    def getActivatedZone(self):
        if self.zone_activated != -1:
            return (self.zone_names[self.zone_activated])
        else:
            return (None)

    def getDeactivatedZone(self):
        if self.zone_deactivated != -1:
            return (self.zone_names[self.zone_deactivated])
        else:
            return (None)


if __name__ == '__main__':
    emaze = EMaze()
