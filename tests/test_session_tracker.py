"""Unit tests for SessionTracker and fatigue state logic."""

import time
import unittest
from src.analytics.session_tracker import SessionTracker
from src.config import CONFIG, AppConfig


class TestSessionTracker(unittest.TestCase):

    def setUp(self):
        self.config = AppConfig(
            EAR_OPEN_THRESHOLD=0.25,
            EAR_DROWSY_THRESHOLD=0.20,
            EAR_CLOSED_THRESHOLD=0.18,
            DROWSINESS_ALERT_SEC=0.1,  # Short alert for testing
            NO_FACE_TIMEOUT_SEC=0.1,
            MAX_BLINK_DURATION_SEC=0.3,
        )
        self.tracker = SessionTracker(self.config)
        self.tracker.start_session()

    def test_state_focused(self):
        snap = self.tracker.update(face_detected=True, ear=0.30)
        self.assertEqual(snap.state, self.config.STATE_FOCUSED)
        self.assertFalse(snap.is_drowsy_alert)
        self.assertFalse(snap.is_absent_alert)

    def test_state_drowsy_warning(self):
        snap = self.tracker.update(face_detected=True, ear=0.22)
        self.assertEqual(snap.state, self.config.STATE_DROWSY)

    def test_drowsiness_alert_trigger(self):
        # Eyes closed continuously
        self.tracker.update(face_detected=True, ear=0.14)
        time.sleep(0.12)  # Exceeds DROWSINESS_ALERT_SEC
        snap = self.tracker.update(face_detected=True, ear=0.14)
        self.assertTrue(snap.is_drowsy_alert)
        self.assertEqual(snap.state, self.config.STATE_CLOSED)
        self.assertGreater(self.tracker.drowsiness_alerts_count, 0)

    def test_absence_alert_trigger(self):
        # No face detected
        self.tracker.update(face_detected=False, ear=0.0)
        time.sleep(0.12)  # Exceeds NO_FACE_TIMEOUT_SEC
        snap = self.tracker.update(face_detected=False, ear=0.0)
        self.assertTrue(snap.is_absent_alert)
        self.assertEqual(snap.state, self.config.STATE_ABSENT)

    def test_blink_detection(self):
        # Normal blink: Open -> Closed -> Open quickly
        self.tracker.update(face_detected=True, ear=0.30)
        self.tracker.update(face_detected=True, ear=0.15)  # Blink dip
        time.sleep(0.05)
        self.tracker.update(face_detected=True, ear=0.30)  # Blink recovery
        self.assertEqual(self.tracker.total_blinks, 1)

    def test_session_summary(self):
        self.tracker.update(face_detected=True, ear=0.30)
        summary = self.tracker.get_summary()
        self.assertTrue(summary["session_active"])
        self.assertIn("focus_percentage", summary)
        self.assertIn("state_durations_sec", summary)


if __name__ == '__main__':
    unittest.main()
