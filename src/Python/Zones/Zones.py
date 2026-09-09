import time
import numpy
import csv

from datetime import datetime

from src.Python.Loger.Loger import Loger
from src.Python.Settings import Settings
#from src.Python.MainLoop.MainLoop import MainLoop
from src.Python.MainLoop.MainLoopSelector import MainLoop    #07.08.06 Tomasz


class Zones(Loger):
    zonNames = {5: "Right", 4: "left"}  # 4:E1 5:E2

    zoneMap = {-1: 1, 0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1, 10: 0, 11: 0, 12: 3, 13: 3}

    zoneDelta = 0

    active_zone = -1

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

    def add_zone(self, x0, y0, w, h, zone_name=""):
        self.zones.append([x0, y0, w, h])
        self.zone_names.append(zone_name)
        self.zones_nr = len(self.zone_names)
        self.active_pix = numpy.zeros(self.zones_nr)

    def finish(self):
        self.loger("NR IN ZONES TOTAL", self.number_in_zones)
        self.loger("TIMES IN ZONES TOTAL", self.time_in_zones)
        self.loger("NR IN ZONES LEFT", self.number_in_zones_L)
        self.loger("TIMES IN ZONES LEFT", self.time_in_zones_L)
        self.loger("NR IN ZONES RIGHT", self.number_in_zones_R)
        self.loger("TIMES IN ZONES RIGHT", self.time_in_zones_R)
        now = datetime.now()
        file_name = now.strftime(f"{Settings.dataLocation}\\zones%Y%m%d_%H_%M_%S") + ".csv"
        with open(file_name, "w") as fh:
            csv_writer = csv.writer(fh)
            for k in self.time_in_zones.keys():
                csv_writer.writerow(
                    [k, self.number_in_zones[k], self.time_in_zones[k], self.number_in_zones_L[k],
                     self.time_in_zones_L[k],
                     self.number_in_zones_R[k], self.time_in_zones_R[k]])

    def print_zone(self, zone_nr):
        zone = self.zones[zone_nr]
        self.loger("x0= %d, y0=%d, w= %d, h=%d" % (zone[0], zone[1], zone[2], zone[3]))

    def get_zone_coords(self, zone_nr):
        zone = self.zones[zone_nr]
        return zone[0], zone[1], zone[2], zone[3]


    def _resolveDecision(self, active_zone):
        haveMouseMadeDecision = self.deactivated_zone == "D" and active_zone in (4, 5)
        decisionLeft = self.deactivated_zone == "D" and active_zone == 5
        decisionRight = self.deactivated_zone == "D" and active_zone == 4
        return haveMouseMadeDecision, decisionLeft, decisionRight

    def check_zone_change(self):
        active_zone = self.active_zone
        self._check_zone_change(active_zone)

    def _check_zone_change(self, active_zone):
        self._check_trial_nr_change()
        self.activated_zone = -1
        self.deactivated_zone = -1

        if (active_zone != self.active_last_zone) & (self.active_last_zone != -1):

            self.deactivated_zone = self.zone_names[self.active_last_zone]

            time_in_zone = time.time() - self.time_activated
            MainLoop.log_data_csv(self.deactivated_zone, time_in_zone)

            self.loger("WHICHLOGIC", self.which_logic_Set.value)
            self.loger("TRIAL_NR", self.trial_nr.value)
            self.loger("ZONE %s \t DEACTIVATED AFTER \t %f" % (self.deactivated_zone, time_in_zone))

            self.number_in_zones[self.deactivated_zone] += 1
            self.time_in_zones[self.deactivated_zone] += time_in_zone
            self.number_in_zones_TRIAL[self.deactivated_zone] += 1
            self.time_in_zones_TRIAL[self.deactivated_zone] += time_in_zone

            haveMouseMadeDecision, decisionLeft, decisionRight = None, None, None

            if self.which_logic_Set.value:
                self.number_in_zones_R[self.deactivated_zone] += 1
                self.time_in_zones_R[self.deactivated_zone] += time_in_zone
                haveMouseMadeDecision, _, decisionRight = self._resolveDecision(active_zone)
                direction = "Right"
            else:
                self.number_in_zones_L[self.deactivated_zone] += 1
                self.time_in_zones_L[self.deactivated_zone] += time_in_zone
                haveMouseMadeDecision, decisionLeft, _ = self._resolveDecision(active_zone)
                direction = "Left"

            if haveMouseMadeDecision and (decisionLeft or decisionRight):
                self.loger(f"Mouse Make correct decision to the {direction} in logic: {self.which_logic_Set.value}")
            elif haveMouseMadeDecision:
                self.loger(f"Mouse Make wrong decision")

        if (active_zone != -1) & (active_zone != self.active_last_zone):
            self.activated_zone = self.zone_names[active_zone]
            self.time_activated = time.time()
            self.loger("ZONE %s \t ACTIVATED" % self.activated_zone)
        self.active_last_zone = self.active_zone

    def _check_trial_nr_change(self):
        if self.trial_nr.value != self.old_trial_nr:
            self.old_trial_nr = self.trial_nr.value
            self.loger("TRIAL_NR_CHANGE", self.old_trial_nr, "->", self.trial_nr.value)
            self.loger("time in zones_trial", self.time_in_zones_TRIAL)
            self.loger("number in zones_trial", self.number_in_zones_TRIAL)
            for k in self.time_in_zones_TRIAL.keys():
                self.time_in_zones_TRIAL[k] = 0.
            for k in self.number_in_zones_TRIAL.keys():
                self.number_in_zones_TRIAL[k] = 0

    def get_active_zone(self, correctedLocation):
        correctedLocation = int(correctedLocation[0]//0.5), int(correctedLocation[1]//0.5)
        return self.__resolveZoneFromLocation(correctedLocation)

    def __resolveZoneFromLocation(self, location):

        for zone_nr in range(self.zones_nr):
            x0, y0, w, h = self.zones[zone_nr]
            if x0 < location[0] < x0 + w and y0 < location[1] < y0 + h:
                self.active_zone = zone_nr
                break

        return self.active_zone