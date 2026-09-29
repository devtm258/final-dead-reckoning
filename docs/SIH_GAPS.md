# SIH requirements and remaining work

This implementation maps to the problem statement supplied in the conversation. Official https://sih.gov.in/ and the problem-statement portal returned access errors during research. Current event-wide rules, submission formats, team eligibility and exact evaluator protocols were not independently verified. Do not claim official compliance based on this package.

| Supplied requirement | Implemented | Still required |
|---|---|---|
| Smartphone alignment/calibration | Pre-outage phone-GNSS projection calibration in replay; explicit 3D mount transform | Reliable full automatic pitch/roll/yaw, mount-change detection and reinitialization on real phones |
| AI speed/vibration filtering | Causal TCN, CNN-GRU, tree baselines; robust loss; IMU-only speed features | Separate pothole/phone-motion classifier; cross-vehicle vibration generalization; measured real-world suppression |
| NHC/ZUPT | Adaptive heuristic covariance, gated constraints, conservative stationary logic | Validate on turns, slopes, slip, idling, electric vehicles and motorcycles; learned NHC covariance optional research |
| GNSS+INS fusion | Planar replay EKF and separate 3D error-state engine; learned-speed uncertainty | Phone/device validation; magnetometer gating; heading recovery; smooth recovery under bad fixes |
| GNSS deficit transition | Fix validity/freshness handling and inertial continuation | Measured blackout detection/recovery latency on native phone APIs |
| Offline maps | Local diagnostic GeoJSON beam matching | Routing-aware HMM integrated with uncertainty; offline tile pack; multilayer ambiguity |
| Working mobile navigation app | Responsive redesigned research dashboard; portable engine and exports | Native Android/iOS IMU/GNSS capture, lifecycle, battery and real-time map integration |
| External IMU support / ~200 Hz | 3D engine accepts calibrated samples; synthetic 200 Hz propagation test | Actual FOG device adapter, accuracy and sustained real-device timing |
| <10% blackout drift | Honest multi-outage evaluation with eligibility guards | Consistent held-out success; provided results do not establish this |
| 10 Hz phone output / lane-level accuracy | 10 Hz recording replay and small models | Device profiling and lane-level reference tests; 10% drift is not equivalent to lane-level positioning |
| IO-VNBD preliminary model / plots | Supplied paired recording, saved trained candidates, UI trajectory plots, metrics JSON | Confirm dataset provenance/license and export required proposal artifacts in official format |

These gaps are substantive. In particular, an unconstrained IMU cannot uniquely observe absolute constant speed; vibration-based learning relies on vehicle/road correlations. Do not promise that a new architecture alone guarantees the benchmark. Test initial heading, reference synchronization and GNSS initialization error separately from inertial drift.
