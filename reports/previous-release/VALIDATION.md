# Recorded-data validation

These measurements are from the supplied S-M/V-M pair, with purged chronological 70/15/15 splits. They are not unseen-vehicle results. No test-based parameter selection was performed in this build; further development must use a new untouched final test set. Default CNN-GRU selection uses validation MAE.

| Candidate | Model ID | Validation MAE (m/s) | Test MAE (m/s) | Test RMSE (m/s) | Desktop inference P95 (ms) |
|---|---|---:|---:|---:|---:|
| extra_trees | 2c4ca75ea7284972 | 2.205 | 2.755 | 3.529 | 3.820 |
| tcn | 5444c7b9d9134101 | 1.988 | 2.812 | 3.695 | 0.979 |
| tcn | 4a04f57f33ec44b2 | 1.939 | 2.638 | 3.528 | 0.710 |
| cnn_gru | 5953a00cc3994cd1 | 1.573 | 3.429 | 4.477 | 1.381 |

Timing uses one 30-sample window, 25 timed calls after warmup, this host CPU, and NumPy serving (single-thread tree inference). It excludes phone sensor collection, resampling, map rendering and network. Host values are not mobile guarantees. This table uses remeasured serving latency; generated training logs are omitted from the lean package.

## Outage tests

10/30/60-second outages at two fixed starts each, using actual phone GNSS initialization, no reference-assisted heading, and no post-hoc trajectory alignment. Six trials per candidate are only a diagnostic sample. Stops/very short travel are excluded from percentage-drift eligibility, not counted as passes.

| Report | Eligible trials | Pass fraction (<10% endpoint error/distance) | Median drift % | P95 drift % |
|---|---:|---:|---:|---:|
| benchmark-4a04f57f33ec44b2.json | 4 | 0.00 | 20.80 | 32.66 |
| benchmark-5953a00cc3994cd1.json | 4 | 0.00 | 16.32 | 24.09 |
| benchmark-extra_trees.json | 4 | 0.25 | 18.35 | 43.89 |
| benchmark-tcn.json | 4 | 0.00 | 21.68 | 28.48 |

**Conclusion: the supplied tests do not establish the required benchmark.** The best speed-validation candidate is not necessarily the best trajectory candidate. The expanded TCN has lower test speed MAE than the tree baseline, but its measured outage pass rate does not improve. Architecture choice alone does not repair heading, initialization and domain shift. No percentage improvement over the original backend is claimed because an equivalent untouched old/new test protocol has not been run.

Reference alignment depends on recorded pairing and bounded prefix lag estimates. Import preprocessing may inspect reference metadata to construct labels; runtime propagation never accesses reference telemetry. Reference accuracy and repeated phone-GPS timestamps limit interpretation. Maximum and lateral errors are included in JSON because endpoint error alone can hide excursions. Current reports do not provide a complete standard RTE/ATE research suite.

## Verification scope

The original build passed 15 tests; see OPTIMIZATION.md for lean-build verification. Tests cover causal inference, Torch/NumPy parity, gap-safe windows, filter constraints/covariance, independent blackout inputs, invalid intervals and API validation. The 200 Hz test is synthetic strapdown propagation, not a real FOG benchmark. Historical restart/export/API checks are recorded in integration-checks.json. Frontend production build succeeds; browser execution could not be verified because the browser binary download failed in this environment.

Final automated suite: **15 passed**. ONNX/NumPy parity passed for both exported networks. Two fresh processes loaded the saved associated model and returned identical predictions. In-process HTTP integration passed for the compiled UI, model listing/attachment and an actual 30-second simulation.
