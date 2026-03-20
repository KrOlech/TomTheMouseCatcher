from src.Python.Butch.Loger.Loger import Loger
from src.Python.Butch.Setup.Setup import Setup
from src.Python.Butch.maskOutMazeBorders.maskOutMazeBorders import MaskOutMazeBorders

class Butch(Loger):
    corners = {"00":(750,0), "01":(950,0), "02":(1100,0), "03":(1300,0), #Tylna sciana
               "10":(570,0), "11":(890,0), "12":(1150,0), "13":(1380,0), #gora sciany tyl
               "20":(0,190), "21":(700,220), "22":(1370,220), "23":(2020,240), #gora sciany przud
               "30":(550,390),"31":(930,220),"32":(1110,220), "33":(1550,460), #podloga tyl
               "40":(0,975), "41":(770,790), "42":(1300,800), "43":(2030,980), #podloga przud
               }
    def __init__(self):
        ...

    def run(self):

        self.locateAruco()

        self.maskOutMazeBorders()

        self.locateMaus()

    def locateAruco(self):
        ...

    def maskOutMazeBorders(self):
        self.borders =  MaskOutMazeBorders(self.corners).run()

    def locateMaus(self):
        ...

if __name__ == '__main__':
    Setup(Loger).setUp()
    b = Butch()
    b.run()