import time

import serial

from src.Python.Settings import Settings
from src.Python.Loger.Loger import Loger


class VirtualCarrage(Loger):
    position: int = 100

    SPEED: int = 50  # m/s
    SPEED_STEPS: int = 500 # ps/s

    MAZE_LENGTH: float = 1.5  # mm
    MAZE_LENGTH_MM: float = 1.5*1000  # mm

    MAZE_LENGTH_PIZELS: int = 1920

    SPEED_PIXELS: int = int(MAZE_LENGTH_PIZELS * SPEED / MAZE_LENGTH)

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


    def __init__(self):
        if Settings.arduinoLineCome:
            self.arduino = serial.Serial(port=Settings.arduinoLineCome, baudrate=Settings.baudrate, timeout=.1)

    last_status = None

    def advance(self, zoneCords):

        x0, y0, w, h = zoneCords

        if self.position < x0 + w / 2 - self.SPEED // 2:
            # right
            self.position += self.SPEED
            if self.last_status != "right":
                self.last_status = "right"
                self.loger("moving virtual carriage to the right")
                if Settings.arduinoLineCome:
                    self.loger("sending right commend to Arduino")
                    self.arduino.write(bytes("1", 'utf-8'))
                    self.loger(f"Arduino ack: {self.arduino.readline()}")
                    self.timeGoingRight = time.time()

            else:
                timeDelta = time.time() - self.timeGoingRight
                self.timeGoingRight = time.time()
                stepsDone = self.SPEED_STEPS * timeDelta
                self.positionMM+= self.oneSteplength*stepsDone
                if self.positionMM > self.MAZE_LENGTH_MM-self.safetyDistance:
                    self.loger("Stoping virtual carriage")
                    if Settings.arduinoLineCome:
                        self.loger("sending stop commend to Arduino")
                        self.arduino.write(bytes("100", 'utf-8'))
                        self.loger(f"Arduino ack: {self.arduino.readline()}")




        elif self.position > x0 + w / 2 + self.SPEED // 2:
            # left
            self.position -= self.SPEED
            if self.last_status != "Left":
                self.last_status = "Left"
                self.loger("moving virtual carriage to the Left")
                if Settings.arduinoLineCome:
                    self.loger("sending left commend to Arduino")
                    self.arduino.write(bytes("-1", 'utf-8'))
                    self.loger(f"Arduino ack: {self.arduino.readline()}")
                    self.timeGoingLeft = time.time()
            else:
                timeDelta = time.time() - self.timeGoingLeft
                self.timeGoingLeft = time.time()
                stepsDone = self.SPEED_STEPS * timeDelta
                self.positionMM -= self.oneSteplength * stepsDone
                if self.positionMM < self.safetyDistance:
                    self.loger("Stoping virtual carriage")
                    if Settings.arduinoLineCome:
                        self.loger("sending stop commend to Arduino")
                        self.arduino.write(bytes("100", 'utf-8'))
                        self.loger(f"Arduino ack: {self.arduino.readline()}")

        else:
            # stop
            if self.last_status != "stop":
                self.last_status = "stop"
                self.loger("Stoping virtual carriage")
                if Settings.arduinoLineCome:
                    self.loger("sending stop commend to Arduino")
                    self.arduino.write(bytes("100", 'utf-8'))
                    self.loger(f"Arduino ack: {self.arduino.readline()}")

        if self.position > self.MAZE_LENGTH_PIZELS:
            if Settings.arduinoLineCome:
                self.loger("sending stop commend to Arduino")
                self.arduino.write(bytes("100", 'utf-8'))
                self.loger(f"Arduino ack: {self.arduino.readline()}")
            self.position = self.MAZE_LENGTH_PIZELS
        if self.position < 0:
            if Settings.arduinoLineCome:
                self.loger("sending stop commend to Arduino")
                self.arduino.write(bytes("100", 'utf-8'))
                self.loger(f"Arduino ack: {self.arduino.readline()}")
            self.position = 0
