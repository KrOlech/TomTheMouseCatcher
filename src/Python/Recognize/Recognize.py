import csv
import os
import time
from datetime import datetime

import numpy

from src.Python.MainLoop.MainLoop import MainLoop
from src.Python.Settings import Settings
from src.Python.Zones.Zones import Zones


class Recognize(Zones):
    def _get_zone(self, image, zone_nr):
        zone = self.zones[zone_nr]
        x0 = zone[0]
        y0 = zone[1]
        w = zone[2]
        h = zone[3]
        return (image[y0:y0 + h, x0:x0 + w])

    def add_zone(self, x0, y0, w, h, zone_name=""):
        self.zones.append([x0, y0, w, h])
        self.zone_names.append(zone_name)
        self.zones_nr = len(self.zone_names)
        self.active_pix = numpy.zeros(self.zones_nr)

    def set_ref_image(self, img):
        self.ref_image = img

    def print_zone(self, zone_nr):
        zone = self.zones[zone_nr]
        print("x0= %d, y0=%d, w= %d, h=%d" % (zone[0], zone[1], zone[2], zone[3]))

    def get_zone_coords(self, zone_nr):
        zone = self.zones[zone_nr]
        return (zone[0], zone[1], zone[2], zone[3])

    def get_refer_diff(self, img1, zone_nr):
        return (self.get_rel_diff(img1, self.ref_image, zone_nr))

    def get_rel_diff(self, img1, img2, zone_nr):
        img1_zone = self._get_zone(img1, zone_nr)
        img2_zone = self._get_zone(img2, zone_nr)
        diff = numpy.subtract(img2_zone, img1_zone)
        return (numpy.sum(abs(diff) > Settings.threshold))

    def get_active_zone(self, img1):
        active_flag = 0
        for zone_nr in range(self.zones_nr):
            pixels_diff = self.get_refer_diff(img1, zone_nr)
            if (pixels_diff > Settings.minDiffPix):
                self.active_pix[zone_nr] = pixels_diff
                active_flag = 1
            else:
                self.active_pix[zone_nr] = 0
        if active_flag == 0:
            self.active_zone = -1
        else:
            self.active_zone = numpy.argmax(self.active_pix)
        return (self.active_zone)

    def check_zone_change(self):
        active_zone = self.active_zone
        self._check_zone_change(active_zone)

    def _check_zone_change(self, active_zone):
        self._check_trial_nr_change()
        self.activated_zone = -1
        self.deactivated_zone = -1
        if ((active_zone != self.active_last_zone) & (self.active_last_zone != -1)):
            self.deactivated_zone = self.zone_names[self.active_last_zone]
            time_in_zone = time.time() - self.time_activated
            MainLoop.log_data_csv(self.deactivated_zone, time_in_zone)
            print("WHICHLOGIC", self.which_logic_Set.value)
            print("TRIAL_NR", self.trial_nr.value)
            print("ZONE %s \t DEACTIVATED AFTER \t %f" % (self.deactivated_zone, time_in_zone))
            self.number_in_zones[self.deactivated_zone] = self.number_in_zones[self.deactivated_zone] + 1
            self.time_in_zones[self.deactivated_zone] = self.time_in_zones[self.deactivated_zone] + time_in_zone
            self.number_in_zones_TRIAL[self.deactivated_zone] = self.number_in_zones_TRIAL[self.deactivated_zone] + 1
            self.time_in_zones_TRIAL[self.deactivated_zone] = self.time_in_zones_TRIAL[
                                                                  self.deactivated_zone] + time_in_zone
            if self.which_logic_Set.value == 0:
                self.number_in_zones_L[self.deactivated_zone] = self.number_in_zones_L[self.deactivated_zone] + 1
                self.time_in_zones_L[self.deactivated_zone] = self.time_in_zones_L[self.deactivated_zone] + time_in_zone
            if self.which_logic_Set.value == 1:
                self.number_in_zones_R[self.deactivated_zone] = self.number_in_zones_R[self.deactivated_zone] + 1
                self.time_in_zones_R[self.deactivated_zone] = self.time_in_zones_R[self.deactivated_zone] + time_in_zone
        if ((active_zone != -1) & (active_zone != self.active_last_zone)):
            self.activated_zone = self.zone_names[active_zone]
            self.time_activated = time.time()
            print("ZONE %s \t ACTIVATED" % self.activated_zone)
        self.active_last_zone = self.active_zone

    def _check_trial_nr_change(self):
        if self.trial_nr.value != self.old_trial_nr:
            self.old_trial_nr = self.trial_nr.value
            print("TRIAL_NR_CHANGE", self.old_trial_nr, "->", self.trial_nr.value)
            print("time in zones_trial", self.time_in_zones_TRIAL)
            print("number in zones_trial", self.number_in_zones_TRIAL)
            for k in self.time_in_zones_TRIAL.keys():
                self.time_in_zones_TRIAL[k] = 0.
            for k in self.number_in_zones_TRIAL.keys():
                self.number_in_zones_TRIAL[k] = 0

    def finish(self):
        print("NR IN ZONES TOTAL", self.number_in_zones)
        print("TIMES IN ZONES TOTAL", self.time_in_zones)
        print("NR IN ZONES LEFT", self.number_in_zones_L)
        print("TIMES IN ZONES LEFT", self.time_in_zones_L)
        print("NR IN ZONES RIGHT", self.number_in_zones_R)
        print("TIMES IN ZONES RIGHT", self.time_in_zones_R)
        now = datetime.now()
        file_name = now.strftime(f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\zones%Y%m%d_%H_%M_%S") + ".csv"
        fh = open(file_name, "w")
        csv_writer = csv.writer(fh)
        for k in self.time_in_zones.keys():
            csv_writer.writerow(
                [k, self.number_in_zones[k], self.time_in_zones[k], self.number_in_zones_L[k], self.time_in_zones_L[k],
                 self.number_in_zones_R[k], self.time_in_zones_R[k]])
        fh.close()
