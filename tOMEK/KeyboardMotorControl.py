"""Manual keyboard control for the stepper motor connected to Arduino.

Controls:
    Hold Left Arrow  -> move left
    Hold Right Arrow -> move right
    Release arrow    -> stop immediately
    Space            -> emergency stop

The class owns COM3. No other Python class/process may open COM3 at the same time.
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

    def __init__(
        self,
        finish_flag,
        port: str = "COM3",
        baudrate: int = 9600,
        heartbeat_interval: float = 0.10,
    ) -> None:
        self.finish_flag = finish_flag
        self.port = port
        self.baudrate = baudrate
        self.heartbeat_interval = heartbeat_interval

        self.left_pressed = False
        self.right_pressed = False
        self._last_command: Optional[bytes] = None
        self._lock = threading.Lock()
        self._closed = False

        self.arduino = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0.05,
            write_timeout=0.05,
        )

        # Most Arduino boards reset when the serial port is opened.
        time.sleep(2.0)
        self.arduino.reset_input_buffer()
        self.arduino.reset_output_buffer()

        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

        print(f"Keyboard motor control connected to {self.port}.")
        print("Hold LEFT/RIGHT arrow to move; release to stop; SPACE = emergency stop.")

    def _send(self, command: bytes, force: bool = False) -> None:
        """Send one command to Arduino.

        Movement commands are repeated by the heartbeat loop. The repetition is
        intentional: the Arduino sketch has a watchdog and stops the motor if
        communication disappears.
        """
        if self._closed:
            return

        if not force and command == self._last_command:
            return

        try:
            with self._lock:
                self.arduino.write(command)
                self.arduino.flush()
            self._last_command = command
        except (serial.SerialException, serial.SerialTimeoutException) as exc:
            print(f"Arduino communication error: {exc}")
            self.finish_flag.set()

    def _update_motor(self, force: bool = False) -> None:
        if self.left_pressed and not self.right_pressed:
            self._send(self.COMMAND_LEFT, force=force)
        elif self.right_pressed and not self.left_pressed:
            self._send(self.COMMAND_RIGHT, force=force)
        else:
            self._send(self.COMMAND_STOP, force=force)

    def _on_press(self, key) -> None:
        if key == keyboard.Key.left:
            if not self.left_pressed:
                self.left_pressed = True
                self._update_motor(force=True)

        elif key == keyboard.Key.right:
            if not self.right_pressed:
                self.right_pressed = True
                self._update_motor(force=True)

        elif key == keyboard.Key.space:
            self.left_pressed = False
            self.right_pressed = False
            self._send(self.COMMAND_STOP, force=True)

    def _on_release(self, key) -> None:
        if key == keyboard.Key.left:
            self.left_pressed = False
            self._update_motor(force=True)

        elif key == keyboard.Key.right:
            self.right_pressed = False
            self._update_motor(force=True)

    def run(self) -> None:
        """Run until the shared application finish flag is set."""
        self._send(self.COMMAND_STOP, force=True)
        self.listener.start()

        try:
            while not self.finish_flag.is_set():
                # Repeat a movement command as a safety heartbeat.
                if self.left_pressed or self.right_pressed:
                    self._update_motor(force=True)
                time.sleep(self.heartbeat_interval)
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        try:
            # Write directly because _send() is disabled once _closed is set.
            if self.arduino.is_open:
                with self._lock:
                    self.arduino.write(self.COMMAND_STOP)
                    self.arduino.flush()
                time.sleep(0.05)
        except serial.SerialException:
            pass

        try:
            self.listener.stop()
        except Exception:
            pass

        try:
            if self.arduino.is_open:
                self.arduino.close()
        except serial.SerialException:
            pass

        print("Keyboard motor control stopped; motor STOP command sent.")


def run_keyboard_motor_control(finish_flag) -> None:
    """Multiprocessing target used by emaze.py."""
    controller: Optional[KeyboardMotorControl] = None
    try:
        controller = KeyboardMotorControl(finish_flag=finish_flag, port="COM3")
        controller.run()
    except Exception as exc:
        print(f"Could not start keyboard motor control: {exc}")
        finish_flag.set()
    finally:
        if controller is not None:
            controller.close()
