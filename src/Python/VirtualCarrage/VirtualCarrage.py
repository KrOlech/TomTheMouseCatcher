import serial

from src.Python.Settings import Settings
from src.Python.Loger import Loger

class VirtualCarrage(Loger):
    ...

    position:int = 100

    SPEED:int = 100 #m/s

    MAZE_LENGTH:float = 1.5#m

    MAZE_LENGTH_PIZELS:int = 1920

    SPEED_PIXELS:float = MAZE_LENGTH_PIZELS * SPEED / MAZE_LENGTH#

    def __init__(self):
        if Settings.arduinoLineCome:
            self.arduino = serial.Serial(port=Settings.arduinoLineCome, baudrate=Settings.baudrate, timeout=.1)

    def advance(self, zoneCords):

        x0, y0, w, h = zoneCords

        if self.position < x0+w/2:
            #right
            self.position += self.SPEED
            self.log("moving virtual carriage to the right")
            if Settings.arduinoLineCome:
                self.log("saving commend to Arduino")
                self.arduino.write(bytes("1", 'utf-8'))
        elif  self.position > x0+w/2:
            #left
            self.position -= self.SPEED
            self.log("moving virtual carriage to the Left")
            if Settings.arduinoLineCome:
                self.log("saving commend to Arduino")
                self.arduino.write(bytes("-1", 'utf-8'))
        else:
            #stop
            self.log("Stoping virtual carriage")
            if Settings.arduinoLineCome:
                self.log("saving commend to Arduino")
                self.arduino.write(bytes("100", 'utf-8'))

        if  self.position > self.MAZE_LENGTH_PIZELS:
            self.position = self.MAZE_LENGTH_PIZELS
        if self.position < 0:
            self.position = 0

