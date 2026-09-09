import cv2
import numpy as np


class HorizontalCarriageTracker:
    """
    Responsive click-initialized carriage tracker with a controlled
    commutator-occlusion bridge.

    Normal behaviour:
    - local horizontal template search around the latest carriage position;
    - no global/expanding recovery search;
    - smoothed px for ordinary following;
    - raw_px for motor safety.

    Known central occlusion:
    - while the carriage passes below the commutator, it may be invisible;
    - only inside the configured occlusion corridor, position is predicted
      from the previous motor command and recent measured velocity;
    - the predicted position continues through the hidden area;
    - after leaving the corridor, the real template must be reacquired;
    - failure to reacquire shortly after leaving makes detected=False.

    Coordinates passed to this class are processing-image coordinates.
    In the current program, the processing image is half full resolution.
    """

    def __init__(
        self,
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

        # Known commutator occlusion corridor in processing pixels.
        occlusion_left_x=400,
        occlusion_right_x=565,
        occlusion_entry_margin=18,
        occlusion_exit_margin=22,

        # Prediction and reacquisition.
        maximum_occlusion_frames=40,
        reacquire_grace_frames=12,
        reacquire_search_radius=220,
        reacquire_minimum_match=0.24,

        # Default processing-pixel travel per frame.
        creep_prediction_step=2.5,
        medium_prediction_step=5.0,
        fast_prediction_step=9.0,

        velocity_alpha=0.55,
        minimum_prediction_step=1.5,
        maximum_prediction_step=18.0,

        # Reject a false match that suddenly appears far from the last
        # physically plausible carriage position.
        weak_match_max_jump=28.0,
        strong_match_max_jump=48.0,
        maximum_reacquire_error=75.0,
    ):
        self.template_width = int(template_width)
        self.template_height = int(template_height)
        self.search_margin_y = int(search_margin_y)

        self.local_search_radius = int(local_search_radius)
        self.maximum_step = float(maximum_step)

        self.smoothing = float(smoothing)
        self.minimum_match = float(minimum_match)
        self.strong_match = float(strong_match)
        self.template_update_rate = float(template_update_rate)
        self.recovery_growth = int(recovery_growth)
        self.maximum_recovery_radius = int(maximum_recovery_radius)

        self.occlusion_left_x = float(occlusion_left_x)
        self.occlusion_right_x = float(occlusion_right_x)

        if self.occlusion_right_x <= self.occlusion_left_x:
            raise ValueError(
                "occlusion_right_x must be greater than occlusion_left_x"
            )

        self.occlusion_entry_margin = max(
            0.0,
            float(occlusion_entry_margin),
        )
        self.occlusion_exit_margin = max(
            0.0,
            float(occlusion_exit_margin),
        )

        self.maximum_occlusion_frames = max(
            1,
            int(maximum_occlusion_frames),
        )
        self.reacquire_grace_frames = max(
            1,
            int(reacquire_grace_frames),
        )
        self.reacquire_search_radius = max(
            self.local_search_radius,
            int(reacquire_search_radius),
        )
        self.reacquire_minimum_match = float(
            reacquire_minimum_match
        )

        self.creep_prediction_step = max(
            0.1,
            float(creep_prediction_step),
        )
        self.medium_prediction_step = max(
            self.creep_prediction_step,
            float(medium_prediction_step),
        )
        self.fast_prediction_step = max(
            self.medium_prediction_step,
            float(fast_prediction_step),
        )

        self.velocity_alpha = min(
            1.0,
            max(0.01, float(velocity_alpha)),
        )
        self.minimum_prediction_step = max(
            0.1,
            float(minimum_prediction_step),
        )
        self.maximum_prediction_step = max(
            self.minimum_prediction_step,
            float(maximum_prediction_step),
        )

        self.weak_match_max_jump = max(
            8.0,
            float(weak_match_max_jump),
        )
        self.strong_match_max_jump = max(
            self.weak_match_max_jump,
            float(strong_match_max_jump),
        )
        self.maximum_reacquire_error = max(
            self.strong_match_max_jump,
            float(maximum_reacquire_error),
        )

        self.template_gray = None
        self.template_blurred = None
        self.template_edges = None

        self.fixed_y = None
        self.search_y_min = None
        self.search_y_max = None

        self.px = 0.0
        self.py = 0.0

        self.raw_px = 0.0
        self.raw_py = 0.0
        self.last_raw_delta = 0.0

        self.oldLocation = []

        self.initialized = False
        self.detected = False
        self.last_match_score = None
        self.lost_frames = 0

        self.estimated_velocity = 0.0

        self.occlusion_active = False
        self.occlusion_direction = 0
        self.occlusion_frames = 0
        self.reacquire_frames = 0
        self.prediction_only = False

    def initialize_from_click(
        self,
        frame_bgr,
        click_x,
        click_y,
    ):
        patch = self._extract_patch(
            frame_bgr,
            float(click_x),
            float(click_y),
            self.template_width,
            self.template_height,
        )

        if patch is None:
            self.initialized = False
            self.detected = False
            raise ValueError(
                "Could not capture the carriage template at this position."
            )

        self.template_gray = self._prepare_gray(patch)
        self.template_blurred = cv2.GaussianBlur(
            self.template_gray,
            (7, 7),
            0,
        )
        self.template_edges = self._prepare_edges(patch)

        frame_height = frame_bgr.shape[0]
        half_height = self.template_height // 2

        self.fixed_y = float(click_y)
        self.search_y_min = max(
            0,
            int(click_y)
            - half_height
            - self.search_margin_y,
        )
        self.search_y_max = min(
            frame_height,
            int(click_y)
            + half_height
            + self.search_margin_y,
        )

        self.px = float(click_x)
        self.py = float(click_y)
        self.raw_px = float(click_x)
        self.raw_py = float(click_y)
        self.last_raw_delta = 0.0
        self.oldLocation = (self.px, self.py)

        self.initialized = True
        self.detected = True
        self.last_match_score = 1.0
        self.lost_frames = 0

        self.estimated_velocity = 0.0

        self.occlusion_active = False
        self.occlusion_direction = 0
        self.occlusion_frames = 0
        self.reacquire_frames = 0
        self.prediction_only = False

    def get_location(
        self,
        frame_bgr,
        motor_command=0,
    ):
        if not self.initialized or self.template_gray is None:
            self.detected = False
            return self.px, self.py

        motor_command = int(motor_command)

        command_direction = (
            -1
            if motor_command < 0
            else 1
            if motor_command > 0
            else 0
        )

        if self.occlusion_active:
            return self._continue_occlusion(
                frame_bgr=frame_bgr,
                motor_command=motor_command,
                command_direction=command_direction,
            )

        if self._should_enter_occlusion(command_direction):
            self._start_occlusion(command_direction)

            return self._continue_occlusion(
                frame_bgr=frame_bgr,
                motor_command=motor_command,
                command_direction=command_direction,
            )

        match = self._find_match(
            frame_bgr=frame_bgr,
            centre_x=self.raw_px,
            search_radius=self.local_search_radius,
            minimum_match=self.minimum_match,
        )

        if match is None:
            # A match may disappear just before the last visible edge of
            # the commutator. Begin prediction only when position and motor
            # direction show that it is entering the known corridor.
            if self._near_occlusion_entry(command_direction):
                self._start_occlusion(command_direction)

                return self._continue_occlusion(
                    frame_bgr=frame_bgr,
                    motor_command=motor_command,
                    command_direction=command_direction,
                )

            self.detected = False
            self.prediction_only = False
            self.lost_frames += 1
            return self.px, self.py

        measured_x, maximum_score = match

        if not self._measurement_is_plausible(
            measured_x=measured_x,
            maximum_score=maximum_score,
        ):
            self.detected = False
            self.prediction_only = False
            self.lost_frames += 1

            print(
                "Carriage false match rejected: "
                f"candidate_x={measured_x:.1f}, "
                f"last_x={self.raw_px:.1f}, "
                f"score={maximum_score:.3f}"
            )
            return self.px, self.py

        self._accept_measurement(
            frame_bgr=frame_bgr,
            measured_x=measured_x,
            maximum_score=maximum_score,
        )

        return self.px, self.py

    def _should_enter_occlusion(
        self,
        command_direction,
    ):
        if command_direction > 0:
            return (
                self.raw_px
                >= self.occlusion_left_x
                - self.occlusion_entry_margin
                and
                self.raw_px
                <= self.occlusion_right_x
            )

        if command_direction < 0:
            return (
                self.raw_px
                <= self.occlusion_right_x
                + self.occlusion_entry_margin
                and
                self.raw_px
                >= self.occlusion_left_x
            )

        return False

    def _near_occlusion_entry(
        self,
        command_direction,
    ):
        wider_margin = self.occlusion_entry_margin + 35.0

        if command_direction > 0:
            return (
                self.raw_px
                >= self.occlusion_left_x - wider_margin
                and
                self.raw_px
                < self.occlusion_right_x
            )

        if command_direction < 0:
            return (
                self.raw_px
                <= self.occlusion_right_x + wider_margin
                and
                self.raw_px
                > self.occlusion_left_x
            )

        return False

    def _start_occlusion(
        self,
        direction,
    ):
        if direction == 0:
            return

        self.occlusion_active = True
        self.occlusion_direction = int(direction)
        self.occlusion_frames = 0
        self.reacquire_frames = 0
        self.prediction_only = True
        self.lost_frames = 0

        print(
            "Carriage entering commutator occlusion: "
            f"direction={self.occlusion_direction}"
        )

    def _continue_occlusion(
        self,
        frame_bgr,
        motor_command,
        command_direction,
    ):
        if command_direction != 0:
            self.occlusion_direction = command_direction

        direction = self.occlusion_direction

        if direction == 0:
            # The motor is stopped while the carriage is hidden. Hold the
            # last predicted position rather than inventing movement.
            self.detected = True
            self.prediction_only = True
            self.last_match_score = None
            return self.px, self.py

        self.occlusion_frames += 1

        if self.occlusion_frames > self.maximum_occlusion_frames:
            self._fail_occlusion(
                "maximum hidden duration exceeded"
            )
            return self.px, self.py

        prediction_step = self._prediction_step(
            motor_command=motor_command,
        )

        predicted_x = (
            self.raw_px
            + direction * prediction_step
        )

        frame_width = frame_bgr.shape[1]

        predicted_x = float(
            np.clip(
                predicted_x,
                0,
                frame_width - 1,
            )
        )

        self.last_raw_delta = (
            predicted_x - self.raw_px
        )
        self.raw_px = predicted_x
        self.raw_py = float(self.fixed_y)

        # During the hidden section, move the control position with the
        # prediction. Do not apply the normal lagging display smoothing.
        self.px = predicted_x
        self.py = float(self.fixed_y)
        self.oldLocation = (self.px, self.py)

        self.detected = True
        self.prediction_only = True
        self.last_match_score = None
        self.lost_frames = 0

        left_exit = (
            self.occlusion_left_x
            - self.occlusion_exit_margin
        )
        right_exit = (
            self.occlusion_right_x
            + self.occlusion_exit_margin
        )

        still_hidden = (
            left_exit <= self.raw_px <= right_exit
        )

        if still_hidden:
            return self.px, self.py

        # The prediction has emerged from the far side. The actual carriage
        # now has to be found close to the predicted location.
        match = self._find_match(
            frame_bgr=frame_bgr,
            centre_x=self.raw_px,
            search_radius=self.reacquire_search_radius,
            minimum_match=self.reacquire_minimum_match,
        )

        if match is not None:
            measured_x, maximum_score = match

            maximum_reacquire_error = min(
                self.maximum_reacquire_error,
                self.reacquire_search_radius * 0.45,
            )

            if (
                abs(measured_x - self.raw_px)
                <= maximum_reacquire_error
            ):
                self._accept_measurement(
                    frame_bgr=frame_bgr,
                    measured_x=measured_x,
                    maximum_score=maximum_score,
                )

                self.occlusion_active = False
                self.occlusion_direction = 0
                self.occlusion_frames = 0
                self.reacquire_frames = 0
                self.prediction_only = False

                print(
                    "Carriage reacquired after commutator."
                )

                return self.px, self.py

        self.reacquire_frames += 1

        if self.reacquire_frames > self.reacquire_grace_frames:
            self._fail_occlusion(
                "not reacquired after leaving commutator"
            )

        return self.px, self.py

    def _fail_occlusion(
        self,
        reason,
    ):
        self.detected = False
        self.prediction_only = False
        self.occlusion_active = False
        self.occlusion_direction = 0
        self.lost_frames += 1

        print(
            "Carriage occlusion bridge failed: "
            f"{reason}"
        )

    def _prediction_step(
        self,
        motor_command,
    ):
        speed_level = abs(int(motor_command))

        if speed_level >= 3:
            default_step = self.fast_prediction_step
        elif speed_level == 2:
            default_step = self.medium_prediction_step
        else:
            default_step = self.creep_prediction_step

        observed_step = abs(
            self.estimated_velocity
        )

        if observed_step < self.minimum_prediction_step:
            step = default_step
        else:
            # The recent measured velocity is useful, but do not allow a
            # single noisy frame to create an excessive blind prediction.
            step = (
                0.60 * observed_step
                + 0.40 * default_step
            )

        return float(
            np.clip(
                step,
                self.minimum_prediction_step,
                self.maximum_prediction_step,
            )
        )

    def _find_match(
        self,
        frame_bgr,
        centre_x,
        search_radius,
        minimum_match,
    ):
        frame_height, frame_width = frame_bgr.shape[:2]

        y0 = max(0, int(self.search_y_min))
        y1 = min(frame_height, int(self.search_y_max))

        template_height, template_width = (
            self.template_gray.shape[:2]
        )
        half_template_width = template_width // 2

        x0 = max(
            0,
            int(round(centre_x))
            - int(search_radius)
            - half_template_width,
        )
        x1 = min(
            frame_width,
            int(round(centre_x))
            + int(search_radius)
            + half_template_width,
        )

        roi = frame_bgr[y0:y1, x0:x1]

        if (
            roi.shape[0] < template_height
            or roi.shape[1] < template_width
        ):
            return None

        roi_gray = self._prepare_gray(roi)
        roi_blurred = cv2.GaussianBlur(
            roi_gray,
            (7, 7),
            0,
        )
        roi_edges = self._prepare_edges(roi)

        gray_result = cv2.matchTemplate(
            roi_gray,
            self.template_gray,
            cv2.TM_CCOEFF_NORMED,
        )
        blurred_result = cv2.matchTemplate(
            roi_blurred,
            self.template_blurred,
            cv2.TM_CCOEFF_NORMED,
        )
        edge_result = cv2.matchTemplate(
            roi_edges,
            self.template_edges,
            cv2.TM_CCOEFF_NORMED,
        )

        combined_result = (
            0.42 * gray_result
            + 0.38 * blurred_result
            + 0.20 * edge_result
        )

        (
            _minimum_score,
            maximum_score,
            _minimum_location,
            maximum_location,
        ) = cv2.minMaxLoc(combined_result)

        self.last_match_score = float(
            maximum_score
        )

        if maximum_score < float(minimum_match):
            return None

        measured_x = (
            x0
            + maximum_location[0]
            + template_width / 2.0
        )

        return float(measured_x), float(maximum_score)

    def _measurement_is_plausible(
        self,
        measured_x,
        maximum_score,
    ):
        jump = abs(
            float(measured_x) - float(self.raw_px)
        )

        allowed_jump = (
            self.strong_match_max_jump
            if float(maximum_score) >= self.strong_match
            else self.weak_match_max_jump
        )

        return jump <= allowed_jump

    def _accept_measurement(
        self,
        frame_bgr,
        measured_x,
        maximum_score,
    ):
        frame_width = frame_bgr.shape[1]

        previous_raw_x = self.raw_px
        measured_delta = (
            float(measured_x) - previous_raw_x
        )

        self.last_raw_delta = measured_delta

        self.estimated_velocity = (
            (1.0 - self.velocity_alpha)
            * self.estimated_velocity
            + self.velocity_alpha
            * measured_delta
        )

        self.estimated_velocity = float(
            np.clip(
                self.estimated_velocity,
                -self.maximum_prediction_step,
                self.maximum_prediction_step,
            )
        )

        self.raw_px = float(
            np.clip(
                measured_x,
                0,
                frame_width - 1,
            )
        )
        self.raw_py = float(self.fixed_y)

        raw_delta = measured_x - self.px

        limited_delta = float(
            np.clip(
                raw_delta,
                -self.maximum_step,
                self.maximum_step,
            )
        )

        safe_measured_x = (
            self.px + limited_delta
        )

        tracked_x = (
            (1.0 - self.smoothing)
            * self.px
            + self.smoothing
            * safe_measured_x
        )

        self.px = float(
            np.clip(
                tracked_x,
                0,
                frame_width - 1,
            )
        )
        self.py = float(self.fixed_y)
        self.oldLocation = (
            self.px,
            self.py,
        )

        self.detected = True
        self.prediction_only = False
        self.last_match_score = float(
            maximum_score
        )
        self.lost_frames = 0

        if (
            self.template_update_rate > 0.0
            and maximum_score >= self.strong_match
        ):
            current_patch = self._extract_patch(
                frame_bgr,
                self.raw_px,
                self.fixed_y,
                self.template_width,
                self.template_height,
            )

            if current_patch is not None:
                self._update_template(
                    current_patch
                )

    def _update_template(
        self,
        patch_bgr,
    ):
        new_gray = self._prepare_gray(
            patch_bgr
        )
        new_blurred = cv2.GaussianBlur(
            new_gray,
            (7, 7),
            0,
        )
        new_edges = self._prepare_edges(
            patch_bgr
        )

        rate = self.template_update_rate

        self.template_gray = cv2.addWeighted(
            self.template_gray,
            1.0 - rate,
            new_gray,
            rate,
            0,
        )
        self.template_blurred = cv2.addWeighted(
            self.template_blurred,
            1.0 - rate,
            new_blurred,
            rate,
            0,
        )
        self.template_edges = cv2.addWeighted(
            self.template_edges,
            1.0 - rate,
            new_edges,
            rate,
            0,
        )

    @staticmethod
    def _extract_patch(
        frame_bgr,
        center_x,
        center_y,
        width,
        height,
    ):
        frame_height, frame_width = (
            frame_bgr.shape[:2]
        )

        half_width = width // 2
        half_height = height // 2

        x0 = (
            int(round(center_x))
            - half_width
        )
        y0 = (
            int(round(center_y))
            - half_height
        )
        x1 = x0 + width
        y1 = y0 + height

        if (
            x0 < 0
            or y0 < 0
            or x1 > frame_width
            or y1 > frame_height
        ):
            return None

        patch = frame_bgr[
            y0:y1,
            x0:x1,
        ].copy()

        if (
            patch.size == 0
            or patch.shape[1] != width
            or patch.shape[0] != height
        ):
            return None

        return patch

    @staticmethod
    def _prepare_gray(
        image_bgr,
    ):
        gray = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2GRAY,
        )

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(4, 4),
        )
        gray = clahe.apply(gray)

        return cv2.GaussianBlur(
            gray,
            (3, 3),
            0,
        )

    @staticmethod
    def _prepare_edges(
        image_bgr,
    ):
        gray = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2GRAY,
        )
        gray = cv2.GaussianBlur(
            gray,
            (5, 5),
            0,
        )

        return cv2.Canny(
            gray,
            25,
            90,
        )