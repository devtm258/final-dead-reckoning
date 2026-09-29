# Persistent training architecture

The existing CSV adapter, compact neural architectures, NumPy inference, navigation filters and diagnostic map matcher are retained. This update replaces the old training loop and job handling.

## Components

| Component | Responsibility |
|---|---|
| idr/data.py | Explicit sensor columns, timestamps, segmentation, pairing and causal windows |
| idr/models.py | CNN-GRU/TCN architecture definitions, tree features, NumPy serving and metrics |
| idr/registry.py | SQLite dataset collection, immutable family roles, versions, run history and active model |
| idr/training.py | Plan validation, bounded multi-recording windows, replay, optimizer training and atomic checkpoints |
| idr/storage.py | Durable dataset/model files, atomic JSON and bounded caches |
| server.py | Upload, metadata, training, pause/resume, activation and evaluation APIs |
| DatasetCollection.jsx | Multiple file/folder import and user-confirmed acquisition groups |
| TrainingPanel.jsx | Create/continue/activate controls, saved history, progress, loss curves and recovery |

## Model and split contracts

Neural input is N×6×window at approximately 10 Hz: gravity-subtracted acceleration x/y/z (m/s²), gyro x/y/z (rad/s). Reference velocity is a target, never a network input. Neural output is forward speed plus log variance. Speeds are clipped to 0–60 m/s; reversing is unsupported. CNN-GRU uses a causal convolution with 24 channels and GRU with 32 hidden units. TCN uses three residual blocks at dilations 1/2/4, 24 channels and a 29-sample receptive field (larger input windows do not automatically enlarge this TCN).

Each recording belongs to one acquisition group and one Train/Validation/Test role in a model family. A group cannot cross roles. Source hashes reject duplicate source files with alternate import settings. User-confirmed provenance is still necessary for edited/re-encoded duplicates and related clips. The code cannot infer independent acquisitions from arbitrary filenames. Roles/group metadata lock once a run is reserved, including failed runs, so retries cannot silently repurpose held-out data.

Valid windows never cross recording/segment boundaries or invalid-label spans. Window subsampling is deterministic and capped per recording. Normalization uses selected training windows only. Continuing a model reuses the parent's normalization and best weights/optimizer, and automatically reloads earlier Train recordings when replay is enabled. Fixed validation/test assignments carry forward; parent source-level split lineage also carries forward for imported models.

No Test windows are passed to the training optimizer, early stopping, variance calibration or training metrics. Test eligibility/count checks inspect label availability; they do not evaluate the model. Navigation test endpoints reject acquisition groups reserved for training or validation. Validation trajectories can be inspected in Exploration mode. Do not tune on repeated test benchmark results.

## Crash consistency

A checkpoint is written to a temporary file, flushed/fsynced, then atomically replaced after each complete epoch. `latest.pt` contains current weights, optimizer state, epoch, updates, RNG state, normalization, history, best-so-far weights/optimizer and the complete frozen plan. Embedding best state in the same transaction prevents mismatched latest/best files after interruption.

On completion, best weights are exported to `weights.npz`, the selected optimizer to `checkpoint.pt`, and metadata is atomically marked complete. Incomplete versions never appear as inference candidates. SQLite run updates happen after checkpoint replacement; if the process dies between these operations, resume uses the checkpoint as its progress authority. Failed jobs preserve checkpoints. A changed dataset checksum prevents resuming on altered data.

A single worker serializes CPU training. SQLite transactions reserve versions and prevent a second queued/running job. This application is single-process/single-user: run one uvicorn worker, and stop it before CLI training or state-folder backup. Original versions are never overwritten by continued training. Activation is a separate explicit action.

## Example training request

Use actual saved recording IDs, and edit their acquisition groups first:

```json
{
  "mode": "create",
  "name": "CNN-GRU-35",
  "kind": "cnn_gru",
  "window": 35,
  "epochs": 20,
  "max_windows": 30000,
  "n_estimators": 60,
  "replay": true,
  "assignments": [
    {"session_id": "TRAIN_RECORDING_ID", "role": "train"},
    {"session_id": "VALIDATION_RECORDING_ID", "role": "validation"},
    {"session_id": "TEST_RECORDING_ID", "role": "test"}
  ]
}
```

Continuation uses `mode: "continue"` plus `parent_id`, the same kind/window, and new Train assignments. Prior roles are restored from the registry. Resume is `POST /api/jobs/{run_id}/resume` with no changed configuration. `GET /api/jobs` exposes progress, histories and frozen plans; `GET /api/models` lists only completed candidates.

## Navigation scope unchanged

The dashboard still uses planar replay with phone-GNSS initialization, learned speed, adaptive NHC and conservative stationary updates. The separate 3D edge engine requires calibrated frames/mounting. Diagnostic GeoJSON road matching does not feed corrections into the replay filter. No native Android/iOS sensor application, automated mounting-change detector or new heading correction is added by this training update. Old accuracy reports are historical, not evidence of improved drift from these workflow changes.
