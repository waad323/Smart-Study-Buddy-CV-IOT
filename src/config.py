"""Global Configuration and Telemetry Parameters.

Defines Eye Aspect Ratio (EAR) mathematical thresholds, drowsiness timeouts,
hardware baud rates, and application settings.
"""

from dataclasses import dataclass
import os


@dataclass
class AppConfig:
    # --------------------------
    # Vision & EAR Thresholds
    # --------------------------
    EAR_OPEN_THRESHOLD: float = 0.25       # EAR above this indicates open, alert eyes
    EAR_DROWSY_THRESHOLD: float = 0.20     # EAR between 0.18 and 0.25 indicates half-blink / fatigue
    EAR_CLOSED_THRESHOLD: float = 0.18     # EAR below this indicates closed eyes

    # --------------------------
    # Temporal Alert Thresholds
    # --------------------------
    DROWSINESS_ALERT_SEC: float = 1.8      # Continuous eyes closed duration to trigger alarm
    NO_FACE_TIMEOUT_SEC: float = 15.0      # Continuous absence duration to trigger distraction alert
    MAX_BLINK_DURATION_SEC: float = 0.4    # Max time for an involuntary normal blink

    # --------------------------
    # State Enum Definitions
    # --------------------------
    STATE_CLOSED: int = 0                  # Eyes Closed (Alarm)
    STATE_DROWSY: int = 1                  # Drowsy / Half-Blink (Warning)
    STATE_FOCUSED: int = 2                 # Focused / Eyes Open (Healthy)
    STATE_ABSENT: int = 3                  # Away / No Face (Distracted Alarm)

    # --------------------------
    # Hardware & Network Setup
    # --------------------------
    SERIAL_PORT: str = os.environ.get('STUDY_BUDDY_PORT', 'COM4')
    BAUD_RATE: int = 115200
    DEFAULT_STREAM_URL: str = os.environ.get('ESP32_STREAM_URL', 'http://192.168.3.23/')

    # --------------------------
    # Display Settings
    # --------------------------
    WINDOW_TITLE: str = "Smart Study Buddy & Drowsiness Monitor"
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 480


CONFIG = AppConfig()
