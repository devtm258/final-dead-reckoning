# Results dashboard update

## Upgrade without losing your work
1. Stop the running app (Ctrl+C) and back up the existing project.
2. Extract the new package into a separate folder.
3. Copy its frontend folder, backend/idr folder, and backend/server.py into your existing project, replacing those files.
4. Do not overwrite backend/state. It contains your recordings, model versions and training history.
5. In Anaconda Prompt, activate smartphone_nav, enter the existing project folder and run python start.py.
6. Open http://127.0.0.1:8000 and press Ctrl+F5. Run a new test to calculate the new outputs.

For a fresh install, use the complete package and the main README setup instructions. The compiled frontend includes Leaflet; no npm command is required for normal operation.

## Outputs on Results
- OpenStreetMap with VBOX, inertial baseline and AI-aided routes, blackout markers, visibility toggles, fit-to-routes and replay position.
- Three total travel distances; signed distance errors in metres and percent.
- Cumulative distance, distance-error, same-time position-error and speed charts.
- Side-by-side mean position error, position RMSE, maximum position error, endpoint position error, endpoint drift percentage and maximum-error percentage.
- Navigation-mode timeline and first available post-blackout phone GNSS update.
- Recording, model version/ID, estimator, requested and sampled blackout times, reference coverage, held-out/exploration status and scoring exclusions.
- Desktop/server replay latency and throughput. Smartphone/edge update rates are explicitly not measured.
- Expandable heading comparison/error, heading RMSE, mounting calibration, quality flags, import warnings, and raw model-speed diagnostics.
- Offline road GeoJSON upload and the existing road matcher's separate diagnostic route overlay.
- Multi-run benchmark table with baseline/AI errors per interval, under-10-percent count, median/worst AI endpoint drift, and failed/unscorable/skipped rows with reasons.
- Download all result data or benchmark data as JSON.

## Definitions and safeguards
Travel distance is the sum of horizontal distances between successive native-rate positions during the blackout. It is calculated before display downsampling, using identical valid adjacent reference intervals for all three paths. It is not an integral of the speed prediction and is not map-snapped. As with any reference trajectory, coordinate noise can influence path length.

Signed distance error = estimated travel distance minus VBOX travel distance. Position error = horizontal separation at the same timestamp. Endpoint error uses the last sampled timestamp inside the requested blackout, which is shown explicitly. RMSE and mean/max position errors use valid matching reference samples.

Percentages divide by total reference blackout distance. Below 5 metres, percentages are unavailable. Missing reference intervals are never bridged; distances are labelled partial, missing endpoint errors are unavailable, and incomplete-reference runs are excluded from a held-out pass. This is stricter than the earlier 95% coverage eligibility rule. Full-coverage trajectory estimates are unchanged by this output update.

The endpoint <10% indicator is specifically an endpoint criterion, not proof that errors remained below that limit throughout the blackout or that lane-level accuracy was achieved. Maximum error and error curves are shown separately.

Online OpenStreetMap tiles require internet and include attribution. No bulk tile download is performed. If tiles fail, the routes remain visible and a warning appears; disable the background for an offline view. Offline road geometry is supplied as a GeoJSON FeatureCollection containing LineString/MultiLineString road features. Map matching is an optional diagnostic overlay on display points, not a validated road constraint inside the scored estimator.

A GNSS update available in the timeline can still be rejected by the filter. Between-fix propagation is labelled separately. No phone transition-latency or on-device update-rate claim is made. Invalid readings/gaps may reject simulation before an output is generated; import warnings and sensor flags do not establish labelled fault detection.

Calibration projections and warnings are available, but this planar estimator does not establish complete mount-independent pitch/roll/yaw calibration. No new anomaly classifier or mobile sensor adapter was introduced.

## Changed files
Backend: idr/results.py (new), idr/navigation.py, server.py, tests/test_results.py (new).
Frontend: App.jsx; Train.jsx; Replay.jsx; RouteMap.jsx, MetricPlot.jsx and BenchmarkResults.jsx (new); index.css; package.json/package-lock.json; regenerated dist.
Documentation: README.md, this guide, SIMPLER_UI.md notice, reports/RESULTS_DASHBOARD_QA.md.

## Verification
See reports/RESULTS_DASHBOARD_QA.md. Existing accuracy reports describe earlier development experiments and are not a new certification. The UI remains a local recorded-data workspace; unavailable real-device metrics are labelled, not fabricated.

Map integration references: https://leafletjs.com/examples/quick-start/ and https://operations.osmfoundation.org/policies/tiles/.
