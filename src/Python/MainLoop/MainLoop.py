import time
from abc import ABC

from src.Python.MainLoop.MainLoopAbstract import MainLoopAbstract
from src.Python.Settings import Settings


class MainLoop(MainLoopAbstract, ABC):

    which_logic_Set = None   # multiprocessing.Value
    trial_nr = None          # multiprocessing.Value
    active_zone = None       # multiprocessing.Value

    finishFlag = None        # multiprocessing.Event

    counter: int = 0

    def __init__(self):
        super().__init__()

        self.flagTrial: bool = False
        self.isS1touched: bool = True
        self.isS2touched: bool = True

        self.drop1: bool = False
        self.drop2: bool = False

        # IMPORTANT:
        # MainLoop variants such as HABITUATION do not necessarily need
        # Settings.LogicList, so do not fail here if it is absent.
        logic_list = getattr(Settings, "LogicList", [])

        if logic_list:
            # Trial 0 follows LogicList[0]
            self.whichLogic: bool = bool(logic_list[0])
        else:
            self.whichLogic: bool = False


    # ================================================================
    # HELPERS
    # ================================================================

    def _set_logic_for_current_trial(self):
        """
        Load LEFT/RIGHT choice for the current trial.

        LogicList:
            0 = LEFT
            1 = RIGHT
        """

        logic_list = getattr(Settings, "LogicList", None)

        if logic_list is None:
            raise RuntimeError(
                "Settings.LogicList is not defined. "
                "It is required when MainLoopMode = 'NORMAL'."
            )

        if self.counter >= len(logic_list):
            raise RuntimeError(
                f"LogicList is too short. "
                f"counter={self.counter}, "
                f"len(LogicList)={len(logic_list)}, "
                f"MaxTrials={Settings.MaxTrials}"
            )

        self.whichLogic = bool(logic_list[self.counter])

        self.loger(
            "Trial logic:",
            self.counter,
            "RIGHT" if self.whichLogic else "LEFT"
        )


    def _activate_L1(self):
        """
        Give milk through L1 using duration specified in Settings.LTime1.
        """

        self.CloseDoor("L1")
        self.loger("L1 activated")

        time.sleep(Settings.LTime1)

        self.CloseDoor("L1")
        self.OpenDoor("L1")


    def _activate_L2(self):
        """
        Give milk through L2 using duration specified in Settings.LTime2.
        """

        self.CloseDoor("L2")
        self.loger("L2 activated")

        time.sleep(Settings.LTime2)

        self.CloseDoor("L2")
        self.OpenDoor("L2")


    def _finish_trial(self):
        """
        Increment trial counter and prepare LogicList entry
        for the next trial.
        """

        if self.flagTrial:

            self.loger("Counter=", self.counter)

            self.counter += 1

        self.flagTrial = False

        # Do not read LogicList after the final trial.
        if self.counter < Settings.MaxTrials:
            self._set_logic_for_current_trial()


    # ================================================================
    # MAIN LOOP
    # ================================================================

    def mainLoop(self):

        time.sleep(2)

        self.checkActivation()

        # NORMAL protocol requires LogicList.
        logic_list = getattr(Settings, "LogicList", None)

        if logic_list is None:
            raise RuntimeError(
                "MainLoop NORMAL requires Settings.LogicList. "
                "Uncomment one LogicList in Settings.py."
            )

        if len(logic_list) < Settings.MaxTrials:
            raise RuntimeError(
                f"LogicList has only {len(logic_list)} entries, "
                f"but MaxTrials = {Settings.MaxTrials}."
            )

        # Make absolutely sure trial 0 follows LogicList[0].
        self._set_logic_for_current_trial()

        self.loger(
            "Starting NORMAL MainLoop. Trial 0:",
            "RIGHT" if self.whichLogic else "LEFT"
        )

        for _ in iter(int, 1):

            time.sleep(Settings.LoopTime)

            self.checkActivation()

            # --------------------------------------------------------
            # EVEN trials = FORCED CHOICE
            # ODD trials  = FREE CHOICE
            # --------------------------------------------------------

            if self.counter % 2:

                # FREE trial

                if self.whichLogic:

                    self.Free_RightLogic()

                    if self.which_logic_Set is not None:
                        self.which_logic_Set.value = 1

                else:

                    self.Free_LeftLogic()

                    if self.which_logic_Set is not None:
                        self.which_logic_Set.value = 0

            else:

                # FORCED trial

                if self.whichLogic:

                    self.RightLogic()

                    if self.which_logic_Set is not None:
                        self.which_logic_Set.value = 1

                else:

                    self.LeftLogic()

                    if self.which_logic_Set is not None:
                        self.which_logic_Set.value = 0


            if self.trial_nr is not None:
                self.trial_nr.value = self.counter


            # Experiment finishes after MaxTrials and return to A.
            if (
                self.getActivatedZone() == "A"
                and self.counter >= Settings.MaxTrials
            ):

                self.finishFlag.set()

                break


            if self.finishFlag.is_set():
                break


        self.finishFlag.set()


    # ================================================================
    # FORCED RIGHT
    # ================================================================

    def RightLogic(self):

        zone = self.getActivatedZone()


        # ------------------------------------------------------------
        # S1
        # ------------------------------------------------------------

        if zone == "S1":

            self._setS1Flag()

            self.CloseDoor("D5")


        # ------------------------------------------------------------
        # A
        # ------------------------------------------------------------

        if zone == "A":

            self._turnLightsOn([1, 2])

            self._turnLightsOff([3, 4])

            self._playSound1()


        if zone == "A":

            self.flagTrial = True

            self.drop1 = True

            # Forced RIGHT:
            # LEFT side closed
            self._closeDoors(
                ["D1", "D2", "D3", "D4"]
            )

            # RIGHT side open
            self._openDoors(
                ["D5", "D6"]
            )


        # ------------------------------------------------------------
        # B
        # ------------------------------------------------------------

        if zone == "B":

            self.flagTrial = True

            self.drop1 = True

            self._closeDoors(
                ["D1", "D2", "D3", "D4"]
            )

            self._openDoors(
                ["D5", "D6"]
            )

            self._turnLightsOn([1, 2])

            self._turnLightsOff([3, 4])


        # ------------------------------------------------------------
        # E1
        # ------------------------------------------------------------

        if zone == "E1":

            self.CloseDoor("D5")


        # ------------------------------------------------------------
        # F1
        # ------------------------------------------------------------

        if zone == "F1":

            self.CloseDoor("D6")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )


        # ------------------------------------------------------------
        # MILK L1
        # ------------------------------------------------------------

        if (
            zone == "E1"
            and self.isS1touched
            and self.drop1
        ):

            self.isS1touched = False

            self.drop1 = False

            self._activate_L1()


        # ------------------------------------------------------------
        # H1
        # ------------------------------------------------------------

        if zone == "H1":

            self._finish_trial()

            self.OpenDoor("D1")

            self.finPygem()


    # ================================================================
    # FORCED LEFT
    # ================================================================

    def LeftLogic(self):

        zone = self.getActivatedZone()


        # ------------------------------------------------------------
        # S2
        # ------------------------------------------------------------

        if zone == "S2":

            self._setS2Flag()

            self.CloseDoor("D4")


        # ------------------------------------------------------------
        # A
        # ------------------------------------------------------------

        if zone == "A":

            self._turnLightsOn([1, 2])

            self._turnLightsOff([3, 4])

            self._playSound2()


        if zone == "A":

            self.flagTrial = True

            self.drop2 = True

            # Forced LEFT
            self._closeDoors(
                ["D1", "D2", "D5", "D6"]
            )

            self._openDoors(
                ["D3", "D4"]
            )


        # ------------------------------------------------------------
        # B
        # ------------------------------------------------------------

        if zone == "B":

            self.flagTrial = True

            self.drop2 = True

            self._closeDoors(
                ["D1", "D2", "D5", "D6"]
            )

            self._openDoors(
                ["D3", "D4"]
            )

            self._turnLightsOff([1, 2])

            self._turnLightsOn([3, 4])

            self._playSound2()


        # ------------------------------------------------------------
        # MILK L2
        # ------------------------------------------------------------

        if (
            zone == "E2"
            and self.isS2touched
            and self.drop2
        ):

            self.isS2touched = False

            self.drop2 = False

            self._activate_L2()


        # ------------------------------------------------------------
        # E2
        # ------------------------------------------------------------

        if zone == "E2":

            self.CloseDoor("D4")


        # ------------------------------------------------------------
        # F2
        # ------------------------------------------------------------

        if zone == "F2":

            self.CloseDoor("D3")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )


        # ------------------------------------------------------------
        # H2
        # ------------------------------------------------------------

        if zone == "H2":

            self._finish_trial()

            self.OpenDoor("D2")

            self.finPygem()


    # ================================================================
    # FREE RIGHT
    # ================================================================

    def Free_RightLogic(self):

        zone = self.getActivatedZone()


        # ------------------------------------------------------------
        # S1 / S2
        # ------------------------------------------------------------

        if zone == "S1":

            self._setS1Flag()

            self.CloseDoor("D5")


        if zone == "S2":

            self.CloseDoor("D4")

            self._setS2Flag()


        # ------------------------------------------------------------
        # A
        # ------------------------------------------------------------

        if zone == "A":

            self._turnLightsOn([1, 2])

            self._turnLightsOff([3, 4])

            self._playSound1()


        if zone == "A":

            self.flagTrial = True

            self.drop1 = True

            # FREE choice:
            # both arms available
            self._closeDoors(
                ["D1", "D2"]
            )

            self._openDoors(
                ["D3", "D4", "D5", "D6"]
            )


        # ------------------------------------------------------------
        # B
        # ------------------------------------------------------------

        if zone == "B":

            self.flagTrial = True

            self.drop1 = True

            self._closeDoors(
                ["D1", "D2"]
            )

            self._openDoors(
                ["D3", "D4", "D5", "D6"]
            )

            self._turnLightsOn([1, 2])

            self._turnLightsOff([3, 4])

            self._playSound1()


        # ------------------------------------------------------------
        # F1
        # ------------------------------------------------------------

        if zone == "F1":

            self.CloseDoor("D6")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )


        # ------------------------------------------------------------
        # MILK L1
        # ------------------------------------------------------------

        if (
            zone == "E1"
            and self.isS1touched
            and self.drop1
        ):

            self.isS1touched = False

            self.drop1 = False

            self._activate_L1()


        # ------------------------------------------------------------
        # F2
        # ------------------------------------------------------------

        if zone == "F2":

            self.CloseDoor("D3")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )

            self.finPygem()


        # ------------------------------------------------------------
        # E1
        # ------------------------------------------------------------

        if zone == "E1":

            self.CloseDoor("D5")


        # ------------------------------------------------------------
        # E2
        # ------------------------------------------------------------

        if zone == "E2":

            self.CloseDoor("D4")

            self.finPygem()


        # ------------------------------------------------------------
        # H1
        # ------------------------------------------------------------

        if zone == "H1":

            self._finish_trial()

            self.OpenDoor("D1")

            self.finPygem()


        # ------------------------------------------------------------
        # H2
        # ------------------------------------------------------------

        if zone == "H2":

            self._finish_trial()

            self.OpenDoor("D2")


    # ================================================================
    # FREE LEFT
    # ================================================================

    def Free_LeftLogic(self):

        zone = self.getActivatedZone()


        # ------------------------------------------------------------
        # S1 / S2
        # ------------------------------------------------------------

        if zone == "S1":

            self._setS1Flag()

            self.CloseDoor("D5")


        if zone == "S2":

            self._setS2Flag()

            self.CloseDoor("D4")


        # ------------------------------------------------------------
        # A
        # ------------------------------------------------------------

        if zone == "A":

            self._turnLightsOff([1, 2])

            self._turnLightsOn([3, 4])

            self._playSound2()


        if zone == "A":

            self.flagTrial = True

            self.drop2 = True

            # FREE choice
            self._closeDoors(
                ["D1", "D2"]
            )

            self._openDoors(
                ["D3", "D4", "D5", "D6"]
            )


        # ------------------------------------------------------------
        # B
        # ------------------------------------------------------------

        if zone == "B":

            self.flagTrial = True

            self.drop2 = True

            self._closeDoors(
                ["D1", "D2"]
            )

            self._openDoors(
                ["D3", "D4", "D5", "D6"]
            )

            self._turnLightsOff([1, 2])

            self._turnLightsOn([3, 4])

            self._playSound2()


        # ------------------------------------------------------------
        # E1
        # ------------------------------------------------------------

        if zone == "E1":

            self.CloseDoor("D5")

            self.finPygem()


        # ------------------------------------------------------------
        # E2
        # ------------------------------------------------------------

        if zone == "E2":

            self.CloseDoor("D4")


        # ------------------------------------------------------------
        # MILK L2
        # ------------------------------------------------------------

        if (
            zone == "E2"
            and self.isS2touched
            and self.drop2
        ):

            self.isS2touched = False

            self.drop2 = False

            self._activate_L2()


        # ------------------------------------------------------------
        # F1
        # ------------------------------------------------------------

        if zone == "F1":

            self.CloseDoor("D6")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )


        # ------------------------------------------------------------
        # F2
        # ------------------------------------------------------------

        if zone == "F2":

            self.CloseDoor("D3")

            self._turnLightsOff(
                [1, 2, 3, 4]
            )


        # ------------------------------------------------------------
        # H1
        # ------------------------------------------------------------

        if zone == "H1":

            self._finish_trial()

            self.OpenDoor("D1")


        # ------------------------------------------------------------
        # H2
        # ------------------------------------------------------------

        if zone == "H2":

            self._finish_trial()

            self.OpenDoor("D2")

            self.finPygem()