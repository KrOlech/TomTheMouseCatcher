import multiprocessing

from src.Python.eMaze_App_TOM.Setup.Setup import Setup
from src.Python.eMaze_App_TOM.VideoCapture.VideoCapture import VideoCapture
from src.Python.eMaze_App_TOM.eMaze.apstract import EMazeAbstract
from src.Python.eMaze_App_TOM.Loger.Loger import Loger


class EMazeNoDoors(EMazeAbstract):

    def CloseDoor(self, name):
        pass

    def OpenDoor(self, name):
        pass

    def LightOff(self, ln):
        pass

    def LightOn(self, ln):
        pass

    def __init__(self):
        super(EMazeNoDoors, self).__init__()

        self.p = multiprocessing.Process(target=VideoCapture,
                                         args=(
                                             self.active_zone, multiprocessing.Event(), self.finishFlag,
                                             self.which_logic_Set, self.trial_nr))

    def run(self):
        self.p.start()
        self.mainLoop()


if __name__ == '__main__':
    Setup(Loger).setUp()
    eMaze = EMazeNoDoors()
    eMaze.run()
