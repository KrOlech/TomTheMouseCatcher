import multiprocessing

import numpy

from src.Python.Settings import Settings
from src.Python.Doors.DoorControl import DoorControl
from src.Python.MainLoop.MainLoop import MainLoop  # Line to choose the logic: from (insert logic name) import MainLoop
from src.Python.Setup.Setup import Setup
from src.Python.VideoCapture.VideoCapture import VideoCapture
from src.Python.Zones.Zones import Zones


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

        p = multiprocessing.Process(target=VideoCapture,
                                    args=(self.active_zone, e, self.finishFlag, self.which_logic_Set, self.trial_nr))
        p.start()

        dc = multiprocessing.Process(target=DoorControl, args=(self.door_status, self.light_status, self.finishFlag,))
        dc.start()

        super(EMaze, self).__init__()

    def _getDoorIndex(self, door_name):
        return DoorControl.getDoorIndex(door_name, self.door_names)

    def CloseDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 1

    def OpenDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 0

    def LightOn(self, ln):
        self.light_status[ln - 1] = 1
        self.loger("Light %d turned on" % ln)

    def LightOff(self, ln):
        self.light_status[ln - 1] = 0
        self.loger("Light %d turned off" % ln)

    def get_active_zone(self):
        zone_nr = self.active_zone.value
        if zone_nr > (-1):
            return self.zone_names[zone_nr]
        else:
            return None

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
            return self.zone_names[self.zone_activated]
        else:
            return None


if __name__ == '__main__':
    Setup().setUp()
    eMaze = EMaze()
    eMaze.mainLoop()
