import cv2
import numpy as np


class HorizontalCarriageTracker:
    """LED-based horizontal carriage tracker for eMaze.

    Drop-in replacement for the current HorizontalCarriageTracker used by
    the automatic VideoCapture version.

    Main behaviour:
    - detects a GREEN LED by default (set led_color="blue" for blue),
    - automatically acquires the LED from the full frame,
    - tracks locally around the last carriage X,
    - if local tracking fails, searches the full width in the rail band,
    - automatically reacquires without a mouse click,
    - retains the known central commutator prediction bridge,
    - keeps the public attributes expected by the rest of eMaze.

    Coordinates are processing-image coordinates (half-resolution frame_lum
    in the current program).
    """

    def __init__(
        self,
        # Existing arguments retained for compatibility with VideoCapture.py
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
        weak_match_max_jump=28.0,
        strong_match_max_jump=48.0,
        maximum_reacquire_error=75.0,

        # LED settings
        led_color="green",  # change to "blue" for a blue LED
        green_h_min=35,
        green_h_max=95,
        blue_h_min=90,
        blue_h_max=140,
        led_s_min=70,
        led_v_min=110,
        channel_min=90,
        dominance_margin=20,
        led_min_area=2.0,
        led_max_area=450.0,
        led_max_width=45,
        led_max_height=45,
        auto_acquire_frames=3,
        auto_acquire_max_jump=35.0,
        rail_half_height=32,
        global_recovery=True,
        y_update_alpha=0.10,
        stable_frames_required=5,
    ):
        # Compatibility values
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
        self.reacquire_search_radius = int(reacquire_search_radius)
        self.reacquire_minimum_match = float(reacquire_minimum_match)
        self.weak_match_max_jump = float(weak_match_max_jump)
        self.strong_match_max_jump = float(strong_match_max_jump)
        self.maximum_reacquire_error = float(maximum_reacquire_error)

        # LED configuration
        self.led_color = str(led_color).lower().strip()
        if self.led_color not in ("green", "blue"):
            raise ValueError('led_color must be "green" or "blue"')

        self.green_h_min = int(green_h_min)
        self.green_h_max = int(green_h_max)
        self.blue_h_min = int(blue_h_min)
        self.blue_h_max = int(blue_h_max)
        self.led_s_min = int(led_s_min)
        self.led_v_min = int(led_v_min)
        self.channel_min = int(channel_min)
        self.dominance_margin = int(dominance_margin)
        self.led_min_area = float(led_min_area)
        self.led_max_area = float(led_max_area)
        self.led_max_width = int(led_max_width)
        self.led_max_height = int(led_max_height)
        self.auto_acquire_frames = max(1, int(auto_acquire_frames))
        self.auto_acquire_max_jump = float(auto_acquire_max_jump)
        self.rail_half_height = max(8, int(rail_half_height))
        self.global_recovery = bool(global_recovery)
        self.y_update_alpha = float(np.clip(y_update_alpha, 0.0, 1.0))
        self.stable_frames_required = max(1, int(stable_frames_required))

        # Occlusion bridge
        self.occlusion_left_x = float(occlusion_left_x)
        self.occlusion_right_x = float(occlusion_right_x)
        self.occlusion_entry_margin = float(occlusion_entry_margin)
        self.occlusion_exit_margin = float(occlusion_exit_margin)
        self.maximum_occlusion_frames = max(1, int(maximum_occlusion_frames))
        self.reacquire_grace_frames = max(1, int(reacquire_grace_frames))

        self.creep_prediction_step = float(creep_prediction_step)
        self.medium_prediction_step = float(medium_prediction_step)
        self.fast_prediction_step = float(fast_prediction_step)
        self.velocity_alpha = float(np.clip(velocity_alpha, 0.01, 1.0))
        self.minimum_prediction_step = float(minimum_prediction_step)
        self.maximum_prediction_step = float(maximum_prediction_step)

        # Public attributes used by eMaze
        self.px = 0.0
        self.py = 0.0
        self.raw_px = 0.0
        self.raw_py = 0.0
        self.last_raw_delta = 0.0
        self.oldLocation = []

        self.fixed_y = None
        self.search_y_min = None
        self.search_y_max = None

        self.initialized = False
        self.detected = False
        self.last_match_score = None
        self.lost_frames = 0
        self.prediction_only = False

        # Used by optional automatic re-arming in VideoCapture
        self.stable_detection_frames = 0
        self.auto_reacquired = False

        # Initial automatic acquisition state
        self._pending_x = None
        self._pending_y = None
        self._pending_frames = 0

        # Motion / occlusion state
        self.estimated_velocity = 0.0
        self.occlusion_active = False
        self.occlusion_direction = 0
        self.occlusion_frames = 0
        self.reacquire_frames = 0

        # Debug products
        self.last_mask = None
        self.last_candidate = None

        # Compatibility attributes from the old template tracker
        self.template_gray = None
        self.template_blurred = None
        self.template_edges = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize_from_click(self, frame_bgr, click_x, click_y):
        """Optional manual fallback: seed X/Y, then continue LED tracking."""
        frame_height, frame_width = frame_bgr.shape[:2]

        x = float(np.clip(click_x, 0, frame_width - 1))
        y = float(np.clip(click_y, 0, frame_height - 1))

        self.px = x
        self.py = y
        self.raw_px = x
        self.raw_py = y
        self.fixed_y = y
        self._update_rail_bounds(frame_height)

        self.oldLocation = (self.px, self.py)
        self.initialized = True
        self.detected = True
        self.last_match_score = 1.0
        self.lost_frames = 0
        self.stable_detection_frames = 0
        self.auto_reacquired = False
        self.estimated_velocity = 0.0
        self.occlusion_active = False
        self.occlusion_direction = 0
        self.occlusion_frames = 0
        self.reacquire_frames = 0
        self.prediction_only = False

    def get_location(self, frame_bgr, motor_command=0):
        """Return carriage (px, py), automatically acquiring/reacquiring LED."""
        self.auto_reacquired = False

        if frame_bgr is None or frame_bgr.size == 0:
            self._mark_lost()
            return self.px, self.py

        frame_height, frame_width = frame_bgr.shape[:2]

        # 1) No initialization -> search whole frame for a stable LED.
        if not self.initialized:
            candidate = self._find_led(
                frame_bgr,
                0,
                frame_width,
                0,
                frame_height,
                expected_x=None,
                expected_y=None,
            )

            if candidate is None:
                self.detected = False
                self.last_match_score = None
                self._pending_frames = 0
                return self.px, self.py

            cx, cy, quality, _ = candidate

            if (
                self._pending_x is not None
                and abs(cx - self._pending_x) <= self.auto_acquire_max_jump
                and abs(cy - self._pending_y) <= self.auto_acquire_max_jump
            ):
                self._pending_frames += 1
            else:
                self._pending_frames = 1

            self._pending_x = float(cx)
            self._pending_y = float(cy)

            if self._pending_frames < self.auto_acquire_frames:
                self.detected = False
                self.last_match_score = quality
                return self.px, self.py

            self._accept_direct_detection(
                frame_bgr,
                float(cx),
                float(cy),
                quality,
                snap=True,
            )
            self.initialized = True
            self.stable_detection_frames = 1
            print(
                "LED carriage automatically acquired at "
                f"x={self.raw_px:.1f}, y={self.raw_py:.1f}"
            )
            return self.px, self.py

        # 2) Normal local search around last LED X.
        local_x0 = max(0, int(round(self.raw_px)) - self.local_search_radius)
        local_x1 = min(
            frame_width,
            int(round(self.raw_px)) + self.local_search_radius,
        )
        y0, y1 = self._rail_bounds(frame_height)

        candidate = self._find_led(
            frame_bgr,
            local_x0,
            local_x1,
            y0,
            y1,
            expected_x=self.raw_px,
            expected_y=self.fixed_y,
        )

        # 3) Local search failed -> immediately search full width in rail band.
        if candidate is None and self.global_recovery:
            candidate = self._find_led(
                frame_bgr,
                0,
                frame_width,
                y0,
                y1,
                expected_x=self.raw_px,
                expected_y=self.fixed_y,
                distance_weight=0.15,
            )

        if candidate is not None:
            cx, cy, quality, _ = candidate
            was_lost = (
                not self.detected
                or self.lost_frames > 0
                or self.prediction_only
                or self.occlusion_active
            )

            self._accept_direct_detection(
                frame_bgr,
                float(cx),
                float(cy),
                quality,
                snap=was_lost,
            )

            if was_lost:
                self.auto_reacquired = True
                print(
                    "LED carriage automatically reacquired at "
                    f"x={self.raw_px:.1f}"
                )

            self.occlusion_active = False
            self.occlusion_direction = 0
            self.occlusion_frames = 0
            self.reacquire_frames = 0
            self.prediction_only = False
            return self.px, self.py

        # 4) LED missing. Only predict inside known commutator corridor.
        direction = (
            -1 if int(motor_command) < 0
            else 1 if int(motor_command) > 0
            else 0
        )

        if self._may_be_in_occlusion(direction):
            return self._predict_through_occlusion(
                frame_bgr,
                int(motor_command),
                direction,
            )

        # Everywhere else: report loss so the motor controller can STOP.
        self._mark_lost()
        return self.px, self.py

    # ------------------------------------------------------------------
    # LED detection
    # ------------------------------------------------------------------

    def _make_led_mask(self, roi_bgr):
        hsv = cv2.cvtColor(
            roi_bgr,
            cv2.COLOR_BGR2HSV
        )

        # Prześwietlona niebieska LED wygląda dla kamery jak biała.
        lower_led = np.array(
            [0, 0, 235],
            dtype=np.uint8
        )

        upper_led = np.array(
            [180, 45, 255],
            dtype=np.uint8
        )

        mask = cv2.inRange(
            hsv,
            lower_led,
            upper_led
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (3, 3)
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )

        return mask, hsv

    def _find_led(
        self,
        frame_bgr,
        x_min,
        x_max,
        y_min,
        y_max,
        expected_x=None,
        expected_y=None,
        distance_weight=0.45,
    ):
        frame_height, frame_width = frame_bgr.shape[:2]
        x0 = int(np.clip(x_min, 0, frame_width))
        x1 = int(np.clip(x_max, 0, frame_width))
        y0 = int(np.clip(y_min, 0, frame_height))
        y1 = int(np.clip(y_max, 0, frame_height))

        if x1 <= x0 or y1 <= y0:
            return None

        roi = frame_bgr[y0:y1, x0:x1]
        mask, hsv = self._make_led_mask(roi)
        self.last_mask = mask

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates = []

        for contour in contours:
            area = float(cv2.contourArea(contour))
            if not (self.led_min_area <= area <= self.led_max_area):
                continue

            rx, ry, rw, rh = cv2.boundingRect(contour)
            if rw <= 0 or rh <= 0:
                continue
            if rw > self.led_max_width or rh > self.led_max_height:
                continue

            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                continue

            local_cx = moments["m10"] / moments["m00"]
            local_cy = moments["m01"] / moments["m00"]
            cx = float(x0 + local_cx)
            cy = float(y0 + local_cy)

            contour_mask = np.zeros(mask.shape, dtype=np.uint8)
            cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
            _, mean_s, mean_v, _ = cv2.mean(hsv, mask=contour_mask)

            sat_q = np.clip(
                (mean_s - self.led_s_min) / max(1.0, 255 - self.led_s_min),
                0.0,
                1.0,
            )
            val_q = np.clip(
                (mean_v - self.led_v_min) / max(1.0, 255 - self.led_v_min),
                0.0,
                1.0,
            )
            visual_quality = float(0.5 * sat_q + 0.5 * val_q)

            penalty = 0.0
            if expected_x is not None:
                penalty += (
                    distance_weight
                    * abs(cx - float(expected_x))
                    / max(1.0, self.local_search_radius)
                )
            if expected_y is not None:
                penalty += (
                    0.35
                    * abs(cy - float(expected_y))
                    / max(1.0, self.rail_half_height)
                )

            ranking_score = visual_quality - penalty
            candidates.append(
                (
                    ranking_score,
                    cx,
                    cy,
                    visual_quality,
                    area,
                    (rx + x0, ry + y0, rw, rh),
                )
            )

        if not candidates:
            self.last_candidate = None
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        _, cx, cy, quality, area, bbox = candidates[0]

        self.last_candidate = {
            "x": cx,
            "y": cy,
            "quality": quality,
            "area": area,
            "bbox": bbox,
        }

        # Keep a high normalized confidence value for compatibility with
        # motor-control versions that inspect carriage_match_score.
        reported_quality = float(
            np.clip(0.70 + 0.29 * quality, 0.70, 0.99)
        )
        return cx, cy, reported_quality, area

    # ------------------------------------------------------------------
    # Accept / loss handling
    # ------------------------------------------------------------------

    def _accept_direct_detection(
        self,
        frame_bgr,
        measured_x,
        measured_y,
        quality,
        snap=False,
    ):
        previous_raw_x = float(self.raw_px)

        self.last_raw_delta = (
            float(measured_x) - previous_raw_x
            if self.initialized
            else 0.0
        )

        if self.initialized:
            self.estimated_velocity = (
                (1.0 - self.velocity_alpha) * self.estimated_velocity
                + self.velocity_alpha * self.last_raw_delta
            )
        else:
            self.estimated_velocity = 0.0

        self.raw_px = float(measured_x)
        self.raw_py = float(measured_y)

        if self.fixed_y is None:
            self.fixed_y = float(measured_y)
        else:
            self.fixed_y = (
                (1.0 - self.y_update_alpha) * self.fixed_y
                + self.y_update_alpha * float(measured_y)
            )

        self._update_rail_bounds(frame_bgr.shape[0])

        if snap or not self.initialized:
            self.px = self.raw_px
        else:
            delta = float(
                np.clip(
                    self.raw_px - self.px,
                    -self.maximum_step,
                    self.maximum_step,
                )
            )
            safe_measured = self.px + delta
            self.px = (
                (1.0 - self.smoothing) * self.px
                + self.smoothing * safe_measured
            )

        self.py = float(self.fixed_y)
        self.oldLocation = (self.px, self.py)
        self.initialized = True
        self.detected = True
        self.prediction_only = False
        self.last_match_score = float(quality)
        self.lost_frames = 0
        self.stable_detection_frames += 1

    def _mark_lost(self):
        self.detected = False
        self.prediction_only = False
        self.last_match_score = None
        self.lost_frames += 1
        self.stable_detection_frames = 0

    # ------------------------------------------------------------------
    # Central commutator prediction bridge
    # ------------------------------------------------------------------

    def _may_be_in_occlusion(self, direction):
        if direction == 0:
            return False
        left = self.occlusion_left_x - self.occlusion_entry_margin
        right = self.occlusion_right_x + self.occlusion_entry_margin
        return left <= self.raw_px <= right

    def _predict_through_occlusion(
        self,
        frame_bgr,
        motor_command,
        direction,
    ):
        if not self.occlusion_active:
            self.occlusion_active = True
            self.occlusion_direction = int(direction)
            self.occlusion_frames = 0
            self.reacquire_frames = 0
            print(
                "LED temporarily hidden in commutator corridor; "
                "using short prediction bridge."
            )

        if direction != 0:
            self.occlusion_direction = int(direction)

        direction = self.occlusion_direction
        self.occlusion_frames += 1

        if (
            direction == 0
            or self.occlusion_frames > self.maximum_occlusion_frames
        ):
            self.occlusion_active = False
            self._mark_lost()
            return self.px, self.py

        step = self._prediction_step(motor_command)
        predicted_x = float(
            np.clip(
                self.raw_px + direction * step,
                0,
                frame_bgr.shape[1] - 1,
            )
        )

        self.last_raw_delta = predicted_x - self.raw_px
        self.raw_px = predicted_x
        self.raw_py = float(self.fixed_y)
        self.px = predicted_x
        self.py = float(self.fixed_y)
        self.oldLocation = (self.px, self.py)

        # Same convention as the present tracker inside the known occlusion.
        self.detected = True
        self.prediction_only = True
        self.last_match_score = None
        self.lost_frames = 0
        self.stable_detection_frames = 0
        return self.px, self.py

    def _prediction_step(self, motor_command):
        speed_level = abs(int(motor_command))
        if speed_level >= 3:
            default_step = self.fast_prediction_step
        elif speed_level == 2:
            default_step = self.medium_prediction_step
        else:
            default_step = self.creep_prediction_step

        observed_step = abs(self.estimated_velocity)
        if observed_step < self.minimum_prediction_step:
            observed_step = default_step

        step = 0.55 * default_step + 0.45 * observed_step
        return float(
            np.clip(
                step,
                self.minimum_prediction_step,
                self.maximum_prediction_step,
            )
        )

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _update_rail_bounds(self, frame_height):
        if self.fixed_y is None:
            self.search_y_min = 0
            self.search_y_max = frame_height
            return

        self.search_y_min = max(
            0,
            int(round(self.fixed_y)) - self.rail_half_height,
        )
        self.search_y_max = min(
            frame_height,
            int(round(self.fixed_y)) + self.rail_half_height + 1,
        )

    def _rail_bounds(self, frame_height):
        if self.fixed_y is None:
            return 0, frame_height
        self._update_rail_bounds(frame_height)
        return int(self.search_y_min), int(self.search_y_max)
