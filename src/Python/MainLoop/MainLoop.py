import time
from abc import ABC

from src.Python.MainLoop.MainLoopAbstract import MainLoopAbstract
from src.Python.Settings import Settings


class MainLoop(MainLoopAbstract, ABC):
    which_logic_Set = None  # to fill with multiprocessing.value
    trial_nr = None  # to fill with multiprocessing.value
    active_zone = None  # to fill with multiprocessing.value

    finishFlag = None  # to fill multiprocessing.Event

    counter: int = 0  # count of the loop

    def __init__(self):
        super().__init__()
        self.flagTrial: bool = False
        self.isS1touched: bool = True
        self.isS2touched: bool = True
        self.whichLogic: bool = False
        self.drop1: bool = False
        self.drop2: bool = False

    def mainLoop(self):
        time.sleep(2)
        self.checkActivation()

        for _ in iter(int, 1):

            time.sleep(Settings.LoopTime)
            self.checkActivation()

            if self.counter % 2:
                if self.whichLogic:
                    self.Free_RightLogic()
                    self.which_logic_Set.value = 1
                else:
                    self.Free_LeftLogic()
                    self.which_logic_Set.value = 0

            else:
                if self.whichLogic:
                    self.RightLogic()
                    self.which_logic_Set.value = 1
                else:
                    self.LeftLogic()
                    self.which_logic_Set.value = 0

            self.trial_nr.value = self.counter

            if self.getActivatedZone() == "A" and self.counter >= Settings.MaxTrials:
                break

        self.finishFlag.set()

    def RightLogic(self):
        if self.getActivatedZone() == "S1":
            self._setS1Flag()
            self.CloseDoor("D5")

        if self.getActivatedZone() == "A":
            self._turnLightsOn([1, 2])
            self._turnLightsOff([3, 4])
            self._playSound1()

        if self.getActivatedZone() == "A":
            self.flagTrial = True
            self.drop1 = True
            self._closeDoors(["D1", "D2", "D3", "D4"])
            self._openDoors(["D5", "D6"])

        if self.getActivatedZone() == "B":
            self.flagTrial = True
            self.drop1 = True
            self._closeDoors(["D1", "D2", "D3", "D4"])
            self._openDoors(["D5", "D6"])
            self._turnLightsOn([1, 2])
            self._turnLightsOff([3, 4])

        if self.getActivatedZone() == "E1":
            self.CloseDoor("D5")

        if self.getActivatedZone() == "F1":
            self.CloseDoor("D6")
            self._turnLightsOff([1, 2, 3, 4])

        if self.getActivatedZone() == "E1" and self.isS1touched and self.drop1:
            self.isS1touched = False
            self.drop1 = False
            self.CloseDoor("L1")
            self.loger("L1 activated")
            time.sleep(0.1)
            self.CloseDoor("L1")
            self.OpenDoor("L1")

        if self.getActivatedZone() == "H1":

            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1

            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")
            self.finPygem()

    def LeftLogic(self):

        if self.getActivatedZone() == "S2":
            self._setS2Flag()
            self.CloseDoor("D4")

        if self.getActivatedZone() == "A":
            self._turnLightsOn([1, 2])
            self._turnLightsOff([3, 4])
            self._playSound2()

        if self.getActivatedZone() == "A":
            self.flagTrial = True
            self.drop2 = True
            self._closeDoors(["D1", "D2", "D5", "D6"])
            self._openDoors(["D3", "D4"])

        if self.getActivatedZone() == "B":
            self.flagTrial = True
            self.drop2 = True
            self._closeDoors(["D1", "D2", "D5", "D6"])
            self._openDoors(["D3", "D4"])
            self._turnLightsOff([1, 2])
            self._turnLightsOn([3, 4])
            self._playSound2()

        if self.getActivatedZone() == "E2" and self.isS2touched and self.drop2:
            self.isS2touched = False
            self.drop2 = False
            self.CloseDoor("L2")
            self.loger("L2 activated")
            time.sleep(0.1)
            self.CloseDoor("L2")
            self.OpenDoor("L2")

        if self.getActivatedZone() == "E2":
            self.CloseDoor("D4")

        if self.getActivatedZone() == "F2":
            self.CloseDoor("D3")
            self._turnLightsOff([1, 2, 3, 4])

        if self.getActivatedZone() == "H2":

            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1

            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")

            self.finPygem()

    def Free_RightLogic(self):
        if self.getActivatedZone() == "S1":
            self._setS1Flag()
            self.CloseDoor("D5")

        if self.getActivatedZone() == "S2":
            self.CloseDoor("D4")
            self._setS2Flag()

        if self.getActivatedZone() == "A":
            self._turnLightsOn([1, 2])
            self._turnLightsOff([3, 4])
            self._playSound1()

        if self.getActivatedZone() == "A":
            self.flagTrial = True
            self.drop1 = True
            self._closeDoors(["D1", "D2"])
            self._openDoors(["D3", "D4", "D5", "D6"])

        if self.getActivatedZone() == "B":
            self.flagTrial = True
            self.drop1 = True
            self._closeDoors(["D1", "D2"])
            self._openDoors(["D3", "D4", "D5", "D6"])
            self._turnLightsOn([1, 2])
            self._turnLightsOff([3, 4])
            self._playSound1()

        if self.getActivatedZone() == "F1":
            self.CloseDoor("D6")
            self._turnLightsOff([1, 2, 3, 4])

        if self.getActivatedZone() == "E1" and self.isS1touched and self.drop1:
            self.isS1touched = False
            self.drop1 = False
            self.CloseDoor("L1")
            self.loger("L1 activated")
            time.sleep(0.1)
            self.CloseDoor("L1")
            self.OpenDoor("L1")

        if self.getActivatedZone() == "F2":
            self.CloseDoor("D3")
            self._turnLightsOff([1, 2, 3, 4])
            self.finPygem()

        if self.getActivatedZone() == "E1":
            self.CloseDoor("D5")

        if self.getActivatedZone() == "E2":
            self.CloseDoor("D4")
            self.finPygem()

        if self.getActivatedZone() == "H1":
            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")
            self.finPygem()

        if self.getActivatedZone() == "H2":
            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")

    def Free_LeftLogic(self):
        if self.getActivatedZone() == "S1":
            self._setS1Flag()
            self.CloseDoor("D5")

        if self.getActivatedZone() == "S2":
            self._setS2Flag()
            self.CloseDoor("D4")

        if self.getActivatedZone() == "A":
            self._turnLightsOff([1, 2])
            self._turnLightsOn([3, 4])
            self._playSound2()

        if self.getActivatedZone() == "A":
            self.flagTrial = True
            self.drop2 = True
            self._closeDoors(["D1", "D2"])
            self._openDoors(["D3", "D4", "D5", "D6"])

        if self.getActivatedZone() == "B":
            self.flagTrial = True
            self.drop2 = True
            self._closeDoors(["D1", "D2"])
            self._openDoors(["D3", "D4", "D5", "D6"])
            self._turnLightsOff([1, 2])
            self._turnLightsOn([3, 4])
            self._playSound2()

        if self.getActivatedZone() == "E1":
            self.CloseDoor("D5")
            self.finPygem()

        if self.getActivatedZone() == "E2":
            self.CloseDoor("D4")

        if self.getActivatedZone() == "E2" and self.isS2touched and self.drop2:
            self.isS2touched = False
            self.drop2 = False
            self.CloseDoor("L2")
            self.loger("L2 activated")
            time.sleep(0.1)
            self.CloseDoor("L2")
            self.OpenDoor("L2")

        if self.getActivatedZone() == "F1":
            self.CloseDoor("D6")
            self._turnLightsOff([1, 2, 3, 4])

        if self.getActivatedZone() == "F2":
            self.CloseDoor("D3")
            self._turnLightsOff([1, 2, 3, 4])

        if self.getActivatedZone() == "H1":
            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")

        if self.getActivatedZone() == "H2":
            if self.flagTrial:
                self.loger("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = False
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")
            self.finPygem()
