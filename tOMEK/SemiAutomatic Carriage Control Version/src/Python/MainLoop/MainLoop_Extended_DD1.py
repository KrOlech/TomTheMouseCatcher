import random
import threading
import time

from src.Python.MainLoop.MainLoop import MainLoop as BaseMainLoop
from src.Python.Settings import Settings


class MainLoop(BaseMainLoop):
    """Extended DD1: L1 reward 100%, L2 reward 25%, delayed opening of D5 in zone D."""

    MAX_TRIALS = 50
    REWARD_PULSE_SEC = 0.1
    DD_REWARD_PROBABILITY = 0.25

    def __init__(self):
        super().__init__()
        self._delayed_door_pending = False

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
                    self._reward("L1")

                if self.isS2touched:
                    self.isS2touched = False
                    if random.random() <= self.DD_REWARD_PROBABILITY:
                        self._reward("L2")
                    else:
                        self.loger("L2 action skipped (75% chance)")

                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2", "D5"])
                self._openDoors(["D3", "D4", "D6"])

            if zone == "B":
                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2"])
                self._openDoors(["D3", "D4", "D6"])

            if zone == "C":
                self.CloseDoor("D5")

            if zone == "D":
                self.activate_d5_with_delay()

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

    def activate_d5_with_delay(self):
        if self._delayed_door_pending:
            return
        self._delayed_door_pending = True
        initial_counter = self.counter

        def delayed_open():
            try:
                delay = self._delay_for_trial(initial_counter)
                if delay > 0:
                    time.sleep(delay)
                if (
                    not self.finishFlag.is_set()
                    and self.counter == initial_counter
                    and self.getActivatedZone() == "D"
                ):
                    self.OpenDoor("D5")
                    self.loger(f"D5 opened after {delay} s (counter={initial_counter})")
                else:
                    self.loger("D5 delayed opening cancelled: context changed")
            finally:
                self._delayed_door_pending = False

        threading.Thread(target=delayed_open, daemon=True).start()

    @staticmethod
    def _delay_for_trial(counter):
        if 10 <= counter <= 19:
            return 1
        if 20 <= counter <= 29:
            return 3
        if 30 <= counter <= 39:
            return 5
        if 40 <= counter <= 50:
            return 7
        return 0

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
