import multiprocessing

import numpy

from src.Python.Doors.DoorControl import DoorControl
from src.Python.Setup.Setup import Setup
from src.Python.eMaze.emazeNodors import EMazeNoDoors


class EMaze(EMazeNoDoors):

    def __init__(self):
        super(EMaze, self).__init__()

        self.door_status = multiprocessing.Array('i', numpy.zeros(self.nr_of_doors, dtype=numpy.uint))
        self.light_status = multiprocessing.Array('i', numpy.zeros(4, dtype=numpy.uint))

        self.dc = multiprocessing.Process(target=DoorControl,
                                          args=(self.door_status, self.light_status, self.finishFlag,))

    def run(self):
        self.p.start()
        self.dc.start()
        self.mainLoop()

    def _getDoorIndex(self, door_name):
        return DoorControl.getDoorIndex(door_name, self.door_names)

    def CloseDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 1

    def OpenDoor(self, name):
        door_index = self._getDoorIndex(name)
        self.door_status[door_index] = 0

    def LightOn(self, ln):
        self.light_status[ln - 1] = 1
        self.loger(f"Light {ln} turned on")

    def LightOff(self, ln):
        self.light_status[ln - 1] = 0
        self.loger(f"Light {ln} turned off")


if __name__ == '__main__':
    Setup().setUp()
    eMaze = EMaze()
    eMaze.run()
