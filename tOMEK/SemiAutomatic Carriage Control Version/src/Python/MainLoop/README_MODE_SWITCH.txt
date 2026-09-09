FILES TO COPY INTO:
C:\Users\kradwanska\Desktop\emaze\eMaze FIBER\src\Python\MainLoop\

1. Keep your current MainLoop.py and MainLoopAbstract.py.
2. Copy all corrected MainLoop_* files and MainLoopSelector.py into the same MainLoop folder.

SETTINGS.PY
Inside class Settings add ONE line, for example:

    MainLoopMode = "HABITUATION_DD1"

Available values:
    "NORMAL"
    "HABITUATION1"
    "HABITUATION2"
    "HABITUATION_DD1"
    "HABITUATION_DD2"
    "ALTERNATION_DD1"
    "ALTERNATION_DD2"
    "EXTENDED_DD1"
    "EXTENDED_DD2"

ZONES.PY
Replace:
    from src.Python.MainLoop.MainLoop import MainLoop
with:
    from src.Python.MainLoop.MainLoopSelector import MainLoop

Do not change the existing class definition if it already inherits from MainLoop.
For example, keep:
    class Zones(MainLoop):
        ...

EMAZE.PY
No change is needed in the uploaded current emaze.py. It calls self.mainLoop(),
so the selected implementation arrives through inheritance from Zones/EMazeNoDoors.

IMPORTANT
MainLoop_Habituation2 contains legacy D7 behavior. The corrected version checks
whether D7 exists in self.door_names. If D7 is not configured, it logs a message
and skips that action instead of crashing.
