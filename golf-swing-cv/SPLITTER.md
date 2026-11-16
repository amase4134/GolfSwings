# Session Swing Splitter

Turn a long golf-simulator session recording into one clip per swing.

## How it works

Simulator sessions are mostly quiet (address / reset / watching ball flight) with short bursts of high motion (the swing). The splitter:

1. Downsamples the video (default ~15 fps analysis, 35% scale) for speed
2. Computes **motion energy** = mean absolute difference between consecutive frames
3. Smooths the signal and sets an adaptive threshold above the quiet baseline
4. Finds contiguous active regions, fills short gaps inside a swing, drops noise blips
5. Keeps duration-plausible segments and enforces a minimum gap between peaks
6. Exports padded clips with `ffmpeg` plus a JSON manifest

Optional `--roi` lets you crop to the hitting bay so simulator screen / HUD flicker does not create false positives.

```
session.mp4
    │
    ▼
motion energy ──► threshold / morphology ──► swing windows
                                              │
                                              ▼
                                    swing_001.mp4 …
                                    manifest.json
```

## Install

```bash
cd golf-swing-cv
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# ffmpeg must be on PATH
```

## Usage

```bash
# Detect + export clips
golf-swing-split path/to/session.mp4 -o data/processed/swings

# Preview the motion signal (tune sensitivity without exporting)
golf-swing-split path/to/session.mp4 --dry-run --preview /tmp/motion.png

# Focus on the person / bay (normalized coords: x0 y0 x1 y1)
golf-swing-split path/to/session.mp4 --roi 0.15 0.05 0.85 0.95

# Faster but less precise cuts (stream copy)
golf-swing-split path/to/session.mp4 --copy
```

### Useful knobs

| Flag | Default | Meaning |
| --- | --- | --- |
| `--sensitivity` | `3.0` | Higher → fewer / stronger swings only |
| `--min-swing` / `--max-swing` | `0.8` / `6.0` | Motion duration bounds (seconds) |
| `--min-gap` | `2.0` | Refractory period between swing peaks |
| `--pre-pad` / `--post-pad` | `1.0` / `8.5` | Context before motion, and tail long enough for on-screen ball flight |
| `--close-gap` | `0.55` | Fill brief quiet holes inside one swing |
| `--min-peak-ratio` | `0.25` | Drop swings weaker than this fraction of the strongest peak |
| `--analyze-fps` | `15` | Analysis sample rate |
| `--roi` | off | Ignore screen/HUD regions |

## Outputs

```
data/processed/swings/
  session_swing_001.mp4
  session_swing_002.mp4
  ...
  manifest.json
```

`manifest.json` lists each swing’s padded window, raw motion window, peak time, and output path — handy for the next pose / compare stages.

## Tuning tips for simulator footage

- If the **ball-flight screen** flickers: pass `--roi` covering only you / the mat
- If walks between shots are detected as swings: raise `--sensitivity` or `--min-swing`
- If one swing is split in two: raise `--close-gap` slightly
- If address/setup is clipped: raise `--pre-pad` (try `3.5` when motion starts at the downswing). Keep `--post-pad` at `8.5` unless ball flight is still cut.
- `--post-pad` is the tail after body motion stops. The default `8.5` covers a typical simulator follow-cam (tracer still in the air around 7s, hole view back by about 8s). Raise it if a longer flight is cut; nearby shots will overlap when the gap is shorter than the pad.
- For a comparison re-export, write to a sibling folder (for example `data/processed/{place}_{MM.DD.YYYY}_compare_prepad3.5/`) so the previous processed clips stay available side by side.

## Processing skill

To turn a new raw simulator session into reviewed swing clips, follow [.cursor/skills/process-swing-clips/SKILL.md](../.cursor/skills/process-swing-clips/SKILL.md). Raw files stay flat in `data/raw/`. Clips for one place and date go in `data/processed/{place}_{MM.DD.YYYY}/`. Keep a clip only when the simulator shows a new club-head speed after a ball strike, then delete the rest and leave `manifest.json` matching the files that remain.

## Head speed

After clips are reviewed, append the simulator Head Speed with [.cursor/skills/name-head-speed/SKILL.md](../.cursor/skills/name-head-speed/SKILL.md). One decimal, `_{speed}mph` before `.mp4`. Do not choose the club.

## Limits (v1)

- Motion-based, not pose-based — someone walking through frame can look like a swing
- Does not yet label address / top / impact / finish (Phase 1 keyframes in [PLAN.md](./PLAN.md))
- Best on a fixed camera; handheld shake raises baseline motion

Pose-assisted segmentation can replace or refine this detector later without changing the export/manifest contract.
