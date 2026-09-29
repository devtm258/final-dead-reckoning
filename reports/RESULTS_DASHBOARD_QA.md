# Results dashboard verification

- Full backend suite: 45 tests passed after the results calculations and API changes.
- Final focused results suite: 5 tests passed after adding one additional missing-endpoint text-summary regression test. The total suite now contains 46 tests; the final change was checked with the focused suite.
- Frontend production build and DOM workflow checks: passed.
- Chromium desktop (1440 px) and mobile (390 px): Results page rendered with actual saved-model output; route paths, charts, diagnostic expansion, line toggles and fit bounds worked. No uncaught page errors or horizontal page overflow. The benchmark table rendered both estimator rows for every real benchmark interval. Browser API responses were fixtures captured from real backend calls; model-role gating was adjusted only in the browser fixture to exercise the benchmark button.
- Offline tile failure was deliberately simulated: an explicit warning appeared while route geometry and metrics remained usable. Actual remote tile delivery was not verified; it depends on connectivity and the tile service.
- FastAPI TestClient with isolated copies of saved data/models: model attachment, 300–330 s vehicle-mode simulation, new metrics, road upload/matching, and stale-result rejection passed.
- Real held-out benchmark endpoint: 9 intervals returned, 9 eligible, 2 below the 10% endpoint target. This is an output/API smoke check, not a newly tuned model or an overall accuracy claim. See results-dashboard-benchmark-smoke.json for every failure and result.
- Road overlay test geometry followed a known test path to validate integration only; it was not evidence of real-world map-matching accuracy.

Distance tests distinguish correct travel distance from incorrect direction, check exact cumulative values, missing-reference gaps, missing endpoint, stationary percentage handling, native-rate sample counts and summary consistency.

Live smartphone/edge update rates, full 3D mounting calibration and road-constrained navigation accuracy remain unverified and are explicitly labelled in the UI.
