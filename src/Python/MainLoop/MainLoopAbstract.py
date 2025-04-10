import time
from abc import abstractmethod, ABC
import pygame
import csv

from src.Python.Settings import Settings

try:
    pygame.mixer.init()
    sound2 = pygame.mixer.Sound('C:\\Users\\kradwanska\\Desktop\\7k_hz.wav')
    sound1 = pygame.mixer.Sound('C:\\Users\\kradwanska\\Desktop\\14k_hz.wav')
    sound1.set_volume(Settings.volume2)
    sound2.set_volume(Settings.volume1)
except FileNotFoundError as e:
    print(e)


class MainLoopAbstract(ABC):

    def __init__(self):
        ...
        # todo add proper PyGame init

    @abstractmethod
    def checkActivation(self):
        ...

    @abstractmethod
    def getActivatedZone(self):
        ...

    @abstractmethod
    def CloseDoor(self, name):
        ...

    @abstractmethod
    def OpenDoor(self, name):
        ...

    @abstractmethod
    def LightOn(self, ln):
        ...

    @abstractmethod
    def LightOff(self, ln):
        ...

    @staticmethod
    def finPygem():
        pygame.mixer.pause()
        pygame.mixer.quit()
        pygame.mixer.init()

    @staticmethod
    def log_data_csv(zone_name, duration):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")  # Get actual time
        log_entry = [timestamp, zone_name, round(duration, 2)]
        with open(".\\data\\zone_activity_log.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(log_entry)

    @staticmethod
    def _playSound1():
        try:
            pygame.mixer.init()
            sound1.play(loops=-1)
        except pygame.error as e:
            print(e)

    @staticmethod
    def _playSound2():
        try:
            pygame.mixer.init()
            sound2.play(loops=-1)
        except pygame.error as e:
            print(e)

    def _closeDoors(self, names: list[str]):
        for name in names:
            self.CloseDoor(name)

    def _openDoors(self, names: list[str]):
        for name in names:
            self.OpenDoor(name)

    def _turnLightsOn(self, ln: list[int]):
        for l in ln:
            self.LightOn(l)

    def _turnLightsOff(self, ln: list[int]):
        for l in ln:
            self.LightOff(l)

    def _setS1Flag(self):
        self.isS1touched = True
        print("Flag S1 set")

    def _setS2Flag(self):
        self.isS2touched = True
        print("Flag S2 set")
