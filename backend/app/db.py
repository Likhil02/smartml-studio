import sqlite3, json
from contextlib import contextmanager
from .config import DB_PATH, STORAGE

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, name TEXT NOT NULL, UNIQUE(project_id,name));
CREATE TABLE IF NOT EXISTS images(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, filename TEXT NOT NULL, width INT, height INT, size_bytes INT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS datasets(id INTEGER PRIMARY KEY, project_id INT NOT NULL, train_count INT, val_count INT, test_count INT, split_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS training_runs(id INTEGER PRIMARY KEY, project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, status TEXT DEFAULT 'queued', config_json TEXT, total_epochs INT, current_epoch INT DEFAULT 0, error TEXT, overfitting_json TEXT, started_at TEXT DEFAULT CURRENT_TIMESTAMP, finished_at TEXT, elapsed REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY, run_id INT NOT NULL REFERENCES training_runs(id) ON DELETE CASCADE, epoch INT, acc REAL, val_acc REAL, loss REAL, val_loss REAL);
CREATE TABLE IF NOT EXISTS model_versions(id INTEGER PRIMARY KEY, project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, run_id INT, version INT, dataset_json TEXT, epochs INT, batch_size INT, learning_rate REAL, accuracy REAL, precision REAL, recall REAL, f1 REAL, eval_json TEXT, model_path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiments(id INTEGER PRIMARY KEY, project_id INT, source TEXT, payload_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True); STORAGE.mkdir(parents=True, exist_ok=True)
    with conn() as c: c.executescript(SCHEMA)

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c; c.commit()
    finally: c.close()

def q(sql, args=()):
    with conn() as c: return [dict(r) for r in c.execute(sql, args).fetchall()]

def q1(sql, args=()):
    r = q(sql, args); return r[0] if r else None

def ex(sql, args=()):
    with conn() as c: return c.execute(sql, args).lastrowid
