# Training workflow update — 23 September 2026

This release adds persistent multi-recording training to the existing navigation project. It does not replace the navigation filter or demonstrate a new positioning benchmark result.

## Added files

- `backend/idr/registry.py`: SQLite dataset, model-family, role, job and activation registry.
- `backend/idr/training.py`: shared training service, parent continuation, replay and atomic epoch recovery.
- `backend/tests/test_training_workflow.py`: continuation, restart, leakage and API integration tests.
- `frontend/src/components/DatasetCollection.jsx`: batch CSV pairing, recording metadata and split selection.
- `frontend/tests/run-workflow.mjs` and `frontend/tests/workflow.jsx`: automated DOM workflow tests.
- `docs/TRAINING_UPDATE.md`: this change and verification record.

## Changed files

- `backend/server.py`: training, dataset metadata, family and job endpoints; startup recovery; held-out evaluation protection.
- `backend/idr/storage.py`: preserve existing saved data on identical re-upload.
- `backend/idr/models.py`: remove the superseded training implementation; retain shared architecture and inference.
- `backend/run_training.py`: use the same training service as the website.
- `backend/requirements-test.txt`: include neural-training dependencies for recovery tests.
- `frontend/src/components/TrainingPanel.jsx`: create/continue, versions, replay, history, pause/resume and training evidence.
- `frontend/src/components/SimulationPanel.jsx`: explain unavailable held-out evaluation for training recordings.
- `frontend/src/pages/Dashboard.jsx`, `frontend/src/lib/api.js`, `frontend/src/index.css`: connect collection and training controls to the existing interface.
- `frontend/package.json` and `frontend/package-lock.json`: version and reproducible frontend test dependencies.
- `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_AND_RESEARCH.md`: updated setup, workflow and storage documentation.
- `frontend/dist/`: regenerated production assets; no Node installation needed to run the packaged interface.

## Verification scope

Backend tests check that continuing starts from the selected parent's weights, performs optimizer updates, replays previous recordings, preserves older versions, and keeps test data out of training. Both CNN-GRU and TCN recovery tests resume in a new Python process and compare weights and history against uninterrupted training. Other tests cover acquisition leakage, changed input bytes, fixed split roles, persisted activation, and real API job submission.

Frontend DOM interaction tests cover dataset roles, new training, pause/resume and continued training with replay. Production build and unused-import/local checks pass. A real browser visual check was not completed because the Chromium download failed; DOM tests do not establish visual layout correctness.

Synthetic recordings used in automated tests verify software behavior, not model accuracy. No new 15-recording training run, phone latency measurement, or SIH benchmark pass is claimed. Historical accuracy reports remain in `reports/` and should not be interpreted as measurements of a newly trained model.

Dependencies, caches, temporary test data and generated registry databases are excluded from the download. The two supplied legacy models and compressed example dataset are retained for a working starting point. Your own saved state must be migrated as described in README.
