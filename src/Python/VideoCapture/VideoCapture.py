import os
import time
from datetime import datetime
from itertools import count

import cv2
import numpy

from src.Python.Recognize.Recognize import Recognize
from src.Python.Settings import Settings


class VideoCapture:
    frames = []
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

    mesageprinted: bool = False

    offset_nr = 90

    frame = None  # frame buffer
    frame_lum = None  # frame buffer

    out = None  # recorder

    windowName: str = "output"

    def __init__(self, active_zone, recTrigger, finishFlag, which_logic_Set, trial_nr):

        self.rc = Recognize(which_logic_Set, trial_nr)
        self.rc.read_zones()

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
            print(e)
        else:
            self.rc.finish()
        finally:
            self.releaseCapture()

    def runCapture(self):
        if Settings.showZones:
            self.runVideoCaptureSavingFrames()
        else:
            self.runVideoCaptureNotSavingFrames()

    def captureFrame(self):
        ret, frame = self.cap.read()
        self.frames.append(frame)
        self.frame_lum = frame[:, :, 0]

        now = datetime.now()
        self.frame = cv2.putText(frame, str(now), self.org, self.font, self.fontScale, self.color, self.thickness,
                                 cv2.LINE_AA)

    def startRecording(self):
        if not self.last_flagSave and self.current_flagSave:
            self.saving_started = True
            self.out = cv2.VideoWriter(datetime.now().strftime(".\\data\\video%Y%m%d_%H_%M_%S") + ".avi", self.fourcc,
                                       20.0, (self.frame.shape[1], self.frame.shape[0]))
            print("START RECORDING")

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

            if not Settings.showZones and self.saving_started:
                self.out.write(self.frame)

            # Display the resulting frame
            self.frames.pop(0)

            if self.recTrigger.is_set():
                if self.calibratedFlag == 0:
                    cv2.circle(self.frame, (30, 17), 10, (0, 0, 255), -1)
                else:
                    cv2.circle(self.frame, (30, 17), 10, (0, 255, 0), -1)

            if self.calibratedFlag == 1:
                lum = (self.rc.get_active_zone(self.frame_lum))
            else:
                lum = -1

            self.zone_active_last = self.zone_active

            for zone_nr in range(self.rc.zones_nr):
                x0, y0, w, h = self.rc.get_zone_coords(zone_nr)
                if lum == zone_nr:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 0, 250), 2)
                else:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 200, 0), 2)

            if Settings.showZones and self.saving_started:
                self.out.write(self.frame)

            self.rc.check_zone_change()

            if self.frame is not None:
                cv2.imshow(self.windowName, self.frame)

            # STOP SAVING
            if self.last_flagSave and not self.current_flagSave:
                self.out.release()
                self.saving_started = 0
                print("STOP SAVING")

            self.last_flagSave = self.current_flagSave

            if (cv2.waitKey(1) and 0xFF == ord('q')) or self.finishFlag.is_set():
                break

            self.capt_frames_nr = self.capt_frames_nr + 1

            self.active_zone.value = self.rc.active_zone

    def runVideoCaptureNotSavingFrames(self):
        for i in count(0):

            self.captureFrame()

            if i <= self.offset_nr:
                continue

            self.recTrigger.set()

            if self.recTrigger.is_set():
                self.current_flagSave = 1
            else:
                self.current_flagSave = 0

            # CALIBRATE
            self.calibrate()

            # Display the resulting frame
            self.frames.pop(0)

            if self.recTrigger.is_set():
                if self.calibratedFlag == 0:
                    cv2.circle(self.frame, (30, 17), 10, (0, 0, 255), -1)
                else:
                    cv2.circle(self.frame, (30, 17), 10, (0, 255, 0), -1)

            if self.calibratedFlag == 1:
                lum = (self.rc.get_active_zone(self.frame_lum))
            else:
                lum = -1

            self.zone_active_last = self.zone_active

            for zone_nr in range(self.rc.zones_nr):
                x0, y0, w, h = self.rc.get_zone_coords(zone_nr)
                if lum == zone_nr:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 0, 250), 2)
                else:
                    cv2.rectangle(self.frame, (x0, y0), (x0 + w, y0 + h), (0, 200, 0), 2)

            self.rc.check_zone_change()

            if self.frame is not None:
                cv2.imshow(self.windowName, self.frame)

            self.last_flagSave = self.current_flagSave

            if (cv2.waitKey(1) and 0xFF == ord('q')) or self.finishFlag.is_set():
                break

            if cv2.getWindowProperty(self.windowName, cv2.WND_PROP_VISIBLE) < 1:
                break

            self.capt_frames_nr = self.capt_frames_nr + 1

            self.active_zone.value = self.rc.active_zone

    def releaseCapture(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def setCapture(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Settings.FrameWidth)  # todo get screen width
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Settings.FrameHeigth)
        self.ret_val, self.cap_for_exposure = self.cap.read()

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode

    def calibrate(self):
        if self.capt_frames_nr == 10:
            print("Starting calibration...")
            self.calibration_start = 20

        if self.calibration_start > 0:
            self.calibration.append(self.frame_lum.copy())
            self.refCalibration = numpy.mean(self.calibration, axis=0)
            self.rc.set_ref_image(self.refCalibration)

            if self.calibration_start:
                self.refCalibration = numpy.mean(self.calibration, axis=0)
                self.calibratedFlag = 1

                self.save_calibration = 1

            self.calibration_start = self.calibration_start - 1

        if self.calibratedFlag and not self.mesageprinted:
            self.mesageprinted = True
            print("calibration finished")

        if self.save_calibration:
            self.save_calibration = 0
            cv2.imwrite(f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\self.calibration.jpg", self.frame)
