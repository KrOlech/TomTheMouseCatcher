#Instrukcja:

#1. Za każdym razem kiedy chcesz uruchomi skrypt wpisz w okno python rundoors.py
#2. Ja sprawdzam drzwi po kolei, więc między puszczaniem kolejnych zmieniam numer przy "line"
# w linicje 14 (1 - drzwi 2, 2 - drzwi 6, 4 - drzwi 5, 5 - drzwi 3, 6 - drzwi 4, 7 - drzwi 1)
#3. Po każdej zmianie numeru CTRL+S, włącz program i sprawdź czy reagują, to tyle :)


import nidaqmx
import time
from nidaqmx.constants import LineGrouping
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType 
from nidaqmx.constants import TerminalConfiguration as TerminalConfiguration
task=nidaqmx.Task()
task.do_channels.add_do_chan("Dev1/port0/line7")
task.start()
time.sleep(5)

STEPS_NR=1  
for i in range(STEPS_NR):
    task.write([bool(0)])
    time.sleep(2)
    task.write([bool(1)])
    time.sleep(2)
    task.write([bool(0)])
    time.sleep(2)
task.close()
