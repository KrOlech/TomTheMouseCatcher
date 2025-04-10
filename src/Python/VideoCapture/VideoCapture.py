import numpy as np
import multiprocessing
import cv2
from datetime import datetime
import time
import numpy
import os
from src.Python.Settings import Settings
from src.Python.Recognize.Recognize import Recognize


class VideoCapture:

    def __init__(self, active_zone, recTrigger, finishFlag, which_logic_Set, trial_nr):
        rc = Recognize(which_logic_Set, trial_nr)
        self.rc = rc
        rc.read_zones()
        self.save_calibration = 0
        self.active_zone = active_zone
        zone_active = 0
        zone_active_last = 0
        self.calibration_start = 0
        self.calibratedFlag = 0
        timeActivated = time.time()
        self.calibration = []
        self.refCalibration = []
        self.finishFlag = finishFlag
        self.which_logic_Set = which_logic_Set

        cap = cv2.VideoCapture(Settings.CamNr)#todo mock of camera

        self.cap = cap

        i = 0
        self.capt_frames_nr = 0
        frames = []
        offset_nr = 90
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        #cv2.startWindowThread()
        cv2.namedWindow("output", cv2.WND_PROP_VISIBLE)
        # fourcc = cv2.cv.CV_FOURCC(*'XVID')
        self.SetCapture()
        self.last_flagsave = 0
        self.current_flagsave = 0
        self.saving_started = 0
        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (100, 23)
        fontScale = 0.5
        color = (255, 0, 0)
        thickness = 1

        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            frames.append(frame)
            self.frame_lum = frame[:, :, 0]

            i = i + 1
            now = datetime.now()
            frame = cv2.putText(frame, str(now), org, font,
                                fontScale, color, thickness, cv2.LINE_AA)

            if i <= offset_nr:
                continue
            recTrigger.set()
            if recTrigger.is_set():
                self.current_flagsave = 1
            else:
                self.current_flagsave = 0

            # CALIBRATE
            self.Calibrate()

            # START SAVING
            if (self.last_flagsave == 0) & (self.current_flagsave == 1):
                self.saving_started = 1
                now = datetime.now()
                fname = now.strftime(".\\data\\video%Y%m%d_%H_%M_%S") + ".avi"
                out = cv2.VideoWriter(fname, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
                print("START SAVING")
            if Settings.showZones == False:
                if self.saving_started == 1:
                    out.write(frame)

            # Display the resulting frame
            frames.pop(0)
            if recTrigger.is_set():
                if self.calibratedFlag == 0:
                    cv2.circle(frame, (30, 17), 10, (0, 0, 255), -1)
                else:
                    cv2.circle(frame, (30, 17), 10, (0, 255, 0), -1)
            if (self.calibratedFlag == 1):
                lum = (rc.get_active_zone(self.frame_lum))
            else:
                lum = -1
            # print ("ref expo=",numpy.mean(frame_lum[y0:y0+h,x0:x0+w]))
            zone_active_last = zone_active

            for zone_nr in range(rc.zones_nr):
                x0, y0, w, h = rc.get_zone_coords(zone_nr)
                if (lum == zone_nr):
                    cv2.rectangle(frame, (x0, y0), (x0 + w, y0 + h), (0, 0, 250), 2)
                else:
                    cv2.rectangle(frame, (x0, y0), (x0 + w, y0 + h), (0, 200, 0), 2)
            if Settings.showZones == True:
                if self.saving_started == 1:
                    out.write(frame)

            if self.save_calibration:
                self.save_calibration = 0
                cv2.imwrite("self.calibration.jpg", frame)
            # if (zone_active_last>zone_active):
            #	print ("ZONE DEACTIVATED AFTER ",time.time()-timeActivated)
            # if (zone_active_last<zone_active):
            #	print ("ZONE ACTIVATED")
            #	timeActivated=time.time()
            rc.check_zone_change()
            cv2.imshow('output', frame)
            # print (self.last_flagsave,self.current_flagsave)
            # STOP SAVING
            if (self.last_flagsave == 1) & (self.current_flagsave == 0):
                out.release()
                self.saving_started = 0
                print("STOP SAVING")

            self.last_flagsave = self.current_flagsave

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            self.capt_frames_nr = self.capt_frames_nr + 1
            # print ("lum=",lum)
            self.active_zone.value = rc.active_zone

            if self.finishFlag.is_set():
                break
        # When everything done, release the capture
        self.RelaseCapture()
		
    def RelaseCapture(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.rc.finish()

    def SetCapture(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Settings.FrameWidth)
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Settings.FrameHeigth)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
        self.ret_val, self.cap_for_exposure = self.cap.read()
        # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3) # auto mode
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode

    def Calibrate(self):
        if (self.capt_frames_nr == 10):
            # cap.set(cv2.CAP_PROP_EXPOSURE,16)	
            print("Starting calibration...")
            self.calibration_start = 20
        if self.calibration_start > 0:
            self.calibration.append(self.frame_lum.copy())
            # print ("fl=",(frame_lum[y0:y0+h,x0:x0+w])[0:100,2])
            # print ("C0=",(self.calibration[0])[y0:y0+h,x0:x0+w][0:100,2])
            # print ("a=",frame_lum)
            # print ("b=",self.calibration[0])
            # print ("ref expo=",numpy.mean(frame_lum[y0:y0+h,x0:x0+w]))
            self.refCalibration = numpy.mean(self.calibration, axis=0)
            # print (self.refCalibration.shape)
            # if (self.calibration_start==18):
            #	print ("c0=",(self.calibration[0])[y0:y0+h,x0:x0+w][0:100,2],"c1=",(self.calibration[1])[y0:y0+h,x0:x0+w][0:100,2])
            #	os._exit(0)
            # diff=numpy.mean(numpy.subtract(self.frame_lum[y0:y0+h,x0:x0+w],self.refCalibration[y0:y0+h,x0:x0+w]))
            # print ("diff=",diff)
            self.refCalibration = numpy.mean(self.calibration, axis=0)
            self.rc.set_ref_image(self.refCalibration)
            # print ((frame_lum[y0:y0+h,x0:x0+w])[0:100,2],(self.refCalibration[y0:y0+h,x0:x0+w])[0:100,2])
            if self.calibration_start == 1:
                self.refCalibration = numpy.mean(self.calibration, axis=0)
                self.calibratedFlag = 1
                print("calibration finished...")
                self.save_calibration = 1

            self.calibration_start = self.calibration_start - 1
