import os
import time
import cProfile
from datetime import datetime
from itertools import count
from copy import deepcopy


import cv2
import numpy as np

from src.Python.Loger.Loger import Loger
from src.Python.Recognize.Recognize_AB_Filter import Recognize
from src.Python.Settings import Settings
from src.Python.VirtualCarrage.VirtualCarrage import VirtualCarrage
from src.Python.Zones.Zones import Zones
from src.Python.VideoCapture.VideoSaveThread import VideoSaveThread

from queue import Queue
from threading import Thread

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

class VideoCaptureMT(Loger):

    font = cv2.FONT_HERSHEY_SIMPLEX
    org = (100, 23)
    fontScale = 0.5
    color = (255, 0, 0)
    thickness = 1

    windowName: str = "output"

    start_time = 0

    frame = None

    target_fps = Settings.fps
    frame_delay = 1.0 / target_fps
    start_time = 0

    #def __init__(self, active_zone, recTrigger, finishFlag, which_logic_Set, trial_nr):
    def __init__(self):

        self.frameQueueSaving = Queue(maxsize=100)
        self.frameQueueMouse = Queue(maxsize=100)
        self.frameQueueCarriage = Queue(maxsize=100)


        self.locationQueueMouse = Queue(maxsize=100)
        self.locationQueueCarriage = Queue(maxsize=100)

        mouseMainMask = [np.array([85, 85, 150]), np.array([100, 150, 220])]
        mousePlexyMask = [np.array([0, 0, 210]), np.array([110, 25, 250])]
        mouseArea = [400, 5500]
        mouseAspect = [0.25, 3.3]
        self.rcMouse = Recognize(mouseMainMask, mouseArea, mouseAspect, frameQue=self.frameQueueMouse, ogDifferents=False, locationQue=self.locationQueueMouse, plexyMask=mousePlexyMask)
        self.rcMouseThred = Thread(target=self.rcMouse.getLocationsSeparateThread)
        self.rcMouseThred.daemon = True
        self.rcMouseThred.start()

        carriageMainMask = [np.array([0, int(255 * 0.25), int(255 * 0.9)]), np.array([25, int(255 * 0.45), 255])]
        carriageArea = [400, 5500]
        carriageAspect = [0.5, 1.5]
        carriage_yBound = [450, 650]
        self.rcCarriage = Recognize(carriageMainMask, carriageArea, carriageAspect,frameQue=self.frameQueueCarriage, locationQue=self.locationQueueCarriage, ogDifferents=False, erosion_size=5,
                                    yBound=carriage_yBound)
        self.rcCarriageThred = Thread(target=self.rcCarriage.getLocationsSeparateThread)
        self.rcCarriageThred.daemon = True
        self.rcCarriageThred.start()

        self.virtualCarage = VirtualCarrage()

        #self.zon = Zones(which_logic_Set, trial_nr)
        #self.zon.read_zones()

        self.cap = cv2.VideoCapture(Settings.CamNr)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Settings.FrameWidth)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Settings.FrameHeigth)

        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        fileName = datetime.now().strftime(f"{os.path.expanduser('~')}\\Documents\\TOM\\data\\video%Y%m%d_%H_%M_%S") + ".avi"
        self.out = cv2.VideoWriter(fileName, fourcc, 20.0, (int(self.cap.get(3)), int(self.cap.get(4))))

        self.videoSave =  VideoSaveThread(self.out, self.frameQueueSaving)
        self.videoSaveThred = Thread(target=self.videoSave.saveFrames)
        self.videoSaveThred.daemon = True
        self.videoSaveThred.start()

        cv2.startWindowThread()
        cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)


    def runCaptureTryExcept(self):
        try:
            speedtest(self.runVideoCaptureSavingFrames)
        except Exception as e:
            self.logError(e)
        else:
            ...
            #self.zon.finish()
        finally:
            self.releaseCapture()

    def releaseCapture(self):
        self.cap.release()
        self.out.release()
        cv2.destroyAllWindows()

    def captureFrame(self):
        self.start_time = time.time()
        ret, frame_T = self.cap.read()

        frame = deepcopy(frame_T)
        self.frameQueueSaving.put(frame.copy())
        self.frameQueueMouse.put(frame.copy())
        self.frameQueueCarriage.put(frame.copy())

        now = datetime.now()
        self.frame = cv2.putText(frame_T, str(now), self.org, self.font, self.fontScale, self.color, self.thickness,
                                 cv2.LINE_AA)

    def runVideoCaptureSavingFrames(self):

        for i in count(0):

            self.captureFrame()

            if self.frame is not None:
                cv2.imshow(self.windowName, self.frame)

            #print(self.locationQueueMouse.get())
            #print(self.locationQueueCarriage.get())

            if cv2.waitKey(1) and 0xFF == ord('q'):
                ...

            processing_time = time.time() - self.start_time
            sleep_time = self.frame_delay - processing_time
            self.loger("fream leeway time is " + str(sleep_time))
            time.sleep( max(0, int(sleep_time)))



if __name__ == '__main__':
    VideoCaptureMT().runCaptureTryExcept()
