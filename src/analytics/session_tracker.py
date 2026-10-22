"""Session Tracker and Fatigue Analytics Engine.

Calculates rolling blink rates, continuous eye closure durations,
focus percentages, and session telemetry metrics.
"""

from collections import deque
from dataclasses import dataclass, field
import json
import time
from typing import Any, Deque, Dict, List, Optional

from src.config import CONFIG, AppConfig


@dataclass
class SessionSnapshot:
    timestamp: float
    ear: float
    state: int
    blinks_total: int
    bpm: float
    focus_percentage: float
    is_drowsy_alert: bool
    is_absent_alert: bool


class SessionTracker:
    """Monitors ocular metrics and tracks user fatigue throughout a study session."""

    def __init__(self, config: AppConfig = CONFIG):
        self.config = config

        self.session_started = False
        self.start_time = 0.0
        self.total_frames = 0

        # State tracking
        self.current_state = config.STATE_FOCUSED
        self.last_face_time = time.time()
        self.closed_start_time: Optional[float] = None

        # Blink Detection
        self.total_blinks = 0
        self.blink_timestamps: Deque[float] = deque(maxlen=200)
        self.is_currently_blinking = False
        self.blink_start_time = 0.0

        # Cumulative time spent per state (seconds)
        self.state_durations: Dict[int, float] = {
            config.STATE_CLOSED: 0.0,
            config.STATE_DROWSY: 0.0,
            config.STATE_FOCUSED: 0.0,
            config.STATE_ABSENT: 0.0,
        }
        self.last_update_time = time.time()

        # Alert Counters
        self.drowsiness_alerts_count = 0
        self.absence_alerts_count = 0

        # Recent history buffer for visualization
        self.ear_history: Deque[float] = deque(maxlen=100)

    def start_session(self) -> None:
        """Starts or resets a study session."""
        self.session_started = True
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_face_time = self.start_time
        self.total_blinks = 0
        self.blink_timestamps.clear()
        self.drowsiness_alerts_count = 0
        self.absence_alerts_count = 0
        for k in self.state_durations:
            self.state_durations[k] = 0.0

    def stop_session(self) -> None:
        """Stops the active study session."""
        self.session_started = False

    def toggle_session(self) -> bool:
        """Toggles session active status."""
        if self.session_started:
            self.stop_session()
        else:
            self.start_session()
        return self.session_started

    def update(self, face_detected: bool, ear: float) -> SessionSnapshot:
        """Processes current frame telemetry and updates analytics state.

        Args:
            face_detected: True if MediaPipe detected a human face.
            ear: Average Eye Aspect Ratio.

        Returns:
            SessionSnapshot containing updated telemetry.
        """
        now = time.time()
        dt = max(0.001, now - self.last_update_time)
        self.last_update_time = now
        self.total_frames += 1

        is_drowsy_alert = False
        is_absent_alert = False

        if face_detected:
            self.last_face_time = now
            self.ear_history.append(ear)

            # 1. Blink Detection State Machine
            if ear < self.config.EAR_DROWSY_THRESHOLD:
                if not self.is_currently_blinking:
                    self.is_currently_blinking = True
                    self.blink_start_time = now
            else:
                if self.is_currently_blinking:
                    blink_duration = now - self.blink_start_time
                    if blink_duration <= self.config.MAX_BLINK_DURATION_SEC:
                        self.total_blinks += 1
                        self.blink_timestamps.append(now)
                    self.is_currently_blinking = False

            # 2. Continuous Eye Closure (Micro-sleep / Drowsiness Alarm)
            if ear < self.config.EAR_CLOSED_THRESHOLD:
                if self.closed_start_time is None:
                    self.closed_start_time = now
                elif now - self.closed_start_time >= self.config.DROWSINESS_ALERT_SEC:
                    is_drowsy_alert = True
                    self.current_state = self.config.STATE_CLOSED
            else:
                self.closed_start_time = None

            # 3. Categorize State if not in hard alarm
            if not is_drowsy_alert:
                if ear >= self.config.EAR_OPEN_THRESHOLD:
                    self.current_state = self.config.STATE_FOCUSED
                elif ear >= self.config.EAR_DROWSY_THRESHOLD:
                    self.current_state = self.config.STATE_DROWSY
                else:
                    self.current_state = self.config.STATE_CLOSED

        else:
            # No face detected in frame
            self.closed_start_time = None
            self.is_currently_blinking = False
            self.ear_history.append(0.0)

            if now - self.last_face_time >= self.config.NO_FACE_TIMEOUT_SEC:
                is_absent_alert = True
                self.current_state = self.config.STATE_ABSENT
            else:
                # Transitioning away
                self.current_state = self.config.STATE_DROWSY

        # Count alert triggers
        if is_drowsy_alert:
            self.drowsiness_alerts_count += 1
        if is_absent_alert:
            self.absence_alerts_count += 1

        # Accumulate state durations if session is active
        if self.session_started:
            self.state_durations[self.current_state] += dt

        # Calculate rolling Blinks Per Minute (BPM) in past 60 seconds
        cutoff = now - 60.0
        while self.blink_timestamps and self.blink_timestamps[0] < cutoff:
            self.blink_timestamps.popleft()
        bpm = float(len(self.blink_timestamps))

        # Calculate Focus Percentage
        total_time = sum(self.state_durations.values())
        focused_time = self.state_durations[self.config.STATE_FOCUSED]
        focus_pct = round((focused_time / total_time) * 100, 1) if total_time > 0 else 100.0

        return SessionSnapshot(
            timestamp=now,
            ear=ear,
            state=self.current_state,
            blinks_total=self.total_blinks,
            bpm=bpm,
            focus_percentage=focus_pct,
            is_drowsy_alert=is_drowsy_alert,
            is_absent_alert=is_absent_alert,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured session summary dictionary for reporting."""
        now = time.time()
        elapsed = now - self.start_time if self.session_started else 0.0
        total_time = sum(self.state_durations.values())
        focused_time = self.state_durations[self.config.STATE_FOCUSED]
        focus_pct = round((focused_time / total_time) * 100, 1) if total_time > 0 else 100.0

        return {
            "session_active": self.session_started,
            "session_duration_sec": round(elapsed, 1),
            "focus_percentage": focus_pct,
            "total_blinks": self.total_blinks,
            "drowsiness_alerts": self.drowsiness_alerts_count,
            "absence_alerts": self.absence_alerts_count,
            "state_durations_sec": {
                "focused": round(self.state_durations[self.config.STATE_FOCUSED], 1),
                "drowsy": round(self.state_durations[self.config.STATE_DROWSY], 1),
                "closed": round(self.state_durations[self.config.STATE_CLOSED], 1),
                "absent": round(self.state_durations[self.config.STATE_ABSENT], 1),
            },
        }

    def export_report(self, filepath: str) -> None:
        """Saves session summary to a JSON file."""
        summary = self.get_summary()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
