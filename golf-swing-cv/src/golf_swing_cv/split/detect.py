"""Detect individual swing windows from a motion-energy signal."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.ndimage import binary_closing, binary_opening, uniform_filter1d

from golf_swing_cv.split.motion import MotionSignal


@dataclass(frozen=True)
class DetectionConfig:
    """Tunables for converting motion energy into swing segments."""

    # Smoothing / thresholding
    smooth_sec: float = 0.35
    baseline_percentile: float = 25.0
    sensitivity: float = 3.0  # threshold = baseline + sensitivity * robust_std
    min_active_sec: float = 0.45  # ignore tiny blips before merging

    # Morphology in time (seconds)
    close_gap_sec: float = 0.55  # fill short quiet gaps inside a swing
    open_noise_sec: float = 0.15  # drop very short noise bursts

    # Segment filters
    min_swing_sec: float = 0.8
    max_swing_sec: float = 6.0
    min_gap_sec: float = 2.0  # refractory period between swings
    # Drop weak detections vs the strongest swing in the session (0 disables)
    min_peak_ratio: float = 0.25

    # Output padding around detected motion.
    # post_pad keeps the simulator ball-flight camera after the body stops.
    # On bay footage the tracer was still in the air ~7s after motion end
    # and the follow-cam was back on the hole view by ~8s, so 8.5s covers
    # a typical flight plus a short hold on the landing.
    pre_pad_sec: float = 1.0
    post_pad_sec: float = 8.5

    def validate(self) -> None:
        if self.smooth_sec < 0:
            raise ValueError("smooth_sec must be >= 0")
        if not (0.0 <= self.baseline_percentile <= 50.0):
            raise ValueError("baseline_percentile should be in [0, 50]")
        if self.sensitivity <= 0:
            raise ValueError("sensitivity must be > 0")
        if self.min_swing_sec <= 0 or self.max_swing_sec <= self.min_swing_sec:
            raise ValueError("require 0 < min_swing_sec < max_swing_sec")
        if self.min_gap_sec < 0:
            raise ValueError("min_gap_sec must be >= 0")
        if not (0.0 <= self.min_peak_ratio < 1.0):
            raise ValueError("min_peak_ratio must be in [0, 1)")
        if self.pre_pad_sec < 0 or self.post_pad_sec < 0:
            raise ValueError("padding must be >= 0")


@dataclass(frozen=True)
class SwingSegment:
    index: int
    start_sec: float
    end_sec: float
    peak_sec: float
    peak_energy: float
    motion_start_sec: float
    motion_end_sec: float

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> dict:
        data = asdict(self)
        data["duration_sec"] = self.duration_sec
        return data


def smooth_energy(signal: MotionSignal, config: DetectionConfig) -> np.ndarray:
    """Return smoothed motion energy aligned to ``signal.times_sec``."""
    energy = signal.energy.astype(np.float64)
    sample_fps = max(signal.sample_fps, 1e-6)
    smooth_samples = max(1, int(round(config.smooth_sec * sample_fps)))
    if smooth_samples > 1:
        return uniform_filter1d(energy, size=smooth_samples, mode="nearest")
    return energy.copy()


def activity_threshold(smoothed: np.ndarray, config: DetectionConfig) -> float:
    """
    Adaptive activity threshold above the quiet baseline.

    Uses MAD of quiet samples, floored by the quiet→peak gap so near-zero
    encoder noise does not collapse the threshold to ~0.
    """
    baseline = float(np.percentile(smoothed, config.baseline_percentile))
    quiet_mask = smoothed <= np.percentile(smoothed, 40.0)
    quiet = smoothed[quiet_mask] if np.any(quiet_mask) else smoothed
    mad = float(np.median(np.abs(quiet - np.median(quiet))))
    mad_std = 1.4826 * mad
    high = float(np.percentile(smoothed, 95.0))
    span_floor = max(0.0, high - baseline) * 0.05
    # Pixel-diff energies are typically O(1)–O(20); keep a tiny absolute floor.
    robust_std = max(mad_std, span_floor, 1e-3)
    return baseline + config.sensitivity * robust_std


def detect_swings(
    signal: MotionSignal,
    config: DetectionConfig | None = None,
) -> list[SwingSegment]:
    """
    Segment a session video into individual swings.

    Pipeline:
      1. Smooth motion energy
      2. Adaptive threshold vs quiet baseline
      3. Morphological open/close to reject noise and fill intra-swing gaps
      4. Keep duration-plausible active regions, enforce min gap
      5. Pad start/end for comfortable clip boundaries
    """
    cfg = config or DetectionConfig()
    cfg.validate()

    times = signal.times_sec
    sample_fps = max(signal.sample_fps, 1e-6)
    smoothed = smooth_energy(signal, cfg)
    threshold = activity_threshold(smoothed, cfg)

    active = smoothed >= threshold

    open_k = max(1, int(round(cfg.open_noise_sec * sample_fps)))
    close_k = max(1, int(round(cfg.close_gap_sec * sample_fps)))
    if open_k > 1:
        active = binary_opening(active, structure=np.ones(open_k, dtype=bool))
    if close_k > 1:
        active = binary_closing(active, structure=np.ones(close_k, dtype=bool))

    raw_segments = _contiguous_regions(active)
    min_active_samples = max(1, int(round(cfg.min_active_sec * sample_fps)))
    raw_segments = [(a, b) for a, b in raw_segments if (b - a) >= min_active_samples]

    duration = signal.video.duration_sec
    candidates: list[SwingSegment] = []
    for start_i, end_i in raw_segments:
        motion_start = float(times[start_i])
        # end_i is exclusive index into samples; clamp to last sample time
        last_i = min(end_i, len(times)) - 1
        motion_end = float(times[last_i])
        motion_dur = motion_end - motion_start
        if motion_dur < cfg.min_swing_sec or motion_dur > cfg.max_swing_sec:
            continue

        window = smoothed[start_i:end_i]
        peak_energy = float(np.max(window))
        # Energy-weighted time is stabler than argmax on flat plateaus
        weights = np.maximum(window - threshold, 0.0)
        if float(np.sum(weights)) > 1e-6:
            peak_sec = float(np.average(times[start_i:end_i], weights=weights))
        else:
            peak_i = int(start_i + np.argmax(window))
            peak_sec = float(times[peak_i])

        start_sec = max(0.0, motion_start - cfg.pre_pad_sec)
        end_sec = min(duration, motion_end + cfg.post_pad_sec)
        if end_sec <= start_sec:
            continue

        candidates.append(
            SwingSegment(
                index=-1,
                start_sec=start_sec,
                end_sec=end_sec,
                peak_sec=peak_sec,
                peak_energy=peak_energy,
                motion_start_sec=motion_start,
                motion_end_sec=motion_end,
            )
        )

    if candidates and cfg.min_peak_ratio > 0:
        max_peak = max(s.peak_energy for s in candidates)
        floor = max_peak * cfg.min_peak_ratio
        candidates = [s for s in candidates if s.peak_energy >= floor]

    # Enforce refractory gap using peak times (prefer higher-energy on conflict)
    candidates.sort(key=lambda s: s.peak_energy, reverse=True)
    accepted: list[SwingSegment] = []
    for seg in candidates:
        if any(abs(seg.peak_sec - other.peak_sec) < cfg.min_gap_sec for other in accepted):
            continue
        accepted.append(seg)

    accepted.sort(key=lambda s: s.start_sec)
    return [
        SwingSegment(
            index=i,
            start_sec=s.start_sec,
            end_sec=s.end_sec,
            peak_sec=s.peak_sec,
            peak_energy=s.peak_energy,
            motion_start_sec=s.motion_start_sec,
            motion_end_sec=s.motion_end_sec,
        )
        for i, s in enumerate(accepted, start=1)
    ]


def _contiguous_regions(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return [start, end) index pairs for True runs in a 1D boolean mask."""
    if mask.size == 0:
        return []
    padded = np.concatenate(([False], mask.astype(bool), [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return list(zip(starts.tolist(), ends.tolist(), strict=True))
