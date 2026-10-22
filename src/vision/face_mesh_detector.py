"""MediaPipe FaceMesh and FaceLandmarker Universal Detection Wrapper.

Supports both the modern Google MediaPipe Tasks API (`FaceLandmarker`) and the
legacy `mp.solutions.face_mesh` API for complete cross-version compatibility
(Python 3.10 through 3.14+).
"""

from dataclasses import dataclass
import logging
import os
from typing import List, Optional, Tuple
import urllib.request
import cv2
import numpy as np

from src.vision.ear_calculator import LEFT_EYE_LANDMARKS, RIGHT_EYE_LANDMARKS, calculate_average_ear

logger = logging.getLogger(__name__)

MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


@dataclass
class FaceDetectionResult:
    detected: bool
    landmarks: List[Tuple[int, int]]
    left_ear: float
    right_ear: float
    avg_ear: float
    left_eye_pts: List[Tuple[int, int]]
    right_eye_pts: List[Tuple[int, int]]
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)


class FaceMeshDetector:
    """Universal detector for 468+ facial landmarks and ocular geometry."""

    def __init__(self, model_path: Optional[str] = None):
        self.mode = None
        self.detector = None

        if model_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            model_path = os.path.join(root_dir, 'models', 'face_landmarker.task')

        self.model_path = model_path
        self._initialize_detector()

    def _ensure_model_file(self) -> bool:
        """Downloads face_landmarker.task model if absent."""
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 100000:
            return True
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            logger.info(f"Downloading Google FaceLandmarker model to {self.model_path}...")
            urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, self.model_path)
            return True
        except Exception as e:
            logger.warning(f"Could not download model asset: {e}")
            return False

    def _initialize_detector(self) -> None:
        """Initializes modern Tasks API or legacy solutions API."""
        # 1. Try modern Tasks API (MediaPipe >= 1.0)
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            if self._ensure_model_file():
                base_options = python.BaseOptions(model_asset_path=self.model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=False,
                    output_facial_transformation_matrixes=False,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                )
                self.detector = vision.FaceLandmarker.create_from_options(options)
                self.mode = "tasks"
                logger.info("[FaceMeshDetector] Initialized with Google MediaPipe Tasks FaceLandmarker.")
                return
        except Exception as e:
            logger.debug(f"Tasks API not available: {e}")

        # 2. Try legacy solutions API (MediaPipe < 1.0)
        try:
            import mediapipe as mp
            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
                self.detector = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                self.mode = "solutions"
                logger.info("[FaceMeshDetector] Initialized with legacy MediaPipe Solutions FaceMesh.")
                return
        except Exception as e:
            logger.debug(f"Solutions API not available: {e}")

        logger.warning("[FaceMeshDetector] No neural FaceMesh backend available. Running in fallback mode.")
        self.mode = "fallback"

    def process_frame(self, frame: np.ndarray) -> FaceDetectionResult:
        """Processes BGR frame and returns landmark coordinates & EAR."""
        if frame is None or frame.size == 0:
            return FaceDetectionResult(
                detected=False, landmarks=[], left_ear=0.0, right_ear=0.0, avg_ear=0.0,
                left_eye_pts=[], right_eye_pts=[], bbox=None
            )

        h, w, _ = frame.shape

        if self.mode == "tasks" and self.detector is not None:
            import mediapipe as mp
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self.detector.detect(mp_image)

            if not res.face_landmarks or len(res.face_landmarks) == 0:
                return FaceDetectionResult(
                    detected=False, landmarks=[], left_ear=0.0, right_ear=0.0, avg_ear=0.0,
                    left_eye_pts=[], right_eye_pts=[], bbox=None
                )

            landmarks_px = [
                (int(lm.x * w), int(lm.y * h)) for lm in res.face_landmarks[0]
            ]
            return self._build_result(landmarks_px, w, h)

        elif self.mode == "solutions" and self.detector is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.detector.process(rgb)

            if not res.multi_face_landmarks:
                return FaceDetectionResult(
                    detected=False, landmarks=[], left_ear=0.0, right_ear=0.0, avg_ear=0.0,
                    left_eye_pts=[], right_eye_pts=[], bbox=None
                )

            landmarks_px = [
                (int(lm.x * w), int(lm.y * h)) for lm in res.multi_face_landmarks[0].landmark
            ]
            return self._build_result(landmarks_px, w, h)

        return FaceDetectionResult(
            detected=False, landmarks=[], left_ear=0.0, right_ear=0.0, avg_ear=0.0,
            left_eye_pts=[], right_eye_pts=[], bbox=None
        )

    def _build_result(self, landmarks_px: List[Tuple[int, int]], w: int, h: int) -> FaceDetectionResult:
        left_ear, right_ear, avg_ear = calculate_average_ear(landmarks_px)
        left_pts = [landmarks_px[i] for i in LEFT_EYE_LANDMARKS if i < len(landmarks_px)]
        right_pts = [landmarks_px[i] for i in RIGHT_EYE_LANDMARKS if i < len(landmarks_px)]

        xs = [pt[0] for pt in landmarks_px]
        ys = [pt[1] for pt in landmarks_px]
        min_x, max_x = max(0, min(xs)), min(w, max(xs))
        min_y, max_y = max(0, min(ys)), min(h, max(ys))
        bbox = (min_x, min_y, max_x - min_x, max_y - min_y)

        return FaceDetectionResult(
            detected=True,
            landmarks=landmarks_px,
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            left_eye_pts=left_pts,
            right_eye_pts=right_pts,
            bbox=bbox,
        )

    def release(self) -> None:
        if self.detector:
            if hasattr(self.detector, 'close'):
                self.detector.close()
