> **Results dashboard update:** Data → Test → **Results** now shows route maps, travelled distances, distance errors, endpoint errors, full position-error charts, heading/quality diagnostics and benchmark tables. See [docs/RESULTS_UPDATE.md](docs/RESULTS_UPDATE.md).
>
> **Upgrade requires backend and frontend changes.** Stop the app, back up your project, then replace `frontend/`, `backend/idr/`, and `backend/server.py` from this package. **Keep your existing `backend/state/` unchanged.** Restart with `python start.py` and press Ctrl+F5. Run a new test to populate the new measurements. No Node build is needed.

# Tesseracts IDR — audited vehicle-navigation prototype

**This release improves measured replay performance but does not meet every-run-below-50%.**

| Recorded-data evaluation | Below 50% | Median drift | Worst drift |
|---|---:|---:|---:|
| Uploaded refined engine, main suite | 27/70 | 66.99% | 66,566.46% |
| Updated vehicle estimator, same suite | **65/70** | **12.89%** | **68.98%** |
| Updated estimator, original six early/end starts | **3/6** | 69.25% | 137.14% |

The main suite attempted 72 cases on eight recordings; two were below the 5-metre travel threshold and were not counted as passes. These are development replays, including previously used training/validation data, not fresh final-test evidence. Read **reports/RESULTS.md** for full methods, per-recording results, failures, repository audit and research links.

## Start on Windows without Anaconda

1. Extract this ZIP into a **new folder**. Keep your old installation and `backend\state` backup.
2. Open Command Prompt in the folder containing `start.py`.
3. Use Python 3.12:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-lock.txt
python start.py
```

Open **http://127.0.0.1:8000**. The frontend is already compiled; Node.js is not needed to run it. Keep the terminal open. Ctrl+C stops it.

For **neural training**, also install PyTorch before starting:

```bat
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Next time:

```bat
cd /d "YOUR EXTRACTED PROJECT FOLDER"
.venv\Scripts\activate
python start.py
```

If Python 3.12 is absent, install it alongside your other Python version. Do not run this tested environment with a different interpreter and assume dependency compatibility.

## Run an actual replay

1. The app opens the training/replay workspace directly.
2. Select the recording in the saved-recordings list.
3. Click the saved **Categorized tcn 35** model card to activate it for that recording. Its model ID is `e95a44ff893b4342`.
4. Set **Navigation estimator → Calibrated vehicle + learned speed**.
5. Enter **Blackout start** and **Duration** in seconds. Prefer at least 120 seconds of preceding sensor history for meaningful calibration. Early-start cases are still allowed and can fail.
6. Click **RUN SELECTED BLACKOUT**.
7. Open **Replay** for the three route traces, matching speed traces, position errors, threshold result and calibration warnings.
8. Use **BENCHMARK 10 / 30 / 60 s** for the existing fixed-start test protocol; it deliberately includes difficult early starts. It is not the same protocol as the expanded 120-second-prefix suite.

VBOX is an independent scoring/reference source. It is not fed into navigation during blackout. The inertial baseline remains a comparison; “AI-aided navigation” uses the selected vehicle estimator and saved speed network. Raw network speed is an optional fourth speed trace.

The alternative **Planar ESKF comparison** remains available. Its smoothing/quality experiments are separate from the new vehicle estimator. Vehicle mode currently supports observation-only quality flags; requesting its unsupported smoothing/adaptation settings produces an explicit error.

## Continue training the same network

1. Import the matching S/V CSV pairs (or an extracted dataset folder).
2. Save each recording's acquisition identity. Related clips from one acquisition must share an identity.
3. Assign Train, Val and Test using separate acquisitions. Never reuse a previously trained recording as an unseen test.
4. For a new model choose **Create new family**, architecture, window (e.g. 35), epochs and name.
5. For more learning choose the parent under **Continue saved model**. Its architecture and window are preserved. The current interface includes earlier training recordings automatically (`replay=true`).
6. Click **CONTINUE TRAINING**. A new version is saved; the parent is retained.
7. Use **Resume** for an interrupted/paused run. Completed-epoch checkpoints restore progress.

Uploading alone does not update weights. No neural weights were retrained for this audit: the two supplied networks were compared using identical validation-navigation cases and TCN was retained. The new sensor-transfer model learns from earlier phone fixes within each replay.

## Your previous saved data

The included state contains the supplied saved datasets, CNN–GRU/TCN weights and registry. Do not blindly overwrite it with an old folder: preserve backups and compare your versions first. If you point `IDR_DATA_DIR` at another complete state directory, its datasets and model records are used instead.

The local-engine importer introduced a full-recording VBOX-derived mounting correction. The corrected reader rejects saved datasets marked `mount_yaw_deg`: re-import their original S/V files. Models trained on those contaminated inputs should be retrained in a fresh family. The shipped saved datasets lack that correction and retain raw device-frame inputs compatible with the supplied weights.

## Reproduce evaluation and tests

```bat
python backend\evaluate_audit.py --output reports\recheck-development.json
cd backend
python evaluate_release.py b82c60b0547756df e95a44ff893b4342 ..\reports\recheck-original-six.json
cd ..
python -m pip install -r backend\requirements-test.txt
set PYTHONPATH=backend
python -m pytest backend\tests -q
```

`docs/CHANGED_FILES.md` lists additions and edits. `reports/RESULTS.md` is the authoritative report for this release; `reports/previous-release` and `docs/README_BEFORE_AUDIT.md` are historical.

## Limits

This is recorded-data vehicle navigation, not a finished phone app. Live phone acquisition, phone latency, native deployment, full 3D/parking-floor positioning and operational map fusion remain unverified. A fresh drive is needed for an independent final evaluation. Neither <50% on every case nor the original <10% target is established.
