"""Small SQLite registry; large recordings and checkpoints remain ordinary files."""
import json
import sqlite3
import time
from contextlib import contextmanager
from . import storage as st


@contextmanager
def connection():
    db = sqlite3.connect(st.ROOT / 'registry.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, name TEXT NOT NULL,
            acquisition TEXT NOT NULL, details TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS families (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, window INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments (
            family TEXT NOT NULL, dataset TEXT NOT NULL, source TEXT NOT NULL,
            acquisition TEXT NOT NULL, role TEXT NOT NULL,
            PRIMARY KEY(family, dataset));
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, family TEXT NOT NULL, version INTEGER NOT NULL,
            status TEXT NOT NULL, payload TEXT NOT NULL, updated REAL NOT NULL,
            UNIQUE(family, version));
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def register_dataset(sid, name=None, acquisition=None):
    path = st.ROOT / 'datasets' / st.safe(sid) / 'metadata.json'
    meta = json.loads(path.read_text())
    report = meta['report']
    with connection() as db:
        old = db.execute('SELECT * FROM datasets WHERE id=?', (sid,)).fetchone()
        if old:
            return dict(old)
        db.execute('INSERT INTO datasets VALUES (?,?,?,?,?)', (
            sid, report.get('source_id', meta['fingerprint']), name or 'Recording ' + sid[:8],
            acquisition or 'unassigned-' + sid, json.dumps(report)))
    return dataset(sid)


def dataset(sid):
    with connection() as db:
        row = db.execute('SELECT * FROM datasets WHERE id=?', (st.safe(sid),)).fetchone()
    if row is None:
        raise ValueError('Dataset is not registered. Upload it or restart to import old datasets.')
    result = dict(row)
    result['report'] = json.loads(result.pop('details'))
    result['session_id'] = result.pop('id')
    return result


def datasets():
    with connection() as db:
        ids = [r[0] for r in db.execute('SELECT id FROM datasets ORDER BY name')]
    return [dataset(sid) for sid in ids]


def edit_dataset(sid, name, acquisition):
    acquisition = acquisition.strip().casefold()
    if not name.strip() or not acquisition or acquisition.startswith('unassigned-'):
        raise ValueError('Supply a recording name and an acquisition group (same original drive = same group).')
    with connection() as db:
        old = db.execute('SELECT acquisition FROM datasets WHERE id=?', (st.safe(sid),)).fetchone()
        if not old:
            raise ValueError('Dataset not found')
        locked = db.execute('SELECT 1 FROM assignments WHERE dataset=?', (sid,)).fetchone()
        if locked and acquisition != old[0]:
            raise ValueError('Acquisition group is locked after use in a training plan.')
        db.execute('UPDATE datasets SET name=?,acquisition=? WHERE id=?', (name.strip(), acquisition, sid))
    return dataset(sid)


def run(rid):
    with connection() as db:
        row = db.execute('SELECT payload FROM runs WHERE id=?', (st.safe(rid),)).fetchone()
    if not row:
        raise ValueError('Training run not found')
    return json.loads(row[0])


def save_run(value):
    value['updated'] = time.time()
    with connection() as db:
        db.execute('UPDATE runs SET status=?,payload=?,updated=? WHERE id=?',
                   (value['status'], json.dumps(value, allow_nan=False), value['updated'], value['job_id']))


def runs():
    with connection() as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM runs ORDER BY updated DESC')]


def family(fid):
    with connection() as db:
        row = db.execute('SELECT * FROM families WHERE id=?', (fid,)).fetchone()
        entries = [dict(r) for r in db.execute('SELECT * FROM assignments WHERE family=?', (fid,))]
    if row is None:
        raise ValueError('Model family not found')
    return {**dict(row), 'assignments': entries}


def set_active(mid):
    st.get_model(mid)
    with connection() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES ('active_model',?)", (mid,))


def active():
    with connection() as db:
        row = db.execute("SELECT value FROM settings WHERE key='active_model'").fetchone()
    if row and (st.ROOT / 'models' / row[0] / 'metadata.json').exists():
        return row[0]
    return None


def bootstrap():
    for path in (st.ROOT / 'datasets').glob('*/metadata.json'):
        register_dataset(path.parent.name)
    for meta in st.list_models():
        fid = meta.get('family_id', meta['model_id'])
        with connection() as db:
            db.execute('INSERT OR IGNORE INTO families VALUES (?,?,?,?)', (
                fid, meta.get('family_name', 'Imported ' + meta['kind'] + ' ' + fid[:6]),
                meta['kind'], meta['window']))
    for value in runs():
        if value['status'] in ('queued', 'running', 'pausing'):
            value.update(status='interrupted', message='Server restarted. Resume from the last completed epoch.')
            save_run(value)
