# Categorized-drive validation and reproducibility

This is a measured research prototype, **not an SIH benchmark pass or a working phone app**. Its local dashboard and training backend are functional. It still needs a native phone sensor adapter, mobile latency tests and accurate offline map fusion.

## Dataset identities and split

The delivered model family uses distinct driver acquisition groups. Train: M (Driver B) plus S1, S2, S3a, S3c and S4 (Driver A). Validation: Y1 (Driver D). Test, untouched during weight selection: Vw04 (Driver E). Paired VBOX supplies labels and scoring only; the runtime filter reads phone sensors/GNSS. Each recording is grouped by acquisition and windows stay within its own segment. Normalization is fitted on Train only; validation chooses checkpoints. Test is not passed to the training loop.

| Candidate | Saved model ID | Validation speed MAE | Epochs completed | Selection |
|---|---|---:|---:|---|
| CNN + GRU, 35 samples | `9089d396f2164f11` | 2.624 m/s | 7 of 20, early stopping | No |
| Causal TCN, 35 samples | `e95a44ff893b4342` | 2.551 m/s | 18 of 20, early stopping | Yes |

The selected TCN's held-out Vw04 speed MAE is 10.645 m/s, RMSE 13.594 m/s, and mean bias −9.807 m/s on 8,000 evenly sampled valid windows. This is severe driver/vehicle domain shift. The previous saved CNN-GRU has 11.575 m/s MAE on the same windows. Selection did **not** use these test values.

## Identical fixed-start outage protocol

All rows below use Vw04, the same two deterministic starts per duration (10/30/60 s), the same endpoint error divided by VBOX path length, original eligibility rules, no VBOX-aided filter updates and no post-hoc alignment. The previous saved CNN-GRU is a separate prior model, not the parent checkpoint of the categorized TCN. The middle row isolates revised initialization using that prior model. Comparing the first and last rows includes both filter and model changes.

| Regenerated report | Eligible trials | Pass fraction (<10% endpoint error/distance) | Median drift % | P95 drift % |
|---|---:|---:|---:|---:|
| `benchmark-before-Vw04.json` — original filter, prior CNN-GRU | 6 | 0.00 | 80.19 | 317.46 |
| `benchmark-reanchored-Vw04.json` — revised boundary reset, prior CNN-GRU | 6 | 0.00 | 64.98 | 151.84 |
| `benchmark-final-tcn-Vw04.json` — revised filter and categorized TCN | 6 | 0.00 | 98.03 | 149.32 |

The first and third rows are **not a gain** in median drift. On the final six trials, median heading RMSE is about 36.2°; some starts have no recent phone GNSS fix. An outage initiated after a pre-existing real phone-GNSS gap is a harder condition than switching from a fresh GNSS fix. To examine the latter without filtering on VBOX error, `evaluate_valid_starts.py` selects candidates using only phone fix freshness, phone speed, segment bounds and a 90-second prefix. `benchmark-valid-start-tcn-Vw04.json`: 9 eligible, pass fraction **0.00**, median **55.81%**, P95 **239.65%**. This supplementary protocol is separate from the fixed-start comparison.

## Root-cause evidence

- The original planar calibration sometimes selected the phone Y gyro channel as yaw, while it always built its lateral acceleration axis in phone XY. That cannot be assumed to form a rigid vehicle frame, especially because these legacy `Yaw/Pitch/Roll` fields need not correspond to physical XYZ. The revision estimates the lateral axis from pre-outage **phone GNSS** course change and IMU acceleration when excited; a flagged fallback remains when insufficient turns occur. This is not full device mounting calibration.
- The original filter started up to 90 s before the blackout with a potentially stale/slow first course and small yaw covariance. Its GNSS innovation gate could reject later fixes, leaving a large pre-outage position error. A causal reset to the latest **phone** position, course and speed at the blackout boundary reduced the previous model's median Vw04 drift from 80.19% to 64.98%, while P95 fell from 317.46% to 151.84%. Some blackout starts have no recent fix, so the reset cannot apply.
- The new speed model generalizes poorly from drivers A/B to E despite validation on D. Its ∼9.8 m/s mean underprediction accumulates rapidly in an outage. An online bias estimate from prior phone GNSS speed was added with uncertainty inflation; it cannot help when the phone has no timely fixes and it does not solve heading drift.
- `idr/mapmatch.py` remains an independent diagnostic matcher; the scored ESKF never uses its map path as a measurement. The separate 3D `eskf3d.py` assumes verified sensor-to-vehicle rotation. Neither module can be cited as a measured cause of lane-level accuracy here.
- The supplied paired VBOX is a reference with its own synchronization and quality limits. A single static 10% endpoint measure can conceal intermediate excursions; inspect the JSON's maximum, along-track and cross-track errors.

**Conclusion: this implementation does not cross the supplied <10% benchmark.** The hypothesis that heading, initialization and cross-vehicle speed shift dominate was supported, but the corrections and retraining were insufficient. More hyperparameter tuning on Vw04 would contaminate this test; collect a new final held-out drive before further selection.

## Reproduce

The deliverable's `backend/state` contains the saved models, grouped recordings and SQLite run history. From its root, install `backend/requirements-training.txt`, then:

```text
cd backend
python evaluate_release.py b82c60b0547756df e95a44ff893b4342 ../reports/recheck-tcn-Vw04.json
python evaluate_valid_starts.py b82c60b0547756df e95a44ff893b4342 ../reports/recheck-valid-start.json
```

The model inference path uses saved NumPy weights and does not require Torch; further neural training does. In two fresh Python processes the same saved TCN produced the identical SHA-256 prediction hash `81130af14e165b9983ff6c7454e62aeb84e48a2ca20289adbe9907330174d146` on the first ten Vw04 windows. The backend test suite passed **31/31** with `PYTHONPATH=backend python -m pytest backend/tests -q`; the Vite production build passed. An actual phone or browser visual test was not available in this environment.
