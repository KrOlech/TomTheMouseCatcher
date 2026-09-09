import os
import time
from datetime import datetime
from itertools import count
#from copy import deepcopy

import cv2
import numpy as np

from src.Python.Loger.Loger import Loger
from src.Python.Recognize.Recognize_AB_Filter import Recognize
from src.Python.Settings import Settings
from src.Python.Zones.Zones import Zones


class VideoCapture(Loger):
    calibration = []
    refCalibration = []

    font = cv2.FONT_HERSHEY_SIMPLEX
    org = (100, 23)
    fontScale = 0.5
    color = (255, 0, 0)
    thickness = 1

    last_flagSave = 0
    current_flagSave = 0
    saving_started = 0
    save_calibration = 0
    zone_active = 0
    zone_active_last = 0
    calibration_start = 0
    calibratedFlag = 0

    messagePrinted: bool = False

    offset_nr = 90

    frame = None  # frame buffer
    frame_lum = None  # frame buffer

    out = None  # recorder

    windowName: str = "output"

    target_fps = Settings.fps
    frame_delay = 1.0 / target_fps
    start_time = 0

    def __init__(self, active_zone, recTrigger, finishFlag, which_logic_Set, trial_nr):
        self.frames = 0
        self.start = time.time()

        self.zon = Zones(which_logic_Set, trial_nr)
        self.zon.read_zones()

        mouseMainMask = [np.array([85, 85, 150]),np.array([100, 150, 220])]
        mousePlexyMask = [np.array([0, 0, 210]),np.array([110, 25, 250])]
        mouseArea = [int(400*0.25), int(5500*0.25)]
        mouseAspect = [0.25, 3.3]
        self.rcMouse = Recognize(mouseMainMask,mouseArea,mouseAspect, mousePlexyMask)

        carriageMainMask = [np.array([0, int(255 * 0.25), int(255 * 0.9)]),np.array([25, int(255 * 0.45), 255])]
        carriageArea = [int(400*0.25), int(5500*0.25)]
        carriageAspect = [0.5, 1.8]
        carriage_yBound = [int(450*0.5), int(650*0.5)]
        self.rcCarriage = Recognize(carriageMainMask, carriageArea, carriageAspect, ogDifferents=False, erosion_size= 2, yBound=carriage_yBound)

        self.recTrigger = recTrigger

        self.active_zone = active_zone

        self.timeActivated = time.time()

        self.finishFlag = finishFlag
        self.which_logic_Set = which_logic_Set

        self.cap = cv2.VideoCapture(Settings.CamNr)

        self.capt_frames_nr = 0

        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        cv2.startWindowThread()
        cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)

        self.setCapture()

        self.runCaptureTryExcept()

    def runCaptureTryExcept(self):
        try:
            self.runCapture()
        except Exception as e:
            self.logError(e)
        else:
            self.zon.finish()
        finally:
            self.releaseCapture()

    def runCapture(self):
        self.runVideoCaptureSavingFrames()
        if self.out is not None:
            self.out.release()
        self.saving_started = 0
        self.loger("STOP SAVING")

    def captureFrame(self):
        self.start_time = time.time()

        ret, frame = self.cap.read()

        if not ret or frame is None:
            raise RuntimeError("Could not read a frame from the camera or video.")

        self.rowFrame = frame.copy()

        processing_scale = 0.5

        self.frame_lum  = cv2.resize(
            frame,
            None,
            fx=processing_scale,
            fy=processing_scale,
            interpolation=cv2.INTER_AREA
        )

        now = datetime.now()

        self.frame = cv2.putText(
            frame,
            str(now),
            self.org,
            self.font,
            self.fontScale,
            self.color,
            self.thickness,
            cv2.LINE_AA
        )

    def startRecording(self):
        if not self.last_flagSave and self.current_flagSave:
            self.saving_started = True
            self.out = cv2.VideoWriter(datetime.now().strftime(f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\video%Y%m%d_%H_%M_%S") + ".avi", self.fourcc,
                                       20.0, (self.rowFrame.shape[1], self.rowFrame.shape[0]))
            self.loger("START RECORDING")

    def runVideoCaptureSavingFrames(self):
        for i in count(0):

            self.captureFrame()

            if i <= self.offset_nr:
                continue

            self.recTrigger.set()

            if self.recTrigger.is_set():
                self.current_flagSave = 1
            else:
                self.current_flagSave = 0

            self.calibrate()

            self.startRecording()


            if self.recTrigger.is_set():
                if self.calibratedFlag == 0:
                    cv2.circle(self.frame, (30, 17), 10, (0, 0, 255), -1)
                else:
                    cv2.circle(self.frame, (30, 17), 10, (0, 255, 0), -1)

            if self.calibratedFlag == 1:
                lum = self.zon.get_active_zone(self.rcMouse.get_location(self.frame_lum))
                self.rcCarriage.get_location(self.frame_lum)
            else:
                lum = -1

            self.zone_active_last = self.zone_active

            for zone_nr in range(self.zon.zones_nr):
                x0, y0, w, h = self.zon.get_zone_coords(zone_nr)
                if lum == zone_nr:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 0, 250), 2)
                else:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 200, 0), 2)


            self.zon.check_zone_change()

            self.cross()
            cv2.circle(self.frame, (int(self.rcMouse.px//0.5), int(self.rcMouse.py//0.5)), 4, (0, 0, 255), -1)

            #self.logPositionData((self.rcMouse.px, self.rcMouse.py), self.rcMouse.oldLocation)




            cv2.circle(self.frame, (int(self.rcCarriage.px//0.5), int(self.rcCarriage.py//0.5)), 4, (0, 255, 0), -1)


            processing_time = time.time() - self.start_time
            #sleep_time = max(0, int(self.frame_delay - processing_time))
            #time.sleep(sleep_time)
            sleep_time = max(0.0, self.frame_delay - processing_time)
            time.sleep(sleep_time)
            if self.frame is not None:
                self.frames += 1

                if time.time() - self.start >= 1:
                    print("FPS:", self.frames)
                    self.frames = 0
                    self.start = time.time()
                cv2.imshow(self.windowName, self.frame)

            # STOP SAVING
            if self.last_flagSave and not self.current_flagSave:
                if self.out is not None:
                    self.out.release()
                self.saving_started = 0
                self.loger("STOP SAVING")

            self.last_flagSave = self.current_flagSave

            if (cv2.waitKey(1) and 0xFF == ord('q')) or self.finishFlag.is_set():
                self.finishFlag.set()
                if self.out is not None:
                    self.out.release()
                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            if cv2.getWindowProperty(self.windowName, cv2.WND_PROP_VISIBLE) < 1:
                self.finishFlag.set()
                if self.out is not None:
                    self.out.release()
                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            self.capt_frames_nr = self.capt_frames_nr + 1

            self.active_zone.value = self.zon.active_zone

    def cross(self):
        if  len(self.rcMouse.oldLocation)==2:
            x,y = self.rcMouse.oldLocation
            x,y = int(x//0.5), int(y//0.5)
            cv2.line(self.frame, (x-10, y), (x+10, y), (255, 0, 0), 1)
            cv2.line(self.frame, (x, y-10), (x, y+10), (255, 0, 0), 1)

        if  len(self.rcCarriage.oldLocation)==2:
            x,y = self.rcCarriage.oldLocation
            x,y = int(x//0.5), int(y//0.5)
            cv2.line(self.frame, (x-10, y), (x+10, y), (0, 255, 0), 1)
            cv2.line(self.frame, (x, y-10), (x, y+10), (0, 255, 0), 1)

    def releaseCapture(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def setCapture(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Settings.FrameWidth)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Settings.FrameHeigth)
        self.ret_val, self.cap_for_exposure = self.cap.read()

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode

    def calibrate(self):
        if self.capt_frames_nr == 1:
            self.rcMouse.set_ref_image(self.frame_lum)

        if self.capt_frames_nr == 10:
            self.loger("Starting calibration...")
            self.calibration_start = 20

        if self.calibration_start > 0:
            self.calibration.append(cv2.cvtColor(self.frame_lum, cv2.COLOR_RGB2GRAY).copy())
            self.refCalibration = np.mean(self.calibration, axis=0)
            #self.zon.set_ref_image(self.frame_lum)
            #todo proper calibration for new recognize
            #self.zon.set_ref_image(self.refCalibration) #old save image for old recognize

            if self.calibration_start:
                self.refCalibration = np.mean(self.calibration, axis=0)
                self.calibratedFlag = 1

                self.save_calibration = 1

            self.calibration_start = self.calibration_start - 1

        if self.calibratedFlag and not self.messagePrinted:
            self.messagePrinted = True
            self.loger("calibration finished")

        if self.save_calibration:
            self.save_calibration = 0
            cv2.imwrite(f"{Settings.dataLocation}\\self.calibration.jpg", self.frame)
