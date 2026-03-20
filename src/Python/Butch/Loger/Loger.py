from src.Python.Loger.Loger import LogerUni
import os

class Loger(LogerUni):
    PROGRAM_NAME = "Butche"
    Program_VERSION = "0.1.0.1"
    LogLocation = f"{os.path.expanduser('~')}\\Documents\\Butch\\log"
