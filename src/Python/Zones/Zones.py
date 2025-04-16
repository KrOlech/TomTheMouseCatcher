import time

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

    def get_zone_names(self):
        zone_names = sorted(Settings.zones.keys())
        for zone in zone_names:
            self.time_in_zones[zone] = 0.
            self.number_in_zones[zone] = 0
            self.time_in_zones_R[zone] = 0.
            self.number_in_zones_R[zone] = 0
            self.time_in_zones_L[zone] = 0.
            self.number_in_zones_L[zone] = 0
            self.time_in_zones_TRIAL[zone] = 0.
            self.number_in_zones_TRIAL[zone] = 0
        return (zone_names)

    def read_zones(self):
        zones_names = self.get_zone_names()
        for zone_name in zones_names:
            self.loger("Adding zone ", zone_name)
            zone = Settings.zones[zone_name]
            self.add_zone(zone[0], zone[1], zone[2], zone[3], zone_name)
