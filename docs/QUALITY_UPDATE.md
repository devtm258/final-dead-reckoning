# Sensor quality and interface update

## Starting on Windows without Anaconda

Install Python 3.12 alongside other Python versions. Open Command Prompt in the extracted project folder containing start.py:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r backend\requirements-lock.txt
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python start.py
```

Open http://127.0.0.1:8000. On subsequent starts, activate the environment and run start.py. Keep the entire backend/state folder when upgrading; stop the previous server and back it up before copying it into the new project.

## Interface

- Datasets: upload one pair, load the preset, batch-import recordings, edit acquisition groups and assign split roles.
- Model training: choose create/continue, parent version, architecture, window, epochs and replay. Existing recovery and history are retained. For continuation, choose the parent before editing dataset selections; its fixed split roles are restored.
- Simulation & results: choose a saved recording, select a model and click Activate model, set the blackout interval, then Run simulation.

The map and speed chart use orange for VBOX reference, dashed grey for the unaided dead-reckoning baseline and cyan for AI-aided navigation. Shared checkboxes toggle these lines. Raw ML speed is an optional yellow diagnostic line. The highlighted thick cyan route segment marks blackout. Position-error curves compare both estimates against VBOX, during blackout only.

VBOX remains a reference and label source. Smartphone GNSS supplies navigation corrections outside blackout; all such corrections are withheld inside blackout. No VBOX trajectory is fed back into the estimator to improve its score.

## New signal processing

SensorQuality uses an eleven-sample trailing history, with a minimum history requirement, and per-axis median/MAD thresholds. Acceleration and angular-rate floors prevent near-zero MAD from flagging every small fluctuation. These are heuristic spike flags, not verified event labels. A timestamp deviation greater than 0.05 seconds from the nominal 0.1 seconds is flagged. Non-finite readings, nonpositive intervals and gaps above 0.5 seconds reset the processor and raise an explicit error; they are not silently imputed. Existing import segmentation prevents replay across acquisition gaps and invalid runs.

Optional smoothing is a causal first-order exponential low-pass: alpha = 1 - exp(-2*pi*cutoff*dt). The default nominal cutoff is 2 Hz, configurable up to 4 Hz for the approximately 10 Hz replay pipeline. It adds delay and is not a high-frequency anti-aliasing solution. Both acceleration and gyro are smoothed for the aided propagation path only. Raw ML windows and the baseline are unchanged. A new processor is constructed for every replay, with no cross-recording state reuse.

Quality modes:

- Off: no detection unless smoothing is requested.
- Observe (default): flag events; do not change filter uncertainty.
- Adaptive (experimental): multiply acceleration-related velocity process noise by four on acceleration flags; multiply yaw process noise by four on gyro flags. Relax lateral non-holonomic measurement variance by four at large yaw rates (>0.35 rad/s) or acceleration magnitudes (>4 m/s²). Scaling is bounded and returns to one when the triggering condition ends.

The learned speed retains its own calibrated measurement variance. Sensor anomaly flags alone are not sufficient evidence to inflate this variance. No second anomaly ML classifier is trained in this release.

## Heading investigation

Tests cover the conversion from GNSS course (clockwise from North, degrees) to planar yaw (counterclockwise from East, radians). No sign correction is introduced without evidence. Gyro and forward-axis calibration projections are displayed with insufficient-excitation warnings. Low-speed or missing initial course now produces an explicit warning. The existing calibration is still a constrained planar approximation, not a solution for arbitrary changing phone mounting angles.

Heading error is measured against reference course only at valid, moving (>2 m/s) reference samples; it is not stationary vehicle body-heading ground truth. Large directional errors remain an open accuracy risk.

## Comparisons and timing

Compare 4 variants runs the same model, recording and interval with current processing, smoothing only, adaptation only, and both. To isolate quality processing, this comparison fixes adaptive NHC, stationary updates and learned-speed aiding on, and the smoothing cutoff to 2 Hz. Single-run simulation honours the selected Advanced settings. The existing 10/30/60-second benchmark uses the default observation mode without smoothing.

Replay-step p95 includes quality processing and both estimators, but excludes the precomputed batched neural predictions. Total replay milliseconds include inference and setup. These host timings do not establish smartphone 10 Hz or external-IMU 200 Hz performance. Quality event counts include the pre-blackout warmup and post-blackout recovery shown in the replay.

The included quality-comparison.json is an exploratory ablation using the bundled CNN-GRU window-30 model and S-M/V-M recording, not a newly trained window-35 model. It reuses an already inspected held-out interval and cannot be treated as a pristine final evaluation. No benchmark pass or general improvement is guaranteed. Full SIH gaps remain in SIH_GAPS.md.

## Files

Added: backend/idr/quality.py, backend/tests/test_quality.py, docs/QUALITY_UPDATE.md, reports/quality-comparison.json.

Also added: reports/QUALITY_VALIDATION.md with measured outcomes and regressions. Removed unused frontend HeroPanel.jsx and AiSummaryPanel.jsx; full-run JSON replaces the separate report panel. The summary API is retained for compatibility.

Changed: backend/idr/navigation.py, backend/server.py; frontend/src/pages/Dashboard.jsx; frontend/src/components/TrainingPanel.jsx, SimulationPanel.jsx, MapPanel.jsx, MetricsPanel.jsx; frontend/src/index.css; frontend/tests/workflow.jsx; README.md; compiled frontend/dist assets.

Saved model formats, training optimizer/checkpoint logic and dataset split protections are retained.
