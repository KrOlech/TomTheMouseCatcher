"""Legacy carriage-position helper.

Automatic motor control has deliberately been removed. COM3 is now owned only
by KeyboardMotorControl.py, so this class must never open the serial port.
"""

from src.Python.Loger.Loger import Loger


class VirtualCarrage(Loger):
    position: int = 100
    positionMM: float = 10.0

    def __init__(self):
        self.last_status = "manual"

    def advance(self, x0, c0):
        """Update only the displayed carriage position; do not drive the motor."""
        del x0
        self.position = int(c0 / 0.5)

    def stop(self):
        """Kept for compatibility; motor STOP belongs to KeyboardMotorControl."""
        self.last_status = "manual"

    def left(self):
        raise RuntimeError(
            "Automatic motor control is disabled. Use KeyboardMotorControl."
        )

    def right(self):
        raise RuntimeError(
            "Automatic motor control is disabled. Use KeyboardMotorControl."
        )
