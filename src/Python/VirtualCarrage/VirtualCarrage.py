
class VirtualCarrage:
    ...

    position:int = 100

    SPEED:int = 100 #m/s

    MAZE_LENGTH:float = 1.5#m

    MAZE_LENGTH_PIZELS:int = 1920

    SPEED_PIXELS:float = MAZE_LENGTH_PIZELS * SPEED / MAZE_LENGTH#

    def __init__(self):
        ...


    def advance(self, sine, zoneCords):

        x0, y0, w, h = zoneCords

        if self.position < x0+w/2:
            self.position += self.SPEED
        if  self.position > x0+w/2:
            self.position -= self.SPEED


        if  self.position > self.MAZE_LENGTH_PIZELS:
            self.position = self.MAZE_LENGTH_PIZELS
        if self.position < 0:
            self.position = 0

