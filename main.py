"""Smart Study Buddy & Edge Drowsiness Detection System - Main Application.

Real-Time Ocular Biometrics, Attention Tracking, and ESP32 IoT Microcontroller Control.
"""

import argparse
import logging
import os
import sys
import time
import cv2

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.analytics.session_tracker import SessionTracker
from src.config import CONFIG
from src.hardware.serial_controller import SerialController
from src.ui.hud_renderer import HUDRenderer
from src.vision.face_mesh_detector import FaceMeshDetector
from src.vision.frame_streamer import create_streamer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("StudyBuddy")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Study Buddy & Edge Drowsiness Monitor")
    parser.add_argument(
        "--source",
        type=str,
        default="webcam",
        choices=["webcam", "esp32", "video", "synthetic"],
        help="Video capture source (default: webcam)",
    )
    parser.add_argument("--url", type=str, default=CONFIG.DEFAULT_STREAM_URL, help="ESP32-CAM HTTP stream URL")
    parser.add_argument("--device", type=int, default=0, help="Webcam device index (default: 0)")
    parser.add_argument("--video_path", type=str, default="", help="Path to input video file")
    parser.add_argument("--port", type=str, default=CONFIG.SERIAL_PORT, help="Serial port for ESP32 (default: COM4)")
    parser.add_argument("--baud", type=int, default=CONFIG.BAUD_RATE, help="Serial baud rate (default: 115200)")
    parser.add_argument("--no_serial", action="store_true", help="Run in standalone CV mode without hardware")
    parser.add_argument("--headless", action="store_true", help="Run without GUI window for automated testing")
    parser.add_argument("--max_frames", type=int, default=0, help="Exit after N frames (0 for infinite loop)")
    parser.add_argument("--save_report", type=str, default="session_report.json", help="Export session JSON report path")
    return parser.parse_args()


def main():
    args = parse_arguments()

    print("\n" + "=" * 60)
    print("      SMART STUDY BUDDY & DROWSINESS MONITOR v2.0")
    print("=" * 60)
    print(f"  Capture Source  : {args.source.upper()}")
    print(f"  Serial Control  : {'DISABLED' if args.no_serial else args.port}")
    print(f"  Headless Mode   : {'ENABLED' if args.headless else 'DISABLED'}")
    print("  Controls        : [S] Toggle Session | [R] Reset | [Q/ESC] Quit")
    print("=" * 60 + "\n")

    # 1. Initialize Video Streamer
    logger.info(f"Initializing video stream from source: {args.source}...")
    streamer = create_streamer(
        source=args.source,
        device_index=args.device,
        url=args.url,
        path=args.video_path,
    )

    # 2. Initialize Computer Vision & Analytics Pipelines
    logger.info("Loading MediaPipe FaceMesh neural models...")
    detector = FaceMeshDetector()
    tracker = SessionTracker()
    hud = HUDRenderer()

    # 3. Initialize Hardware Serial Interface
    def on_hardware_start():
        tracker.start_session()
        logger.info("Session started via hardware push button.")

    def on_hardware_stop():
        tracker.stop_session()
        logger.info("Session stopped via hardware push button.")

    serial_ctrl = None
    if not args.no_serial:
        serial_ctrl = SerialController(
            port=args.port,
            baud_rate=args.baud,
            on_session_start=on_hardware_start,
            on_session_stop=on_hardware_stop,
        )

    # Start session by default
    tracker.start_session()
    frame_count = 0

    try:
        while True:
            ret, frame = streamer.get_frame()
            if not ret or frame is None:
                if args.source == "esp32":
                    time.sleep(0.05)
                    continue
                else:
                    logger.info("End of stream or device disconnected.")
                    break

            frame_count += 1

            # Computer Vision Detection
            detection = detector.process_frame(frame)

            # Analytics & State Machine Update
            snapshot = tracker.update(detection.detected, detection.avg_ear)

            # Hardware Actuation Dispatch
            if serial_ctrl:
                serial_ctrl.send_focus_state(snapshot.state)
                serial_ctrl.poll_hardware_events()

            # Render Telemetry HUD
            elapsed = time.time() - tracker.start_time if tracker.session_started else 0.0
            rendered_frame = hud.render(
                frame=frame,
                detection=detection,
                snapshot=snapshot,
                session_active=tracker.session_started,
                elapsed_sec=elapsed,
            )

            # Display GUI
            if not args.headless:
                cv2.imshow(CONFIG.WINDOW_TITLE, rendered_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q'), ord('Q')):
                    break
                elif key in (ord('s'), ord('S')):
                    active = tracker.toggle_session()
                    logger.info(f"Session toggled -> {'ACTIVE' if active else 'PAUSED'}")
                elif key in (ord('r'), ord('R')):
                    tracker.start_session()
                    logger.info("Session metrics reset.")

            if args.max_frames > 0 and frame_count >= args.max_frames:
                logger.info(f"Reached requested frame limit ({args.max_frames}). Exiting.")
                break

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    finally:
        # Cleanup
        streamer.release()
        detector.release()
        if serial_ctrl:
            serial_ctrl.close()
        cv2.destroyAllWindows()

        # Session Summary Report
        summary = tracker.get_summary()
        if args.save_report:
            tracker.export_report(args.save_report)
            logger.info(f"Session telemetry report saved to: {args.save_report}")

        print("\n" + "=" * 55)
        print("          STUDY SESSION TELEMETRY REPORT")
        print("=" * 55)
        print(f"  Duration           : {summary['session_duration_sec']} seconds")
        print(f"  Focus Percentage   : {summary['focus_percentage']}%")
        print(f"  Total Blinks       : {summary['total_blinks']}")
        print(f"  Drowsiness Alerts  : {summary['drowsiness_alerts']}")
        print(f"  Absence Alerts     : {summary['absence_alerts']}")
        print(f"  Time Focused       : {summary['state_durations_sec']['focused']}s")
        print(f"  Time Drowsy        : {summary['state_durations_sec']['drowsy']}s")
        print(f"  Time Eyes Closed   : {summary['state_durations_sec']['closed']}s")
        print(f"  Time Away          : {summary['state_durations_sec']['absent']}s")
        print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
