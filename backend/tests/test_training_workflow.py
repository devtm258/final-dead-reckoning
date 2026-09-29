"""Behavior tests: continuation, replay, crash recovery, immutable evaluation roles."""
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pandas as pd
import pytest

from idr import registry as reg, storage as st
from idr.data import load_pair
from idr.training import prepare_plan, reserve, run_training


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(st, 'ROOT', tmp_path)
    for name in ('datasets', 'models', 'jobs', 'reports'):
        (tmp_path / name).mkdir()
    st.get_dataset.cache_clear(); st.get_model.cache_clear()
    yield tmp_path
    st.get_dataset.cache_clear(); st.get_model.cache_clear()


def recording(seed, group=None):
    n = 360
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 100
    d = pd.DataFrame({'GPS LATITUDE': 52 + np.arange(n) * .000001 + seed * .00001,
                      'GPS LONGITUDE': np.full(n, -1.), 'GPS SPEED': np.full(n, 4.),
                      'TIME SINCE START': t, 'GPS ORIENTATION': np.zeros(n)})
    for axis in 'XYZ':
        g = 9.80665 if axis == 'Z' else 0.
        d['ACCELEROMETER ' + axis] = g + rng.normal(0, .1, n)
        d['GRAVITY ' + axis] = g
        d['GYROSCOPE ' + axis] = rng.normal(0, .01, n)
    ds = load_pair(d.to_csv(index=False).encode(), speed_unit='m/s')
    ds.frame['ref_speed'] = 4. + .2 * np.sin(t / 1000)
    ds.frame['ref_valid'] = True
    ds.frame['ref_lat'] = ds.frame.lat
    ds.frame['ref_lon'] = ds.frame.lon
    ds.frame['ref_heading'] = 0.
    ds.report['reference'] = 'synthetic-test-only'
    sid = st.store_dataset(ds)
    reg.register_dataset(sid, f'Test drive {seed}', group or f'drive-{seed}')
    return sid


def request(ids, **overrides):
    return dict({'name': 'CNN-GRU-35', 'kind': 'cnn_gru', 'window': 35,
                 'epochs': 3, 'max_windows': 128, 'n_estimators': 10,
                 'mode': 'create', 'parent_id': None, 'replay': True,
                 'assignments': [{'session_id': sid, 'role': role}
                                 for sid, role in zip(ids, ('train', 'validation', 'test'))]}, **overrides)


def test_continue_replays_and_preserves_parent(isolated):
    ids = [recording(i) for i in range(3)]
    first = reserve(prepare_plan(request(ids, epochs=2)))
    parent = run_training(first['job_id'])
    parent_bytes = (parent.folder / 'weights.npz').read_bytes()
    new = recording(3)
    r = request(ids, mode='continue', parent_id=parent.meta['model_id'], epochs=2,
                assignments=[{'session_id': new, 'role': 'train'}])
    plan = prepare_plan(r)
    assert plan['replayed'] == [ids[0]]
    assert {e['session_id'] for e in plan['entries'] if e['role'] == 'train'} == {ids[0], new}
    second = reserve(plan)
    child = run_training(second['job_id'])
    assert child.meta['initial_weights_sha256'] == parent.meta['weights_sha256']
    assert child.meta['optimizer_updates'] > 0
    assert child.meta['latest_weights_changed']
    assert child.meta['version'] == 2
    assert child.meta['family_id'] == parent.meta['family_id']
    assert (parent.folder / 'weights.npz').read_bytes() == parent_bytes
    assert child.meta['test'] is None
    assert ids[2] not in reg.run(second['job_id'])['training_windows']
    assert child.meta['normalization_mean'] == parent.meta['normalization_mean']
    reg.set_active(child.meta['model_id'])
    assert reg.active() == child.meta['model_id']


@pytest.mark.parametrize('kind', ['cnn_gru', 'tcn'])
def test_restart_matches_uninterrupted_training(isolated, kind):
    import torch
    ids = [recording(i) for i in range(3)]
    uninterrupted = reserve(prepare_plan(request(ids, kind=kind)))
    reference = run_training(uninterrupted['job_id'])
    interrupted = reserve(prepare_plan(request(ids, kind=kind)))
    def crash(epoch):
        if epoch == 1:
            raise RuntimeError('simulated process loss after atomic checkpoint')
    with pytest.raises(RuntimeError, match='simulated'):
        run_training(interrupted['job_id'], epoch_hook=crash)
    assert (st.ROOT / 'models' / interrupted['job_id'] / 'latest.pt').exists()
    # A genuinely fresh interpreter restores the checkpoint, RNG and optimizer.
    env = dict(os.environ, IDR_DATA_DIR=str(st.ROOT))
    code = "from idr import registry as r;r.bootstrap();from idr.training import run_training;run_training('" + interrupted['job_id'] + "')"
    subprocess.run([sys.executable, '-c', code], check=True, env=env, timeout=90)
    resumed = st.get_model(interrupted['job_id'])
    assert resumed.meta['weights_sha256'] == reference.meta['weights_sha256']
    a = torch.load(reference.folder / 'latest.pt', weights_only=True)
    b = torch.load(resumed.folder / 'latest.pt', weights_only=True)
    assert all(torch.equal(a['model'][k], b['model'][k]) for k in a['model'])
    assert a['updates'] == b['updates']
    assert a['history'] == b['history']


