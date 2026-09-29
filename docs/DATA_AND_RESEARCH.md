# Data feeding and next experiments

## First: labelled data and honest benchmarking

The supplied pair has 105,974 rows at roughly 10 Hz, one elapsed-clock reset, three acquisition segments and mostly repeated phone GPS positions. The adapter uses wall-clock ordering, separates gaps/resets, explicitly maps columns and diagnoses speed units against VBOX. The phone speed header appears inconsistent with its values: automatic diagnosis chooses m/s; verify logger documentation. Repeated coordinates do not reveal the exact measurement timestamp, so residual stale-fix delay is a limitation.

Reference synchronization is label preparation, not a runtime input. The default bounded lag calibration uses initial motion per segment, producing lags 9/20/32 samples for this pair. A smaller correlation of 0.6545 in the middle segment deserves manual verification. Row pairing relies on the supplied paired-recording relationship; unrelated files must not be paired by row count. Use explicit unit/alignment controls and inspect the quality report. Preserve raw recordings.

CSV adapter requires `TIME SINCE START` (milliseconds), `GPS LATITUDE`, `GPS LONGITUDE`, `GPS SPEED`, accelerometer X/Y/Z and gyroscope X/Y/Z (or legacy Roll/Pitch/Yaw). Gravity X/Y/Z is strongly recommended; missing gravity uses a z-up approximation inappropriate for arbitrary mounting. Optional DATE is parsed with the supplied logger format, GPS ORIENTATION and GPS ACCURACY. Use `data.py` as the exact contract. Other raw formats require an explicit adapter, not guessed columns.

Collect several independent drives, devices, mounting angles, vehicles, temperatures, stops and turns. Split by acquisition/vehicle/route before windows; never split shuffled windows. The v3 interface and API use explicit `assignments` with Train/Validation/Test roles and acquisition groups. Earlier roles remain fixed during continued training. Keep train/test identities stable and do not tune constraints on the final test set. Same recording copied with changed encodings requires manual duplicate control beyond byte hashes.

Prioritized experiments:

1. Verify axis signs, angular-rate units, gravity convention, reference lag and GPS latency; quantify timestamp uncertainty. A speed network cannot repair wrong heading alignment.
2. Benchmark fixed initialization versus actual last-phone-fix initialization to expose initial position/yaw errors. The included benchmark uses actual operational phone fixes and no post-hoc trajectory alignment.
3. Keep ExtraTrees, TCN and CNN-GRU on identical split manifests and sample budgets. Current training budgets differ; packaged comparisons are exploratory, not a controlled architecture study.
4. Sweep causal receptive field and update spacing on validation only. Add physically plausible bias, rotations and noise augmentation with consistent coordinate transforms; do not rotate labels incorrectly.
5. Test NHC off/fixed/adaptive, ML off/on, ZUPT off/on. Measure false ZUPT triggers, stop precision, heading error, cross-track/along-track error, endpoint/max position error and error versus outage duration/distance.
6. Add calibrated motion-state/constraint covariance models after the deterministic filter baseline is understood. Correlated overlapping windows cannot be treated as independent measurements without accounting for correlation.
7. Move to unseen vehicle/mount tests, speed strata and 50 m / 1 km scenarios. Report coverage and worst-case failures. More test runs are required than the packaged six-per-model diagnostic suite.

## Then: unlabelled / uncategorised data

Do not feed arbitrary files directly into supervised training or turn current model predictions into unquestioned ground truth. Preserve source schema, units, sensor clocks, sampling frequency, frame convention, device/vehicle/mount IDs, GPS quality and consent/provenance. Build an adapter into the existing six-channel contract. Segment resets and phone movement, quarantine invalid rows, and produce a quality report first.

If good GNSS/reference exists outside outages, synchronize it, mark label validity and derive robust velocity targets with known delay. If no usable reference exists, retain data for domain characterization or self-supervised pretraining; do not call it labelled benchmark data. Pseudo-labels should carry uncertainty and remain separate from independent ground truth. A later semi-supervised pipeline is not implemented in this package.

## Research starting points

- AI-IMU Dead-Reckoning: https://arxiv.org/abs/1904.06064 — learned constraint covariance and invariant filtering.
- TLIO: https://arxiv.org/abs/2007.01867 — learned displacement uncertainty and filter updates.
- RoNIN: https://arxiv.org/abs/1905.12853 — learned inertial odometry and generalization evaluation.
- Search exact terms: `vehicle smartphone IMU speed observability`, `causal TCN vehicle odometry`, `non holonomic constraints lever arm sideslip`, `IMU GNSS time synchronization delay estimation`, `NIS NEES learned measurement covariance`, `inertial odometry overlapping windows correlation`, `Allan variance MEMS thermal bias`, `HMM map matching stacked roads`.
- ONNX Runtime mobile deployment: https://onnxruntime.ai/docs/tutorials/mobile/ . PyTorch reproducibility: https://pytorch.org/docs/stable/notes/randomness.html . OSM attribution/license: https://www.openstreetmap.org/copyright . SIH official portal: https://sih.gov.in/ .

The user's supplied paper summaries were design inputs, not verified implementation specifications. No quoted percentage gain from another dataset is promised here. Standard temporal convolutions mix channels; inertial drift is not universally exponential; a zero-velocity update and a zero-angular-rate update are distinct. Position ATE, endpoint drift and windowed relative errors are different metrics and must be named accurately.
