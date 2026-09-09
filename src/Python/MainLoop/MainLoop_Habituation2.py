import threading
import time

from src.Python.MainLoop.MainLoop import MainLoop as BaseMainLoop
from src.Python.Settings import Settings


class MainLoop(BaseMainLoop):
    """Legacy Habituation2 adapted to current architecture.

    L1 and L2 are rewarded in A. F1/F2 do not close D6/D3, matching the old file.
    If D7 exists in door_names, it is opened after 5 s in A; otherwise it is skipped safely.
    """

    MAX_TRIALS = 30
    REWARD_PULSE_SEC = 0.1
    D7_DELAY_SEC = 5.0

    def __init__(self):
        super().__init__()
        self._d7_timer_pending = False
        self._d7_missing_logged = False

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
                    self._reward("L2")

                self._schedule_d7_open_if_available()
                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2"])
                self._openDoors(["D3", "D4", "D5", "D6"])

            if zone == "B":
                self._finish_previous_trial_if_needed()
                self._closeDoors(["D1", "D2"])
                self._openDoors(["D3", "D4", "D5", "D6"])

            if zone == "E1":
                self.CloseDoor("D5")
            if zone == "H1":
                self.flagTrial = True
                self.OpenDoor("D1")

            if zone == "E2":
                self.CloseDoor("D4")
            if zone == "H2":
                self.flagTrial = True
                self.OpenDoor("D2")

            self._sync_trial_number()
            if self.counter >= self.MAX_TRIALS:
                self.finishFlag.set()

        self.finishFlag.set()

    def _schedule_d7_open_if_available(self):
        door_names = getattr(self, "door_names", [])
        if "D7" not in door_names:
            if not self._d7_missing_logged:
                self.loger("Habituation2: D7 is not configured; delayed D7 action skipped")
                self._d7_missing_logged = True
            return

        if self._d7_timer_pending:
            return

        self._d7_timer_pending = True
        initial_counter = self.counter

        def delayed_open():
            try:
                time.sleep(self.D7_DELAY_SEC)
                if (
                    not self.finishFlag.is_set()
                    and self.counter == initial_counter
                    and self.getActivatedZone() == "A"
                ):
                    self.OpenDoor("D7")
                    self.loger("D7 opened after 5 s in zone A")
            finally:
                self._d7_timer_pending = False

        threading.Thread(target=delayed_open, daemon=True).start()

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
