import time
from abc import abstractmethod

from src.Python.Loger.Loger import Loger
from src.Python.Settings import Settings


class Zones(Loger):


    def __init__(self, which_logic_Set, trial_nr):
        self.zones = []
        self.active_pix = []
        self.zones_nr = 0
        self.zone_names = []
        self.ref_image = []
        self.active_zone = -1
        self.active_last_zone = -1
        self.activated_zone = -1
        self.deactivated_zone = -1
        self.which_logic_Set = which_logic_Set
        self.trial_nr = trial_nr
        self.old_trial_nr = 0
        self.time_in_zones = {}
        self.number_in_zones = {}
        self.time_in_zones_R = {}
        self.number_in_zones_R = {}
        self.time_in_zones_L = {}
        self.number_in_zones_L = {}
        self.time_in_zones_TRIAL = {}
        self.number_in_zones_TRIAL = {}
        self.time_activated = time.time()

    @staticmethod
    def get_zone_names():
        return sorted(Settings.zones)

    def _rest_zones(self):
        for zone in self.get_zone_names():
            self.time_in_zones[zone] = 0.
            self.number_in_zones[zone] = 0
            self.time_in_zones_R[zone] = 0.
            self.number_in_zones_R[zone] = 0
            self.time_in_zones_L[zone] = 0.
            self.number_in_zones_L[zone] = 0
            self.time_in_zones_TRIAL[zone] = 0.
            self.number_in_zones_TRIAL[zone] = 0

    def read_zones(self):
        self._rest_zones()
        for zone_name, zone_values in Settings.zones.items():
            self.loger("Adding zone ", zone_name)
            self.add_zone(*zone_values, zone_name)

    @abstractmethod
    def add_zone(self, x0, y0, w, h, zone_name=""):
        ...