def test_pause_and_restart_detection(isolated):
    ids = [recording(i) for i in range(3)]
    job = reserve(prepare_plan(request(ids)))
    stop = threading.Event()
    run_training(job['job_id'], stop, epoch_hook=lambda ep: stop.set())
    assert reg.run(job['job_id'])['status'] == 'paused'
    assert reg.run(job['job_id'])['epoch'] == 1
    value = reg.run(job['job_id']); value['status'] = 'running'; reg.save_run(value)
    reg.bootstrap()
    assert reg.run(job['job_id'])['status'] == 'interrupted'
    result = run_training(job['job_id'])
    assert result.meta['epochs_completed'] == 3


def test_group_leakage_rejected(isolated):
    ids = [recording(0, 'same-trip'), recording(1, 'same-trip'), recording(2)]
    with pytest.raises(ValueError, match='crosses split'):
        prepare_plan(request(ids))


def test_test_role_cannot_be_reused_as_training(isolated):
    ids = [recording(i) for i in range(3)]
    job = reserve(prepare_plan(request(ids, epochs=1)))
    parent = run_training(job['job_id'])
    r = request(ids, mode='continue', parent_id=parent.meta['model_id'],
                assignments=[{'session_id': ids[2], 'role': 'train'}])
    with pytest.raises(ValueError, match='roles are fixed'):
        prepare_plan(r)
    with pytest.raises(ValueError, match='locked'):
        reg.edit_dataset(ids[2], 'renamed', 'pretend-new-drive')
    other = recording(4, 'drive-2')
    r['assignments'] = [{'session_id': other, 'role': 'train'}]
    with pytest.raises(ValueError, match='crosses split'):
        prepare_plan(r)


def test_changed_data_blocks_resume(isolated):
    ids = [recording(i) for i in range(3)]
    job = reserve(prepare_plan(request(ids)))
    path = st.ROOT / 'datasets' / ids[0] / 'data.csv.gz'
    with open(path, 'ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='changed'):
        run_training(job['job_id'])


def test_duplicate_source_import_settings_rejected(isolated):
    ids = [recording(i) for i in range(3)]
    ds = st.get_dataset(ids[0])
    from copy import deepcopy
    alternative = deepcopy(ds); alternative.fingerprint = 'f' * 64
    sid = st.store_dataset(alternative)
    reg.register_dataset(sid, 'Same source different import', 'different-label')
    r = request(ids)
    r['assignments'].append({'session_id': sid, 'role': 'test'})
    with pytest.raises(ValueError, match='Duplicate source'):
        prepare_plan(r)


def test_api_startup_restores_registry_and_active_model(isolated):
    from fastapi.testclient import TestClient
    from server import app
    ids = [recording(i) for i in range(3)]
    job = reserve(prepare_plan(request(ids, epochs=1)))
    model = run_training(job['job_id'])
    with TestClient(app) as client:
        response = client.post('/api/models/attach', json={'session_id': ids[0], 'model_id': model.meta['model_id']})
        assert response.status_code == 200, response.text
        assert response.json()['test_range'] is None
        assert client.post('/api/pipeline/benchmark', json={'session_id': ids[0]}).status_code == 400
    with TestClient(app) as client:
        assert client.get('/api/').json()['active_model'] == model.meta['model_id']
        assert len(client.get('/api/datasets').json()) == 3
        assert client.get('/api/jobs').json()[0]['status'] == 'complete'
        assert client.post('/api/pipeline/train', json=request(ids, window=0)).status_code == 422


def test_api_submits_real_training_job(isolated):
    from fastapi.testclient import TestClient
    from server import app
    ids = [recording(i) for i in range(3)]
    with TestClient(app) as client:
        response = client.post('/api/pipeline/train', json=request(ids, epochs=1, max_windows=1000))
        assert response.status_code == 200, response.text
        jid = response.json()['job_id']
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            job = client.get(f'/api/jobs/{jid}').json()
            if job['status'] in ('complete', 'failed'):
                break
            time.sleep(.05)
        assert job['status'] == 'complete', job
        model = st.get_model(jid)
        assert model.meta['optimizer_updates'] > 0
        assert model.meta['test'] is None
        assert client.post(f'/api/jobs/{jid}/resume').status_code == 400
