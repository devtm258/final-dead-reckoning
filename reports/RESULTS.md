# Engineering audit and measured results — 26 September 2026

**The requested all-runs-below-50% goal is NOT achieved.** This is an improved research prototype, not a perfect model or an SIH benchmark pass.

## Main matched comparison

The unchanged uploaded refined engine and the final candidate were evaluated on the same 72 predetermined intervals across eight paired recordings. All scenarios were selected from sensor timestamps and segment boundaries, not from reference errors: 10, 30 and 60 seconds, at the 10th, 50th and 90th percentiles of usable segment duration, with 120 seconds of preceding sensor history. Two S1 scenarios travelled less than 5 metres (0.49 m and 4.09 m), so percentage drift is undefined by the existing eligibility rule. They remain in the JSON with their metre errors; they are not counted as passes. Both have full reference coverage.

Drift = 100 × absolute endpoint position error / VBOX path length during the blackout. There is no post-hoc trajectory alignment, scale matching, VBOX runtime update, or error-dependent scenario selection. Maximum and along/cross-track errors are also retained.

| Metric | Uploaded refined engine | Final vehicle estimator |
|---|---:|---:|
| Attempted scenarios | 72 | 72 |
| Scorable scenarios | 70 | 70 |
| Below 50% | 27 / 70 | **65 / 70** |
| Median drift | 66.99% | **12.89%** |
| Worst drift | 66,566.46% | **68.98%** |
| Below original 10% target | See JSON | 26 / 70 |

The very large original outlier is included unchanged; it reflects a diverging estimator, not a formatting error. Below are all recording groups, including failures.

| Recording | Original below 50% | Final below 50% | Final median | Final worst |
|---|---:|---:|---:|---:|
| S4 | 1/9 | 8/9 | 13.03% | 68.98% |
| S3c | 2/9 | 9/9 | 8.83% | 33.83% |
| S2 | 2/9 | 7/9 | 13.22% | 60.90% |
| S (Driver A)/S1 | 3/7 | 6/7 | 10.42% | 56.28% |
| Y (Driver D)/Y1 | 5/9 | 9/9 | 9.36% | 33.76% |
| S3a | 4/9 | 8/9 | 16.23% | 63.35% |
| Vw04 (Driver E) | 3/9 | 9/9 | 15.23% | 20.37% |
| M (Driver B) | 7/9 | 9/9 | 10.58% | 24.41% |

## Early-blackout stress test — also included, not hidden

The original six Vw04 scenarios start at 15 seconds or near the recording's end. The final estimator passes **3/6 below 50%**, with a worst drift of **137.14%**. The three outages beginning at 15 seconds fail: there are too few fresh moving phone fixes to identify the sensor-to-vehicle transfer reliably. Their results are 107.03%, 132.22% and 137.14% for 10/30/60-second outages. The interface reports provisional calibration; the evaluator does not silently exclude these failures.

This is why the 65/70 result cannot be presented as an all-conditions guarantee. The main suite gives the system a longer preceding history. Choosing the longer-history suite does not make the early-start failures disappear.

## Remaining failures in the main suite

| Recording | Start | Duration | Drift |
|---|---:|---:|---:|
| S4 | 1026.670 s | 10 s | 68.98% |
| S2 | 1180.748 s | 30 s | 55.21% |
| S2 | 1204.748 s | 60 s | 60.90% |
| S (Driver A)/S1 | 4614.149 s | 60 s | 56.28% |
| S3a | 2217.900 s | 10 s | 63.35% |

These failures predominantly involve speed transitions, stops, and absolute phone-position initialization error. The S1 failure travels only 21.67 m; a roughly 9.5 m starting error already consumes much of its 50% allowance. More model training cannot remove an unknown absolute initial-position error.

## Evidence limits

These are **development replays**, not a new untouched test evaluation. Some drives trained the bundled networks; Y1 was validation; Vw04 was previously called test but has now repeatedly informed diagnosis. All changes above were inspected against these recordings. A fresh acquisition is required for an independent final result. No smartphone inference-time, battery, tunnel deployment, wheel-mounted hardware, or lane-level certification is claimed.

The TCN weights were preserved, not secretly retrained on Vw04. The new small transfer regressions are fitted from **pre-blackout phone data** for each replay. Existing CNN–GRU/TCN creation, continued training, replay and epoch checkpoints remain available.

## Which uploaded repository works?

| Upload | Identity | Actual check | Relevance / limitation |
|---|---|---|---|
| PROJECT 1.0 | AI-IMU Dead-Reckoning | NumPy filter executed a 10-second synthetic 5 m/s trajectory, ending at [50,0,0] m | Strong vehicle-filter research reference. Uploaded archive lacks KITTI data and trained adapter weights; published KITTI results not reproduced. |
| PROJECT 2.0 | Android DeadReckoning | Inspected step counters and Android build; attempted Gradle build | Pedestrian app, not vehicle velocity inference. Build blocked at unavailable Gradle distribution; no APK/device test. |
| PROJECT 3.0 | Wheel-INS | Compiled C++; ran supplied robot recording after correcting example paths; 183,000 finite output rows over 915 s | Runnable specialist system. Requires an IMU physically mounted on a rotating wheel and wheel radius. No new independent accuracy claim from this smoke run. |
| PROJECT 4.0 | Smartphone yaw walking demo | Executed supplied Python plotting example | Uses a fixed 0.97 m/s walking speed and rescales/shifts estimated paths to GPS; unsuitable as honest vehicle-blackout benchmark. |
| PROJECT 5.0 | MATLAB PDR coupled with GNSS | Inspected stride, step, attitude and fusion code | Pedestrian model. MATLAB/Octave unavailable; original sensor files referenced by hard-coded paths are absent. Not executed end to end. |
| Tesseracts-IDR(1) | Refined full application | Original 31 backend tests passed after installing requirements; actual recorded-data benchmark reproduced | Best integration base, but importer leakage and navigation defects required corrections. |

