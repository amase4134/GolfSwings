"""Unit tests for swing detection on synthetic motion signals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from golf_swing_cv.ingest.video import VideoInfo
from golf_swing_cv.split.detect import DetectionConfig, detect_swings
from golf_swing_cv.split.motion import MotionSignal


def _fake_signal(energy: np.ndarray, fps: float = 15.0) -> MotionSignal:
    n = energy.size
    times = np.arange(n, dtype=np.float64) / fps
    duration = float(times[-1]) if n else 0.0
    video = VideoInfo(
        path=Path("synthetic.mp4"),
        fps=fps,
        frame_count=int(duration * fps) + 1,
        width=320,
        height=240,
        duration_sec=duration + (1.0 / fps),
    )
    return MotionSignal(
        times_sec=times,
        energy=energy.astype(np.float64),
        sample_fps=fps,
        video=video,
        analyze_scale=1.0,
        frame_stride=1,
    )


def test_detects_three_separated_swings():
    fps = 15.0
    duration_sec = 40.0
    n = int(duration_sec * fps)
    energy = np.full(n, 2.0, dtype=np.float64)

    # Three ~2s motion bursts centered near 8s, 18s, 30s
    for center in (8.0, 18.0, 30.0):
        start = int((center - 1.0) * fps)
        end = int((center + 1.0) * fps)
        energy[start:end] = 40.0
        energy[start + 5 : end - 5] = 70.0

    signal = _fake_signal(energy, fps=fps)
    segments = detect_swings(
        signal,
        DetectionConfig(
            sensitivity=3.0,
            min_swing_sec=0.8,
            max_swing_sec=5.0,
            min_gap_sec=3.0,
            pre_pad_sec=0.5,
            post_pad_sec=0.5,
            close_gap_sec=0.4,
            open_noise_sec=0.1,
        ),
    )

    assert len(segments) == 3
    peaks = [s.peak_sec for s in segments]
    assert peaks[0] == pytest.approx(8.0, abs=0.75)
    assert peaks[1] == pytest.approx(18.0, abs=0.75)
    assert peaks[2] == pytest.approx(30.0, abs=0.75)


def test_ignores_short_noise_blips():
    fps = 15.0
    n = int(25 * fps)
    energy = np.full(n, 1.5, dtype=np.float64)

    # Real swing ~2s
    energy[int(10 * fps) : int(12 * fps)] = 50.0
    # Noise blip ~0.2s
    energy[int(16 * fps) : int(16.2 * fps)] = 80.0

    signal = _fake_signal(energy, fps=fps)
    segments = detect_swings(
        signal,
        DetectionConfig(
            sensitivity=3.0,
            min_swing_sec=0.8,
            min_gap_sec=2.0,
            open_noise_sec=0.15,
            close_gap_sec=0.4,
        ),
    )
    assert len(segments) == 1
    assert 9.0 < segments[0].peak_sec < 13.0
