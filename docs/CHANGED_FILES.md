# Changed files

Source is compared against the supplied Tesseracts-IDR(1).zip. Research repositories were examined separately; their third-party source was not copied into this project.

| Status | File |
|---|---|
| Changed | `README.md` |
| Changed | `backend/requirements-lock.txt` |
| Added | `backend/evaluate_audit.py` |
| Changed | `backend/idr/data.py` |
| Changed | `backend/idr/navigation.py` |
| Changed | `backend/idr/storage.py` |
| Added | `backend/idr/vehicle.py` |
| Changed | `backend/server.py` |
| Added | `backend/tests/test_audit_fixes.py` |
| Added | `docs/README_BEFORE_AUDIT.md` |
| Added | `frontend/dist/assets/index-CFiwYtXt.js` |
| Added | `frontend/dist/assets/index-Du2KZHSY.css` |
| Changed | `frontend/dist/index.html` |
| Changed | `frontend/src/App.jsx` |
| Changed | `frontend/src/components/nexus/Replay.jsx` |
| Changed | `frontend/src/components/nexus/ReplayPlot.jsx` |
| Added | `frontend/src/components/nexus/SeriesPlot.jsx` |
| Changed | `frontend/src/components/nexus/Train.jsx` |

Compiled frontend files were rebuilt. New JSON reports, test/build logs and RESULTS.md are in reports/. Older release reports are retained under reports/previous-release/. The dataset association and active-model setting select the existing TCN; neural weights and saved dataset contents were preserved.
