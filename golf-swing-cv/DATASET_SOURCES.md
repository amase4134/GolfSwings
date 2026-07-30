# Dataset Sources & Research Notes

Research notes on assembling a large, legally usable, well-labeled golf swing dataset for computer vision analysis.

The biggest challenge for a high-quality golf swing analysis model is not the model itself—it is assembling the right data. Aim for videos from three groups:

1. **Professional golfers** — ideal mechanics
2. **Amateur golfers** — real-world variability
3. **Annotated swing videos** — for supervised learning

---

## 1. YouTube (best for research and prototyping)

Many PGA and LPGA swings are available from:

- Official tournament broadcasts
- Instruction channels
- Slow-motion compilations
- Launch monitor demonstrations

**Example channels:**

- Official PGA Tour channel
- Official LPGA channel
- Golf Digest
- Titleist
- TaylorMade Golf
- TrackMan
- Athletic Motion Golf

**Advantages**

- Thousands of swings
- Multiple camera angles
- High-resolution video
- Slow-motion footage

**Disadvantages**

- Copyright restrictions
- Cannot freely redistribute videos in a commercial dataset
- Need to extract and label frames yourself

Excellent for personal research; be cautious if the goal is a commercial product.

---

## 2. Public research datasets

Computer vision datasets that contain golf swings include:

- **GolfDB** (most well-known)
- Golf Swing Sequence Dataset
- AIHub sports datasets (availability varies)
- Various university research datasets

### GolfDB

Contains:

- Over 1,000 golf swing videos
- Swing event annotations
- Frame-level labels
- Professional golfers
- Different clubs

Common research uses:

- Swing event detection
- Pose estimation
- Temporal modeling

Strong starting point for Phase 0–2 prototyping in this project.

---

## 3. Kaggle

Search terms:

- `golf swing dataset`
- `golf pose estimation`
- `golf swing videos`

You may find:

- Frame datasets
- Skeleton keypoints
- Slow-motion swings
- Classification datasets

Quality varies, but it is a good place to start.

---

## 4. PGA Tour video archives

The PGA Tour has an enormous library of professional swings.

Caveats:

- Licensing is required
- Broadcast footage is copyrighted
- Commercial use requires permission

For an academic or commercial product, expect to need a licensing agreement.

---

## 5. Professional coaching websites

Some instructors publish thousands of slow-motion swings.

Examples:

- Skillest coaches
- GolfTec
- HackMotion
- AMG (Athletic Motion Golf)

Many include face-on and down-the-line views across driver, iron, wedge, and putting.

Useful as references; check each site’s licensing terms before building a dataset.

---

## 6. Your own data collection (best long-term)

Many commercial golf AI products eventually build proprietary datasets.

Sources:

- Local teaching professionals
- Collegiate golfers
- High school golfers
- Amateur golfers
- Yourself

**Consistent setup**

- Face-on camera
- Down-the-line camera
- 120–240 fps
- Tripod
- Good lighting

Have participants sign consent forms granting permission to use recordings for machine learning.

---

## 7. Motion capture systems

If budget allows, systems that can provide synchronized swing metrics as ground truth:

- TrackMan
- Foresight GCQuad
- Swing Catalyst
- Vicon motion capture

---

## What to label

Do not only collect videos—label each swing with rich metadata:

| Label | Example |
| --- | --- |
| Golfer | Rory McIlroy |
| Club | 7 Iron |
| Camera View | Face-on |
| Handedness | Right |
| Swing Speed | 113 mph |
| Handicap | +3 |
| Club Path | In-to-out |
| Attack Angle | -4° |
| Shot Result | Draw |
| Frame of Address | Frame 14 |
| Top of Backswing | Frame 63 |
| Impact | Frame 98 |
| Finish | Frame 141 |

This metadata supports richer models than simple video classification.

---

## Pose estimation pipeline

Many successful golf swing analysis systems do not operate directly on raw video. A common pipeline:

1. Detect the golfer
2. Estimate body keypoints (shoulders, elbows, wrists, hips, knees, ankles) with a pose model
3. Track those keypoints across the swing
4. Feed the resulting time series into a temporal model (LSTM or Transformer) to classify swing phases or identify mechanics

This reduces the amount of training data needed and makes outputs easier to interpret. It aligns with the approach in [PLAN.md](./PLAN.md).

---

## Recommended starter dataset

If building from scratch, aim for:

- **2,000–5,000** professional swings (public research datasets and licensed sources)
- **10,000+** amateur swings (collected with consent)
- Both face-on and down-the-line views
- 120–240 fps when possible
- Frame-level annotations for key swing events
- Pose keypoints extracted for every frame

That combination is a strong foundation for models that analyze mechanics, compare users to expert swings, or generate personalized feedback.

---

## Implications for this project

| Stage | Practical data choice |
| --- | --- |
| Personal MVP / research | YouTube (local-only) + GolfDB + your own filmed swings |
| Supervised event detection | GolfDB / Kaggle annotated sets first |
| Commercial or redistributable product | Licensed archives + consented own collection |
| Ground-truth metrics | Launch monitor / mocap when available |

For Sunday Funday scope: start with **GolfDB + your own videos**, keep YouTube clips offline for personal analysis only, and treat proprietary collection as a later phase if the MVP proves useful.
