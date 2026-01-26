import serial

from src.Python.Settings import Settings
from src.Python.Loger.Loger import Loger


class VirtualCarrage(Loger):
    position: int = 100

    SPEED: int = 50  # m/s

    MAZE_LENGTH: float = 1.5  # m

    MAZE_LENGTH_PIZELS: int = 1920

    SPEED_PIXELS: int = int(MAZE_LENGTH_PIZELS * SPEED / MAZE_LENGTH)

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
            self.position = self.MAZE_LENGTH_PIZELS
        if self.position < 0:
            self.position = 0
