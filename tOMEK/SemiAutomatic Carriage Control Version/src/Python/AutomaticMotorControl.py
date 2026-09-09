"""Mouse-following controller matched to TMC_FAILSAFE_V10.

Camera-image orientation in this installation is mirrored relative to the
physical/Arduino LEFT-RIGHT convention. Therefore Arduino +1/+3 moves left
on the image, while -1/-3 moves right on the image. This controller maps
image directions to those commands without changing mouse detection.

Matched firmware:
    LineCatcher_FAILSAFE_V10_DIRECTION_FIXED.ino

Normal control:
- use current mouse X;
- apply linear perspective correction, maximum 180 mm at each end;
- compare current corrected target with current carriage X;
- FAST everywhere inside the central maze;
- CREEP only while approaching either red line;
- STOP and direction-latch at either red line;
- STOP when aligned;
- no SETTLING;
- no target filter;
- no near-target CREEP;
- no motion watchdog.

Small deadband hysteresis prevents repeated back-and-forth movement around a
stationary mouse without changing normal full-speed travel.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import serial


class AutomaticMotorControl:
    # IMAGE-direction commands. The camera image is mirrored relative to
    # the physical Arduino convention in this installation:
    #   Arduino +1/+3  -> left on camera image
    #   Arduino -1/-3  -> right on camera image
    COMMAND_LEFT_FAST = 3
    COMMAND_LEFT_CREEP = 1
    COMMAND_STOP = 100
    COMMAND_RIGHT_CREEP = -1
    COMMAND_RIGHT_FAST = -3

    COMMAND_EMERGENCY_STOP = 101
    COMMAND_CLEAR_FAULT = 200
    COMMAND_IDENTIFY = 201

    REQUIRED_FIRMWARE_ID = "TMC_FAILSAFE_V10"

    def __init__(
        self,
        finish_flag,
        port: str = "COM3",
        baudrate: int = 115200,
        processing_to_full_scale: float = 2.0,

        # Visible red lines in full-resolution camera pixels.
        fixed_left_stop_full_px: float = 20.0,
        fixed_right_stop_full_px: float = 1900.0,

        # CREEP begins this far BEFORE each red line.
        red_line_creep_margin_full_px: float = 100.0,

        # Alignment thresholds in half-resolution processing pixels.
        stop_deadband_px: float = 18.0,
        start_deadband_px: float = 26.0,
        reverse_deadband_px: float = 45.0,

        maze_length_mm: float = 1500.0,
        maximum_perspective_offset_mm: float = 180.0,

        # Absolute live cable-safety envelope in FULL-resolution pixels.
        # The carriage may never continue outward beyond this distance
        # from the currently detected mouse position.
        maximum_mouse_separation_full_px: float = 150.0,
        mouse_separation_brake_margin_full_px: float = 30.0,

        heartbeat_interval_s: float = 0.05,
        tracking_loss_frames_to_latch: int = 5,

        # Compatibility with existing VideoCapture.py arguments.
        deadband: Optional[float] = None,
        deadband_px: Optional[float] = None,
        movement_start_deadband_px: Optional[float] = None,
        movement_stop_deadband_px: Optional[float] = None,
        settle_time_s: Optional[float] = None,
        target_filter_alpha: Optional[float] = None,
        target_filter_snap_px: Optional[float] = None,
        slow_left_full_px: Optional[float] = None,
        slow_right_full_px: Optional[float] = None,
        stop_trigger_margin_full_px: Optional[float] = None,
        fixed_release_margin_full_px: Optional[float] = None,
        target_margin_full_px: Optional[float] = None,
        mouse_hold_s: Optional[float] = None,
        heartbeat_interval: Optional[float] = None,
        **_unused,
    ) -> None:
        del (
            settle_time_s,
            target_filter_alpha,
            target_filter_snap_px,
            slow_left_full_px,
            slow_right_full_px,
            fixed_release_margin_full_px,
            target_margin_full_px,
            mouse_hold_s,
        )

        if deadband is not None:
            stop_deadband_px = float(deadband)

        if deadband_px is not None:
            stop_deadband_px = float(deadband_px)

        if movement_stop_deadband_px is not None:
            stop_deadband_px = float(
                movement_stop_deadband_px
            )

        if movement_start_deadband_px is not None:
            start_deadband_px = float(
                movement_start_deadband_px
            )

        if heartbeat_interval is not None:
            heartbeat_interval_s = float(
                heartbeat_interval
            )

        self.finish_flag = finish_flag
        self.port = str(port)
        self.baudrate = int(baudrate)

        self.processing_to_full_scale = max(
            0.001,
            float(processing_to_full_scale),
        )

        self.fixed_left_stop_full_px = float(
            fixed_left_stop_full_px
        )
        self.fixed_right_stop_full_px = float(
            fixed_right_stop_full_px
        )

        if (
            self.fixed_right_stop_full_px
            <= self.fixed_left_stop_full_px
        ):
            raise ValueError(
                "Right red line must be greater than left red line."
            )

        self.red_line_creep_margin_full_px = max(
            0.0,
            float(red_line_creep_margin_full_px),
        )

        # Trigger the latched emergency stop before the visible red line.
        # This compensates for frame, serial and motor stopping latency.
        self.stop_trigger_margin_full_px = max(
            0.0,
            float(
                25.0
                if stop_trigger_margin_full_px is None
                else stop_trigger_margin_full_px
            ),
        )

        self.stop_deadband_px = max(
            2.0,
            float(stop_deadband_px),
        )
        self.start_deadband_px = max(
            self.stop_deadband_px,
            float(start_deadband_px),
        )
        self.reverse_deadband_px = max(
            self.start_deadband_px,
            float(reverse_deadband_px),
        )
        self.near_target_creep_px = 90.0

        self.maze_length_mm = max(
            1.0,
            float(maze_length_mm),
        )
        self.maximum_perspective_offset_mm = max(
            0.0,
            float(maximum_perspective_offset_mm),
        )

        self.maximum_mouse_separation_full_px = max(
            50.0,
            float(maximum_mouse_separation_full_px),
        )
        self.mouse_separation_brake_margin_full_px = min(
            self.maximum_mouse_separation_full_px - 10.0,
            max(
                10.0,
                float(mouse_separation_brake_margin_full_px),
            ),
        )
        self.mouse_separation_soft_limit_full_px = (
            self.maximum_mouse_separation_full_px
            - self.mouse_separation_brake_margin_full_px
        )

        self.heartbeat_interval_s = max(
            0.02,
            float(heartbeat_interval_s),
        )
        self.tracking_loss_frames_to_latch = max(
            2,
            int(tracking_loss_frames_to_latch),
        )

        self.enabled = False
        self.requires_carriage_click = True
        self._closed = False

        self._desired_command = self.COMMAND_STOP
        self._status = "WAITING FOR CARRIAGE CLICK"
        self._last_motion_direction = 0
        self._tracking_lost_frames = 0

        self._backoff_active = False
        self._end_lock_side = ""

        # Software red-line latch:
        # LEFT blocks further left movement until the target moves right.
        # RIGHT blocks further right movement until the target moves left.
        self._red_stop_side = ""

        self._serial_lock = threading.Lock()
        self._clear_ok_event = threading.Event()
        self._clear_failed_event = threading.Event()

        # Attributes used by existing VideoCapture overlays.
        self.raw_mouse_x = 0.0
        self.corrected_target_x = 0.0
        self.perspective_offset_px = 0.0
        self.raw_carriage_x = 0.0
        self.fixed_carriage_full_x = 0.0
        self.predicted_carriage_x = 0.0
        self.control_error_px = 0.0
        self.control_target_source = "LIVE"
        self.control_mouse_detected = True
        self.control_mouse_lost_frames = 0
        self.pixel_limit_status = "READY"
        self.pixel_stop_latch_side = ""

        # Live mouse-to-carriage cable-safety diagnostics.
        self.mouse_carriage_separation_full_px = 0.0
        self.mouse_leash_left_full_px = 0.0
        self.mouse_leash_right_full_px = 0.0

        self.arduino = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0.05,
            write_timeout=0.20,
        )

        # CP210x/Arduino startup may take longer when launched inside the
        # multiprocessing camera process. Preserve the firmware startup text
        # and allow the board three seconds before identification.
        time.sleep(3.0)
        self._startup_handshake()

        self._worker = threading.Thread(
            target=self._serial_worker,
            name="AutomaticMotorSerialWorker",
            daemon=True,
        )
        self._worker.start()

        print(
            f"Automatic motor connected: {self.port} "
            f"at {self.baudrate} baud."
        )
        print(
            "Normal movement: FAST inside maze; CREEP only near red lines."
        )
        print(
            "End hit: firmware forces bounded reverse backoff and locks."
        )
        print(
            "Live mouse leash: carriage limited to +/-"
            f"{self.maximum_mouse_separation_full_px:.0f} "
            "full-frame pixels from mouse."
        )

    # --------------------------------------------------------------
    # Serial
    # --------------------------------------------------------------

    def _discard_serial_input(self) -> None:
        try:
            self.arduino.reset_input_buffer()
        except (serial.SerialException, OSError):
            pass

    def _write_command(self, command: int) -> None:
        if self._closed:
            return

        try:
            payload = f"{int(command)}\n".encode("ascii")

            with self._serial_lock:
                self.arduino.write(payload)
                self.arduino.flush()

        except (serial.SerialException, OSError) as error:
            self.enabled = False
            self.requires_carriage_click = True
            self._desired_command = self.COMMAND_STOP
            self._status = f"SERIAL ERROR: {error}"

    def _set_command(
        self,
        command: int,
        status: str,
        force: bool = False,
    ) -> str:
        command = int(command)
        changed = command != self._desired_command

        self._desired_command = command
        self._status = str(status)

        if changed or force:
            self._write_command(command)

        return self._status

    def _read_messages(self) -> None:
        try:
            while self.arduino.in_waiting > 0:
                raw = self.arduino.readline()

                if not raw:
                    break

                message = raw.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                if not message:
                    continue

                print(f"Arduino: {message}")
                self._handle_message(message)

        except (serial.SerialException, OSError) as error:
            self.enabled = False
            self.requires_carriage_click = True
            self._desired_command = self.COMMAND_STOP
            self._status = f"SERIAL ERROR: {error}"

    def _handle_message(self, message: str) -> None:
        lower = message.lower()

        if "fault cleared: ready" in lower:
            self._clear_failed_event.clear()
            self._clear_ok_event.set()
            self._backoff_active = False
            self._end_lock_side = ""
            return

        if "fault not cleared:" in lower:
            self._clear_ok_event.clear()
            self._clear_failed_event.set()
            return

        if "forced right backoff" in lower:
            # Physical LEFT end equals IMAGE RIGHT in the mirrored view.
            self._backoff_active = True
            self._end_lock_side = "RIGHT"
            self.pixel_stop_latch_side = "RIGHT"
            self._desired_command = self.COMMAND_STOP
            self._status = "IMAGE RIGHT END: BACKING OFF LEFT"
            return

        if "forced left backoff" in lower:
            # Physical RIGHT end equals IMAGE LEFT in the mirrored view.
            self._backoff_active = True
            self._end_lock_side = "LEFT"
            self.pixel_stop_latch_side = "LEFT"
            self._desired_command = self.COMMAND_STOP
            self._status = "IMAGE LEFT END: BACKING OFF RIGHT"
            return

        if "left backoff complete:" in lower:
            # Physical LEFT end equals IMAGE RIGHT.
            self._backoff_active = False
            self._end_lock_side = "RIGHT"
            self.pixel_stop_latch_side = "RIGHT"
            self.enabled = False
            self.requires_carriage_click = True
            self._desired_command = self.COMMAND_STOP
            self._status = (
                "IMAGE RIGHT BACKOFF COMPLETE - CLICK TO REARM"
            )
            return

        if "right backoff complete:" in lower:
            # Physical RIGHT end equals IMAGE LEFT.
            self._backoff_active = False
            self._end_lock_side = "LEFT"
            self.pixel_stop_latch_side = "LEFT"
            self.enabled = False
            self.requires_carriage_click = True
            self._desired_command = self.COMMAND_STOP
            self._status = (
                "IMAGE LEFT BACKOFF COMPLETE - CLICK TO REARM"
            )
            return

        if "left command blocked" in lower:
            # Physical LEFT command is movement toward IMAGE RIGHT.
            self._end_lock_side = "RIGHT"
            self._status = "IMAGE RIGHT END LOCKED - MOVE MOUSE LEFT"
            return

        if "right command blocked" in lower:
            # Physical RIGHT command is movement toward IMAGE LEFT.
            self._end_lock_side = "LEFT"
            self._status = "IMAGE LEFT END LOCKED - MOVE MOUSE RIGHT"
            return

        if "end lock cleared" in lower:
            self._end_lock_side = ""
            self.pixel_stop_latch_side = ""
            return

        if message.startswith("FAULT:"):
            self.enabled = False
            self.requires_carriage_click = True
            self._desired_command = self.COMMAND_STOP
            self._status = (
                f"{message} - MOVE/CORRECT CARRIAGE AND CLICK"
            )

    def _startup_handshake(self) -> None:
        """Confirm V10 firmware without losing its startup message.

        The previous version cleared the input buffer after two seconds.
        On this CP210x installation that could discard the firmware banner
        before the camera subprocess began polling it.

        This version:
        - preserves and reads startup messages;
        - accepts the startup V10 banner immediately;
        - otherwise sends command 201 repeatedly;
        - uses blocking readline calls with a serial timeout;
        - waits longer before declaring failure.
        """
        received: list[str] = []

        def read_available_for(duration_s: float) -> bool:
            deadline = time.monotonic() + float(duration_s)

            while time.monotonic() < deadline:
                try:
                    raw = self.arduino.readline()
                except (serial.SerialException, OSError) as error:
                    raise RuntimeError(
                        f"Arduino serial read failed: {error}"
                    ) from error

                if raw:
                    message = raw.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()

                    if message:
                        received.append(message)
                        print(f"Arduino: {message}")

                        if self.REQUIRED_FIRMWARE_ID in message:
                            return True
                else:
                    time.sleep(0.01)

            return any(
                self.REQUIRED_FIRMWARE_ID in item
                for item in received
            )

        # First inspect the preserved firmware startup banner.
        if read_available_for(1.0):
            self._write_command(self.COMMAND_CLEAR_FAULT)
            return

        # Then explicitly request identification several times.
        for attempt in range(1, 6):
            self._write_command(self.COMMAND_IDENTIFY)

            if read_available_for(1.25):
                self._write_command(self.COMMAND_CLEAR_FAULT)
                return

            print(
                f"Arduino handshake attempt {attempt}/5 "
                "did not complete; retrying."
            )

        raise RuntimeError(
            "Arduino handshake failed. Required firmware: "
            f"{self.REQUIRED_FIRMWARE_ID}. Received: "
            f"{' | '.join(received) or 'no response'}. "
            "Direct COM3 test should return TMC_FAILSAFE_V10."
        )

    def _serial_worker(self) -> None:
        next_send = time.monotonic()

        while not self._closed:
            if self.finish_flag.is_set():
                break

            self._read_messages()
            now = time.monotonic()

            if now >= next_send:
                if not self._backoff_active:
                    command = (
                        self._desired_command
                        if self.enabled
                        and not self.requires_carriage_click
                        else self.COMMAND_STOP
                    )
                    self._write_command(command)

                next_send = now + self.heartbeat_interval_s

            time.sleep(0.005)

        self._write_command(self.COMMAND_STOP)

    # --------------------------------------------------------------
    # Geometry
    # --------------------------------------------------------------

    def _corrected_target(
        self,
        mouse_x: float,
    ) -> tuple[float, float]:
        left = (
            self.fixed_left_stop_full_px
            / self.processing_to_full_scale
        )
        right = (
            self.fixed_right_stop_full_px
            / self.processing_to_full_scale
        )

        centre = (left + right) / 2.0
        half_width = max(
            1.0,
            (right - left) / 2.0,
        )

        normalized = (
            float(mouse_x) - centre
        ) / half_width
        normalized = max(
            -1.0,
            min(1.0, normalized),
        )

        pixels_per_mm = (
            (right - left)
            / self.maze_length_mm
        )

        maximum_offset_px = (
            self.maximum_perspective_offset_mm
            * pixels_per_mm
        )

        correction_px = normalized * maximum_offset_px
        target_x = float(mouse_x) + correction_px

        # The perspective lead is never allowed to place the requested
        # target outside the inner cable-safety envelope. The hard outer
        # envelope is checked separately in update().
        soft_limit_processing_px = (
            self.mouse_separation_soft_limit_full_px
            / self.processing_to_full_scale
        )
        minimum_target = (
            float(mouse_x) - soft_limit_processing_px
        )
        maximum_target = (
            float(mouse_x) + soft_limit_processing_px
        )
        target_x = max(
            minimum_target,
            min(maximum_target, target_x),
        )
        correction_px = target_x - float(mouse_x)

        return target_x, correction_px

    # --------------------------------------------------------------
    # Normal movement
    # --------------------------------------------------------------

    def _command_to_image_direction(self, command: int) -> int:
        """Return -1 for image-left, +1 for image-right, 0 for STOP."""
        command = int(command)

        if command in (
            self.COMMAND_LEFT_CREEP,
            self.COMMAND_LEFT_FAST,
        ):
            return -1

        if command in (
            self.COMMAND_RIGHT_CREEP,
            self.COMMAND_RIGHT_FAST,
        ):
            return 1

        return 0

    def update(
        self,
        mouse_x: float,
        carriage_x: float,
        mouse_detected: bool,
        carriage_detected: bool,
        carriage_initialized: bool,
        carriage_safety_x: Optional[float] = None,
        carriage_match_score: Optional[float] = None,
    ) -> str:
        del carriage_match_score

        if (
            self.requires_carriage_click
            or not self.enabled
            or not carriage_initialized
        ):
            return self._set_command(
                self.COMMAND_STOP,
                self._status,
            )

        if self._backoff_active:
            return self._status

        if not mouse_detected:
            self.control_mouse_detected = False

            return self._set_command(
                self.COMMAND_STOP,
                "MOUSE LOST",
            )

        self.control_mouse_detected = True

        if not carriage_detected:
            self._tracking_lost_frames += 1

            self._set_command(
                self.COMMAND_STOP,
                (
                    f"CARRIAGE LOST "
                    f"{self._tracking_lost_frames}/"
                    f"{self.tracking_loss_frames_to_latch}"
                ),
            )

            if (
                self._tracking_lost_frames
                >= self.tracking_loss_frames_to_latch
            ):
                self.enabled = False
                self.requires_carriage_click = True
                self._status = (
                    "CARRIAGE LOST - CORRECT IT AND CLICK"
                )

            return self._status

        self._tracking_lost_frames = 0

        control_x = float(carriage_x)
        safety_x = float(
            carriage_safety_x
            if carriage_safety_x is not None
            else carriage_x
        )
        full_x = (
            safety_x * self.processing_to_full_scale
        )

        # ----------------------------------------------------------
        # ABSOLUTE RED-LINE SAFETY — HIGHEST PRIORITY
        # ----------------------------------------------------------
        # This check is deliberately before target calculation, alignment,
        # direction selection and all normal movement logic.
        #
        # It is unconditional: once the raw tracked carriage reaches either
        # inner guard, Arduino receives the latched EMERGENCY STOP command
        # regardless of where the mouse is or which direction was requested.
        left_red_guard = (
            self.fixed_left_stop_full_px
            + self.stop_trigger_margin_full_px
        )
        right_red_guard = (
            self.fixed_right_stop_full_px
            - self.stop_trigger_margin_full_px
        )

        if full_x <= left_red_guard:
            self._red_stop_side = "LEFT"
            self.pixel_stop_latch_side = "LEFT"
            self.pixel_limit_status = "LEFT RED EMERGENCY STOP"
            self.enabled = False
            self.requires_carriage_click = True
            self._last_motion_direction = 0

            return self._set_command(
                self.COMMAND_EMERGENCY_STOP,
                (
                    "LEFT RED LINE - EMERGENCY STOP LATCHED; "
                    "MOVE CARRIAGE INSIDE AND CLICK"
                ),
                force=True,
            )

        if full_x >= right_red_guard:
            self._red_stop_side = "RIGHT"
            self.pixel_stop_latch_side = "RIGHT"
            self.pixel_limit_status = "RIGHT RED EMERGENCY STOP"
            self.enabled = False
            self.requires_carriage_click = True
            self._last_motion_direction = 0

            return self._set_command(
                self.COMMAND_EMERGENCY_STOP,
                (
                    "RIGHT RED LINE - EMERGENCY STOP LATCHED; "
                    "MOVE CARRIAGE INSIDE AND CLICK"
                ),
                force=True,
            )

        # ----------------------------------------------------------
        # ABSOLUTE LIVE MOUSE LEASH
        # ----------------------------------------------------------
        # Coordinates passed to this controller are half-resolution, while
        # the requested safety distance is defined in full-image pixels.
        mouse_full_x = (
            float(mouse_x) * self.processing_to_full_scale
        )
        separation_full_px = full_x - mouse_full_x

        hard_limit = self.maximum_mouse_separation_full_px
        soft_limit = self.mouse_separation_soft_limit_full_px

        self.mouse_carriage_separation_full_px = (
            separation_full_px
        )
        self.mouse_leash_left_full_px = (
            mouse_full_x - hard_limit
        )
        self.mouse_leash_right_full_px = (
            mouse_full_x + hard_limit
        )

        # If the carriage is already outside the hard envelope, never let
        # it continue outward. Permit only slow movement back toward the
        # currently detected mouse.
        if separation_full_px <= -hard_limit:
            self._last_motion_direction = 1
            self.pixel_limit_status = (
                "MOUSE LEASH: TOO FAR LEFT - RETURN RIGHT"
            )

            return self._set_command(
                self.COMMAND_RIGHT_CREEP,
                (
                    "MOUSE LEASH EXCEEDED LEFT - "
                    "CREEP RIGHT TOWARD MOUSE"
                ),
                force=True,
            )

        if separation_full_px >= hard_limit:
            self._last_motion_direction = -1
            self.pixel_limit_status = (
                "MOUSE LEASH: TOO FAR RIGHT - RETURN LEFT"
            )

            return self._set_command(
                self.COMMAND_LEFT_CREEP,
                (
                    "MOUSE LEASH EXCEEDED RIGHT - "
                    "CREEP LEFT TOWARD MOUSE"
                ),
                force=True,
            )

        target_x, correction_px = self._corrected_target(
            float(mouse_x)
        )

        error = target_x - control_x
        absolute_error = abs(error)

        self.raw_mouse_x = float(mouse_x)
        self.corrected_target_x = target_x
        self.perspective_offset_px = correction_px
        self.raw_carriage_x = safety_x
        self.fixed_carriage_full_x = full_x
        self.predicted_carriage_x = control_x
        self.control_error_px = error
        self.control_target_source = "LIVE"

        requested_direction = (
            1 if error > 0.0 else -1
        )

        current_direction = self._command_to_image_direction(
            self._desired_command
        )

        if absolute_error <= self.stop_deadband_px:
            if current_direction != 0:
                self._last_motion_direction = current_direction

            return self._set_command(
                self.COMMAND_STOP,
                "ALIGNED",
            )

        if (
            current_direction == 0
            and absolute_error < self.start_deadband_px
        ):
            return self._set_command(
                self.COMMAND_STOP,
                "ALIGNED",
            )

        if (
            current_direction == 0
            and self._last_motion_direction != 0
            and requested_direction
            != self._last_motion_direction
            and absolute_error < self.reverse_deadband_px
        ):
            return self._set_command(
                self.COMMAND_STOP,
                "ALIGNED",
            )

        # Red-line handling is performed unconditionally above, before
        # all normal target-following logic.

        # Begin braking before the 150-pixel hard cable boundary. This
        # prevents normal outward movement from using motor inertia to cross
        # the hard mouse-to-carriage envelope.
        if (
            requested_direction < 0
            and separation_full_px <= -soft_limit
        ):
            self._last_motion_direction = -1
            self.pixel_limit_status = (
                "MOUSE LEASH LEFT BRAKE - STOP"
            )

            return self._set_command(
                self.COMMAND_STOP,
                (
                    "MOUSE LEASH LEFT SOFT LIMIT - "
                    "OUTWARD MOVEMENT STOPPED"
                ),
                force=True,
            )

        if (
            requested_direction > 0
            and separation_full_px >= soft_limit
        ):
            self._last_motion_direction = 1
            self.pixel_limit_status = (
                "MOUSE LEASH RIGHT BRAKE - STOP"
            )

            return self._set_command(
                self.COMMAND_STOP,
                (
                    "MOUSE LEASH RIGHT SOFT LIMIT - "
                    "OUTWARD MOVEMENT STOPPED"
                ),
                force=True,
            )

        if (
            self._end_lock_side == "LEFT"
            and requested_direction < 0
        ):
            return self._set_command(
                self.COMMAND_STOP,
                "LEFT END LOCKED - MOVE MOUSE RIGHT",
            )

        if (
            self._end_lock_side == "RIGHT"
            and requested_direction > 0
        ):
            return self._set_command(
                self.COMMAND_STOP,
                "RIGHT END LOCKED - MOVE MOUSE LEFT",
            )

        left_creep_threshold = (
            self.fixed_left_stop_full_px
            + self.red_line_creep_margin_full_px
        )
        right_creep_threshold = (
            self.fixed_right_stop_full_px
            - self.red_line_creep_margin_full_px
        )

        near_red_line = (
            (
                requested_direction < 0
                and full_x <= left_creep_threshold
            )
            or
            (
                requested_direction > 0
                and full_x >= right_creep_threshold
            )
        )

        near_live_target = (
            absolute_error <= self.near_target_creep_px
        )
        use_creep = near_red_line or near_live_target

        self._last_motion_direction = requested_direction
        self.pixel_limit_status = (
            "CREEP"
            if use_creep
            else "FAST"
        )

        if requested_direction < 0:
            return self._set_command(
                (
                    self.COMMAND_LEFT_CREEP
                    if use_creep
                    else self.COMMAND_LEFT_FAST
                ),
                (
                    "LEFT CREEP TO TARGET"
                    if use_creep
                    else "LEFT FAST TO TARGET"
                ),
            )

        return self._set_command(
            (
                self.COMMAND_RIGHT_CREEP
                if use_creep
                else self.COMMAND_RIGHT_FAST
            ),
            (
                "RIGHT CREEP TO TARGET"
                if use_creep
                else "RIGHT FAST TO TARGET"
            ),
        )

    # --------------------------------------------------------------
    # Manual recovery
    # --------------------------------------------------------------

    def recover_from_click(
        self,
        carriage_x: float,
    ) -> str:
        self._clear_ok_event.clear()
        self._clear_failed_event.clear()

        self._desired_command = self.COMMAND_STOP
        self._write_command(self.COMMAND_STOP)
        time.sleep(0.05)
        self._write_command(self.COMMAND_CLEAR_FAULT)

        deadline = time.monotonic() + 1.25

        while time.monotonic() < deadline:
            if self._clear_failed_event.is_set():
                self.enabled = False
                self.requires_carriage_click = True
                self._status = (
                    "END SWITCH ACTIVE - MOVE CARRIAGE AWAY"
                )
                return self._status

            if self._clear_ok_event.is_set():
                break

            time.sleep(0.01)

        if not self._clear_ok_event.is_set():
            self.enabled = False
            self.requires_carriage_click = True
            self._status = (
                "NO ARDUINO CLEAR CONFIRMATION - CLICK AGAIN"
            )
            return self._status

        self.raw_carriage_x = float(carriage_x)
        self.fixed_carriage_full_x = (
            float(carriage_x)
            * self.processing_to_full_scale
        )

        self._tracking_lost_frames = 0
        self._last_motion_direction = 0
        self._backoff_active = False
        self._end_lock_side = ""
        self._red_stop_side = ""
        self.pixel_stop_latch_side = ""

        self.enabled = True
        self.requires_carriage_click = False
        self._desired_command = self.COMMAND_STOP
        self._status = "READY"

        print(
            "Carriage position accepted at full-frame "
            f"X={self.fixed_carriage_full_x:.1f}."
        )

        return self._status

    def stop(self, force: bool = False) -> str:
        return self._set_command(
            self.COMMAND_STOP,
            "STOPPED",
            force=force,
        )

    def disable(self) -> str:
        self.enabled = False
        self.requires_carriage_click = True

        return self._set_command(
            self.COMMAND_STOP,
            "AUTOMATIC DISABLED - CLICK CARRIAGE",
            force=True,
        )

    def enable(self) -> str:
        self.enabled = False
        self.requires_carriage_click = True
        self._status = "CLICK CARRIAGE TO ENABLE"
        return self._status

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        try:
            self._write_command(self.COMMAND_STOP)
        finally:
            try:
                self.arduino.close()
            except (serial.SerialException, OSError):
                pass

        print("Automatic motor connection closed.")