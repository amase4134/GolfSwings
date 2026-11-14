"""Optional motion-signal preview plot for tuning detection."""

from __future__ import annotations

from pathlib import Path

from golf_swing_cv.split.detect import (
    DetectionConfig,
    SwingSegment,
    activity_threshold,
    smooth_energy,
)
from golf_swing_cv.split.motion import MotionSignal


def save_motion_preview(
    signal: MotionSignal,
    segments: list[SwingSegment],
    output_path: str | Path,
    config: DetectionConfig,
) -> Path:
    """Write a PNG plot of motion energy with detected swing windows."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for --preview; pip install matplotlib"
        ) from exc

    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    smoothed = smooth_energy(signal, config)
    threshold = activity_threshold(smoothed, config)
    times = signal.times_sec

    fig, ax = plt.subplots(figsize=(12, 4), dpi=120)
    ax.plot(times, signal.energy, color="#9aa0a6", linewidth=0.8, label="raw")
    ax.plot(times, smoothed, color="#1a73e8", linewidth=1.4, label="smoothed")
    ax.axhline(threshold, color="#d93025", linestyle="--", linewidth=1, label="threshold")

    for seg in segments:
        ax.axvspan(seg.start_sec, seg.end_sec, color="#34a853", alpha=0.18)
        ax.axvline(seg.peak_sec, color="#188038", linewidth=0.9, alpha=0.8)

    ax.set_title(f"Motion energy — {signal.video.path.name} ({len(segments)} swings)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mean abs frame diff")
    ax.legend(loc="upper right")
    ax.set_xlim(0, max(float(times[-1]), 0.1))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
