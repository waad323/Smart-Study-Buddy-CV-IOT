"""Unified Video Frame Streaming Engine.

Supports multiple input sources:
  1. 'webcam'   : Local USB / integrated webcams via OpenCV.
  2. 'esp32'    : ESP32-CAM MJPEG HTTP stream with boundary byte parsing.
  3. 'video'    : Prerecorded MP4/AVI video files for offline evaluation.
  4. 'synthetic': Procedural face simulator with blinking cycles for CI/CD.
"""

from abc import ABC, abstractmethod
import math
import time
from typing import Generator, Optional, Tuple
import cv2
import numpy as np
import requests


class BaseStreamer(ABC):
    @abstractmethod
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Retrieves next frame as (success_flag, bgr_image_array)."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Releases capture resources."""
        pass


class WebcamStreamer(BaseStreamer):
    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480):
        self.cap = cv2.VideoCapture(device_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if ret and frame is not None:
            frame = cv2.flip(frame, 1)  # Mirror view
            return True, frame
        return False, None

    def release(self) -> None:
        if self.cap.isOpened():
            self.cap.release()


class ESP32Streamer(BaseStreamer):
    """Parses JPEG byte chunks from ESP32-CAM HTTP endpoint."""

    def __init__(self, stream_url: str = "http://192.168.3.23/", timeout: int = 10):
        self.stream_url = stream_url
        self.timeout = timeout
        self.bytes_buffer = bytes()
        self.response = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.response = requests.get(self.stream_url, stream=True, timeout=self.timeout)
            if self.response.status_code != 200:
                print(f"[ESP32Streamer] Error: HTTP status {self.response.status_code}")
                self.response = None
        except Exception as e:
            print(f"[ESP32Streamer] Connection failed: {e}")
            self.response = None

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.response is None:
            return False, None

        try:
            for chunk in self.response.iter_content(chunk_size=1024):
                self.bytes_buffer += chunk

                start_idx = self.bytes_buffer.find(b'\xff\xd8')  # JPEG SOI
                end_idx = self.bytes_buffer.find(b'\xff\xd9')    # JPEG EOI

                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    jpg_data = self.bytes_buffer[start_idx:end_idx + 2]
                    self.bytes_buffer = self.bytes_buffer[end_idx + 2:]

                    frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        frame = cv2.flip(frame, 1)
                        return True, frame
        except Exception as e:
            print(f"[ESP32Streamer] Stream read error: {e}")
            return False, None

        return False, None

    def release(self) -> None:
        if self.response:
            try:
                self.response.close()
            except Exception:
                pass


class FileStreamer(BaseStreamer):
    def __init__(self, file_path: str):
        self.cap = cv2.VideoCapture(file_path)

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return ret, frame

    def release(self) -> None:
        if self.cap.isOpened():
            self.cap.release()


class SyntheticStreamer(BaseStreamer):
    """Generates procedural simulated frames with periodic blinking for testing & CI."""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.frame_idx = 0

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        self.frame_idx += 1
        canvas = np.full((self.height, self.width, 3), (35, 30, 25), dtype=np.uint8)

        # Draw head / face
        center = (self.width // 2, self.height // 2)
        cv2.ellipse(canvas, center, (120, 160), 0, 0, 360, (210, 190, 180), -1)

        # Periodic blinking simulation (blink every ~60 frames)
        blink_cycle = self.frame_idx % 70
        is_closed = 0 <= blink_cycle <= 6

        eye_y = center[1] - 20
        left_x, right_x = center[0] - 45, center[0] + 45

        eye_radius_y = 3 if is_closed else 14
        cv2.ellipse(canvas, (left_x, eye_y), (20, eye_radius_y), 0, 0, 360, (255, 255, 255), -1)
        cv2.ellipse(canvas, (right_x, eye_y), (20, eye_radius_y), 0, 0, 360, (255, 255, 255), -1)

        if not is_closed:
            # Irises
            cv2.circle(canvas, (left_x, eye_y), 7, (70, 50, 40), -1)
            cv2.circle(canvas, (right_x, eye_y), 7, (70, 50, 40), -1)

        # Mouth
        cv2.ellipse(canvas, (center[0], center[1] + 65), (35, 10), 0, 0, 180, (120, 80, 80), 3)

        time.sleep(0.03)  # Simulate ~30 FPS
        return True, canvas

    def release(self) -> None:
        pass


def create_streamer(source: str = "webcam", **kwargs) -> BaseStreamer:
    """Factory helper creating the appropriate streamer instance."""
    source_lower = source.lower()
    if source_lower == "esp32":
        url = kwargs.get("url", "http://192.168.3.23/")
        return ESP32Streamer(stream_url=url)
    elif source_lower in ("video", "file"):
        path = kwargs.get("path", "")
        return FileStreamer(file_path=path)
    elif source_lower == "synthetic":
        return SyntheticStreamer()
    else:
        dev_idx = int(kwargs.get("device_index", 0))
        return WebcamStreamer(device_index=dev_idx)
