import nidaqmx
import time
from nidaqmx.constants import LineGrouping
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType 
from nidaqmx.constants import TerminalConfiguration as TerminalConfiguration

task=nidaqmx.Task()
task.do_channels.add_do_chan("Dev1/port0/line0:7")

task.start()
time.sleep(2)
task.write([False, False, False, False, False, False, False, False])  # Set all channels to True
time.sleep(5)
task.close()
