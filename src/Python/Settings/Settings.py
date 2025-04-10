import nidaqmx

FrameWidth = 1920
FrameHeigth = 1080

# if provided int number it will connect to usb camera
# if provided a path to recording it will use that recording instead
#CamNr = 0
CamNr = r"C:\Users\Zenbook\Downloads\m16.avi"

minDiffPix = 500  # minimal number of thresholded pixels to recognize the mouse
threshold = 40  # relative threshold used to segment the mouse
lightFlash = False  # decision whether light flashes or not
lightFlash_step = 0  # how fast light flashes (s)
lightFlashEXC = [1, 2, 3, 4]  # number of lights that should not be flashing

# Zone coordinates (DO NOT EDIT)

# Coordintaes nearest light;
zones = {}
zones["A"] = [105, 456, 207, 176]
zones["B"] = [343, 445, 592, 196]
zones["C"] = [954, 442, 544, 196]
zones["D"] = [1510, 456, 352, 168]
zones["E1"] = [1671, 663, 217, 72]
zones["E2"] = [1663, 345, 226, 72]
zones["F1"] = [1284, 660, 277, 176]
zones["F2"] = [1284, 238, 277, 176]
zones["G1"] = [586, 660, 664, 184]
zones["G2"] = [592, 236, 668, 182]
zones["H1"] = [120, 670, 431, 162]
zones["H2"] = [120, 240, 431, 162]
zones["S1"] = [1672, 740, 70, 89]
zones["S2"] = [1672, 247, 70, 89]
# zones["S1"]=[1672,779,39,46]
# zones["S2"]=[1666,233,39,46]


# Coordinares for lickometers middle:
# zones={}
# zones["A"]=[105,456,207,176]
# zones["B"]=[343,445,592,196]
# zones["C"]=[954,442,544,196]
# zones["D"]=[1510,456,352,168]
# zones["E1"]=[1673,663,214,164]
# zones["E2"]=[1673,252,214,165]
# zones["F1"]=[1427,663,144,173]
# zones["F2"]=[1425,240,154,172]
# zones["F1b"]=[1287,667,129,81]
# zones["F2b"]=[1284,340,133,73]
# zones["G1"]=[586,660,664,184]
# zones["G2"]=[592,236,668,182]
# zones["H1"]=[120,670,431,162]
# zones["H2"]=[120,240,431,162]
# zones["S1"]=[1307,755,72,89]
# zones["S2"]=[1348,237,72,89]

# Coordinates for lickometers at the back
# zones={}
# zones["A"]=[105,456,207,176]
# zones["B"]=[343,445,592,196]
# zones["C"]=[954,442,544,196]
# zones["D"]=[1510,456,352,168]
# zones["E1"]=[1642,684,222,148]
# zones["E2"]=[1652,248,208,142]
# zones["F1"]=[1314,660,218,176]
# zones["F2"]=[1316,238,218,176]
# zones["G1"]=[586,660,664,184]
# zones["G2"]=[592,236,668,182]
# zones["H1"]=[166,670,324,162]
# zones["H2"]=[166,240,324,162]
# zones["S1"]=[84,700,70,89]
# zones["S2"]=[84,292,70,89]

# Connections (do not edit)
# Version for 7 doors
# doors = {
# "D7": {"channel": "line0", "type": "DO"},
# "D1": {"channel": "line7", "type": "DO"},
# "D2": {"channel": "line1", "type": "DO"},
# "D3": {"channel": "line5", "type": "DO"},
# "D4": {"channel": "line6", "type": "DO"},
# "D5": {"channel": "line4", "type": "DO"},
# "D6": {"channel": "line2", "type": "DO"},
# "L1": {"channel": "line3", "type": "DO"},
# "L2": {"channel": "line0", "type": "DO"},


# Lines on NiDAQmx for all the doors on channel 0:
doors = {}
doors["L1"] = "line0"
doors["L2"] = "line3"
doors["D1"] = "line6"
doors["D2"] = "line7"
doors["D3"] = "line2"
doors["D4"] = "line1"
doors["D5"] = "line4"
doors["D6"] = "line5"

# Initial door position: 0 are up, 1 is down, in forced choice all should be up at the start and activation of A shall open desired side

initDoorsPos = {}
initDoorsPos["D1"] = 0
initDoorsPos["D2"] = 0
initDoorsPos["D3"] = 0
initDoorsPos["D4"] = 0
initDoorsPos["D5"] = 0
initDoorsPos["D6"] = 0
initDoorsPos["D7"] = 0
initDoorsPos["L1"] = 0
initDoorsPos["L2"] = 0

# Flag for showing zone frames and active/inactive state on videos
showZones = False

# Check for value = 0.01 first if the drop forms and stays on the needle (other times to try for water: 0.1, 5% sach: 0.05 and milk: 0.01); 0.003 s yields 10 uL of milk
LTime1 = 0.25
LTime2 = 0.25
# 0.0001

# Time flags (do not edit)
LoopTime = 0.075
DCntrlTime = 0.1

# Sound file for cue:
soundFile = "C:\\Users\\kradwanska\\Desktop\\7k_hz.wav"
soundFile2 = "C:\\Users\\kradwanska\\Desktop\\14k_hz.wav"
volume1 = 0.28183829312644537
volume2 = 0.12589254117941673

# Trial numbers flag
MaxTrials = 30

# Trial sequence flag
# To randomize the list enter Spyder4 interface and copy the last line of result of code provided below:
# Paste and unhash in Spyder4 line 132 - 135:
# import random
# LogicList = [0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]
# random.shuffle(LogicList)
# print (LogicList)


# Forced Choices - 30 trials:

LogicList = [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1,
             0]  # - Randomized 1
# LogicList = [0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1] #- Randomized 2
# LogicList = [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0] #- Randomized 3
# LogicList = [1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1] #- Randomized 4
# LogicList = [1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0,] #- Randomized 5

# Forced Choices - 50 trials:
# LogicList = [0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1] # - 50 trial version randomised 1
# LogicList = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1] # - 50 tiral version randomised 2
# LogicList = [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1] # - 50 tiral version randomised 3
# LogicList = [0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1] # - 50 trial version randomised 4
# LogicList = [0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0] # - 50 trial version randomised 5

# Free Choices - 50 trials:

# LogicList = [1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1] # - 50 trial version randomised 1
# LogicList = [1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1] # - 50 trial version randomised 2
# LogicList = [1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0] # - 50 trial version randomised 3
# LogicList = [0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1] # - 50 trial version randomised 4
# LogicList = [0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0] # - 50 trial version randomised 5
