import nidaqmx
import time
from nidaqmx.constants import LineGrouping
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType
from nidaqmx.constants import TerminalConfiguration as TerminalConfiguration

task = nidaqmx.Task()
task.do_channels.add_do_chan("Dev1/port0/line0:7")

task.start()
time.sleep(2)
task.write([True, True, True, True, True, True, True, True])  # Set all channels to False (low)
time.sleep(5)
task.close()
