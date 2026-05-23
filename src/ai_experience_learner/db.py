"""SQLite database operations for experience memory."""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lessons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    filename        TEXT NOT NULL UNIQUE,
    topic           TEXT,
    problem_type    TEXT,
    technique       TEXT,
    task_type       TEXT,
    success         INTEGER DEFAULT 1,
    source_project  TEXT,
    lesson_text     TEXT NOT NULL,
    embedding       BLOB,
    cluster_id      INTEGER DEFAULT -1
);

CREATE TABLE IF NOT EXISTS concept_clusters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id   INTEGER,
    name        TEXT NOT NULL,
    description TEXT,
    level       INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_lessons_task_type ON lessons(task_type);
CREATE INDEX IF NOT EXISTS idx_lessons_cluster ON lessons(cluster_id);
"""


def get_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.close()
