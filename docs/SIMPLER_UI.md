> This describes the earlier UI-only update. The new Results dashboard also changes backend calculations: follow RESULTS_UPDATE.md for the current upgrade procedure.

# Simpler workspace update

The original dark green, ivory and yellow palette, typography, cards and bottom dock are preserved.

## Everyday testing
1. Open **Data**. Select both S-*.csv and V-*.csv, or choose an extracted folder.
2. Click **Test this** on the recording.
3. Choose a saved model. All saved versions are available in the dropdown.
4. Enter blackout start and duration, or use the 10 / 30 / 60 second duration shortcuts.
5. Click **Run test & view results**. Results open automatically with the route, speed and error plots.
6. Use **Back to test setup** for another interval.

Uploading does not train a model. Exploratory tests remain labelled Exploration; the held-out benchmark remains restricted to a saved model's Test recordings.

## Training
On Data, expand **Training role & recording details** to edit recording names, acquisition groups and Train / Validation / Test assignments. Clips from the same original drive must share a group.
Open **Train**, choose a new model or an existing version under **Start from**, and start training. Continued training retains earlier-data replay. Pause/resume remains available for the current job.

## Advanced controls
- Test → Advanced test settings: estimator and held-out benchmark.
- Train → Saved model versions: saved versions and validation metrics.
- More → Open engine diagnostics: diagnostic console.
- More → Switch mode: device workspace.

## Upgrade an existing installation
Stop the server and back up your existing project. Copy only this package's **frontend** folder into your existing project, replacing the old frontend files. This includes the compiled frontend/dist, so no Node build is needed to run it. Keep your existing backend/state folder; do not overwrite it with the sample state from this package. Restart with `python start.py` and refresh your browser (Ctrl+F5 if necessary).

For a fresh installation, extract the complete package and follow README.md.

## Changes
frontend/src/App.jsx; components/nexus/Train.jsx, Dock.jsx, Settings.jsx, Replay.jsx, ReplayPlot.jsx; frontend/src/index.css; rebuilt frontend/dist; frontend/package.json and package-lock.json; frontend/check-ui.mjs; this guide; README.md.

Backend source, model weights and navigation algorithms were not changed. Existing benchmark reports still describe the earlier navigation audit; no new accuracy claim is made by this interface update.

## Verification
Production build passed. Automated DOM interaction checks passed for navigation, all model versions, disabled run gating, simulation request, automatic Results navigation, selection persistence, recording-change reset, continued-training payload with replay, and diagnostics access. Run `npm ci`, `npm run test:ui`, and `npm run build` in frontend to reproduce.
Browser visual verification was unavailable: Chromium download failed. DOM checks do not establish pixel-level or mobile-browser rendering correctness.
