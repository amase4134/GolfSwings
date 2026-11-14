"""Frame-difference motion energy for swing activity detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from golf_swing_cv.ingest.video import VideoInfo, probe_video


@dataclass(frozen=True)
class MotionSignal:
    """Per-sample motion energy aligned to source-video timestamps."""

    times_sec: np.ndarray  # shape (N,)
    energy: np.ndarray  # shape (N,), non-negative
    sample_fps: float
    video: VideoInfo
    analyze_scale: float
    frame_stride: int


def compute_motion_signal(
    path: str | Path,
    *,
    analyze_fps: float = 15.0,
    analyze_scale: float = 0.35,
    blur_ksize: int = 5,
    roi: tuple[float, float, float, float] | None = None,
) -> MotionSignal:
    """
    Compute a 1D motion-energy signal from consecutive downsampled frames.

    Energy is mean absolute pixel difference after grayscale + blur.
    Optional ``roi`` is (x0, y0, x1, y1) in normalized [0, 1] coords to focus
    on the hitting bay / person and ignore screen / HUD flicker.
    """
    video = probe_video(path)
    if not video.has_valid_timing:
        raise RuntimeError(f"Invalid video timing metadata: {video.path}")

    if analyze_fps <= 0:
        raise ValueError("analyze_fps must be > 0")
    if not (0.05 <= analyze_scale <= 1.0):
        raise ValueError("analyze_scale must be in [0.05, 1.0]")

    frame_stride = max(1, int(round(video.fps / analyze_fps)))
    sample_fps = video.fps / frame_stride

    cap = cv2.VideoCapture(str(video.path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video.path}")

    ksize = blur_ksize if blur_ksize % 2 == 1 else blur_ksize + 1
    times: list[float] = []
    energy: list[float] = []
    prev_gray: np.ndarray | None = None
    frame_idx = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx % frame_stride != 0:
                frame_idx += 1
                continue

            gray = _prepare_frame(frame, analyze_scale, ksize, roi)
            t = frame_idx / video.fps
            if prev_gray is None:
                times.append(t)
                energy.append(0.0)
            else:
                diff = cv2.absdiff(gray, prev_gray)
                times.append(t)
                energy.append(float(np.mean(diff)))
            prev_gray = gray
            frame_idx += 1
    finally:
        cap.release()

    if len(energy) < 3:
        raise RuntimeError("Video too short to compute a motion signal")

    return MotionSignal(
        times_sec=np.asarray(times, dtype=np.float64),
        energy=np.asarray(energy, dtype=np.float64),
        sample_fps=sample_fps,
        video=video,
        analyze_scale=analyze_scale,
        frame_stride=frame_stride,
    )


def _prepare_frame(
    frame: np.ndarray,
    scale: float,
    blur_ksize: int,
    roi: tuple[float, float, float, float] | None,
) -> np.ndarray:
    if roi is not None:
        h, w = frame.shape[:2]
        x0, y0, x1, y1 = roi
        xa, xb = int(w * x0), int(w * x1)
        ya, yb = int(h * y0), int(h * y1)
        xa, xb = max(0, min(xa, xb)), min(w, max(xa, xb))
        ya, yb = max(0, min(ya, yb)), min(h, max(ya, yb))
        if xb - xa < 8 or yb - ya < 8:
            raise ValueError(f"ROI too small after clamping: {roi}")
        frame = frame[ya:yb, xa:xb]

    if scale < 1.0:
        frame = cv2.resize(
            frame,
            dsize=None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if blur_ksize > 1:
        gray = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
    return gray
