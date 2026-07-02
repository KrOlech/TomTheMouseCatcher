import os
from inspect import stack
import sys
from datetime import datetime

from src.Python.Settings import Settings


class Loger:

    def logStart(self):
        self._logImportant(" Program Starting ", (41, 42))
        self._logImportant(" Program V1.1.2.4 ", (41, 42))
        self._logImportant(" Program Starting ", (41, 42), 'positions-')
        self.__log(" (Filtr X, Filtr Y) (Detected X, Detected Y)")
    def logEnd(self):
        self._logImportant(" Program Stoping ", (41, 42))

    def _logImportant(self, mesage, offset=(42, 42), sufix=''):
        self.loger("#" * 100,sufix=sufix)
        self.loger("#" * offset[0] + mesage + "#" * offset[1],sufix=sufix)
        self.loger("#" * 100,sufix=sufix)

    def loger(self, *message, sufix=''):
        self.__log(*message, state="log",sufix=sufix)

    def logError(self, *message):
        self.__log(*message, state="ERROR")
        msg = []
        for fun in stack():
            msg.append(fun.function)
        self.__log(msg, state="ERROR")

    def logWarning(self, *message):
        self.__log(*message, state="Warning")

    def abstractmetod(self, name=None):
        if name:
            self.__log(f"Abstract Methode {name}", state="Warning")
        else:
            self.__log("Abstract Methode", state="Warning")

    def __log(self, *message, state="log", sufix=''):
        info = f"[{datetime.now()}] - [{type(self).__name__}] - [{stack()[2].function}] [{state}] [{[mes for mes in message]}]"

        print(info)

        self.__saveToFile(info, sufix)

    @staticmethod
    def log(message, type, state="log"):
        info = f"[{datetime.now()}] - [{type}] - [{stack()[2].function}] [{state}] [{message}]"

        print(info)

        Loger.__saveToFile(info)

    @staticmethod
    def __saveToFile(info, suffix=""):
        with open(f"{Settings.logLocation}\\{suffix}{datetime.now().day}-{datetime.now().month}-{datetime.now().year}.log", "a") as file:
            file.write(info + "\n")

    @staticmethod
    def isDebuggerActive() -> bool:
        return hasattr(sys, 'gettrace') and sys.gettrace() is not None

    def logPositionData(self, calculated, detection):
        if detection:
            self.__saveToFile(f"[{datetime.now()}] {calculated} {detection}","positions-")
