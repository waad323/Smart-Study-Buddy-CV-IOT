"""Real-Time Computer Vision HUD and Telemetry Renderer.

Overlays geometric contours, telemetry meters, attention badges,
and alert banners onto video frames using OpenCV drawing primitives.
"""

import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.analytics.session_tracker import SessionSnapshot
from src.config import CONFIG, AppConfig
from src.vision.face_mesh_detector import FaceDetectionResult


class HUDRenderer:
    """Renders professional telemetry HUD over video frames."""

    # Color Palette (BGR format)
    COLOR_BG_DARK = (20, 20, 25)
    COLOR_FOCUSED = (50, 205, 50)      # Lime / Emerald
    COLOR_DROWSY = (0, 215, 255)       # Amber / Gold
    COLOR_ALERT = (30, 30, 235)        # Crimson / Red
    COLOR_AWAY = (0, 140, 255)         # Orange
    COLOR_TEXT_WHITE = (245, 245, 245)
    COLOR_MUTED = (160, 160, 165)
    COLOR_ACCENT = (230, 140, 40)      # Electric Blue

    def __init__(self, config: AppConfig = CONFIG):
        self.config = config
        self.prev_frame_time = time.time()
        self.fps = 0.0

    def _update_fps(self) -> None:
        now = time.time()
        dt = now - self.prev_frame_time
        self.prev_frame_time = now
        if dt > 0:
            current_fps = 1.0 / dt
            self.fps = 0.9 * self.fps + 0.1 * current_fps  # Exponential smoothing

    def render(
        self,
        frame: np.ndarray,
        detection: FaceDetectionResult,
        snapshot: SessionSnapshot,
        session_active: bool,
        elapsed_sec: float,
    ) -> np.ndarray:
        """Draws complete telemetry overlay onto a copy of the frame.

        Args:
            frame: Input BGR frame.
            detection: FaceDetectionResult from FaceMesh.
            snapshot: Current SessionSnapshot telemetry.
            session_active: True if session timer is active.
            elapsed_sec: Session duration in seconds.

        Returns:
            Rendered BGR frame with visual overlays.
        """
        self._update_fps()
        canvas = frame.copy()
        h, w, _ = canvas.shape

        # 1. Draw Eye Contours and Landmarks
        if detection.detected:
            # Draw eye polygon contours
            if len(detection.left_eye_pts) == 6:
                pts_l = np.array(detection.left_eye_pts, dtype=np.int32)
                cv2.polylines(canvas, [pts_l], True, self.COLOR_ACCENT, 1, cv2.LINE_AA)
                for pt in detection.left_eye_pts:
                    cv2.circle(canvas, pt, 2, self.COLOR_TEXT_WHITE, -1, cv2.LINE_AA)

            if len(detection.right_eye_pts) == 6:
                pts_r = np.array(detection.right_eye_pts, dtype=np.int32)
                cv2.polylines(canvas, [pts_r], True, self.COLOR_ACCENT, 1, cv2.LINE_AA)
                for pt in detection.right_eye_pts:
                    cv2.circle(canvas, pt, 2, self.COLOR_TEXT_WHITE, -1, cv2.LINE_AA)

        # 2. Semi-Transparent Top Telemetry Header
        header_h = 75
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (w, header_h), self.COLOR_BG_DARK, -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)
        cv2.line(canvas, (0, header_h), (w, header_h), (60, 60, 70), 1, cv2.LINE_AA)

        # 3. Status Badge (Top-Left)
        state_configs = {
            self.config.STATE_FOCUSED: ("FOCUSED", self.COLOR_FOCUSED),
            self.config.STATE_DROWSY: ("DROWSY", self.COLOR_DROWSY),
            self.config.STATE_CLOSED: ("EYES CLOSED", self.COLOR_ALERT),
            self.config.STATE_ABSENT: ("AWAY", self.COLOR_AWAY),
        }
        badge_text, badge_color = state_configs.get(snapshot.state, ("UNKNOWN", self.COLOR_MUTED))

        # Badge pill
        cv2.rectangle(canvas, (14, 14), (160, 58), badge_color, 2, cv2.LINE_AA)
        cv2.circle(canvas, (32, 36), 6, badge_color, -1, cv2.LINE_AA)
        cv2.putText(canvas, badge_text, (48, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.62, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

        # 4. EAR Meter Gauge (Center-Left)
        ear_text = f"EAR: {snapshot.ear:.3f}" if detection.detected else "EAR: --"
        cv2.putText(canvas, ear_text, (180, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        # Mini horizontal bar for EAR
        bar_x, bar_y, bar_w, bar_h = 180, 42, 120, 10
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 70), -1)
        fill_ratio = min(1.0, max(0.0, (snapshot.ear - 0.10) / 0.25))
        fill_w = int(bar_w * fill_ratio)
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), badge_color, -1)

        # 5. Session Status & Timer (Center)
        mins = int(elapsed_sec // 60)
        secs = int(elapsed_sec % 60)
        session_str = f"SESSION: {mins:02d}:{secs:02d}" if session_active else "SESSION: PAUSED [Press S]"
        sess_color = self.COLOR_FOCUSED if session_active else self.COLOR_MUTED
        cv2.putText(canvas, session_str, (325, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, sess_color, 1, cv2.LINE_AA)

        focus_str = f"Focus Score: {snapshot.focus_percentage:.1f}%"
        cv2.putText(canvas, focus_str, (325, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.50, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        # 6. Blinks & Fatigue Metrics (Top-Right)
        blink_str = f"Blinks: {snapshot.blinks_total} ({snapshot.bpm:.0f}/min)"
        cv2.putText(canvas, blink_str, (w - 200, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.50, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        fps_str = f"FPS: {self.fps:.1f}"
        cv2.putText(canvas, fps_str, (w - 200, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_MUTED, 1, cv2.LINE_AA)

        # 7. Big Alert Banner on Drowsiness or Absence
        if snapshot.is_drowsy_alert:
            self._render_alert_box(canvas, "DROWSINESS DETECTED - WAKE UP!", self.COLOR_ALERT)
        elif snapshot.is_absent_alert:
            self._render_alert_box(canvas, "DISTRACTION DETECTED - PLEASE RETURN", self.COLOR_AWAY)

        return canvas

    def _render_alert_box(self, canvas: np.ndarray, message: str, color: Tuple[int, int, int]) -> None:
        """Renders an eye-catching pulsing alert notification box."""
        h, w, _ = canvas.shape
        box_w, box_h = min(560, w - 40), 65
        x = (w - box_w) // 2
        y = h - 100

        overlay = canvas.copy()
        cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h), color, -1)
        cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)
        cv2.rectangle(canvas, (x, y), (x + box_w, y + box_h), (255, 255, 255), 2, cv2.LINE_AA)

        text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.70, 2)[0]
        text_x = x + (box_w - text_size[0]) // 2
        text_y = y + (box_h + text_size[1]) // 2
        cv2.putText(canvas, message, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)
