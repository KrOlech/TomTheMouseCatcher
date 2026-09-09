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

        # The carriage is hidden briefly below the central commutator.
        # Coordinates below use the half-resolution processing image.
        #
        # Full-image occlusion corridor:
        # approximately X=800..1130
        #
        # Processing-image corridor:
        # X=400..565
        self.rcCarriage = HorizontalCarriageTracker(
            template_width=32,
            template_height=26,
            search_margin_y=16,

            local_search_radius=180,
            maximum_step=70,
            smoothing=0.72,
            minimum_match=0.28,
            strong_match=0.58,
            template_update_rate=0.0,
            recovery_growth=0,
            maximum_recovery_radius=180,

            occlusion_left_x=400,
            occlusion_right_x=565,
            occlusion_entry_margin=18,
            occlusion_exit_margin=22,

            maximum_occlusion_frames=40,
            reacquire_grace_frames=12,
            reacquire_search_radius=220,
            reacquire_minimum_match=0.24,

            creep_prediction_step=2.5,
            medium_prediction_step=5.0,
            fast_prediction_step=9.0,

            velocity_alpha=0.55,
            minimum_prediction_step=1.5,
            maximum_prediction_step=18.0,
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

        # Fixed-pixel version: every left click initializes the carriage.
        # motor_limits.json and click-calibrated speed zones are not used.
        self.limit_click_mode = None

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

        # --------------------------------------------------------------
        # SIMPLE TWO-SPEED END PROTECTION
        # --------------------------------------------------------------
        # All values use FULL-resolution camera X coordinates.
        #
        # Visible red STOP coordinates. Keep them safely inside the
        # physical end switches.
        fixed_left_stop_full_px = 20.0
        fixed_right_stop_full_px = 1900.0

        # Hidden slowdown boundaries. The motor changes from FAST to CREEP
        # before it reaches either visible red STOP line.
        slow_left_full_px = 500.0
        slow_right_full_px = 1400.0

        print(
            "Pre-slow/red-stop mode: "
            f"red STOP={fixed_left_stop_full_px:.1f}.."
            f"{fixed_right_stop_full_px:.1f}; "
            f"hidden CREEP={slow_left_full_px:.1f}.."
            f"{slow_right_full_px:.1f} full-frame px"
        )

        self.automatic_motor = AutomaticMotorControl(
            finish_flag=self.finishFlag,
            port="COM3",
            baudrate=115200,

            # Responsive positioning: no SETTLING delay.
            deadband=16.0,
            movement_start_deadband_px=28.0,
            movement_stop_deadband_px=16.0,
            reverse_deadband_px=55.0,
            settle_time_s=0.0,
            target_filter_alpha=0.50,
            target_filter_snap_px=16.0,

            # Carriage tracker coordinates are half-resolution.
            processing_to_full_scale=2.0,

            # Visible red software STOP coordinates.
            fixed_left_stop_full_px=fixed_left_stop_full_px,
            fixed_right_stop_full_px=fixed_right_stop_full_px,

            # Hidden boundaries where FAST changes to CREEP.
            slow_left_full_px=slow_left_full_px,
            slow_right_full_px=slow_right_full_px,

            # Stop slightly before the tracked centre reaches the red line.
            stop_trigger_margin_full_px=25.0,

            # After a hard stop, outward movement stays blocked until the
            # carriage has moved back toward the centre.
            fixed_release_margin_full_px=80.0,

            # Corrected mouse targets may approach close to each hard line.
            target_margin_full_px=30.0,

            heartbeat_interval_s=0.05,
            mouse_hold_s=0.40,

            # Stop immediately during a miss, but allow automatic local
            # reacquisition before requiring another carriage click.
            tracking_loss_frames_to_latch=30,

            # Perspective correction: carriage is placed ahead of the mouse
            # toward the left or right end of the eMaze.
            maze_length_mm=1500.0,
            maximum_perspective_offset_mm=180.0,
        )

        self.motor_status = "WAITING FOR CLICK"

        self.runCaptureTryExcept()

    def draw_fixed_pixel_safety(self):
        """Draw only the two visible red STOP boundaries."""
        if self.frame is None or self.automatic_motor is None:
            return

        frame_height, frame_width = self.frame.shape[:2]

        for x_position in (
            int(round(
                self.automatic_motor.fixed_left_stop_full_px
            )),
            int(round(
                self.automatic_motor.fixed_right_stop_full_px
            )),
        ):
            if 0 <= x_position < frame_width:
                cv2.line(
                    self.frame,
                    (x_position, 0),
                    (x_position, frame_height),
                    (0, 0, 255),
                    4,
                )

    def draw_perspective_diagnostics(self):
        """Show raw mouse, corrected target, and raw carriage positions."""
        if self.frame is None or self.automatic_motor is None:
            return

        frame_height, frame_width = self.frame.shape[:2]
        scale_to_full = 2.0

        raw_mouse_full = (
            self.automatic_motor.raw_mouse_x
            * scale_to_full
        )
        corrected_target_full = (
            self.automatic_motor.corrected_target_x
            * scale_to_full
        )
        carriage_raw_full = (
            self.automatic_motor.raw_carriage_x
            * scale_to_full
        )
        offset_full = (
            self.automatic_motor.perspective_offset_px
            * scale_to_full
        )

        def draw_vertical(
            x_value: float,
            colour: tuple[int, int, int],
            label: str,
            y_text: int,
        ) -> None:
            x = int(round(x_value))

            if not 0 <= x < frame_width:
                return

            cv2.line(
                self.frame,
                (x, 0),
                (x, frame_height),
                colour,
                2,
            )
            cv2.putText(
                self.frame,
                label,
                (max(2, x - 45), y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                colour,
                1,
                cv2.LINE_AA,
            )

        # Yellow: detected mouse.
        draw_vertical(
            raw_mouse_full,
            (0, 255, 255),
            "MOUSE",
            200,
        )

        # Cyan: perspective-corrected carriage target.
        draw_vertical(
            corrected_target_full,
            (255, 255, 0),
            "TARGET",
            225,
        )

        # Magenta: newest unsmoothed carriage position.
        draw_vertical(
            carriage_raw_full,
            (255, 0, 255),
            "CARRIAGE",
            250,
        )

        relation = (
            "TARGET LEFT OF MOUSE"
            if corrected_target_full < raw_mouse_full
            else
            "TARGET RIGHT OF MOUSE"
            if corrected_target_full > raw_mouse_full
            else
            "TARGET = MOUSE"
        )

        cv2.putText(
            self.frame,
            (
                f"MOUSE={raw_mouse_full:.1f}  "
                f"TARGET={corrected_target_full:.1f}  "
                f"CARRIAGE={carriage_raw_full:.1f}  "
                f"OFFSET={offset_full:+.1f}px  "
                f"{relation}"
            ),
            (250, 195),
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
        """Capture or re-capture the carriage template."""
        del flags, param

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if self.frame_lum is None:
            print("No camera frame available yet.")
            return

        processing_scale = 0.5

        processing_x = int(x * processing_scale)
        processing_y = int(y * processing_scale)

        # Fixed-only mode: every click initializes or re-initializes
        # the real carriage position.
        self.limit_click_mode = None

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

                current_motor_command = 0

                if self.automatic_motor is not None:
                    current_motor_command = int(
                        getattr(
                            self.automatic_motor,
                            "_desired_command",
                            0,
                        )
                    )

                # Arduino command polarity is mirrored relative to image X:
                # positive Arduino command moves image-left, while the
                # tracker expects positive direction to mean image-right.
                tracker_image_command = -current_motor_command

                self.rcCarriage.get_location(
                    self.frame_lum,
                    motor_command=tracker_image_command,
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

            # Keep only the two red motor stop lines on the video.
            self.draw_fixed_pixel_safety()

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

            if key == ord("[") or key == ord("]"):
                print(
                    "Speed zones are removed. Change "
                    "fixed_left_stop_full_px and "
                    "fixed_right_stop_full_px in VideoCapture.py."
                )

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