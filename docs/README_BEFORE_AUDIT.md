# Tesseracts IDR — local research workspace

The redesigned dashboard is served by the existing FastAPI service. It has no Base44 dependency or login. Uploaded paired S/V recordings, training jobs, checkpoints and model versions persist under `backend/state`. The packaged model is a causal TCN trained on categorized IO-VNBD driver groups. **It does not currently meet the <10% SIH drift benchmark**, and the live phone navigation panel has no mobile sensor adapter. Read [reports/VALIDATION-2026.md](reports/VALIDATION-2026.md) and its regenerated benchmark JSON before using any result in a proposal.

## Run on Windows / Anaconda Prompt

```bat
conda create -n tesseracts-idr python=3.12 -y
conda activate tesseracts-idr
cd C:\path\to\Tesseracts-IDR
python -m pip install -r backend\requirements-training.txt
python start.py
```

Open `http://127.0.0.1:8000`. Stop with Ctrl+C. A subsequent `python start.py` reads the same disk models and SQLite registry. To serve and replay only, `backend/requirements.txt` omits PyTorch; neural training needs `requirements-training.txt`.

## Training and inspecting actual data

1. Enter **MODEL TRAINING → Train**. The packaged recordings and two real saved model versions are listed. Click a saved model card to activate it for the selected recording.
2. To add recordings, select matching `S-*.csv` and `V-*.csv` together, or choose an extracted folder containing pairs. The importer groups clips by the Driver label in the folder name. Review and save each acquisition group; clips from the same original drive must share a group.
3. Assign entire groups to **Train**, **Val** and **Test** with at least one labeled recording in each. Choose a new model family, or select a saved CNN-GRU/TCN as the parent for continued training. Test assignments are fixed for a model family; new Train recordings create a saved version with a new ID.
4. Click **TRAIN & SAVE**, watch actual epoch loss and validation speed MAE, and activate a completed saved card. Early stopping can finish before the maximum epoch setting. The model weights, optimizer checkpoint and job history survive a restart.
5. Select a paired recording and click **RUN INFERENCE ON SUBSET**. Open **Replay** for actual VBOX reference, unaided inertial baseline and fused traces. For an attached held-out Test recording, **BENCHMARK 10 / 30 / 60 s** runs the backend scorer. Training screens never show manufactured metrics.

The backend expects the IO-VNBD CSV schema used here, approximately 10 Hz inertial samples and correctly synchronized S/V timestamps. It rejects incomplete/ambiguous time series instead of inventing alignment. Two categorized source clips with backwards phone wall-clock timestamps were deliberately rejected. The importer has a bounded, checked repair only for a locally consistent duplicate VBOX timestamp. Arbitrary dataset formats need a validated adapter.

## Build or change the UI

The prebuilt `frontend/dist` is served automatically by `python start.py`. After editing `frontend/src`:

```bat
cd frontend
npm ci
npm run build
cd ..
python start.py
```

The source retains the supplied design's mode selection, training, diagnostics, replay and dock. Live navigation explicitly reports an unavailable phone stream. It is a local web research dashboard, **not** an Android/iOS mobile application, offline road navigation engine or 200 Hz FOG benchmark. The map matcher is currently diagnostic and is not part of the scored fusion path.

## What remains

Validate complete phone mounting calibration and GNSS reacquisition on real hardware; integrate and evaluate map matching in the filter; gather varied labeled drives with trustworthy timing; and reserve a fresh unseen driver for final screening. Official SIH 2026 submission rules were not independently established from the accessible website, so this package makes no compliance certification.
