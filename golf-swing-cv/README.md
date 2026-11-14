# Golf Swing CV

Computer vision project: compare your golf swing videos to professional swings and surface biomechanical differences.

## Docs

| Doc | Purpose |
| --- | --- |
| [PLAN.md](./PLAN.md) | Development plan (approach, metrics, phases, MVP) |
| [SPLITTER.md](./SPLITTER.md) | Session video → per-swing clip tool (implemented) |
| [DATASET_SOURCES.md](./DATASET_SOURCES.md) | Research notes on dataset sources, labeling, and pose pipelines |

## Status

**Phase 1 starter shipped:** motion-based session swing splitter. Pose smoke test and key-position labeling come next.

## Quick start — split a simulator session

```bash
cd golf-swing-cv
pip install -e ".[dev]"

golf-swing-split /path/to/long_session.mp4 -o data/processed/swings
# or: python -m golf_swing_cv.cli /path/to/long_session.mp4 -o data/processed/swings
```

Writes one MP4 per detected swing plus `manifest.json`. See [SPLITTER.md](./SPLITTER.md) for ROI / sensitivity tuning.

## Layout

```
golf-swing-cv/
  src/golf_swing_cv/
    ingest/     # video probe helpers
    split/      # motion energy, swing detect, ffmpeg export
    cli.py      # golf-swing-split entrypoint
  tests/
  PLAN.md
  SPLITTER.md
  data/         # local videos (gitignored)
```
