"""Integration test: synthesize a session video, detect, and export clips."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from golf_swing_cv.cli import main
from golf_swing_cv.split.detect import DetectionConfig, detect_swings
from golf_swing_cv.split.export import export_swings, write_manifest
from golf_swing_cv.split.motion import compute_motion_signal


def _write_session_video(path: Path, *, fps: int = 20, duration_sec: float = 24.0) -> list[tuple[float, float]]:
    """
    Create a synthetic bay video: mostly still, with moving rectangles as swings.

    Returns expected motion windows (start_sec, end_sec) without padding.
    """
    width, height = 320, 240
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    assert writer.isOpened(), "failed to open VideoWriter"

    # Static bay background (fixed grain so quiet frames have ~zero diff)
    rng = np.random.default_rng(0)
    base = np.full((height, width, 3), 30, dtype=np.uint8)
    grain = rng.integers(0, 6, size=base.shape, dtype=np.uint8)
    base = cv2.add(base, grain)

    swings = [(5.0, 7.0), (13.0, 15.0), (20.0, 22.0)]
    total_frames = int(duration_sec * fps)

    for i in range(total_frames):
        t = i / fps
        frame = base.copy()

        for start, end in swings:
            if start <= t <= end:
                # Moving bright block = golfer motion
                progress = (t - start) / (end - start)
                x = int(40 + progress * 180)
                y = int(80 + 20 * np.sin(progress * np.pi * 4))
                cv2.rectangle(frame, (x, y), (x + 50, y + 90), (220, 220, 220), -1)
                # Club-ish stick
                cv2.line(frame, (x + 25, y), (x + 25, y - 40), (200, 200, 200), 2)

        writer.write(frame)

    writer.release()
    return swings


@pytest.fixture()
def session_video(tmp_path: Path) -> tuple[Path, list[tuple[float, float]]]:
    path = tmp_path / "session.mp4"
    expected = _write_session_video(path)
    return path, expected


def test_end_to_end_split_and_export(session_video, tmp_path: Path):
    video_path, expected = session_video
    out_dir = tmp_path / "swings"

    signal = compute_motion_signal(
        video_path,
        analyze_fps=10.0,
        analyze_scale=0.5,
    )
    segments = detect_swings(
        signal,
        DetectionConfig(
            sensitivity=2.5,
            min_swing_sec=0.7,
            max_swing_sec=5.0,
            min_gap_sec=2.0,
            pre_pad_sec=0.4,
            post_pad_sec=0.4,
            close_gap_sec=0.35,
            open_noise_sec=0.1,
            smooth_sec=0.25,
        ),
    )

    assert len(segments) == len(expected)
    for seg, (exp_start, exp_end) in zip(segments, expected, strict=True):
        assert seg.motion_start_sec == pytest.approx(exp_start, abs=0.6)
        assert seg.motion_end_sec == pytest.approx(exp_end, abs=0.6)

    clips = export_swings(signal.video, segments, out_dir, reencode=True)
    assert len(clips) == 3
    for clip in clips:
        assert clip.exists()
        assert clip.stat().st_size > 1000

    manifest = write_manifest(
        video=signal.video,
        signal=signal,
        segments=segments,
        clip_paths=clips,
        config=DetectionConfig(),
        output_path=out_dir / "manifest.json",
    )
    data = json.loads(manifest.read_text())
    assert data["swing_count"] == 3


def test_cli_dry_run(session_video, tmp_path: Path, capsys):
    video_path, _ = session_video
    code = main(
        [
            str(video_path),
            "-o",
            str(tmp_path / "out"),
            "--dry-run",
            "--analyze-fps",
            "10",
            "--sensitivity",
            "2.5",
            "--min-swing",
            "0.7",
            "--pre-pad",
            "0.4",
            "--post-pad",
            "0.4",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Detected 3 swing(s)" in captured.out
