"""Session Simulator & Telemetry Visualization Benchmark.

Simulates an entire 60-second study session with periodic eye blinks,
micro-sleeps, and attention transitions. Generates an analytics plot
and report for documentation and recruiter presentation.
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.analytics.session_tracker import SessionTracker
from src.config import CONFIG
from src.vision.frame_streamer import SyntheticStreamer


def run_simulation(duration_frames: int = 150):
    print("\n--- Running Smart Study Buddy Session Simulation ---")
    tracker = SessionTracker()
    streamer = SyntheticStreamer()
    tracker.start_session()

    ear_records = []
    state_records = []
    timestamps = []

    # Simulate realistic temporal EAR profile:
    # 0 - 40 frames: Awake / Focused (EAR ~ 0.28 - 0.32)
    # 40 - 55 frames: Drowsy / heavy eyelids (EAR ~ 0.21 - 0.24)
    # 55 - 75 frames: Micro-sleep / closed eyes (EAR ~ 0.12 - 0.15) -> Triggers Alarm!
    # 75 - 110 frames: Alerted / fully awake (EAR ~ 0.29 - 0.33)
    # 110 - 130 frames: Distracted / looking away (No face) -> Triggers Distraction!
    # 130 - 150 frames: Return & Focused (EAR ~ 0.30)

    for i in range(duration_frames):
        face_detected = True
        if 0 <= i < 40:
            ear = float(np.random.normal(0.30, 0.015))
        elif 40 <= i < 55:
            ear = float(np.random.normal(0.22, 0.01))
        elif 55 <= i < 75:
            ear = float(np.random.normal(0.14, 0.01))  # Closed eyes!
        elif 75 <= i < 110:
            ear = float(np.random.normal(0.31, 0.015))
        elif 110 <= i < 130:
            face_detected = False
            ear = 0.0  # Away!
        else:
            ear = float(np.random.normal(0.29, 0.015))

        snap = tracker.update(face_detected=face_detected, ear=ear)
        ear_records.append(ear)
        state_records.append(snap.state)
        timestamps.append(i * 0.1)  # 10 Hz simulation

    summary = tracker.get_summary()

    # Generate Visualization Plot
    os.makedirs('assets', exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=150)

    # Plot 1: Eye Aspect Ratio (EAR) over Time
    ax1.plot(timestamps, ear_records, color='#2563EB', linewidth=2, label='Measured EAR')
    ax1.axhline(CONFIG.EAR_OPEN_THRESHOLD, color='#10B981', linestyle='--', label=f'Open Threshold ({CONFIG.EAR_OPEN_THRESHOLD})')
    ax1.axhline(CONFIG.EAR_DROWSY_THRESHOLD, color='#F59E0B', linestyle='--', label=f'Drowsy Threshold ({CONFIG.EAR_DROWSY_THRESHOLD})')
    ax1.axhline(CONFIG.EAR_CLOSED_THRESHOLD, color='#EF4444', linestyle='--', label=f'Closed Threshold ({CONFIG.EAR_CLOSED_THRESHOLD})')
    ax1.set_ylabel('Eye Aspect Ratio (EAR)', fontsize=10, fontweight='bold')
    ax1.set_title('Study Session Telemetry: Ocular Dynamics & Fatigue Tracking', fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', framealpha=0.9)

    # Highlight regions
    ax1.axvspan(5.5, 7.5, color='#FEE2E2', alpha=0.5, label='Drowsiness Event')
    ax1.axvspan(11.0, 13.0, color='#FFEDD5', alpha=0.5, label='Distraction Event')

    # Plot 2: State Machine
    state_names = {0: 'Eyes Closed', 1: 'Drowsy', 2: 'Focused', 3: 'Away'}
    ax2.step(timestamps, [state_records[i] for i in range(len(timestamps))], color='#7C3AED', where='post', linewidth=2)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(['0: Closed', '1: Drowsy', '2: Focused', '3: Away'])
    ax2.set_ylabel('Focus State', fontsize=10, fontweight='bold')
    ax2.set_xlabel('Elapsed Time (Seconds)', fontsize=10, fontweight='bold')
    ax2.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    chart_path = os.path.join('assets', 'session_telemetry_plot.png')
    plt.savefig(chart_path)
    plt.close()

    print(f"Simulation completed! Telemetry chart saved -> {chart_path}")
    print(f"Overall Focus Score: {summary['focus_percentage']}%")
    print(f"Drowsiness Alerts  : {summary['drowsiness_alerts']}")
    return summary


if __name__ == "__main__":
    run_simulation()
