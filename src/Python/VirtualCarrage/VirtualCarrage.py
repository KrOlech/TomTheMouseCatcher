import time
from collections import deque

import serial

from src.Python.Settings import Settings
from src.Python.Loger.Loger import Loger


class VirtualCarrage(Loger):

    OneFullRotation_Steps: int = 200

    Gear_1_cog_count: int = 150
    Gear_2_cog_count: int = 20

    Gear_dif: float = Gear_1_cog_count / Gear_2_cog_count

    angleDelta: float = 360 / OneFullRotation_Steps

    belt_peach: float = 2  # mm

    Gear_1_length: float = belt_peach * Gear_1_cog_count
    Gear_2_length: float = belt_peach * Gear_2_cog_count

    oneSteplength: float = (
        Gear_1_length / OneFullRotation_Steps
    )

    safetyDistance: float = 20  # mm

    SPEED_STEPS: int = 325
    SPEED_STEPS_left: int = -SPEED_STEPS
    SPEED_STEPS_right: int = SPEED_STEPS

    SPEED: float = SPEED_STEPS * oneSteplength

    MAZE_LENGTH_MM: float = 1500
    MAZE_LENGTH_PIZELS: int = 1920

    SPEED_PIXELS: int = int(
        MAZE_LENGTH_PIZELS
        * SPEED
        / MAZE_LENGTH_MM
    )

    START_TOLERANCE: int = 100
    STOP_TOLERANCE: int = 50
    REVERSE_TOLERANCE: int = 150

    ERROR_HISTORY_LENGTH: int = 4

    # Camera-based jam detection. At low FPS a reliable reaction cannot
    # always happen in exactly 200 ms, so the code uses a short rolling
    # time window and confirms the stall twice before locking a direction.
    JAM_START_GRACE_SECONDS: float = 0.15
    JAM_WINDOW_SECONDS: float = 0.35
    JAM_MIN_MOVEMENT_PIXELS: float = 5.0
    JAM_REQUIRED_FAILURES: int = 2

    def __init__(self):

        # Estimated carriage position
        self.positionMM = self.safetyDistance

        self.position = int(
            self.positionMM
            * self.MAZE_LENGTH_PIZELS
            / self.MAZE_LENGTH_MM
        )

        # Current movement state:
        # "left", "right", or "stop"
        self.last_status = "stop"

        # End-stop states
        self.left_end_active = False
        self.right_end_active = False

        # Time used to estimate carriage position
        current_time = time.time()

        self.timeGoing_left = current_time
        self.timeGoing_right = current_time

        # Average recent mouse-carriage errors
        self.error_history = deque(
            maxlen=self.ERROR_HISTORY_LENGTH
        )

        # Camera-based jam detection state
        self.jam_position_history = deque()
        self.jam_movement_started_at = None
        self.jam_failure_count = 0

        # Direction blocked after a detected jam. The opposite direction
        # stays available so the carriage can move away from an obstacle.
        self.jammed_direction = None

        self.arduino = None

        if Settings.arduinoLineCome:
            try:
                self.arduino = serial.Serial(
                    port=Settings.arduinoLineCome,
                    baudrate=Settings.baudrate,
                    timeout=0.01
                )

                # Arduino usually resets when the serial port opens
                time.sleep(2)

                self.arduino.reset_input_buffer()
                self.arduino.reset_output_buffer()

            except serial.SerialException as error:
                self.arduino = None

                self.loger(
                    f"Could not open Arduino serial port: {error}"
                )

    def advanceZoneCords(self,zoneCords, carriage_position=None):
        x0, y0, w, h = zoneCords

        if carriage_position is None:
            carriage_position = self.position
        else:
            carriage_position //= 0.5

        self.advance(x0//0.5, carriage_position)

    def advance(self, x0, c0):
        """
        Control carriage movement.

        x0 = detected mouse X coordinate
        c0 = detected carriage X coordinate
        """

        # Read all available Arduino responses first
        self.__readArduinoMessages()

        if x0 is None or c0 is None:
            return

        # c0 must be the real camera-observed carriage X coordinate.
        self.__checkForJam(c0)

        raw_difference = x0 - c0

        self.error_history.append(raw_difference)

        difference = (
            sum(self.error_history)
            / len(self.error_history)
        )

        if self.last_status == "stop":

            if difference > self.START_TOLERANCE:

                if not self.right_end_active:
                    self.__movementInDirection("right")

            elif difference < -self.START_TOLERANCE:

                if not self.left_end_active:
                    self.__movementInDirection("left")

        elif self.last_status == "right":

            if abs(difference) <= self.STOP_TOLERANCE:
                self.stop()

            elif difference < -self.REVERSE_TOLERANCE:
                self.__movementInDirection("left")

        elif self.last_status == "left":

            if abs(difference) <= self.STOP_TOLERANCE:
                self.stop()

            elif difference > self.REVERSE_TOLERANCE:
                self.__movementInDirection("right")

        self.__updatePixelPosition()

    def __movementInDirection(self, direction):

        if direction not in ("left", "right"):
            return

        # Never move farther into an active end-stop.
        if direction == "right" and self.right_end_active:
            return

        if direction == "left" and self.left_end_active:
            return

        # Do not repeatedly drive into the same obstruction.
        if self.jammed_direction == direction:
            self.loger(
                f"movement {direction} blocked: "
                f"carriage jam lock is active"
            )
            return

        # Movement away from the obstruction is allowed and clears the lock.
        if (
            self.jammed_direction is not None
            and direction != self.jammed_direction
        ):
            self.loger(
                f"moving away from {self.jammed_direction} jam; "
                f"clearing jam lock"
            )
            self.jammed_direction = None

        current_time = time.time()

        if self.last_status == direction:
            self.__updateEstimatedPosition(
                direction,
                current_time
            )

        else:
            previous_direction = self.last_status

            if previous_direction in ("left", "right"):
                self.__updateEstimatedPosition(
                    previous_direction,
                    current_time
                )

            # A new movement command starts a fresh jam-checking period.
            self.__resetJamDetection(preserve_jam_lock=True)

            # Moving away from one end-stop releases that lock.
            if direction == "right":
                self.left_end_active = False
            elif direction == "left":
                self.right_end_active = False

            self.last_status = direction
            self.jam_movement_started_at = time.monotonic()

            self.loger(
                f"moving virtual carriage to the {direction}"
            )

            if direction == "right":
                self.right()
            else:
                self.left()

            setattr(
                self,
                f"timeGoing_{direction}",
                current_time
            )

        self.__checkSoftwareLimits()

    def __checkForJam(self, detected_carriage_position):
        """Stop and lock a direction when camera position shows no motion."""

        if detected_carriage_position is None:
            return

        if self.last_status not in ("left", "right"):
            self.__resetJamDetection(preserve_jam_lock=True)
            return

        try:
            detected_position = float(detected_carriage_position)
        except (TypeError, ValueError):
            return

        now = time.monotonic()

        if self.jam_movement_started_at is None:
            self.jam_movement_started_at = now

        if (
            now - self.jam_movement_started_at
            < self.JAM_START_GRACE_SECONDS
        ):
            self.jam_position_history.clear()
            self.jam_position_history.append((now, detected_position))
            return

        self.jam_position_history.append((now, detected_position))

        while (
            self.jam_position_history
            and now - self.jam_position_history[0][0]
            > self.JAM_WINDOW_SECONDS
        ):
            self.jam_position_history.popleft()

        if len(self.jam_position_history) < 2:
            return

        oldest_time, oldest_position = self.jam_position_history[0]
        newest_time, newest_position = self.jam_position_history[-1]
        measured_time = newest_time - oldest_time

        if measured_time < self.JAM_WINDOW_SECONDS * 0.8:
            return

        displacement = newest_position - oldest_position

        if self.last_status == "right":
            expected_movement = displacement
        else:
            expected_movement = -displacement

        if expected_movement < self.JAM_MIN_MOVEMENT_PIXELS:
            self.jam_failure_count += 1
            self.loger(
                "possible carriage jam: "
                f"direction={self.last_status}, "
                f"movement={expected_movement:.1f}px, "
                f"window={measured_time:.3f}s, "
                f"failure={self.jam_failure_count}/"
                f"{self.JAM_REQUIRED_FAILURES}"
            )
        else:
            self.jam_failure_count = 0

        # Start the next independent measurement window here.
        self.jam_position_history.clear()
        self.jam_position_history.append((now, detected_position))

        if self.jam_failure_count >= self.JAM_REQUIRED_FAILURES:
            blocked_direction = self.last_status
            self.loger(
                "CARRIAGE JAM DETECTED: "
                f"blocked direction={blocked_direction}; stopping motor"
            )

            self.jammed_direction = blocked_direction
            self.stop()
            self.__resetJamDetection(preserve_jam_lock=True)

    def __resetJamDetection(self, preserve_jam_lock=False):
        self.jam_position_history.clear()
        self.jam_movement_started_at = None
        self.jam_failure_count = 0

        if not preserve_jam_lock:
            self.jammed_direction = None

    def __updateEstimatedPosition(
        self,
        direction,
        current_time
    ):
        if direction not in ("left", "right"):
            return

        previous_time = getattr(
            self,
            f"timeGoing_{direction}"
        )

        time_delta = current_time - previous_time

        # Protect against invalid or very large time jumps
        if time_delta < 0:
            time_delta = 0

        elif time_delta > 1:
            time_delta = 1

        setattr(
            self,
            f"timeGoing_{direction}",
            current_time
        )

        speed_steps = getattr(
            self,
            f"SPEED_STEPS_{direction}"
        )

        steps_done = speed_steps * time_delta

        self.positionMM += (
            self.oneSteplength * steps_done
        )

    def __checkSoftwareLimits(self):

        right_limit = (
            self.MAZE_LENGTH_MM
            - self.safetyDistance
        )

        if self.positionMM >= right_limit:

            self.positionMM = right_limit
            self.right_end_active = True

            if self.last_status == "right":
                self.stop()

        elif self.positionMM <= self.safetyDistance:

            self.positionMM = self.safetyDistance
            self.left_end_active = True

            if self.last_status == "left":
                self.stop()

    def __updatePixelPosition(self):

        self.position = int(
            self.positionMM
            * self.MAZE_LENGTH_PIZELS
            / self.MAZE_LENGTH_MM
        )

        self.position = max(
            0,
            min(
                self.position,
                self.MAZE_LENGTH_PIZELS
            )
        )

    def stop(self):

        if self.last_status not in ("left", "right"):
            return

        previous_direction = self.last_status
        current_time = time.time()

        self.__updateEstimatedPosition(
            previous_direction,
            current_time
        )

        self.last_status = "stop"

        self.__checkSoftwareLimits()
        self.__updatePixelPosition()

        self.loger("Stopping virtual carriage")

        self.__arduinoStop()

        self.loger(
            f"virtual carriage was moving "
            f"in {previous_direction}"
        )

        # Preserve a jam lock if stop() was called by jam detection.
        self.__resetJamDetection(preserve_jam_lock=True)

    def __arduinoStop(self):
        self.__arduinoCommand("100", "stop")

    def right(self):
        self.__arduinoCommand("1", "right")

    def left(self):
        self.__arduinoCommand("-1", "left")

    def __arduinoCommand(
        self,
        command,
        command_name
    ):
        if self.arduino is None:
            return

        try:
            self.loger(
                f"sending {command_name} command to Arduino"
            )

            self.arduino.write(
                command.encode("utf-8")
            )

        except serial.SerialException as error:
            self.loger(
                f"Arduino write error: {error}"
            )

    def __readArduinoMessages(self):

        if self.arduino is None:
            return

        try:
            while self.arduino.in_waiting > 0:

                raw_message = self.arduino.readline()

                message = raw_message.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if not message:
                    continue

                self.loger(
                    f"Arduino ack: {message}"
                )

                message_lower = message.lower()

                # Physical left end-stop reached
                if (
                    "left" in message_lower
                    and "end" in message_lower
                ):
                    self.left_end_active = True
                    self.right_end_active = False

                    self.positionMM = self.safetyDistance
                    self.last_status = "stop"

                    self.error_history.clear()
                    self.__resetJamDetection(preserve_jam_lock=False)
                    self.__updatePixelPosition()

                    continue

                # Physical right end-stop reached
                if (
                    "right" in message_lower
                    and "end" in message_lower
                ):
                    self.right_end_active = True
                    self.left_end_active = False

                    self.positionMM = (
                        self.MAZE_LENGTH_MM
                        - self.safetyDistance
                    )

                    self.last_status = "stop"

                    self.error_history.clear()
                    self.__resetJamDetection(preserve_jam_lock=False)
                    self.__updatePixelPosition()

                    continue

                # Arduino accepted movement to the left.
                # Therefore, the right end-stop is no longer relevant.
                if message_lower.startswith("left "):
                    self.right_end_active = False

                # Arduino accepted movement to the right.
                # Therefore, the left end-stop is no longer relevant.
                elif message_lower.startswith("right "):
                    self.left_end_active = False

                elif message_lower.startswith("stop "):
                    self.last_status = "stop"
                    self.__resetJamDetection(preserve_jam_lock=True)

        except serial.SerialException as error:
            self.loger(
                f"Arduino read error: {error}"
            )

    def close(self):
        """
        Safely stop the motor and close the serial port.
        """

        try:
            if self.last_status in ("left", "right"):
                self.stop()

            if self.arduino is not None:
                self.arduino.close()
                self.arduino = None

        except serial.SerialException as error:
            self.loger(
                f"Arduino close error: {error}"
            )