import multiprocessing
from abc import abstractmethod

from src.Python.Doors.DoorControl import DoorControl
from src.Python.MainLoop.MainLoop import MainLoop  # Line to choose the logic: from (insert logic name) import MainLoop
from src.Python.Settings import Settings
from src.Python.Zones.Zones import Zones


class EMazeAbstract(MainLoop):

    nr_of_zones = len(Settings.zones)
    nr_of_doors = len(Settings.doors)

    zone_activated = -1
    zone_deactivated = -1
    last_active_zone = -1

    def __init__(self):
        super(EMazeAbstract, self).__init__()
        self.which_logic_Set = multiprocessing.Value('i', 0)
        self.trial_nr = multiprocessing.Value('i', 0)
        self.active_zone = multiprocessing.Value('i', 0)

        self.zone_names = Zones.get_zone_names()

        self.door_names = DoorControl.getDoorNames()

        self.finishFlag = multiprocessing.Event()



    @abstractmethod
    def run(self):
        ...

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


