"""ESP32 Serial Communication Controller.

Manages bidirectional UART serial transport between host PC and ESP32 microcontroller.
Features automatic reconnects, mock fallback when hardware is absent,
and thread-safe state dispatch.
"""

import logging
import time
from typing import Callable, Optional
import serial

logger = logging.getLogger(__name__)


class SerialController:
    """Manages serial connection to ESP32 Study Buddy hardware."""

    def __init__(
        self,
        port: str = "COM4",
        baud_rate: int = 115200,
        timeout: float = 0.5,
        on_session_start: Optional[Callable[[], None]] = None,
        on_session_stop: Optional[Callable[[], None]] = None,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.on_session_start = on_session_start
        self.on_session_stop = on_session_stop

        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.last_sent_state: Optional[int] = None

        self._connect()

    def _connect(self) -> None:
        """Attempts to establish connection with serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            time.sleep(1.5)  # Allow ESP32 reboot sequence
            self.is_connected = True
            logger.info(f"[SerialController] Connected successfully to ESP32 on {self.port} at {self.baud_rate} baud.")
        except Exception as e:
            logger.warning(f"[SerialController] Hardware not detected on {self.port}: {e}. Standalone CV mode active.")
            self.ser = None
            self.is_connected = False

    def send_focus_state(self, state: int) -> bool:
        """Transmits single-byte focus state (0=Closed, 1=Drowsy, 2=Open, 3=Absent)."""
        if not self.is_connected or not self.ser:
            return False

        # Only transmit when state changes or on periodic refresh
        try:
            self.ser.write(bytes([state]))
            self.last_sent_state = state
            return True
        except Exception as e:
            logger.error(f"[SerialController] Failed to transmit state byte: {e}")
            self.is_connected = False
            return False

    def poll_hardware_events(self) -> Optional[str]:
        """Reads inbound serial strings from ESP32 push buttons or telemetry."""
        if not self.is_connected or not self.ser:
            return None

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if "SESSION_START" in line:
                    logger.info("[SerialController] Physical START button triggered on hardware!")
                    if self.on_session_start:
                        self.on_session_start()
                    return "SESSION_START"
                elif "SESSION_STOP" in line:
                    logger.info("[SerialController] Physical STOP button triggered on hardware!")
                    if self.on_session_stop:
                        self.on_session_stop()
                    return "SESSION_STOP"
                return line
        except Exception as e:
            logger.debug(f"[SerialController] Inbound read error: {e}")
        return None

    def close(self) -> None:
        """Closes serial port gracefully."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.is_connected = False
