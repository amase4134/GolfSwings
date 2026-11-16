---
name: process-swing-clips
description: >-
  Turn one raw golf-simulator session video into reviewed swing clips.
  Use when a new raw simulator session should become reviewed swing clips.
---

# Process swing clips

Do not name clips here. Head speed is [name-head-speed](../name-head-speed/SKILL.md). Do not rename clips that already exist.

## Steps

1. Take a raw file from `golf-swing-cv/data/raw/`. Raw files stay flat in that folder. No location/date subfolder for raw.

2. Create clips with `golf-swing-split` (the venv in `golf-swing-cv/.venv`, ffmpeg on PATH). Write them only to `golf-swing-cv/data/processed/{place}_{MM.DD.YYYY}/`. Same place and date share one folder. Take place and date from the raw filename when it is `{place}_{MM.DD.YYYY}`. A suffix after the date (`_approach`) does not make a second folder. Use the splitter’s own filenames.

   When re-running a file to compare against a previous export, do not overwrite that folder. Write to a sibling comparison folder instead, for example `data/processed/{place}_{MM.DD.YYYY}_compare_prepad3.5/`. Leave the earlier processed folder untouched.

   From `golf-swing-cv`, with `PATH` including `.venv/bin`:

   ```bash
   golf-swing-split data/raw/{place}_{MM.DD.YYYY}….mov \
     -o data/processed/{place}_{MM.DD.YYYY}
   ```

   Pass extra flags only for this file, when the checks below say so. Do not change `DetectionConfig` defaults.

3. Review every clip again. Keep a clip only when it shows an actual ball strike: a new nonzero club-head speed appears on the simulator and stays up after the motion. Drop loading screens, address with every stat still 0.0, walking or follow-through after the number is already on screen, waggles, and the same shot captured twice. Also drop clips that start mid-swing (address or takeaway already gone) even if the strike and ball flight look fine.

4. Delete the empty and duplicate clips so the processed folder holds only the clips that passed. Leave the manifest matching the files that remain. Do not rename the survivors. Update `manifest.json` in that folder so `swing_count` and the listed paths are only the clips still on disk.

Do not commit videos, manifests, or `.DS_Store`.

## Settings

Guidance for the split and the review. Not new global defaults.

- Default post-pad is 8.5s and pre-pad is 1.0s. Do not shorten the tail; the simulator ball flight has to finish.
- Check for these failure modes. If any show up, pass flags for that file only:
  - Follow-through longer than 6s is dropped by the default `--max-swing 6`, and a later short burst (walking) is what gets kept. Pass `--max-swing 12` when motion blobs run past 6s. The longest seen was about 10s.
  - A huge non-swing peak (occlusion or loading screen) sets the `--min-peak-ratio 0.25` floor and hides quieter real swings. Pass `--min-peak-ratio 0.12` when the strongest peak is not a swing.
  - Motion detection often starts at the high-energy downswing, so the default `--pre-pad 1.0` cuts address and takeaway. Pass `--pre-pad 3.5` when clips start mid-swing. Keep `--post-pad 8.5`; the longer ball-flight tail is correct.
- The approach video (`No1GolfLounge_10.01.2026_approach.mov`) needed all three: `--max-swing 12 --min-peak-ratio 0.12 --pre-pad 3.5`. Re-export comparison runs for that file go to a sibling folder such as `data/processed/No1GolfLounge_10.01.2026_compare_prepad3.5/`. The first session did not need these flags. Leave the defaults for a file that does not show these failures.
