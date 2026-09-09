import time

import cv2
import numpy as np

from src.Python.Recognize.Recognize_Abstract import Recognize_Abstract


class Recognize(Recognize_Abstract):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def __init__(
        self,
        mainMask,
        area,
        aspect,
        plexyMask=None,
        ogDifferents=True,
        erosion_size=0,
        yBound=None
    ):
        # Keep tracking state separate for mouse and other instances.
        self.oldLocation = []
        self.px, self.py = 0.0, 500.0
        self.vx, self.vy = 0.0, 0.0
        self.start_time = time.time()
        self.plexyMask = False
        self.detected = False

        if yBound is None:
            yBound = []

        self.lower = mainMask[0]
        self.upper = mainMask[1]
        self.area = area
        self.aspect = aspect

        if plexyMask is not None:
            self.lower_underPlexy = plexyMask[0]
            self.upper_underPlexy = plexyMask[1]
            self.plexyMask = True

        self.ogDifferents = ogDifferents
        self.erosion_size = erosion_size
        self.yBound = yBound

    def get_location(self, img_RGB):
        mask = self.__maskTheImage(img_RGB)
        contours = self.__foundContours(mask)
        location = self.__resolveLocationFromConturs(contours)
        return self.__predictPosition(location)

    def __maskTheImage(self, img_RGB):
        if self.ogDifferents:
            dif_RGB = img_RGB - self.ref_image
        else:
            dif_RGB = img_RGB

        img_hsv = cv2.cvtColor(dif_RGB, cv2.COLOR_BGR2HSV)
        gray = cv2.inRange(img_hsv, self.lower, self.upper)

        blureOut = self.__blure(gray)
        eroded = self.__erode(
            blureOut,
            erosion_size=self.erosion_size
        )

        if self.plexyMask:
            grayUnderPlexy = cv2.inRange(
                img_hsv,
                self.lower_underPlexy,
                self.upper_underPlexy
            )
            blureOutUnderPlexy = self.__blure(grayUnderPlexy)
            erodedUnderPlexy = self.__erode(
                blureOutUnderPlexy,
                1
            )
            return self.__combine(eroded, erodedUnderPlexy)

        return eroded

    @staticmethod
    def __combine(image, underPlexy):
        x0, x1 = int(910 * 0.5), int(1080 * 0.5)
        y0, y1 = int(910 * 0.5), int(1080 * 0.5)

        partOfImage = image[x0:x1, y0:y1]
        partUnderPlexy = underPlexy[x0:x1, y0:y1]
        mainCombine = cv2.add(partOfImage, partUnderPlexy)

        image[x0:x1, y0:y1] = mainCombine
        return image

    @staticmethod
    def __blure(img):
        blur = cv2.GaussianBlur(
            img,
            (0, 0),
            sigmaX=11,
            sigmaY=1
        )
        divide = cv2.divide(img, blur, scale=255)
        return cv2.threshold(
            divide,
            200,
            255,
            cv2.THRESH_OTSU
        )[1]

    @staticmethod
    def __erode(img, erosion_size=0):
        erosion_shape = cv2.MORPH_ELLIPSE
        element = cv2.getStructuringElement(
            erosion_shape,
            (2 * erosion_size + 1, 2 * erosion_size + 1),
            (erosion_size, erosion_size)
        )
        return cv2.erode(img, element)

    @staticmethod
    def __foundContours(mask):
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        return contours

    def __resolveLocationFromConturs(self, contours):
        locations = []

        if contours:
            for cnt in contours:
                area = cv2.contourArea(cnt)

                if not (self.area[0] < area < self.area[1]):
                    continue

                _, _, w, h = cv2.boundingRect(cnt)

                if h == 0:
                    continue

                aspect = w / h

                if not (
                    self.aspect[0] < aspect < self.aspect[1]
                ):
                    continue

                moments = cv2.moments(cnt)

                if moments["m00"] == 0:
                    continue

                cx = int(
                    moments["m10"] / moments["m00"]
                )
                cy = int(
                    moments["m01"] / moments["m00"]
                )

                if self.yBound:
                    if self.yBound[0] < cy < self.yBound[1]:
                        locations.append((cx, cy))
                else:
                    locations.append((cx, cy))

        if len(locations) == 0:
            self.detected = False
            return self.px, self.py

        if len(locations) == 1:
            self.detected = True
            self.oldLocation = locations[0]
            return locations[0]

        if not self.oldLocation:
            self.detected = True
            selected = locations[0]
            self.oldLocation = selected
            return selected

        squared_deltas = [
            (
                location[0] - self.oldLocation[0]
            ) ** 2 + (
                location[1] - self.oldLocation[1]
            ) ** 2
            for location in locations
        ]

        self.detected = True
        self.oldLocation = locations[
            int(np.argmin(squared_deltas))
        ]
        return self.oldLocation

    def __predictPosition(self, location):
        dt = max(
            time.time() - self.start_time,
            1e-6
        )
        self.start_time = time.time()

        px_pred = self.px + self.vx * dt
        py_pred = self.py + self.vy * dt

        ex = location[0] - px_pred
        ey = location[1] - py_pred
        innovation = np.array([ex, ey])

        alpha, beta = self.__adaptive_alpha_beta(
            innovation
        )

        self.px = px_pred + alpha * ex
        self.py = py_pred + alpha * ey

        vx_prev, vy_prev = self.vx, self.vy
        self.vx = self.vx + (beta / dt) * ex
        self.vy = self.vy + (beta / dt) * ey

        self.ax = (self.vx - vx_prev) / dt
        self.ay = (self.vy - vy_prev) / dt

        self.speed = np.hypot(self.vx, self.vy)
        self.accel = np.hypot(self.ax, self.ay)

        return self.px, self.py

    @staticmethod
    def __adaptive_alpha_beta(innovation):
        distance = np.linalg.norm(innovation)

        alpha = np.clip(
            0.4 + 0.01 * distance,
            0.4,
            0.85
        )
        beta = np.clip(
            0.05 + 0.002 * distance,
            0.05,
            0.35
        )

        return alpha, beta