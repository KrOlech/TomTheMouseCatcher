import numpy as np
import cv2
from src.Python.Recognize.Recognize_Abstract import Recognize_Abstract
from src.Python.Settings import Settings
import time

class Recognize(Recognize_Abstract):
    # mask
    lower = np.array([85, 85, 150]) #163 154 29
    upper = np.array([100, 150, 220])#196 255 142

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    oldLocation = None

    active_zone = -1

    px, py = 0.0, 500.0
    vx, vy = 0.0, 0.0

    start_time = time.time()

    def get_active_zone(self, img_RGB):

        mask = self.__maskTheImage(img_RGB)

        contours = self.__foundContours(mask)

        location = self.__resolveLocationFromConturs(contours)

        correctedLocation = self.__predictPosition(location)

        zone = self.__resolveZoneFromLocation(correctedLocation)

        return zone

    def __maskTheImage(self, img_RGB):

        dif_RGB = img_RGB -self.ref_image

        img_hsv = cv2.cvtColor(dif_RGB, cv2.COLOR_BGR2HSV)

        gray = cv2.inRange(img_hsv, self.lower, self.upper)

        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=33, sigmaY=33)

        divide = cv2.divide(gray, blur, scale=255)
        out_binary = cv2.threshold(divide, 200, 255, cv2.THRESH_OTSU)[1]

        erosion_size = 0
        erosion_shape = cv2.MORPH_ELLIPSE

        element = cv2.getStructuringElement(erosion_shape, (2 * erosion_size + 1, 2 * erosion_size + 1),
                                            (erosion_size, erosion_size))

        out_binary = cv2.erode(out_binary, element)

        return out_binary

    def __foundContours(self, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours

    def __resolveLocationFromConturs(self, contours):

        locations = []
        if contours:
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (400 < area < 5500):
                    continue

                xm, y, w, h = cv2.boundingRect(cnt)
                aspect = w / h
                if not (0.25 < aspect < 3.3):
                    continue

                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    locations.append((cx, cy))

        if len(locations) == 0:
            return [self.px, self.py]
        elif len(locations) == 1:
            self.oldLocation = locations[0]
            return locations[0]
        elif not self.oldLocation:
            return [self.px, self.py]
        else:
            # todo proper selection using predicted position not just old position
            sqDeltas = [(location[0] - self.oldLocation[0]) ** 2 + (location[1] - self.oldLocation[1]) ** 2 for location
                        in locations]
            self.oldLocation = locations[np.argmin(sqDeltas)]
            return self.oldLocation

    def __resolveZoneFromLocation(self, location):


        for zone_nr in range(self.zones_nr):
            x0, y0, w, h = self.zones[zone_nr]
            if x0 < location[0] < x0 + w and y0 < location[1] < y0 + h:
                self.active_zone = zone_nr
                break

        return self.active_zone

    def __predictPosition(self, location):

        dt = time.time() - self.start_time
        self.start_time = time.time()

        px_pred = self.px + self.vx * dt
        py_pred = self.py + self.vy * dt

        # Innovation
        ex = location[0] - px_pred
        ey = location[1] - py_pred
        innovation = np.array([ex, ey])

        # Adaptive gains
        alpha, beta = self.__adaptive_alpha_beta(innovation)

        # Update position
        self.px = px_pred + alpha * ex
        self.py = py_pred + alpha * ey

        # Update velocity (instant response)
        vx_prev, vy_prev = self.vx, self.vy
        self.vx = self.vx + (beta / dt) * ex
        self.vy = self.vy + (beta / dt) * ey

        self.ax = (self.vx - vx_prev) / dt
        self.ay = (self.vy - vy_prev) / dt

        self.speed = np.hypot(self.vx, self.vy)
        self.accel = np.hypot(self.ax, self.ay)

        return self.px,self.py

    @staticmethod
    def __adaptive_alpha_beta(innovation):
        d = np.linalg.norm(innovation)

        alpha = np.clip(0.4 + 0.01 * d, 0.4, 0.85)
        beta = np.clip(0.05 + 0.002 * d, 0.05, 0.35)

        return alpha, beta