import json
import os
import time
from datetime import datetime
from itertools import count

import cv2
import numpy as np

from src.Python.Loger.Loger import Loger
from src.Python.AutomaticMotorControl import AutomaticMotorControl
from src.Python.Recognize.Recognize_AB_Filter import Recognize
from src.Python.Recognize.HorizontalCarriageTracker import (
    HorizontalCarriageTracker,
)
from src.Python.Settings import Settings
from src.Python.Zones.Zones import Zones


class VideoCapture(Loger):
    calibration = []
    refCalibration = []

    font = cv2.FONT_HERSHEY_SIMPLEX
    org = (100, 23)
    fontScale = 0.5
    color = (255, 0, 0)
    thickness = 1

    last_flagSave = 0
    current_flagSave = 0
    saving_started = 0
    save_calibration = 0
    zone_active = 0
    zone_active_last = 0
    calibration_start = 0
    calibratedFlag = 0

    messagePrinted: bool = False

    offset_nr = 90

    frame = None
    frame_lum = None
    out = None

    windowName: str = "output"

    target_fps = Settings.fps
    frame_delay = 1.0 / target_fps
    start_time = 0

    def __init__(
        self,
        active_zone,
        recTrigger,
        finishFlag,
        which_logic_Set,
        trial_nr,
    ):
        self.frames = 0
        self.start = time.time()

        self.zon = Zones(which_logic_Set, trial_nr)
        self.zon.read_zones()

        mouseMainMask = [
            np.array([85, 85, 150]),
            np.array([100, 150, 220]),
        ]
        mousePlexyMask = [
            np.array([0, 0, 210]),
            np.array([110, 25, 250]),
        ]
        mouseArea = [
            int(400 * 0.25),
            int(5500 * 0.25),
        ]
        mouseAspect = [0.25, 3.3]

        self.rcMouse = Recognize(
            mouseMainMask,
            mouseArea,
            mouseAspect,
            mousePlexyMask,
        )

        self.rcCarriage = HorizontalCarriageTracker(
            template_width=32,
            template_height=26,
            search_margin_y=16,
            local_search_radius=170,
            maximum_step=70,
            smoothing=0.78,
            minimum_match=0.30,
            strong_match=0.58,
            template_update_rate=0.0,
            recovery_growth=45,
            maximum_recovery_radius=420,
        )

        self.recTrigger = recTrigger
        self.active_zone = active_zone
        self.timeActivated = time.time()

        self.finishFlag = finishFlag
        self.which_logic_Set = which_logic_Set

        self.cap = cv2.VideoCapture(Settings.CamNr)

        self.capt_frames_nr = 0
        self.motor_status = "INITIALIZING"
        self.automatic_motor = None

        # Press [ and click to set the LEFT safe boundary.
        # Press ] and click to set the RIGHT safe boundary.
        self.limit_click_mode = None
        self.motor_limits_path = os.path.join(
            os.path.dirname(__file__),
            "motor_limits.json",
        )

        self.fourcc = cv2.VideoWriter_fourcc(*"XVID")

        cv2.startWindowThread()
        cv2.namedWindow(
            self.windowName,
            cv2.WINDOW_NORMAL,
        )
        cv2.setMouseCallback(
            self.windowName,
            self.on_mouse_click,
        )

        self.setCapture()

        processed_width = Settings.FrameWidth * 0.5

        # Conservative defaults based on the rail occupying the central part
        # of the camera image. Calibrate exact boundaries with [ and ].
        default_left_safe = processed_width * 0.15
        default_right_safe = processed_width * 0.85

        left_safe, right_safe = self.load_motor_limits(
            default_left_safe,
            default_right_safe,
        )

        self.automatic_motor = AutomaticMotorControl(
            finish_flag=self.finishFlag,
            port="COM3",
            baudrate=115200,
            deadband=35.0,

            # The raw image range is replaced immediately by calibrated
            # limits below.
            left_limit=left_safe,
            right_limit=right_safe,
            end_guard_px=0.0,

            # Maximum speed remains enabled in the central section.
            fast_distance_px=140.0,
            medium_distance_px=65.0,

            # Full speed remains available in the centre, but braking starts
            # much earlier when moving toward a physical end.
            end_creep_zone_px=95.0,
            end_medium_zone_px=190.0,
            end_prediction_s=0.60,

            # Safety prediction uses the raw, unsmoothed carriage position and
            # a worst-case speed floor, so it still works when the green
            # tracking cross lags behind at high speed.
            safety_prediction_s=0.35,
            emergency_stop_margin_px=35.0,
            carriage_half_width_px=16.0,
            nominal_creep_speed_px_s=80.0,
            nominal_medium_speed_px_s=170.0,
            nominal_fast_speed_px_s=330.0,
            heartbeat_interval_s=0.05,

            maze_length_mm=1500.0,
            maximum_perspective_offset_mm=150.0,
        )

        self.automatic_motor.configure_safe_limits(
            left_safe_px=left_safe,
            right_safe_px=right_safe,
        )

        self.motor_status = "WAITING FOR CLICK"

        self.runCaptureTryExcept()

    def load_motor_limits(
        self,
        default_left: float,
        default_right: float,
    ) -> tuple[float, float]:
        try:
            with open(
                self.motor_limits_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            left = float(data["left_safe_px"])
            right = float(data["right_safe_px"])

            if right - left < 150.0:
                raise ValueError(
                    "Stored limits are too close together."
                )

            print(
                "Loaded motor limits: "
                f"{left:.1f} .. {right:.1f}"
            )
            return left, right

        except (
            OSError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            print(
                "Using conservative default motor limits "
                f"({error})."
            )
            return float(default_left), float(default_right)

    def save_motor_limits(self) -> None:
        if self.automatic_motor is None:
            return

        data = {
            "left_safe_px": (
                self.automatic_motor.safe_left_px
            ),
            "right_safe_px": (
                self.automatic_motor.safe_right_px
            ),
        }

        with open(
            self.motor_limits_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(data, file, indent=2)

        print(
            "Saved motor limits to "
            f"{self.motor_limits_path}"
        )

    def draw_motor_speed_zones(self) -> None:
        if (
            self.automatic_motor is None
            or self.frame is None
        ):
            return

        zones = self.automatic_motor.get_speed_zones()
        scale_to_full = 2.0
        frame_height, frame_width = self.frame.shape[:2]

        def full_x(value: float) -> int:
            return max(
                0,
                min(
                    frame_width - 1,
                    int(round(value * scale_to_full)),
                ),
            )

        safe_left = full_x(zones["safe_left"])
        left_creep_end = full_x(
            zones["left_creep_end"]
        )
        left_medium_end = full_x(
            zones["left_medium_end"]
        )
        right_medium_start = full_x(
            zones["right_medium_start"]
        )
        right_creep_start = full_x(
            zones["right_creep_start"]
        )
        safe_right = full_x(zones["safe_right"])

        overlay = self.frame.copy()

        # Red = forbidden; orange = creep; yellow = medium.
        cv2.rectangle(
            overlay,
            (0, 0),
            (safe_left, frame_height),
            (0, 0, 255),
            -1,
        )
        cv2.rectangle(
            overlay,
            (safe_right, 0),
            (frame_width, frame_height),
            (0, 0, 255),
            -1,
        )
        cv2.rectangle(
            overlay,
            (safe_left, 0),
            (left_creep_end, frame_height),
            (0, 120, 255),
            -1,
        )
        cv2.rectangle(
            overlay,
            (right_creep_start, 0),
            (safe_right, frame_height),
            (0, 120, 255),
            -1,
        )
        cv2.rectangle(
            overlay,
            (left_creep_end, 0),
            (left_medium_end, frame_height),
            (0, 255, 255),
            -1,
        )
        cv2.rectangle(
            overlay,
            (right_medium_start, 0),
            (right_creep_start, frame_height),
            (0, 255, 255),
            -1,
        )

        self.frame = cv2.addWeighted(
            overlay,
            0.10,
            self.frame,
            0.90,
            0.0,
        )

        line_data = [
            (safe_left, (0, 0, 255), "STOP"),
            (
                left_creep_end,
                (0, 120, 255),
                "CREEP",
            ),
            (
                left_medium_end,
                (0, 255, 255),
                "MEDIUM",
            ),
            (
                right_medium_start,
                (0, 255, 255),
                "MEDIUM",
            ),
            (
                right_creep_start,
                (0, 120, 255),
                "CREEP",
            ),
            (safe_right, (0, 0, 255), "STOP"),
        ]

        for x_position, colour, label in line_data:
            cv2.line(
                self.frame,
                (x_position, 0),
                (x_position, frame_height),
                colour,
                2,
            )
            cv2.putText(
                self.frame,
                label,
                (
                    max(2, x_position - 25),
                    105,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )

        cv2.putText(
            self.frame,
            "[ + click: LEFT safe line   "
            "] + click: RIGHT safe line   "
            "MAGENTA=raw safety X  CYAN=predicted X",
            (310, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def on_mouse_click(
        self,
        event,
        x,
        y,
        flags,
        param,
    ):
        """Set safe boundaries or capture/re-capture the carriage."""
        del flags, param

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if self.frame_lum is None:
            print("No camera frame available yet.")
            return

        processing_scale = 0.5

        processing_x = int(x * processing_scale)
        processing_y = int(y * processing_scale)

        if (
            self.limit_click_mode is not None
            and self.automatic_motor is not None
        ):
            left = self.automatic_motor.safe_left_px
            right = self.automatic_motor.safe_right_px

            if self.limit_click_mode == "left":
                left = float(processing_x)
            else:
                right = float(processing_x)

            try:
                self.automatic_motor.configure_safe_limits(
                    left_safe_px=left,
                    right_safe_px=right,
                )
                self.save_motor_limits()
                self.motor_status = (
                    f"{self.limit_click_mode.upper()} "
                    "SAFE LIMIT SAVED"
                )
            except ValueError as error:
                self.motor_status = str(error)
                print(error)
            finally:
                self.limit_click_mode = None

            return

        try:
            self.rcCarriage.initialize_from_click(
                self.frame_lum,
                processing_x,
                processing_y,
            )

            print(
                "Carriage template captured at "
                f"x={processing_x}, y={processing_y}"
            )

            if self.automatic_motor is not None:
                self.motor_status = (
                    self.automatic_motor.recover_from_click(
                        processing_x
                    )
                )

        except ValueError as error:
            print(f"Carriage template error: {error}")

    def runCaptureTryExcept(self):
        try:
            self.runCapture()
        except Exception as error:
            self.logError(error)
        else:
            self.zon.finish()
        finally:
            self.releaseCapture()

    def runCapture(self):
        self.runVideoCaptureSavingFrames()

        if self.out is not None:
            self.out.release()

        self.saving_started = 0
        self.loger("STOP SAVING")

    def captureFrame(self):
        self.start_time = time.time()

        ret, frame = self.cap.read()

        if not ret or frame is None:
            raise RuntimeError(
                "Could not read a frame from the camera or video."
            )

        self.rowFrame = frame.copy()

        processing_scale = 0.5

        self.frame_lum = cv2.resize(
            frame,
            None,
            fx=processing_scale,
            fy=processing_scale,
            interpolation=cv2.INTER_AREA,
        )

        now = datetime.now()

        self.frame = cv2.putText(
            frame,
            str(now),
            self.org,
            self.font,
            self.fontScale,
            self.color,
            self.thickness,
            cv2.LINE_AA,
        )

    def startRecording(self):
        if (
            not self.last_flagSave
            and self.current_flagSave
        ):
            self.saving_started = True

            filename = datetime.now().strftime(
                f"{os.path.expanduser('~')}"
                "\\Documents\\TOM\\data\\"
                "video%Y%m%d_%H_%M_%S.avi"
            )

            self.out = cv2.VideoWriter(
                filename,
                self.fourcc,
                20.0,
                (
                    self.rowFrame.shape[1],
                    self.rowFrame.shape[0],
                ),
            )

            self.loger("START RECORDING")

    def runVideoCaptureSavingFrames(self):
        for i in count(0):
            self.captureFrame()

            if i <= self.offset_nr:
                continue

            self.recTrigger.set()

            self.current_flagSave = (
                1 if self.recTrigger.is_set() else 0
            )

            self.calibrate()
            self.startRecording()

            if self.recTrigger.is_set():
                if self.calibratedFlag == 0:
                    cv2.circle(
                        self.frame,
                        (30, 17),
                        10,
                        (0, 0, 255),
                        -1,
                    )
                else:
                    cv2.circle(
                        self.frame,
                        (30, 17),
                        10,
                        (0, 255, 0),
                        -1,
                    )

            if self.calibratedFlag == 1:
                mouse_location = self.rcMouse.get_location(
                    self.frame_lum
                )

                lum = self.zon.get_active_zone(
                    mouse_location
                )

                self.rcCarriage.get_location(
                    self.frame_lum
                )

                if self.automatic_motor is not None:
                    self.motor_status = (
                        self.automatic_motor.update(
                            mouse_x=self.rcMouse.px,
                            carriage_x=self.rcCarriage.px,
                            mouse_detected=(
                                self.rcMouse.detected
                            ),
                            carriage_detected=(
                                self.rcCarriage.detected
                            ),
                            carriage_initialized=(
                                self.rcCarriage.initialized
                            ),
                            carriage_safety_x=getattr(
                                self.rcCarriage,
                                "raw_px",
                                self.rcCarriage.px,
                            ),
                            carriage_match_score=(
                                self.rcCarriage.last_match_score
                            ),
                        )
                    )
            else:
                lum = -1

                if self.automatic_motor is not None:
                    self.automatic_motor.stop()
                    self.motor_status = "CALIBRATING"

            requires_click = (
                self.automatic_motor is not None
                and
                self.automatic_motor.requires_carriage_click
            )

            if requires_click:
                cv2.putText(
                    self.frame,
                    "MOTOR STOPPED - CLICK THE CARRIAGE",
                    (350, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            elif not self.rcCarriage.initialized:
                cv2.putText(
                    self.frame,
                    "CLICK ON THE CARRIAGE",
                    (500, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            elif not self.rcCarriage.detected:
                cv2.putText(
                    self.frame,
                    "CARRIAGE LOST - POSITION HELD",
                    (430, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 165, 255),
                    2,
                    cv2.LINE_AA,
                )

            moving_or_aligned = (
                self.motor_status.startswith("LEFT")
                or self.motor_status.startswith("RIGHT")
                or self.motor_status == "ALIGNED"
            )

            status_colour = (
                (0, 255, 0)
                if moving_or_aligned
                else (0, 165, 255)
            )

            cv2.putText(
                self.frame,
                f"AUTO MOTOR: {self.motor_status}",
                (500, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                status_colour,
                2,
                cv2.LINE_AA,
            )

            self.draw_motor_speed_zones()

            self.zone_active_last = self.zone_active

            for zone_nr in range(self.zon.zones_nr):
                x0, y0, w, h = (
                    self.zon.get_zone_coords(zone_nr)
                )

                if lum == zone_nr:
                    cv2.rectangle(
                        self.frame,
                        (x0, y0),
                        (x0 + w, y0 + h),
                        (0, 0, 250),
                        2,
                    )
                else:
                    cv2.rectangle(
                        self.frame,
                        (x0, y0),
                        (x0 + w, y0 + h),
                        (0, 200, 0),
                        2,
                    )

            self.zon.check_zone_change()
            self.cross()

            cv2.circle(
                self.frame,
                (
                    int(self.rcMouse.px // 0.5),
                    int(self.rcMouse.py // 0.5),
                ),
                4,
                (0, 0, 255),
                -1,
            )

            if self.rcCarriage.detected:
                cv2.circle(
                    self.frame,
                    (
                        int(self.rcCarriage.px // 0.5),
                        int(self.rcCarriage.py // 0.5),
                    ),
                    4,
                    (0, 255, 0),
                    -1,
                )

                # Magenta vertical tick = newest unsmoothed carriage match
                # used by the safety controller. At high speed it may lead the
                # green smoothed cross; this is expected and prevents late
                # braking at the red line.
                raw_x = int(
                    getattr(
                        self.rcCarriage,
                        "raw_px",
                        self.rcCarriage.px,
                    )
                    // 0.5
                )
                raw_y = int(
                    self.rcCarriage.py // 0.5
                )

                cv2.line(
                    self.frame,
                    (raw_x, raw_y - 14),
                    (raw_x, raw_y + 14),
                    (255, 0, 255),
                    2,
                )

                if self.automatic_motor is not None:
                    predicted_x = int(
                        self.automatic_motor.predicted_carriage_x
                        // 0.5
                    )
                    cv2.line(
                        self.frame,
                        (predicted_x, raw_y - 10),
                        (predicted_x, raw_y + 10),
                        (255, 255, 0),
                        2,
                    )

            if (
                self.saving_started
                and self.out is not None
            ):
                self.out.write(self.frame)

            processing_time = (
                time.time() - self.start_time
            )

            sleep_time = max(
                0.0,
                self.frame_delay - processing_time,
            )

            time.sleep(sleep_time)

            if self.frame is not None:
                self.frames += 1

                if time.time() - self.start >= 1:
                    print("FPS:", self.frames)
                    self.frames = 0
                    self.start = time.time()

                cv2.imshow(
                    self.windowName,
                    self.frame,
                )

            if (
                self.last_flagSave
                and not self.current_flagSave
            ):
                if self.out is not None:
                    self.out.release()
                    self.out = None

                self.saving_started = 0
                self.loger("STOP SAVING")

            self.last_flagSave = self.current_flagSave

            key = cv2.waitKey(1) & 0xFF

            if key == ord("["):
                self.limit_click_mode = "left"
                self.motor_status = (
                    "CLICK LEFT SAFE LIMIT"
                )
                if self.automatic_motor is not None:
                    self.automatic_motor.stop(force=True)

            elif key == ord("]"):
                self.limit_click_mode = "right"
                self.motor_status = (
                    "CLICK RIGHT SAFE LIMIT"
                )
                if self.automatic_motor is not None:
                    self.automatic_motor.stop(force=True)

            elif key == ord("s"):
                if self.automatic_motor is not None:
                    self.automatic_motor.disable()

            elif key == ord("r"):
                if self.automatic_motor is not None:
                    self.automatic_motor.enable()

            if (
                key == ord("q")
                or self.finishFlag.is_set()
            ):
                self.finishFlag.set()

                if self.out is not None:
                    self.out.release()
                    self.out = None

                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            if (
                cv2.getWindowProperty(
                    self.windowName,
                    cv2.WND_PROP_VISIBLE,
                )
                < 1
            ):
                self.finishFlag.set()

                if self.out is not None:
                    self.out.release()
                    self.out = None

                self.saving_started = 0
                self.loger("STOP SAVING")
                break

            self.capt_frames_nr += 1
            self.active_zone.value = (
                self.zon.active_zone
            )

    def cross(self):
        if len(self.rcMouse.oldLocation) == 2:
            x, y = self.rcMouse.oldLocation
            x, y = int(x // 0.5), int(y // 0.5)

            cv2.line(
                self.frame,
                (x - 10, y),
                (x + 10, y),
                (255, 0, 0),
                1,
            )
            cv2.line(
                self.frame,
                (x, y - 10),
                (x, y + 10),
                (255, 0, 0),
                1,
            )

        if (
            self.rcCarriage.detected
            and len(self.rcCarriage.oldLocation) == 2
        ):
            x, y = self.rcCarriage.oldLocation
            x, y = int(x // 0.5), int(y // 0.5)

            cv2.line(
                self.frame,
                (x - 10, y),
                (x + 10, y),
                (0, 255, 0),
                1,
            )
            cv2.line(
                self.frame,
                (x, y - 10),
                (x, y + 10),
                (0, 255, 0),
                1,
            )

    def releaseCapture(self):
        if self.automatic_motor is not None:
            self.automatic_motor.close()
            self.automatic_motor = None

        self.cap.release()
        cv2.destroyAllWindows()

    def setCapture(self):
        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            Settings.FrameWidth,
        )
        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            Settings.FrameHeigth,
        )

        (
            self.ret_val,
            self.cap_for_exposure,
        ) = self.cap.read()

        if not self.ret_val:
            raise RuntimeError(
                "Camera opened, but the initial frame "
                "could not be read."
            )

        self.cap.set(
            cv2.CAP_PROP_AUTOFOCUS,
            0,
        )
        self.cap.set(
            cv2.CAP_PROP_AUTO_WB,
            0,
        )

        manual_exposure_set = self.cap.set(
            cv2.CAP_PROP_AUTO_EXPOSURE,
            0.25,
        )

        if not manual_exposure_set:
            self.cap.set(
                cv2.CAP_PROP_AUTO_EXPOSURE,
                1,
            )

        print(
            "Camera settings:",
            "autofocus=",
            self.cap.get(cv2.CAP_PROP_AUTOFOCUS),
            "auto_exposure=",
            self.cap.get(
                cv2.CAP_PROP_AUTO_EXPOSURE
            ),
            "auto_white_balance=",
            self.cap.get(cv2.CAP_PROP_AUTO_WB),
            "exposure=",
            self.cap.get(cv2.CAP_PROP_EXPOSURE),
        )

    def calibrate(self):
        if self.capt_frames_nr == 1:
            self.rcMouse.set_ref_image(
                self.frame_lum
            )

        if self.capt_frames_nr == 10:
            self.loger("Starting calibration...")
            self.calibration_start = 20

        if self.calibration_start > 0:
            self.calibration.append(
                cv2.cvtColor(
                    self.frame_lum,
                    cv2.COLOR_BGR2GRAY,
                ).copy()
            )

            self.refCalibration = np.mean(
                self.calibration,
                axis=0,
            )

            if self.calibration_start:
                self.refCalibration = np.mean(
                    self.calibration,
                    axis=0,
                )
                self.calibratedFlag = 1
                self.save_calibration = 1

            self.calibration_start -= 1

        if (
            self.calibratedFlag
            and not self.messagePrinted
        ):
            self.messagePrinted = True
            self.loger("calibration finished")

        if self.save_calibration:
            self.save_calibration = 0

            cv2.imwrite(
                f"{Settings.dataLocation}"
                "\\self.calibration.jpg",
                self.frame,
            )