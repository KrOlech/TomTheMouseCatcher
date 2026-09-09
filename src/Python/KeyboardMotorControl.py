"""Manual stepper control on COM3.

Hold LEFT/RIGHT to move. Releasing the key sends STOP immediately.
Run this controller in a THREAD of the main Python process, not in a
multiprocessing child. This makes the Windows keyboard hook reliable.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import serial
from pynput import keyboard


class KeyboardMotorControl:
    COMMAND_LEFT = b"-1\n"
    COMMAND_RIGHT = b"1\n"
    COMMAND_STOP = b"100\n"
    COMMAND_HEARTBEAT = b"0\n"

    def __init__(
        self,
        finish_flag,
        port: str = "COM3",
        baudrate: int = 115200,
        heartbeat_interval: float = 0.20,
    ) -> None:
        self.finish_flag = finish_flag
        self.port = port
        self.baudrate = baudrate
        self.heartbeat_interval = heartbeat_interval

        self.left_pressed = False
        self.right_pressed = False
        self._last_motion_command: Optional[bytes] = None
        self._lock = threading.Lock()
        self._closed = False

        self.arduino = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0,
            write_timeout=0.05,
        )

        time.sleep(2.0)  # Arduino usually resets after opening COM.
        self.arduino.reset_input_buffer()
        self.arduino.reset_output_buffer()

        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

        print(f"[KeyboardMotorControl] Connected to {self.port} at {self.baudrate} baud.")
        print("[KeyboardMotorControl] Hold A = LEFT, D = RIGHT, release = STOP, SPACE = STOP.")

    def _write(self, command: bytes) -> None:
        if self._closed:
            return
        try:
            with self._lock:
                self.arduino.write(command)
        except (serial.SerialException, serial.SerialTimeoutException) as exc:
            print(f"[KeyboardMotorControl] Arduino communication error: {exc}")
            self.left_pressed = False
            self.right_pressed = False

    def _set_motion(self, command: bytes, force: bool = False) -> None:
        if not force and command == self._last_motion_command:
            return
        self._write(command)
        self._last_motion_command = command

    def _update_motor(self, force: bool = False) -> None:
        if self.left_pressed and not self.right_pressed:
            self._set_motion(self.COMMAND_LEFT, force)
        elif self.right_pressed and not self.left_pressed:
            self._set_motion(self.COMMAND_RIGHT, force)
        else:
            self._set_motion(self.COMMAND_STOP, force)

    def _on_press(self, key) -> None:

        # A = LEFT
        if hasattr(key, "char") and key.char in ("a", "A"):
            if self.left_pressed:
                return

            self.left_pressed = True
            print("[KeyboardMotorControl] LEFT (A) pressed")
            self._update_motor(force=True)

        # D = RIGHT
        elif hasattr(key, "char") and key.char in ("d", "D"):
            if self.right_pressed:
                return

            self.right_pressed = True
            print("[KeyboardMotorControl] RIGHT (D) pressed")
            self._update_motor(force=True)

        # SPACE = STOP
        elif key == keyboard.Key.space:
            self.left_pressed = False
            self.right_pressed = False
            print("[KeyboardMotorControl] SPACE -> STOP")
            self._set_motion(self.COMMAND_STOP, force=True)

    def _on_release(self, key) -> None:

        # A released
        if hasattr(key, "char") and key.char in ("a", "A"):
            self.left_pressed = False
            print("[KeyboardMotorControl] LEFT released")
            self._update_motor(force=True)

        # D released
        elif hasattr(key, "char") and key.char in ("d", "D"):
            self.right_pressed = False
            print("[KeyboardMotorControl] RIGHT released")
            self._update_motor(force=True)

    def _discard_arduino_messages(self) -> None:
        try:
            waiting = self.arduino.in_waiting
            if waiting:
                message = self.arduino.read(waiting).decode("utf-8", errors="replace").strip()
                if message:
                    print(f"[Arduino] {message}")
        except serial.SerialException:
            pass

    def run(self) -> None:
        self._set_motion(self.COMMAND_STOP, force=True)
        self.listener.start()
        print("[KeyboardMotorControl] Keyboard listener started.")

        try:
            next_heartbeat = time.monotonic()
            while not self.finish_flag.is_set():
                now = time.monotonic()
                if now >= next_heartbeat:
                    self._write(self.COMMAND_HEARTBEAT)
                    self._discard_arduino_messages()
                    next_heartbeat = now + self.heartbeat_interval
                time.sleep(0.01)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return

        try:
            if self.arduino.is_open:
                with self._lock:
                    self.arduino.write(self.COMMAND_STOP)
                time.sleep(0.05)
        except serial.SerialException:
            pass

        self._closed = True

        try:
            self.listener.stop()
        except Exception:
            pass

        try:
            if self.arduino.is_open:
                self.arduino.close()
        except serial.SerialException:
            pass

        print("[KeyboardMotorControl] Stopped; STOP sent.")


def run_keyboard_motor_control(finish_flag) -> None:
    controller: Optional[KeyboardMotorControl] = None
    try:
        controller = KeyboardMotorControl(finish_flag=finish_flag, port="COM3")
        controller.run()
    except Exception as exc:
        # A motor-control error must not stop camera/doors/reward logic.
        print(f"[KeyboardMotorControl] Could not start: {exc}")
    finally:
        if controller is not None:
            controller.close()