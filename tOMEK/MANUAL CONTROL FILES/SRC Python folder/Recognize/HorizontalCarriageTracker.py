import cv2
import numpy as np


class HorizontalCarriageTracker:
    """
    Safety-limited, click-initialized template tracker.

    The carriage is initialized by clicking it once in the displayed camera
    image. Tracking is then restricted to a local horizontal search window
    around the last confirmed position.

    Important safety behaviour:
    - no global jumps to distant image locations;
    - X movement is limited per frame;
    - when confidence is low, the previous valid position is retained;
    - Y remains fixed because the carriage moves along one horizontal rail.
    """

    def __init__(
        self,
        template_width=32,
        template_height=26,
        search_margin_y=16,
        local_search_radius=110,
        maximum_step=24,
        smoothing=0.55,
        minimum_match=0.30,
        strong_match=0.58,
        template_update_rate=0.0,
        recovery_growth=45,
        maximum_recovery_radius=420
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

        self.template_gray = None
        self.template_blurred = None
        self.template_edges = None

        self.fixed_y = None
        self.search_y_min = None
        self.search_y_max = None

        self.px = 0.0
        self.py = 0.0
        self.oldLocation = []

        self.initialized = False
        self.detected = False
        self.last_match_score = None
        self.lost_frames = 0

    def initialize_from_click(self, frame_bgr, click_x, click_y):
        """
        Capture a carriage template centred on a click.

        click_x and click_y must refer to the half-resolution processing
        image used by VideoCapture.frame_lum.
        """
        patch = self._extract_patch(
            frame_bgr,
            float(click_x),
            float(click_y),
            self.template_width,
            self.template_height
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
            0
        )
        self.template_edges = self._prepare_edges(patch)

        frame_height = frame_bgr.shape[0]
        half_height = self.template_height // 2

        self.fixed_y = float(click_y)
        self.search_y_min = max(
            0,
            int(click_y) - half_height - self.search_margin_y
        )
        self.search_y_max = min(
            frame_height,
            int(click_y) + half_height + self.search_margin_y
        )

        self.px = float(click_x)
        self.py = float(click_y)
        self.oldLocation = (self.px, self.py)

        self.initialized = True
        self.detected = True
        self.last_match_score = 1.0
        self.lost_frames = 0

    def get_location(self, frame_bgr):
        if not self.initialized or self.template_gray is None:
            self.detected = False
            return self.px, self.py

        frame_height, frame_width = frame_bgr.shape[:2]

        y0 = max(0, int(self.search_y_min))
        y1 = min(frame_height, int(self.search_y_max))

        template_height, template_width = self.template_gray.shape[:2]
        half_template_width = template_width // 2

        # Search near the last confirmed X coordinate. If detection is
        # temporarily lost, expand the search radius progressively, but keep
        # the reported output position safety-limited.
        search_radius = min(
            self.maximum_recovery_radius,
            self.local_search_radius
            + self.lost_frames * self.recovery_growth
        )

        x0 = max(
            0,
            int(round(self.px)) - search_radius - half_template_width
        )
        x1 = min(
            frame_width,
            int(round(self.px)) + search_radius + half_template_width
        )

        roi = frame_bgr[y0:y1, x0:x1]

        if (
            roi.shape[0] < template_height
            or roi.shape[1] < template_width
        ):
            self.detected = False
            self.lost_frames += 1
            return self.px, self.py

        roi_gray = self._prepare_gray(roi)
        roi_blurred = cv2.GaussianBlur(
            roi_gray,
            (7, 7),
            0
        )
        roi_edges = self._prepare_edges(roi)

        gray_result = cv2.matchTemplate(
            roi_gray,
            self.template_gray,
            cv2.TM_CCOEFF_NORMED
        )

        blurred_result = cv2.matchTemplate(
            roi_blurred,
            self.template_blurred,
            cv2.TM_CCOEFF_NORMED
        )

        edge_result = cv2.matchTemplate(
            roi_edges,
            self.template_edges,
            cv2.TM_CCOEFF_NORMED
        )

        # Blurred matching helps when the carriage is less sharp on the
        # right side. Edges still contribute, but cannot dominate.
        combined_result = (
            0.42 * gray_result
            + 0.38 * blurred_result
            + 0.20 * edge_result
        )

        _, maximum_score, _, maximum_location = cv2.minMaxLoc(
            combined_result
        )

        self.last_match_score = float(maximum_score)

        required_match = self.minimum_match

        if self.lost_frames > 0:
            required_match = min(
                0.48,
                self.minimum_match + 0.025 * self.lost_frames
            )

        if maximum_score < required_match:
            # Never jump elsewhere when a reliable match is unavailable.
            self.detected = False
            self.lost_frames += 1
            return self.px, self.py

        measured_x = (
            x0
            + maximum_location[0]
            + template_width / 2.0
        )

        raw_delta = measured_x - self.px

        # Absolute safety limit: one frame can never move the reported
        # carriage position farther than maximum_step processing pixels.
        limited_delta = float(
            np.clip(
                raw_delta,
                -self.maximum_step,
                self.maximum_step
            )
        )

        safe_measured_x = self.px + limited_delta

        tracked_x = (
            (1.0 - self.smoothing) * self.px
            + self.smoothing * safe_measured_x
        )

        self.px = float(
            np.clip(tracked_x, 0, frame_width - 1)
        )
        self.py = float(self.fixed_y)
        self.oldLocation = (self.px, self.py)

        self.detected = True
        self.lost_frames = 0

        # Slowly adapt only during a strong, reliable match. This helps when
        # focus and illumination change gradually toward the right side.
        if (
            self.template_update_rate > 0.0
            and maximum_score >= self.strong_match
        ):
            current_patch = self._extract_patch(
                frame_bgr,
                self.px,
                self.fixed_y,
                self.template_width,
                self.template_height
            )

            if current_patch is not None:
                self._update_template(current_patch)

        return self.px, self.py

    def _update_template(self, patch_bgr):
        new_gray = self._prepare_gray(patch_bgr)
        new_blurred = cv2.GaussianBlur(
            new_gray,
            (7, 7),
            0
        )
        new_edges = self._prepare_edges(patch_bgr)

        rate = self.template_update_rate

        self.template_gray = cv2.addWeighted(
            self.template_gray,
            1.0 - rate,
            new_gray,
            rate,
            0
        )
        self.template_blurred = cv2.addWeighted(
            self.template_blurred,
            1.0 - rate,
            new_blurred,
            rate,
            0
        )
        self.template_edges = cv2.addWeighted(
            self.template_edges,
            1.0 - rate,
            new_edges,
            rate,
            0
        )

    @staticmethod
    def _extract_patch(
        frame_bgr,
        center_x,
        center_y,
        width,
        height
    ):
        frame_height, frame_width = frame_bgr.shape[:2]

        half_width = width // 2
        half_height = height // 2

        x0 = int(round(center_x)) - half_width
        y0 = int(round(center_y)) - half_height
        x1 = x0 + width
        y1 = y0 + height

        if (
            x0 < 0
            or y0 < 0
            or x1 > frame_width
            or y1 > frame_height
        ):
            return None

        patch = frame_bgr[y0:y1, x0:x1].copy()

        if (
            patch.size == 0
            or patch.shape[1] != width
            or patch.shape[0] != height
        ):
            return None

        return patch

    @staticmethod
    def _prepare_gray(image_bgr):
        gray = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2GRAY
        )

        # CLAHE is less aggressive than global histogram equalization and
        # behaves better when illumination changes across the rail.
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(4, 4)
        )
        gray = clahe.apply(gray)

        return cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )

    @staticmethod
    def _prepare_edges(image_bgr):
        gray = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2GRAY
        )
        gray = cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )
        return cv2.Canny(
            gray,
            25,
            90
        )