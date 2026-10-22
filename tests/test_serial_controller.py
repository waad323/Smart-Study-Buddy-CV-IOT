"""Unit tests for SerialController hardware sync and mock fallback."""

import unittest
from src.hardware.serial_controller import SerialController


class TestSerialController(unittest.TestCase):

    def test_mock_fallback_on_invalid_port(self):
        # On ports that don't exist, SerialController gracefully enters mock fallback
        ctrl = SerialController(port="COM999", baud_rate=115200)
        self.assertFalse(ctrl.is_connected)
        # Calling send_focus_state should return False without crashing
        success = ctrl.send_focus_state(2)
        self.assertFalse(success)
        ctrl.close()

    def test_inbound_callbacks(self):
        start_triggered = []
        stop_triggered = []

        def on_start():
            start_triggered.append(True)

        def on_stop():
            stop_triggered.append(True)

        ctrl = SerialController(
            port="COM999",
            on_session_start=on_start,
            on_session_stop=on_stop,
        )
        self.assertFalse(ctrl.is_connected)
        # Verify callbacks are registered
        self.assertIsNotNone(ctrl.on_session_start)
        self.assertIsNotNone(ctrl.on_session_stop)
        ctrl.close()


if __name__ == '__main__':
    unittest.main()
