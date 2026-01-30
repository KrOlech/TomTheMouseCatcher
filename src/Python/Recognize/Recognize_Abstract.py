from src.Python.Zones.Zones import Zones
import csv
import os
import time
from datetime import datetime
from abc import abstractmethod
import numpy

from src.Python.MainLoop.MainLoop import MainLoop
from src.Python.Settings import Settings


class Recognize_Abstract(Zones):
    zonNames = {5: "Right", 4: "left"}  # 4:E1 5:E2

    zoneMap = {-1: 1, 0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1, 10: 0, 11: 0, 12: 3, 13: 3}

    execData = 0

    zoneDelta = 0

    def add_zone(self, x0, y0, w, h, zone_name=""):
        self.zones.append([x0, y0, w, h])
        self.zone_names.append(zone_name)
        self.zones_nr = len(self.zone_names)
        self.active_pix = numpy.zeros(self.zones_nr)

    def set_ref_image(self, img):
        self.ref_image = img

    def print_zone(self, zone_nr):
        zone = self.zones[zone_nr]
        self.loger("x0= %d, y0=%d, w= %d, h=%d" % (zone[0], zone[1], zone[2], zone[3]))

    def get_zone_coords(self, zone_nr):
        zone = self.zones[zone_nr]
        return zone[0], zone[1], zone[2], zone[3]

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
