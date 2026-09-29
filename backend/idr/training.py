"""Protected multi-recording training with atomic epoch checkpoints and model lineage."""
import copy
import hashlib
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import registry as reg, storage as st
from .data import CHANNELS, FEATURE_NAMES, sequence_indices, windows, tree_features
from .models import THREADS, Predictor, make_net, scores

ROLES = ('train', 'validation', 'test')


def digest_file(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def state_digest(state):
    h = hashlib.sha256()
    for key, tensor in sorted(state.items()):
        h.update(key.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def atomic_torch(path, value):
    import torch
    temporary = path.with_suffix('.tmp')
    with open(temporary, 'wb') as stream:
        torch.save(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def valid_indices(ds, window):
    d = ds.frame
    ids = sequence_indices(d, window)
    invalid = np.r_[0, np.cumsum(~d.ref_valid.to_numpy(dtype=bool))]
    return ids[(invalid[ids + 1] - invalid[ids - window + 1]) == 0]


def prepare_plan(request):
    """Validate before reserving a job; freeze identities and data bytes in its plan."""
    mode = request.get('mode', 'create')
    kind, window = request['kind'], request['window']
    parent = None
    if mode == 'continue':
        if kind not in ('cnn_gru', 'tcn'):
            raise ValueError('Trees must be trained anew; continue training is available for CNN-GRU and TCN.')
        if not request.get('parent_id'):
            raise ValueError('Select a completed parent model to continue.')
        parent = st.get_model(request['parent_id']).meta
        if parent['kind'] != kind or parent['window'] != window:
            raise ValueError('Continued training must use the parent architecture and window size.')
        fid = parent.get('family_id', parent['model_id'])
        fam = reg.family(fid)
        name = fam['name']
    else:
        if request.get('parent_id'):
            raise ValueError('Create mode cannot specify a parent checkpoint.')
        fid, name = uuid.uuid4().hex[:16], request['name'].strip()
        if not name:
            raise ValueError('Name your model.')
        fam = {'assignments': []}
    roles = {}
    for entry in request['assignments']:
        sid, role = st.safe(entry['session_id']), entry['role']
        if sid in roles:
            raise ValueError('A recording cannot have two roles.')
        roles[sid] = role
    old = {a['dataset']: a['role'] for a in fam['assignments']}
    replayed = []
    if parent:
        for sid, role in old.items():
            if sid in roles and roles[sid] != role:
                raise ValueError('Dataset roles are fixed within a model family.')
            if role != 'train' or request.get('replay', True):
                if sid not in roles and role == 'train':
                    replayed.append(sid)
                roles[sid] = role
        if any(v != 'train' for v in old.values()):
            for sid, role in roles.items():
                if role != 'train' and sid not in old:
                    raise ValueError('Validation/test sets are fixed. Create a new model family to change them.')
    if set(roles.values()) != set(ROLES):
        raise ValueError('Assign at least one recording each to Train, Validation and Test.')
    if len(roles) > 100:
        raise ValueError('At most 100 recordings per run.')
    entries, seen, groups = [], {}, {}
    for a in fam['assignments']:
        groups[a['acquisition']] = a['role']
        seen[a['source']] = (a['dataset'], a['role'])
    for sid, role in sorted(roles.items()):
        record = reg.dataset(sid)
        group, source = record['acquisition'], record['source']
        if group.startswith('unassigned-'):
            raise ValueError(f"Assign an acquisition group to {record['name']} before training.")
        if group in groups and groups[group] != role:
            raise ValueError(f'Acquisition group {group} crosses split roles. Keep related clips together.')
        if source in seen and seen[source] != (sid, role):
            raise ValueError('Duplicate source or changed import settings would cross a protected recording identity.')
        groups[group] = role
        seen[source] = (sid, role)
        if parent and source in parent.get('source_splits', {}):
            previous_roles = set(parent['source_splits'][source])
            if previous_roles != {role}:
                raise ValueError('This parent used a different split of that recording. Use a new, independent recording or create a fresh model.')
        ds = st.get_dataset(sid)
        if abs(ds.report['sample_hz'] - 10) > 1:
            raise ValueError(f"{record['name']}: these models need approximately 10 Hz inputs.")
        ids = valid_indices(ds, window)
        if len(ids) == 0:
            raise ValueError(f"{record['name']}: no complete labelled windows of size {window}.")
        data_path = st.ROOT / 'datasets' / sid / 'data.csv.gz'
        entries.append({'session_id': sid, 'role': role, 'source': source, 'acquisition': group,
                        'name': record['name'], 'fingerprint': ds.fingerprint,
                        'sha256': digest_file(data_path), 'windows_available': len(ids),
                        'time_range': [float(ds.frame.t.iloc[0]), float(ds.frame.t.iloc[-1])]})
    for role in ROLES:
        if sum(e['windows_available'] for e in entries if e['role'] == role) < 100:
            raise ValueError(f'{role}: need at least 100 valid windows across the selected recordings.')
    return {'family_id': fid, 'family_name': name, 'kind': kind, 'window': window,
            'epochs': request['epochs'], 'max_windows': request['max_windows'],
            'n_estimators': request['n_estimators'], 'parent_id': request.get('parent_id'),
            'mode': mode, 'replay': request.get('replay', True), 'replayed': replayed,
            'entries': entries, 'seed': 42, 'session_id': request.get('session_id')}


def reserve(plan):
    rid = uuid.uuid4().hex[:16]
    with reg.connection() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM runs WHERE status IN ('queued','running','pausing')").fetchone():
            raise ValueError('A training job is already active. Pause it or wait for completion.')
        fid = plan['family_id']
        db.execute('INSERT OR IGNORE INTO families VALUES (?,?,?,?)',
                   (fid, plan['family_name'], plan['kind'], plan['window']))
        # Include imported/bundled version 1 when the first new run continues it.
        previous = db.execute('SELECT MAX(version) FROM runs WHERE family=?', (fid,)).fetchone()[0] or 0
        if plan['parent_id']:
            previous = max(previous, st.get_model(plan['parent_id']).meta.get('version', 1))
        version = previous + 1
        for e in plan['entries']:
            db.execute('INSERT OR IGNORE INTO assignments VALUES (?,?,?,?,?)',
                       (fid, e['session_id'], e['source'], e['acquisition'], e['role']))
        value = {'job_id': rid, 'model_id': rid, 'family_id': fid, 'name': plan['family_name'],
                 'version': version, 'status': 'queued', 'progress': 0, 'message': 'Queued',
                 'plan': plan, 'history': [], 'epoch': 0, 'optimizer_updates': 0,
                 'created': time.time(), 'session_id': plan.get('session_id')}
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',
                   (rid, fid, version, 'queued', json.dumps(value), time.time()))
    return value


def load_arrays(plan, role):
    """Bound memory and give each recording an equal maximum window budget."""
    entries = [e for e in plan['entries'] if e['role'] == role]
    budget = plan['max_windows'] if role == 'train' else min(plan['max_windows'], 10000)
    cap = max(1, budget // len(entries))
    xx, yy, counts = [], [], {}
    for e in entries:
        path = st.ROOT / 'datasets' / e['session_id'] / 'data.csv.gz'
        if digest_file(path) != e['sha256']:
            raise ValueError('A saved recording changed after the training plan was frozen.')
        ds = st.get_dataset(e['session_id'])
        ids = valid_indices(ds, plan['window'])
        rng = np.random.default_rng(plan['seed'])
        if len(ids) > cap:
            ids = np.sort(rng.choice(ids, cap, replace=False))
        xx.append(windows(ds.frame, ids, plan['window']))
        yy.append(ds.frame.ref_speed.to_numpy(np.float32)[ids[:, None] - np.arange(plan['window'] - 1, -1, -1)])
        counts[e['session_id']] = len(ids)
    return np.concatenate(xx), np.concatenate(yy), counts


def run_training(rid, stop=None, epoch_hook=None):
    """Called by a single worker. Latest checkpoint is the source of truth on resume."""
    job = reg.run(rid)
    plan = job['plan']
    folder = st.ROOT / 'models' / rid
    folder.mkdir(parents=True, exist_ok=True)
    latest = folder / 'latest.pt'
    stop = stop or threading.Event()
    def publish(**fields):
        job.update(fields)
        reg.save_run(job)
    try:
        publish(status='running', message='Preparing training and validation windows')
        X, Y, counts = load_arrays(plan, 'train')
        V, T, valcounts = load_arrays(plan, 'validation')
        meta = {'model_id': rid, 'family_id': plan['family_id'], 'family_name': plan['family_name'],
                'version': job['version'], 'parent_id': plan['parent_id'], 'kind': plan['kind'],
                'window': plan['window'], 'sample_hz': 10., 'channels': CHANNELS,
                'feature_names': FEATURE_NAMES, 'created_unix': job['created'],
                'split_method': 'explicit acquisition groups', 'variance_scale': 1.,
                'dataset_splits': {}, 'source_splits': {}, 'n_train': len(X), 'n_val': len(V),
                'test': None, 'training_config': plan, 'feature_importance': []}
        if plan['parent_id']:
            parent = st.get_model(plan['parent_id'])
            for key in ('dataset_splits', 'source_splits'):
                meta[key].update(parent.meta.get(key, {}))
        for e in plan['entries']:
            meta['dataset_splits'][e['fingerprint']] = {e['role']: e['time_range']}
            meta['source_splits'][e['source']] = {e['role']: e['time_range']}
        publish(training_windows=counts, validation_windows=valcounts)
        neural = plan['kind'] in ('cnn_gru', 'tcn')
        if neural:
            import torch
            torch.set_num_threads(THREADS)
            torch.manual_seed(plan['seed'])
            net = make_net(plan['kind'])
            opt = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.0001)
            mean, std = X.mean((0, 2)), np.maximum(X.std((0, 2)), .01)
            start, updates, history, wait, best_epoch = 0, 0, [], 0, 0
            baseline = None
            if plan['parent_id']:
                ck = torch.load(parent.folder / 'checkpoint.pt', map_location='cpu', weights_only=True)
                net.load_state_dict(ck['model'])
                opt.load_state_dict(ck['optimizer'])
                mean = np.array(parent.meta['normalization_mean'], np.float32)
                std = np.array(parent.meta['normalization_std'], np.float32)
            initial_hash = state_digest(net.state_dict())
            best, beststate, bestopt = float('inf'), copy.deepcopy(net.state_dict()), copy.deepcopy(opt.state_dict())
            if latest.exists():
                ck = torch.load(latest, map_location='cpu', weights_only=True)
                if ck['plan'] != plan:
                    raise ValueError('Checkpoint configuration does not match the frozen run.')
                net.load_state_dict(ck['model']); opt.load_state_dict(ck['optimizer'])
                mean, std = np.array(ck['mean'], np.float32), np.array(ck['std'], np.float32)
                start, updates, history, wait = ck['epoch'], ck['updates'], ck['history'], ck['wait']
                best, beststate, bestopt, best_epoch = ck['best'], ck['beststate'], ck['bestopt'], ck['best_epoch']
                baseline, initial_hash = ck['baseline'], ck['initial_hash']
                torch.set_rng_state(ck['rng'])
            xx = torch.from_numpy(((X - mean[None, :, None]) / std[None, :, None]).astype(np.float32))
            vv = torch.from_numpy(((V - mean[None, :, None]) / std[None, :, None]).astype(np.float32))
            yy = torch.from_numpy(Y)
            def validation():
                net.eval()
                with torch.no_grad():
                    pred = torch.cat([net(a)[:, -1, 0] for a in vv.split(256)]).numpy()
                return scores(T[:, -1], np.clip(pred, 0, 60))
            if baseline is None:
                baseline = validation()
                if plan['parent_id']:
                    # Retain the parent's weights if none of the new epochs improves validation.
                    best = baseline['mae']
            publish(baseline_validation=baseline, epoch=start, optimizer_updates=updates, history=history)
            for ep in range(start, plan['epochs']):
                if wait >= 5 or stop.is_set():
                    break
                net.train(); losses = []
                for ix in torch.randperm(len(xx)).split(128):
                    if stop.is_set():
                        publish(status='paused', message='Paused. Resume restores the last completed epoch; partial epoch updates are discarded.')
                        return None
                    out = net(xx[ix]); mu, lv = out[:, :, 0], out[:, :, 1].clamp(-5, 5)
                    truth = yy[ix]; h = min(10, plan['window'] // 2)
                    err = mu[:, -h:] - truth[:, -h:]
                    loss = torch.nn.functional.huber_loss(mu[:, -1], truth[:, -1])
                    loss += .1 * torch.nn.functional.huber_loss(err.sum(1) * .1, torch.zeros(len(ix)))
                    if ep >= min(3, plan['epochs'] // 2):
                        loss += .05 * (.5 * torch.exp(-lv[:, -h:]) * err.square() + .5 * lv[:, -h:]).mean()
                    if not torch.isfinite(loss):
                        raise ValueError('Non-finite training loss; inspect sensor values and labels.')
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.)
                    opt.step(); updates += 1; losses.append(float(loss.detach()))
                result = validation(); mae = result['mae']
                if mae < best:
                    best, wait, best_epoch = mae, 0, ep + 1
                    beststate, bestopt = copy.deepcopy(net.state_dict()), copy.deepcopy(opt.state_dict())
                else:
                    wait += 1
                history.append({'epoch': ep + 1, 'loss': float(np.mean(losses)), 'validation_mae': mae,
                                'optimizer_updates': updates})
                atomic_torch(latest, {'plan': plan, 'model': net.state_dict(), 'optimizer': opt.state_dict(),
                    'epoch': ep + 1, 'updates': updates, 'history': history, 'wait': wait, 'best': best,
                    'beststate': beststate, 'bestopt': bestopt, 'best_epoch': best_epoch,
                    'mean': mean.tolist(), 'std': std.tolist(), 'rng': torch.get_rng_state(),
                    'baseline': baseline, 'initial_hash': initial_hash})
                publish(epoch=ep + 1, optimizer_updates=updates, history=history,
                        progress=(ep + 1) / plan['epochs'] * .95,
                        message=f'Epoch {ep + 1}/{plan["epochs"]} saved; validation MAE {mae:.3f} m/s')
                if epoch_hook:
                    epoch_hook(ep + 1)
            if stop.is_set():
                publish(status='paused', message='Paused at a saved epoch. Resume this run to continue.')
                return None
            atomic_torch(folder / 'checkpoint.pt', {'model': beststate, 'optimizer': bestopt, 'epoch': best_epoch})
            with open(folder / 'weights.tmp.npz', 'wb') as stream:
                np.savez_compressed(stream, **{k: v.numpy() for k, v in beststate.items()})
            os.replace(folder / 'weights.tmp.npz', folder / 'weights.npz')
            meta.update(normalization_mean=mean.tolist(), normalization_std=std.tolist(),
                        parameters=sum(v.numel() for v in net.parameters()), best_epoch=best_epoch,
                        history=history, baseline_validation=baseline, optimizer_updates=updates,
                        initial_weights_sha256=initial_hash, weights_sha256=state_digest(beststate),
                        weights_changed=state_digest(beststate) != initial_hash,
                        latest_weights_changed=state_digest(net.state_dict()) != initial_hash,
                        epochs_completed=len(history))
        else:
            import joblib
            from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
            cls = ExtraTreesRegressor if plan['kind'] == 'extra_trees' else RandomForestRegressor
            net = cls(n_estimators=plan['n_estimators'], max_depth=14, min_samples_leaf=8,
                      n_jobs=THREADS, random_state=plan['seed'])
            net.fit(tree_features(X), Y[:, -1])
            pred = net.predict(tree_features(V))
            meta['residual_variance'] = float(max(.04, np.mean((pred - T[:, -1]) ** 2)))
            joblib.dump(net, folder / 'model.joblib', compress=3)
            meta.update(history=[], optimizer_updates=0, epochs_completed=0)
        meta['training_status'] = 'finalizing'
        st.write_json(folder / 'metadata.json', meta)
        pred = Predictor(folder)
        values, variance = pred.raw(V)
        meta['variance_scale'] = float(np.clip(np.mean((T[:, -1] - values) ** 2 / np.maximum(variance, .04)), .1, 100))
        pred.meta = meta
        values, variance = pred.predict(V)
        meta['validation'] = scores(T[:, -1], values, variance)
        tick = time.perf_counter()
        for _ in range(20):
            pred.predict(V[:1])
        meta['window_latency_ms'] = (time.perf_counter() - tick) * 50
        meta['training_status'] = 'complete'
        st.write_json(folder / 'metadata.json', meta)
        st.get_model.cache_clear()
        publish(status='complete', progress=1, message='Version saved. Use it explicitly to activate; test data was not scored.',
                model_id=rid, result=meta)
        return Predictor(folder)
    except BaseException as exc:
        # Keep epoch checkpoints even after errors or process interruption.
        publish(status='failed', message=str(exc) or type(exc).__name__)
        raise


class TrainingManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='idr-training')
        self.events = {}

    def submit(self, request):
        with self.lock:
            plan = prepare_plan(request)
            value = reserve(plan)
            self._launch(value['job_id'])
            return value

    def _launch(self, rid):
        event = threading.Event()
        self.events[rid] = event
        def work():
            try:
                run_training(rid, event)
            except BaseException:
                pass  # run_training persisted the error for polling/recovery.
            finally:
                self.events.pop(rid, None)
        self.pool.submit(work)

    def pause(self, rid):
        if rid not in self.events:
            raise ValueError('This run is not active in the current process.')
        if reg.run(rid)['plan']['kind'] not in ('cnn_gru', 'tcn'):
            raise ValueError('Tree training cannot pause between epochs. Wait for completion.')
        self.events[rid].set()
        return reg.run(rid)

    def resume(self, rid):
        with self.lock:
            value = reg.run(rid)
            if value['status'] not in ('paused', 'interrupted', 'failed'):
                raise ValueError('Only paused, interrupted or failed runs can resume.')
            if any(j['status'] in ('queued', 'running') for j in reg.runs()):
                raise ValueError('Another training run is active.')
            value.update(status='queued', message='Restoring saved epoch; configuration is unchanged.')
            reg.save_run(value)
            self._launch(rid)
            return value

    def close(self):
        for event in list(self.events.values()):
            event.set()
        self.pool.shutdown(wait=True, cancel_futures=False)
