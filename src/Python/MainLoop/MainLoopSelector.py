from src.Python.Settings import Settings


# ============================================================
# CHECK WHICH SETTINGS FILE IS ACTUALLY USED
# ============================================================

print("============================================================")
print("MAIN LOOP SELECTOR")

try:
    print("Settings file:", Settings.__file__)
except AttributeError:
    print("Settings object:", Settings)


# ============================================================
# MainLoopMode MUST EXIST
# ============================================================

if not hasattr(Settings, "MainLoopMode"):
    raise RuntimeError(
        "Settings.MainLoopMode is NOT defined.\n"
        "Add for example:\n"
        'MainLoopMode = "HABITUATION1"\n'
        "to the Settings.py that is actually imported by the program."
    )


MODE = str(Settings.MainLoopMode).strip().upper()

print("MainLoopMode:", MODE)


# ============================================================
# SELECT MAIN LOOP
# ============================================================

if MODE == "NORMAL":

    print("Loading: MainLoop.py [NORMAL]")

    from src.Python.MainLoop.MainLoop import MainLoop


elif MODE == "HABITUATION1":

    print("Loading: MainLoop_Habituation1.py")

    from src.Python.MainLoop.MainLoop_Habituation1 import MainLoop


elif MODE == "HABITUATION2":

    print("Loading: MainLoop_Habituation2.py")

    from src.Python.MainLoop.MainLoop_Habituation2 import MainLoop


elif MODE == "HABITUATION_DD1":

    print("Loading: MainLoop_HabituationDD1.py")

    from src.Python.MainLoop.MainLoop_HabituationDD1 import MainLoop


elif MODE == "HABITUATION_DD2":

    print("Loading: MainLoop_HabituationDD2.py")

    from src.Python.MainLoop.MainLoop_HabituationDD2 import MainLoop


elif MODE == "ALTERNATION_DD1":

    print("Loading: MainLoop_AlternationDD1.py")

    from src.Python.MainLoop.MainLoop_AlternationDD1 import MainLoop


elif MODE == "ALTERNATION_DD2":

    print("Loading: MainLoop_AlternationDD2.py")

    from src.Python.MainLoop.MainLoop_AlternationDD2 import MainLoop


elif MODE == "EXTENDED_DD1":

    print("Loading: MainLoop_Extended_DD1.py")

    from src.Python.MainLoop.MainLoop_Extended_DD1 import MainLoop


elif MODE == "EXTENDED_DD2":

    print("Loading: MainLoop_Extended_DD2.py")

    from src.Python.MainLoop.MainLoop_Extended_DD2 import MainLoop


else:

    raise ValueError(
        f"Unknown MainLoopMode: {MODE!r}\n\n"
        "Allowed modes:\n"
        "NORMAL\n"
        "HABITUATION1\n"
        "HABITUATION2\n"
        "HABITUATION_DD1\n"
        "HABITUATION_DD2\n"
        "ALTERNATION_DD1\n"
        "ALTERNATION_DD2\n"
        "EXTENDED_DD1\n"
        "EXTENDED_DD2"
    )


print("MainLoop class:", MainLoop)
print("============================================================")