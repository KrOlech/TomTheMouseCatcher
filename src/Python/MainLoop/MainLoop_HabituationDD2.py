import random
import time

from src.Python.MainLoop.MainLoop import MainLoop as BaseMainLoop
from src.Python.Settings import Settings


class MainLoop(BaseMainLoop):
    """Habituation DD2: L1 reward 25%, L2 reward 100%."""

    MAX_TRIALS = 50
    REWARD_PULSE_SEC = 0.1
    DD_REWARD_PROBABILITY = 0.25

    def mainLoop(self):
        time.sleep(2)
        self.checkActivation()
        self.isS1touched = True
        self.isS2touched = True
        self.counter = 0
        self.flagTrial = False

        while not self.finishFlag.is_set():
            time.sleep(Settings.LoopTime)
            self.checkActivation()
            zone = self.getActivatedZone()

            if zone == "S1":
                self.isS1touched = True
                self.loger("Flag S1 set")
                self.CloseDoor("D5")

            if zone == "S2":
                self.isS2touched = True
                self.loger("Flag S2 set")
                self.CloseDoor("D4")

            if zone == "A":
                self._turnLightsOff([1, 2, 3, 4])

                if self.isS1touched:
                    self.isS1touched = False
                    if random.random() <= self.DD_REWARD_PROBABILITY:
                        self._reward("L1")
                    else:
                        self.loger("L1 action skipped (75% chance)")

                if self.isS2touched:
                    self.isS2touched = False
                    self._reward("L2")

                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2"])
                self._openDoors(["D3", "D4", "D5", "D6"])

            if zone == "B":
                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2"])
                self._openDoors(["D3", "D4", "D5", "D6"])

            if zone == "E1":
                self.CloseDoor("D5")
            if zone == "F1":
                self.CloseDoor("D6")
            if zone == "H1":
                self.flagTrial = True
                self.OpenDoor("D1")

            if zone == "E2":
                self.CloseDoor("D4")
            if zone == "F2":
                self.CloseDoor("D3")
            if zone == "H2":
                self.flagTrial = True
                self.OpenDoor("D2")

            self._sync_trial_number()
            if self.counter >= self.MAX_TRIALS:
                self.finishFlag.set()

        self.finishFlag.set()

    def _finish_previous_trial_if_needed(self):
        if self.flagTrial:
            self.loger("Counter=", self.counter)
            self.counter += 1
        self.flagTrial = False

    def _reward(self, line):
        self.CloseDoor(line)
        self.loger(f"{line} activated")
        time.sleep(self.REWARD_PULSE_SEC)
        self.CloseDoor(line)
        self.OpenDoor(line)

    def _sync_trial_number(self):
        if self.trial_nr is not None:
            self.trial_nr.value = self.counter
