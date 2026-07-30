# Golf Swing Computer Vision — Development Plan

Compare your swing videos to professional golfers and surface the biomechanical differences that matter.

## Goal

Build a tool that:

1. Accepts a side/face-on video of your swing
2. Extracts body + club motion over time
3. Aligns that motion to a pro reference swing
4. Reports **where** and **how** your positions diverge (angles, timing, sequencing)

**Success for v1:** Upload two videos (yours + a pro) and get a side-by-side overlay plus a short list of quantified differences at key swing positions (address, top, impact, finish).

---

## Recommended approach

Use **2D pose estimation** first (phone video, no special hardware). Skip 3D reconstruction and club-head tracking until pose comparison is useful.

```
Video → Pose landmarks (per frame)
     → Swing phase detection
     → Temporal alignment to pro
     → Joint-angle / posture metrics
     → Diff report + overlay visualization
```

**Why this path:** MediaPipe / similar models run on a laptop, work on casual filming conditions, and give enough signal for posture and sequencing feedback. Club path and true 3D plane analysis are valuable later but harder and noisier.

---

## Tech stack (proposed)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Best CV / ML ecosystem |
| Pose | MediaPipe Pose (or RTMPose) | Fast, good enough landmarks, easy local install |
| Video I/O | OpenCV | Frame extract, draw overlays |
| Alignment | DTW or phase landmarks | Sync swings of different tempo |
| Metrics | NumPy / SciPy | Angles, velocities, sequencing |
| UI (v1) | Streamlit or Gradio | Fast upload → results loop |
| UI (later) | Next.js + FastAPI | Polished app if you keep using it |
| Storage | Local folders first | No cloud needed for personal use |

Optional later: YOLO for club/ball detection, MediaPipe Holistic, or a lightweight 3D lift (e.g. MotionBERT) if 2D proves limiting.

---

## What to measure

Focus on coach-style checkpoints, not every joint.

### Key positions
- Address
- Takeaway (~halfway back)
- Top of backswing
- Mid-downswing
- Impact
- Finish

### Priority metrics (v1)
- **Spine tilt / shoulder tilt** at address and impact
- **Hip–shoulder separation** (X-factor proxy) near top / transition
- **Lead arm angle** at top
- **Knee flex** at address vs impact
- **Weight shift proxy** (hip center lateral travel) through the swing
- **Tempo** (backswing : downswing time ratio)
- **Sequencing** (peak hip rotation vs peak shoulder rotation timing)

### Defer to later
- Club shaft plane / attack angle
- Exact clubface / path
- Wrist hinge / lag quantification (noisy in 2D)
- Ball flight correlation

---

## Data & filming protocol

Consistency beats model sophistication.

### Your videos
- Phone on a tripod, ~10–15 ft away
- **Two views:** down-the-line (behind) and face-on
- Full body + club in frame; avoid zoom during swing
- Bright, plain background if possible; 60–120 fps preferred (30 fps OK for MVP)
- Same club category when comparing (e.g. driver vs driver)

### Pro reference library
Start small — 5–10 public swings with clear side/face-on views (YouTube fair-use for personal analysis; do not redistribute copyrighted footage).

Store as:

```
data/
  pros/
    scheffler_driver_dtl.mp4
    morikawa_iron_faceon.mp4
  me/
    2026-07-30_driver_dtl.mp4
  processed/
    ...
```

Tag each clip with: golfer, club, view (`dtl` | `faceon`), handedness, fps, notes.

---

## Phased build plan

### Phase 0 — Setup & smoke test
- Repo layout, Python env, MediaPipe running on one sample video
- Draw skeleton overlay and export landmark CSV per frame
- **Exit criteria:** one local script produces an annotated MP4 + CSV

### Phase 1 — Swing segmentation
- Detect swing window (start motion → finish stillness)
- Label approximate key frames (top = max lead-wrist height or shoulder turn; impact ≈ club near ball / hands lowest forward, depending on view)
- Manual keyframe override in UI for bad auto-detects
- **Exit criteria:** reliable key positions on your own footage with optional manual tweak

### Phase 2 — Metrics engine
- Compute joint angles from landmarks each frame
- Aggregate metrics at key positions
- Simple tempo + sequencing features
- **Exit criteria:** printed metric table for one swing

### Phase 3 — Compare to pro
- Normalize for body scale and camera distance (use torso length / hip width)
- Align timelines (phase-based first; DTW if needed)
- Diff metrics + threshold “notable” differences
- Side-by-side / ghost overlay video
- **Exit criteria:** upload me + pro → overlay + 5–10 bullet differences

### Phase 4 — Personal app loop
- Streamlit UI: upload, choose pro + view, run analysis, save history
- Session notes (“felt early extension”) for later correlation
- **Exit criteria:** you can analyze a new range session in under a few minutes

### Phase 5 — Stretch (only if Phase 4 is sticky)
- Club detection / shaft line
- Second-camera sync
- 3D pose lift
- Trend charts across sessions
- Optional coaching LLM that explains diffs in plain language (metrics → text, not vision hallucination)

---

## Suggested repo layout

```
golf-swing-cv/
  PLAN.md
  README.md
  pyproject.toml / requirements.txt
  src/
    ingest/          # video load, resize, fps normalize
    pose/            # MediaPipe wrapper, landmark I/O
    phases/          # key-position detection
    metrics/         # angles, tempo, sequencing
    compare/         # alignment + diffs
    viz/             # overlays, plots
    app/             # Streamlit entrypoint
  data/              # gitignored videos; keep small samples if needed
  notebooks/         # exploration only
  tests/
```

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Camera angle mismatch vs pro | Require same view tag; reject cross-view compare |
| Different body proportions | Normalize by torso/hip scale; compare angles more than raw pixel distances |
| Occlusion / blur at impact | Prefer face-on for posture; DTL for plane proxies; allow manual keyframes |
| “Looking like a pro” ≠ good for you | Frame output as *differences*, not “fixes”; avoid injury-risk language |
| Copyright on pro videos | Personal analysis only; store locally; prefer licensed / your own captures |
| Over-scoped club tracking | Explicitly out of MVP |

---

## MVP definition (ship this first)

A local Streamlit app that:

1. Takes **your** video + **one pro** video (same view)
2. Runs pose estimation
3. Lets you confirm key frames
4. Shows ghost overlay at address / top / impact / finish
5. Lists the largest angle/timing deltas

If that loop is useful on the range, then invest in club tracking and polish.

---

## First implementation tickets

1. Bootstrap Python project + MediaPipe pose demo script
2. Landmark CSV schema + annotated video writer
3. Filming checklist + `data/` conventions
4. Key-position detector with manual override
5. Angle metrics at key positions
6. Two-swing aligner + diff report
7. Streamlit upload / compare UI

---

## Open decisions (resolve when building Phase 0–1)

- MediaPipe Pose vs RTMPose (start MediaPipe; swap if quality insufficient)
- Primary view for v1: **face-on** (posture/sequencing) or **DTL** (plane feel) — recommend face-on first
- Pro set: one model swing vs a small multi-pro library matched by club/view
- Keep analysis fully offline vs optional cloud GPU later

---

## Non-goals (for now)

- Real-time on-course coaching glasses
- Automatic “one tip” prescription engine
- Competitive product / multi-user SaaS
- Replacing a human coach
