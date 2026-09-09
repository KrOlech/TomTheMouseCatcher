import numpy
import cv2
from src.Python.Recognize.Recognize_Abstract import Recognize_Abstract
from src.Python.Settings import Settings


class Recognize(Recognize_Abstract):

    def get_refer_diff(self, img1, zone_nr):
        return self.get_rel_diff(img1, self.ref_image, zone_nr)

    def get_rel_diff(self, img1, img2, zone_nr):
        img1_zone = self._get_zone(img1, zone_nr)
        img2_zone = self._get_zone(img2, zone_nr)
        diff = numpy.subtract(img2_zone, img1_zone)
        return numpy.sum(abs(diff) > Settings.threshold)

    def _get_zone(self, image, zone_nr):
        zone = self.zones[zone_nr]
        x0 = zone[0]
        y0 = zone[1]
        w = zone[2]
        h = zone[3]
        return image[y0:y0 + h, x0:x0 + w]

    def get_active_zone(self, img1):
        img = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        active_flag = 0
        for zone_nr in range(self.zones_nr):
            pixels_diff = self.get_refer_diff(img, zone_nr)
            if pixels_diff > Settings.minDiffPix:
                self.active_pix[zone_nr] = pixels_diff
                active_flag = 1
            else:
                self.active_pix[zone_nr] = 0
        if active_flag == 0:
            self.active_zone = -1
        else:
            self.active_zone = numpy.argmax(self.active_pix)
        return self.active_zone


