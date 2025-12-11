import sys
import linuxCNC_mock as linuxcnc
try:
    s = linuxcnc.stat() # create a connection to the status channel
    s.poll() # get current values
except linuxcnc.error as detail:
    print("error", detail)
    sys.exit(1)

for x in dir(s):
    if not x.startswith("_"):
        print(x, getattr(s,x))