No external repository was blindly merged. The delivered vehicle estimator is new code informed by these methods, not a reproduction of their full invariant filters or their published accuracy.

## Changes implemented

- Removed the incorrect tilt rotation and full-recording VBOX-derived mounting rotation from new imports. Restored raw gravity-subtracted sensor channels consistent with the bundled weights. Bumped importer identity.
- Added a guard rejecting saved datasets marked with that reference-derived mounting calibration; re-import those original S/V files. Shipped saved datasets lack that marker and use the original raw channel representation.
- Added robust phone-prefix calibration of gyro and acceleration transfer functions, including circular course handling across sparse fixes and explicit insufficient-calibration warnings.
- Added scalar-speed vehicle propagation with midpoint turn integration, bounded acceleration, nonnegative speed, and a no-side-slip assumption. This is a planar vehicle approximation, not full 3D navigation.
- Added learned-speed bias/trust estimated from actual pre-blackout phone residuals, bounded/gated updates, and propagation through the age of the last phone fix. Runtime sensor regression uses no VBOX values.
- Removed an incomplete centripetal measurement Jacobian and implicit map pseudo-position updates from the ESKF comparison. Offline map matching remains a separate diagnostic module.
- Added explicit estimator/start/duration controls, visible failures and calibration warnings, consistent route/speed/error plots and line toggles. Geographic plot aspect now accounts for latitude.
- Kept versioned neural training, replay, fixed split restrictions and restart checkpoints.
- Added reproducible multi-recording evaluation and leakage/causality/regression tests.

## Model and ablation selection

On the nine Y1 validation-navigation cases, TCN + final vehicle mode had a 9.36% median and 33.76% worst drift. CNN–GRU + the same mode had a 13.53% median and 43.55% worst. Both were below 50% on all nine; TCN remains the default candidate.

A weak learned-speed update passed 66/70 but left a 286% worst case. Stronger locally calibrated trust passes 65/70 but reduces worst error to 69%, improving the objective of limiting severe failures. An affine speed adapter was also evaluated and rejected: it left a 214% worst case. All ablation JSON files are retained, not silently discarded.

## Reproduce

From the extracted project root, after installation:

```bat
python backend/evaluate_audit.py --output reports/recheck-development.json
cd backend
python evaluate_release.py b82c60b0547756df e95a44ff893b4342 ../reports/recheck-original-six.json
```

`audit-original.json` records the unchanged uploaded engine. `audit-speed-trust.json` records the selected final algorithm (before diagnostic-only fields and low-data fallback refinements; none of its full-calibration cases use that fallback). `final-original-six-starts.json` includes the final fallback behavior. `model-comparison-validation.json` records both networks. Exact source changes are listed in `docs/CHANGED_FILES.md`.

## Research consulted

1. Brossard, Barrau & Bonnabel, **AI-IMU Dead-Reckoning**, https://arxiv.org/abs/1904.06064 — learned uncertainty with vehicle constraints and inertial filtering. Its KITTI result is not a phone benchmark.
2. Qian et al., **AVNet**, Satellite Navigation (2025), https://link.springer.com/article/10.1186/s43020-025-00168-7 — learned attitude and velocity plus an invariant filter; evaluated on its own parking-lot data. It supports addressing heading as well as speed, not assuming a larger speed network solves navigation.
3. Niu, Wu & Kuang, **Wheel-INS**, https://arxiv.org/abs/1912.07805 — wheel rotation provides speed and bias modulation; that hardware assumption does not hold for a dashboard phone.
4. Brossard et al., **RINS-W**, https://arxiv.org/abs/1903.02210 — detect when motion constraints are valid rather than applying them indiscriminately.

## Verification and remaining deployment limits

**41 backend tests passed**, including continued training, restart recovery, importer reference isolation, future/blackout-input causality and circular heading regression. The production frontend build, DOM interaction test and HTTP startup test also passed. See `tests-final.txt`, `frontend-build.txt`, and `frontend-interactions.txt`. The interface interaction test runs in a DOM simulation, exercising dataset loading, model activation, blackout request values, charts and visibility toggles. Chromium download failed, so an actual browser visual check is unverified. The FastAPI test client also executed a real saved-model simulation successfully.

The next accuracy work should address delay in speed transitions, device/mount-specific calibration and initial phone-fix quality, followed by a frozen evaluation on new drives. Achieving every arbitrary blackout below 50% is not established by this deliverable.
