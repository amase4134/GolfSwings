"""Video probing and lightweight frame iteration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    fps: float
    frame_count: int
    width: int
    height: int
    duration_sec: float

    @property
    def has_valid_timing(self) -> bool:
        return self.fps > 0 and self.frame_count > 0


def probe_video(path: str | Path) -> VideoInfo:
    """Open a video and return basic timing / size metadata."""
    video_path = Path(path).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = (frame_count / fps) if fps > 0 else 0.0
        return VideoInfo(
            path=video_path,
            fps=fps,
            frame_count=frame_count,
            width=width,
            height=height,
            duration_sec=duration,
        )
    finally:
        cap.release()
