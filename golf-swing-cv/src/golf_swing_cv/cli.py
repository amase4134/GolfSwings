"""CLI entrypoints for golf-swing-cv tools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from golf_swing_cv.split.detect import DetectionConfig, detect_swings
from golf_swing_cv.split.export import export_swings, write_manifest
from golf_swing_cv.split.motion import compute_motion_signal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="golf-swing-split",
        description=(
            "Split a long golf-simulator session video into one clip per swing "
            "using motion-energy detection."
        ),
    )
    parser.add_argument("video", type=Path, help="Input session video path")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/processed/swings"),
        help="Directory for exported swing clips (default: data/processed/swings)",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Filename prefix for clips (default: source stem)",
    )
    parser.add_argument(
        "--analyze-fps",
        type=float,
        default=15.0,
        help="Motion analysis sample rate (default: 15)",
    )
    parser.add_argument(
        "--analyze-scale",
        type=float,
        default=0.35,
        help="Downscale factor for analysis frames (default: 0.35)",
    )
    parser.add_argument(
        "--roi",
        type=float,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        default=None,
        help="Optional normalized ROI (0-1) to ignore screen/HUD flicker",
    )
    parser.add_argument(
        "--sensitivity",
        type=float,
        default=3.0,
        help="Threshold sensitivity over quiet baseline (default: 3.0)",
    )
    parser.add_argument(
        "--min-swing",
        type=float,
        default=0.8,
        dest="min_swing_sec",
        help="Minimum motion duration to count as a swing (seconds)",
    )
    parser.add_argument(
        "--max-swing",
        type=float,
        default=6.0,
        dest="max_swing_sec",
        help="Maximum motion duration to count as a swing (seconds)",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=2.0,
        dest="min_gap_sec",
        help="Minimum gap between swing peaks (seconds)",
    )
    parser.add_argument(
        "--pre-pad",
        type=float,
        default=1.0,
        dest="pre_pad_sec",
        help="Seconds to include before detected motion",
    )
    parser.add_argument(
        "--post-pad",
        type=float,
        default=8.5,
        dest="post_pad_sec",
        help="Seconds to include after detected motion (covers simulator ball flight)",
    )
    parser.add_argument(
        "--close-gap",
        type=float,
        default=0.55,
        dest="close_gap_sec",
        help="Fill quiet gaps shorter than this inside a swing",
    )
    parser.add_argument(
        "--min-peak-ratio",
        type=float,
        default=0.25,
        dest="min_peak_ratio",
        help="Drop swings weaker than this fraction of the strongest peak (0 disables)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Stream-copy with ffmpeg instead of re-encoding (faster, less precise)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect swings and print results without writing clips",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=None,
        help="Optional path to write a motion-energy preview PNG",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional manifest JSON path (default: <output-dir>/manifest.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    video_path = args.video.expanduser().resolve()
    if not video_path.exists():
        parser.error(f"Video not found: {video_path}")

    config = DetectionConfig(
        sensitivity=args.sensitivity,
        min_swing_sec=args.min_swing_sec,
        max_swing_sec=args.max_swing_sec,
        min_gap_sec=args.min_gap_sec,
        min_peak_ratio=args.min_peak_ratio,
        pre_pad_sec=args.pre_pad_sec,
        post_pad_sec=args.post_pad_sec,
        close_gap_sec=args.close_gap_sec,
    )

    print(f"Analyzing {video_path} ...")
    signal = compute_motion_signal(
        video_path,
        analyze_fps=args.analyze_fps,
        analyze_scale=args.analyze_scale,
        roi=tuple(args.roi) if args.roi else None,
    )
    info = signal.video
    print(
        f"Video: {info.duration_sec:.1f}s @ {info.fps:.2f} fps "
        f"({info.width}x{info.height})"
    )

    segments = detect_swings(signal, config)
    print(f"Detected {len(segments)} swing(s)")
    for seg in segments:
        print(
            f"  #{seg.index:03d}  "
            f"{seg.start_sec:7.2f}s → {seg.end_sec:7.2f}s  "
            f"(motion {seg.motion_start_sec:.2f}–{seg.motion_end_sec:.2f}, "
            f"peak {seg.peak_sec:.2f})"
        )

    if args.preview is not None:
        from golf_swing_cv.split.preview import save_motion_preview

        preview_path = save_motion_preview(signal, segments, args.preview, config)
        print(f"Wrote preview: {preview_path}")

    clip_paths = export_swings(
        info,
        segments,
        args.output_dir,
        prefix=args.prefix,
        reencode=not args.copy,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("Dry run — no clips written")
        for path in clip_paths:
            print(f"  would write {path}")
        return 0

    for path in clip_paths:
        print(f"Wrote {path}")

    manifest_path = args.manifest or (args.output_dir / "manifest.json")
    written = write_manifest(
        video=info,
        signal=signal,
        segments=segments,
        clip_paths=clip_paths,
        config=config,
        output_path=manifest_path,
    )
    print(f"Wrote manifest: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
