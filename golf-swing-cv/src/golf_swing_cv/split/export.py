"""Export detected swing windows to clip files + a JSON manifest."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from golf_swing_cv.ingest.video import VideoInfo
from golf_swing_cv.split.detect import DetectionConfig, SwingSegment
from golf_swing_cv.split.motion import MotionSignal


def export_swings(
    video: VideoInfo,
    segments: list[SwingSegment],
    output_dir: str | Path,
    *,
    prefix: str | None = None,
    reencode: bool = True,
    dry_run: bool = False,
) -> list[Path]:
    """
    Cut each swing segment to ``output_dir``.

    By default re-encodes with ffmpeg for accurate cuts. Use ``reencode=False``
    for faster keyframe-aligned stream copies (cuts may be less precise).
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required on PATH to export swing clips")

    out = Path(output_dir).expanduser().resolve()
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    stem = prefix or video.path.stem
    written: list[Path] = []

    for seg in segments:
        name = f"{stem}_swing_{seg.index:03d}.mp4"
        dest = out / name
        duration = max(0.05, seg.end_sec - seg.start_sec)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{seg.start_sec:.3f}",
            "-i",
            str(video.path),
            "-t",
            f"{duration:.3f}",
        ]
        if reencode:
            cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                ]
            )
        else:
            cmd.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
        cmd.append(str(dest))

        if dry_run:
            written.append(dest)
            continue

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed for swing {seg.index}: {result.stderr.strip()}"
            )
        written.append(dest)

    return written


def write_manifest(
    *,
    video: VideoInfo,
    signal: MotionSignal,
    segments: list[SwingSegment],
    clip_paths: list[Path],
    config: DetectionConfig,
    output_path: str | Path,
) -> Path:
    """Write a JSON manifest describing detection + exported clips."""
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    clips = []
    for seg, clip in zip(segments, clip_paths, strict=True):
        item = seg.to_dict()
        item["path"] = str(clip)
        clips.append(item)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(video.path),
            "fps": video.fps,
            "frame_count": video.frame_count,
            "width": video.width,
            "height": video.height,
            "duration_sec": video.duration_sec,
        },
        "analysis": {
            "sample_fps": signal.sample_fps,
            "analyze_scale": signal.analyze_scale,
            "frame_stride": signal.frame_stride,
            "samples": int(signal.energy.size),
        },
        "config": asdict(config),
        "swing_count": len(segments),
        "swings": clips,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
