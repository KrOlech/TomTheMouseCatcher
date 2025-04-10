import nidaqmx
import time
from nidaqmx.constants import LineGrouping
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType
from nidaqmx.constants import TerminalConfiguration as TerminalConfiguration

task = nidaqmx.Task()
task.do_channels.add_do_chan("Dev1/port0/line3")
task.start()
time.sleep(1)

STEPS_NR = 1
for i in range(STEPS_NR):
    print("off")
    task.write([bool(1)])
    time.sleep(5)
    print("on")
    task.write([bool(0)])
    time.sleep(1)
    print("off")
    task.write([bool(1)])
    time.sleep(5)
task.close()
