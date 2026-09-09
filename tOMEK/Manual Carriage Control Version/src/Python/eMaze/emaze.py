import multiprocessing
import threading

import numpy

from src.Python.Doors.DoorControl import DoorControl
from src.Python.KeyboardMotorControl import run_keyboard_motor_control
from src.Python.Setup.Setup import Setup
from src.Python.eMaze.emazeNodors import EMazeNoDoors


class EMaze(EMazeNoDoors):

    def __init__(self):
        self.logStart()
        super(EMaze, self).__init__()

        self.door_status = multiprocessing.Array(
            'i', numpy.zeros(self.nr_of_doors, dtype=numpy.uint)
        )
        self.light_status = multiprocessing.Array(
            'i', numpy.zeros(4, dtype=numpy.uint)
        )

        self.dc = multiprocessing.Process(
            target=DoorControl,
            args=(self.door_status, self.light_status, self.finishFlag,),
            name="DoorControl",
        )

        # Manual carriage control must run in the main Python process.
        # This thread is the only Python component that opens COM3.
        self.keyboard_motor_thread = threading.Thread(
            target=run_keyboard_motor_control,
            args=(self.finishFlag,),
            name="KeyboardMotorControl",
            daemon=True,
        )

    def run(self):
        self.p.start()
        self.dc.start()
        self.keyboard_motor_thread.start()

        try:
            self.mainLoop()
        finally:
            self.finishFlag.set()

            for process in (self.p, self.dc):
                process.join(timeout=3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)

            self.keyboard_motor_thread.join(timeout=2)

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
    multiprocessing.freeze_support()
    Setup().setUp()
    eMaze = EMaze()
    eMaze.run()