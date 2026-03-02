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

    timeGoing_left = 0
    timeGoing_right = 0

    positionMM = 10

    safetyDistance = 20 #mm

    SPEED_STEPS: int = 500 # ps/s
    SPEED_STEPS_left: int = -500
    SPEED_STEPS_right: int = 500
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

    def __movementInDirection(self, direction):
        if self.last_status != direction:
            self.last_status = direction
            self.loger(f"moving virtual carriage to the {direction}")
            self.__getattribute__(direction)()
            self.__setattr__('timeGoing_'+direction, time.time())

        else:
            timeDelta = time.time() - self.__getattribute__('timeGoing_'+direction)
            self.__setattr__('timeGoing_'+direction, time.time())
            stepsDone = self.__getattribute__('SPEED_STEPS_'+direction) * timeDelta
            self.positionMM += self.oneSteplength * stepsDone
            if self.positionMM > self.MAZE_LENGTH_MM - self.safetyDistance or self.positionMM < self.safetyDistance:
                self.stop()

    def advance(self, x0):

        tolerance = self.SPEED // 5

        if self.position < x0 - tolerance:
            # right
            self.__movementInDirection("right")


        elif self.position > x0 + tolerance:
            # left
            self.__movementInDirection("left")

        else:
            # stop
            if self.last_status != "stop":
                self.stop()

        self.position = int(self.positionMM*self.MAZE_LENGTH_PIZELS/self.MAZE_LENGTH_MM)

    def stop(self):
        self.last_status = "stop"
        self.loger("Stoping virtual carriage")
        self.__arduinoStop()

    def __arduinoStop(self):
        self.__arduinoComand("100","stop")

    def right(self):
        self.__arduinoComand("1","right")

    def left(self):
        self.__arduinoComand("-1","left")

    def __arduinoComand(self, comand, comandName):
        if Settings.arduinoLineCome:
            self.loger(f"sending {comandName} commend to Arduino")
            self.arduino.write(bytes(comand, 'utf-8'))
            self.loger(f"Arduino ack: {self.arduino.readline()}")

