import os
import time
import cProfile
from datetime import datetime
from itertools import count
from copy import deepcopy

from threading import Thread
import threading

import cv2
import numpy as np

from src.Python.Loger.Loger import Loger
from src.Python.Recognize.Recognize_AB_Filter import Recognize
from src.Python.Settings import Settings
from src.Python.VirtualCarrage.VirtualCarrage import VirtualCarrage
from src.Python.Zones.Zones import Zones

from queue import Queue
from threading import Thread

frame_queue = Queue(maxsize=100)
recordVideo = True
cap = cv2.VideoCapture(Settings.CamNr)

def VideoSaveThread():

    fourcc = cv2.VideoWriter_fourcc('M','J','P','G')

    fileName = datetime.now().strftime(
        f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\video%Y%m%d_%H_%M_%S") + ".avi"
    out = cv2.VideoWriter(fileName, fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))

    while recordVideo :
        frame = frame_queue.get()
        out.write(frame)

    print("Released")
    out.release()

def speedtest(function_wrapper):
    import cProfile
    import pstats
    import snakeviz.cli as cli

    with cProfile.Profile() as pr:
        function_wrapper()
    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    filename = "speedtest_profile.prof"
    stats.dump_stats(filename=filename)
    cli.main([filename])

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

        self.virtualCarage = VirtualCarrage()

        self.zon = Zones(which_logic_Set, trial_nr)
        self.zon.read_zones()

        mouseMainMask = [np.array([85, 85, 150]), np.array([100, 150, 220])]
        mousePlexyMask = [np.array([0, 0, 210]), np.array([110, 25, 250])]
        mouseArea = [400, 5500]
        mouseAspect = [0.25, 3.3]
        self.rcMouse = Recognize(mouseMainMask, mouseArea, mouseAspect, plexyMask=mousePlexyMask)

        carriageMainMask = [np.array([0, int(255 * 0.25), int(255 * 0.9)]), np.array([25, int(255 * 0.45), 255])]
        carriageArea = [400, 5500]
        carriageAspect = [0.5, 1.5]
        carriage_yBound = [450, 650]
        self.rcCarriage = Recognize(carriageMainMask, carriageArea, carriageAspect, ogDifferents=False, erosion_size=5,
                                    yBound=carriage_yBound)

        self.recTrigger = recTrigger

        self.active_zone = active_zone

        self.timeActivated = time.time()

        self.finishFlag = finishFlag
        self.which_logic_Set = which_logic_Set

        self.cap = cap

        self.capt_frames_nr = 0

        #self.fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
        cv2.startWindowThread()
        cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)

        self.setCapture()

        #self.runCaptureTryExcept()

    def runCaptureTryExcept(self):
        try:
            speedtest(self.runCapture)
        except Exception as e:
            self.logError(e)
        else:
            self.zon.finish()
        finally:
            self.releaseCapture()

    def runCapture(self):
        self.runVideoCaptureSavingFrames()
        self.saving_started = 0
        self.loger("STOP SAVING")

    def captureFrame(self):
        self.start_time = time.time()
        ret, frame_T = self.cap.read()
        self.frame_lum = frame_T

        frame_queue.put(deepcopy(frame_T))

        now = datetime.now()
        self.frame = cv2.putText(frame_T, str(now), self.org, self.font, self.fontScale, self.color, self.thickness,
                                 cv2.LINE_AA)

    def startRecording(self):

        if not self.last_flagSave and self.current_flagSave:
            self.wiedoWriter = Thread(target=VideoSaveThread)
            self.wiedoWriter.daemon = True
            self.wiedoWriter.start()

            self.saving_started = True
            #fileName = datetime.now().strftime(f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\video%Y%m%d_%H_%M_%S") + ".avi"
            #self.out = cv2.VideoWriter(fileName, self.fourcc,20.0, (int(self.cap.get(3)), int(self.cap.get(4))))
            self.loger("START RECORDING")

    def runVideoCaptureSavingFrames(self):
        sleep_time = 0
        global recordVideo
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

            #if self.saving_started:
            #    self.out.write(self.rowFrame)

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

            #if Settings.showZones and self.saving_started:
            #    self.out.write(self.rowFrame)

            self.zon.check_zone_change()

            cv2.rectangle(self.frame, (self.virtualCarage.position - 10, 480 - 10),
                          (self.virtualCarage.position + 10, 480 + 10), (200, 0, 0), -1)

            cv2.putText(self.frame, str(self.virtualCarage.positionMM), (self.virtualCarage.position + 10, 480 + 10),
                        self.font, self.fontScale, self.color, self.thickness,
                        cv2.LINE_AA)

            self.cross()
            cv2.circle(self.frame, (int(self.rcMouse.px), int(self.rcMouse.py)), 4, (0, 0, 255), -1)

            self.logPositionData((self.rcMouse.px, self.rcMouse.py), self.rcMouse.oldLocation)

            cv2.circle(self.frame, (int(self.rcCarriage.px), int(self.rcCarriage.py)), 4, (0, 255, 0), -1)

            self.virtualCarage.advance(int(self.rcMouse.px), int(self.rcCarriage.px))

            if self.frame is not None:
                cv2.imshow(self.windowName, self.frame)

            # STOP SAVING
            if self.last_flagSave and not self.current_flagSave:
                recordVideo = False
                self.saving_started = 0
                self.loger("STOP SAVING")

            self.last_flagSave = self.current_flagSave

            if (cv2.waitKey(1) and 0xFF == ord('q')) or self.finishFlag.is_set():
                self.finishFlag.set()
                recordVideo = False
                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            if cv2.getWindowProperty(self.windowName, cv2.WND_PROP_VISIBLE) < 1:
                self.finishFlag.set()
                self.out.release()
                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            self.capt_frames_nr = self.capt_frames_nr + 1

            self.active_zone.value = self.zon.active_zone

            processing_time = time.time() - self.start_time
            sleep_time = self.frame_delay - processing_time
            self.loger("fream leeway time is " + str(sleep_time))
            time.sleep( max(0, int(sleep_time)))

    def cross(self):
        if len(self.rcMouse.oldLocation) == 2:
            x, y = self.rcMouse.oldLocation
            cv2.line(self.frame, (x - 10, y), (x + 10, y), (255, 0, 0), 1)
            cv2.line(self.frame, (x, y - 10), (x, y + 10), (255, 0, 0), 1)

        if len(self.rcCarriage.oldLocation) == 2:
            x, y = self.rcCarriage.oldLocation
            cv2.line(self.frame, (x - 10, y), (x + 10, y), (0, 255, 0), 1)
            cv2.line(self.frame, (x, y - 10), (x, y + 10), (0, 255, 0), 1)

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

            self.loger("calibration finished")

            cv2.imwrite(f"{Settings.dataLocation}\\self.calibration.jpg", self.frame)

            self.calibratedFlag = 1

        #if self.capt_frames_nr == 10:
        #    self.loger("Starting calibration...")
        #    self.calibration_start = 20

        #if self.calibration_start > 0:
        #    self.calibration.append(cv2.cvtColor(self.frame_lum, cv2.COLOR_RGB2GRAY).copy())
        #    self.refCalibration = np.mean(self.calibration, axis=0)
            # self.zon.set_ref_image(self.frame_lum)
            # todo proper calibration for new recognize
            # self.zon.set_ref_image(self.refCalibration) #old save image for old recognize

        #    if self.calibration_start:
        #        self.refCalibration = np.mean(self.calibration, axis=0)
        #        self.calibratedFlag = 1

        #        self.save_calibration = 1

        #    self.calibration_start = self.calibration_start - 1

        #if self.calibratedFlag and not self.messagePrinted:
        #    self.messagePrinted = True
        #    self.loger("calibration finished")

        #if self.save_calibration:
        #    self.save_calibration = 0
        #    cv2.imwrite(f"{Settings.dataLocation}\\self.calibration.jpg", self.frame)


