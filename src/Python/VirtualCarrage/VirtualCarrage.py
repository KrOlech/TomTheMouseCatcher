import time

import serial

from src.Python.Settings import Settings
from src.Python.Loger.Loger import Loger


class VirtualCarrage(Loger):
    position: int = 100

    OneFullRotation_Steps:int = 200

    Gear_1_cog_count:int = 80
    Gear_2_cog_count:int = 10

    Gear_dif: float = Gear_1_cog_count / Gear_2_cog_count

    angleDelta: float=360/OneFullRotation_Steps

    belt_peach = 2 # mm

    Gear_1_length = belt_peach*Gear_1_cog_count
    Gear_2_length = belt_peach*Gear_2_cog_count

    oneSteplength = Gear_1_length/OneFullRotation_Steps

    timeGoingLeft = 0
    timeGoingRight = 0

    positionMM = 10

    safetyDistance = 20 #mm

    SPEED_STEPS: int = 500 # ps/s
    SPEED: int = SPEED_STEPS*oneSteplength  # m/s

    MAZE_LENGTH: float = 1.5  # mm
    MAZE_LENGTH_MM: float = 1.5*1000  # mm

    MAZE_LENGTH_PIZELS: int = 1920

    SPEED_PIXELS: int = int(MAZE_LENGTH_PIZELS * SPEED / MAZE_LENGTH_MM)


    def __init__(self):
        if Settings.arduinoLineCome:
            self.arduino = serial.Serial(port=Settings.arduinoLineCome, baudrate=Settings.baudrate, timeout=.1)

    last_status = None

    def advanceZoneCords(self,zoneCords):
        x0, y0, w, h = zoneCords

        self.advance(x0)

    def advance(self, x0):

        if self.position < x0 - self.SPEED // 5:
            # right
            if self.last_status != "right":
                self.last_status = "right"
                self.loger("moving virtual carriage to the right")
                if Settings.arduinoLineCome:
                    self.__arduinoLeft()
                self.timeGoingRight = time.time()

            else:
                timeDelta = time.time() - self.timeGoingRight
                self.timeGoingRight = time.time()
                stepsDone = self.SPEED_STEPS * timeDelta
                self.positionMM += self.oneSteplength*stepsDone
                if self.positionMM > self.MAZE_LENGTH_MM-self.safetyDistance:
                    self.loger("Stoping virtual carriage")
                    if Settings.arduinoLineCome:
                        self.__arduinoStop()


        elif self.position > x0 + self.SPEED // 5:
            # left
            if self.last_status != "Left":
                self.last_status = "Left"
                self.loger("moving virtual carriage to the Left")
                if Settings.arduinoLineCome:
                    self.__arduinoLeft()
                self.timeGoingLeft = time.time()
            else:
                timeDelta = time.time() - self.timeGoingLeft
                self.timeGoingLeft = time.time()
                stepsDone = self.SPEED_STEPS * timeDelta
                self.positionMM -= self.oneSteplength * stepsDone
                if self.positionMM < self.safetyDistance:
                    self.loger("Stoping virtual carriage")
                    if Settings.arduinoLineCome:
                        self.__arduinoStop()

        else:
            # stop
            if self.last_status != "stop":
                self.last_status = "stop"
                self.loger("Stoping virtual carriage")
                if Settings.arduinoLineCome:
                    self.__arduinoStop()

        self.position = int(self.positionMM*self.MAZE_LENGTH_PIZELS/self.MAZE_LENGTH_MM)

    def __arduinoStop(self):
        self.__arduinoComand("100","stop")
    def __arduinoRight(self):
        self.__arduinoComand("1","right")

    def __arduinoLeft(self):
        self.__arduinoComand("-1","left")

    def __arduinoComand(self, comand, comandName):
        self.loger(f"sending {comandName} commend to Arduino")
        self.arduino.write(bytes(comand, 'utf-8'))
        self.loger(f"Arduino ack: {self.arduino.readline()}")

