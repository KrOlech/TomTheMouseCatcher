import time
from abc import abstractmethod
from src.Python.Settings import Settings
import pygame
import csv

pygame.mixer.init()
sound2 = pygame.mixer.Sound('C:\\Users\\kradwanska\\Desktop\\7k_hz.wav')
sound1 = pygame.mixer.Sound('C:\\Users\\kradwanska\\Desktop\\14k_hz.wav')
sound1.set_volume(Settings.volume2)
sound2.set_volume(Settings.volume1)


class MainLoop:
    @abstractmethod
    def log_data_csv(zone_name, duration):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")  # Get actual time
        log_entry = [timestamp, zone_name, round(duration, 2)]
        with open(".\\data\\zone_activity_log.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(log_entry)

    def MainLoop(self):
        time.sleep(2)
        self.checkActivation()
        self.counter = 0
        self.flagTrial = 0
        self.isS1touched = 1
        self.isS2touched = 1
        self.whichLogic = 0
        self.drop1 = 0
        self.drop2 = 0
        while True:
            time.sleep(Settings.LoopTime)
            self.checkActivation()

            if self.counter % 2:
                if self.whichLogic == 0:
                    self.Free_LeftLogic()
                    self.which_logic_Set.value = 0
                else:
                    self.Free_RightLogic()
                    self.which_logic_Set.value = 1
                self.trial_nr.value = self.counter

            else:
                if self.whichLogic == 0:
                    self.LeftLogic()
                    self.which_logic_Set.value = 0
                else:
                    self.RightLogic()
                    self.which_logic_Set.value = 1
                self.trial_nr.value = self.counter

            if self.counter == Settings.MaxTrials and (self.getActivatedZone() == "A"):
                self.finishFlag.set()
                break

    def RightLogic(self):
        if (self.getActivatedZone() == "S1"):
            self.isS1touched = 1
            print("Flag S1 set")
            self.CloseDoor("D5")

        if (self.getActivatedZone() == "A"):
            self.LightOn(1)
            self.LightOn(2)
            self.LightOff(3)
            self.LightOff(4)
            pygame.mixer.init()
            sound1.play(loops=-1)

        if (self.getActivatedZone() == "A"):
            self.flagTrial = 1
            self.drop1 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.CloseDoor("D3")
            self.CloseDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")

        if (self.getActivatedZone() == "B"):
            self.flagTrial = 1
            self.drop1 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.CloseDoor("D3")
            self.CloseDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")
            self.LightOn(1)
            self.LightOn(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "E1"):
            self.CloseDoor("D5")

        if (self.getActivatedZone() == "F1"):
            self.CloseDoor("D6")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "E1" and self.isS1touched == 1 and self.drop1 == 1):
            self.isS1touched = 0
            self.drop1 = 0
            self.CloseDoor("L1")
            print("L1 activated")
            time.sleep(0.1)
            self.CloseDoor("L1")
            self.OpenDoor("L1")

        if (self.getActivatedZone() == "H1"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

    def LeftLogic(self):

        if (self.getActivatedZone() == "S2"):
            self.isS2touched = 1
            print("Flag S2 set")
            self.CloseDoor("D4")

        if (self.getActivatedZone() == "A"):
            self.LightOff(1)
            self.LightOff(2)
            self.LightOn(3)
            self.LightOn(4)
            pygame.mixer.init()
            sound2.play(loops=-1)

        if (self.getActivatedZone() == "A"):
            self.flagTrial = 1
            self.drop2 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.CloseDoor("D5")
            self.CloseDoor("D6")

        if (self.getActivatedZone() == "B"):
            self.flagTrial = 1
            self.drop2 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.CloseDoor("D5")
            self.CloseDoor("D6")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOn(3)
            self.LightOn(4)
            pygame.mixer.init()
            sound2.play(loops=-1)

        if (self.getActivatedZone() == "E2" and self.isS2touched == 1 and self.drop2 == 1):
            self.isS2touched = 0
            self.drop2 = 0
            self.CloseDoor("L2")
            print("L2 activated")
            time.sleep(0.1)
            self.CloseDoor("L2")
            self.OpenDoor("L2")

        if (self.getActivatedZone() == "E2"):
            self.CloseDoor("D4")

        if (self.getActivatedZone() == "F2"):
            self.CloseDoor("D3")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "H2"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

    def Free_RightLogic(self):
        if (self.getActivatedZone() == "S1"):
            self.isS1touched = 1
            self.CloseDoor("D5")
            print("Flag S1 set")

        if (self.getActivatedZone() == "S2"):
            self.CloseDoor("D4")
            self.isS2touched = 1
            print("Flag S2 set")

        if (self.getActivatedZone() == "A"):
            self.LightOn(1)
            self.LightOn(2)
            self.LightOff(3)
            self.LightOff(4)
            pygame.mixer.init()
            sound1.play(loops=-1)

        if (self.getActivatedZone() == "A"):
            self.flagTrial = 1
            self.drop1 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")

        if (self.getActivatedZone() == "B"):
            self.flagTrial = 1
            self.drop1 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")
            self.LightOn(1)
            self.LightOn(2)
            self.LightOff(3)
            self.LightOff(4)
            pygame.mixer.init()
            sound1.play(loops=-1)

        if (self.getActivatedZone() == "F1"):
            self.CloseDoor("D6")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "E1" and self.isS1touched == 1 and self.drop1 == 1):
            self.isS1touched = 0
            self.drop1 = 0
            self.CloseDoor("L1")
            print("L1 activated")
            time.sleep(0.1)
            self.CloseDoor("L1")
            self.OpenDoor("L1")

        if (self.getActivatedZone() == "F2"):
            self.CloseDoor("D3")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

        if (self.getActivatedZone() == "E1"):
            self.CloseDoor("D5")

        if (self.getActivatedZone() == "E2"):
            self.CloseDoor("D4")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

        if (self.getActivatedZone() == "H1"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

        if (self.getActivatedZone() == "H2"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")

    def Free_LeftLogic(self):
        if (self.getActivatedZone() == "S1"):
            self.isS1touched = 1
            self.CloseDoor("D5")
            print("Flag S1 set")

        if (self.getActivatedZone() == "S2"):
            self.isS2touched = 1
            print("Flag S2 set")
            self.CloseDoor("D4")

        if (self.getActivatedZone() == "A"):
            self.LightOff(1)
            self.LightOff(2)
            self.LightOn(3)
            self.LightOn(4)
            pygame.mixer.init
            sound2.play(loops=-1)

        if (self.getActivatedZone() == "A"):
            self.flagTrial = 1
            self.drop2 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")

        if (self.getActivatedZone() == "B"):
            self.flagTrial = 1
            self.drop2 = 1
            self.CloseDoor("D1")
            self.CloseDoor("D2")
            self.OpenDoor("D3")
            self.OpenDoor("D4")
            self.OpenDoor("D5")
            self.OpenDoor("D6")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOn(3)
            self.LightOn(4)
            pygame.mixer.init()
            sound2.play(loops=-1)

        if (self.getActivatedZone() == "E1"):
            self.CloseDoor("D5")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()

        if (self.getActivatedZone() == "E2"):
            self.CloseDoor("D4")

        if (self.getActivatedZone() == "E2" and self.isS2touched == 1 and self.drop2 == 1):
            self.isS2touched = 0
            self.drop2 = 0
            self.CloseDoor("L2")
            print("L2 activated")
            time.sleep(0.1)
            self.CloseDoor("L2")
            self.OpenDoor("L2")

        if (self.getActivatedZone() == "F1"):
            self.CloseDoor("D6")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "F2"):
            self.CloseDoor("D3")
            self.LightOff(1)
            self.LightOff(2)
            self.LightOff(3)
            self.LightOff(4)

        if (self.getActivatedZone() == "H1"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D1")

        if (self.getActivatedZone() == "H2"):
            if self.flagTrial == 1:
                print("Counter=", self.counter)
                self.counter += 1
            self.flagTrial = 0
            self.whichLogic = Settings.LogicList[self.counter]
            self.OpenDoor("D2")
            pygame.mixer.pause()
            pygame.mixer.quit()
            pygame.mixer.init()
