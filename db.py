"""Optional SQLite helpers for UniTutor.

The web layer does not require a database yet – this module is the single place
to put persistence code when chat history or a PDF library needs to survive a
restart. ``init_db()`` is idempotent and safe to call on every start-up.
"""

import sqlite3
from contextlib import contextmanager

from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    job           TEXT NOT NULL CHECK (job IN ('student', 'teacher')),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id          INTEGER PRIMARY KEY,
    teacher_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    semester    TEXT NOT NULL CHECK (semester IN ('1', '2')),
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (teacher_id, name)
);

CREATE TABLE IF NOT EXISTS lectures (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    course_id        INTEGER NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT,
    youtube_url      TEXT,
    youtube_video_id TEXT,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (course_id, title)
);

CREATE TABLE IF NOT EXISTS recordings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id    INTEGER NOT NULL,
    teacher_id   INTEGER NOT NULL,
    filename     TEXT NOT NULL,
    stored_path  TEXT NOT NULL,
    duration_sec INTEGER,
    transcript   TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id)  REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES users(id)   ON DELETE CASCADE,
    UNIQUE (course_id, filename)
);

CREATE INDEX IF NOT EXISTS idx_courses_teacher    ON courses(teacher_id);
CREATE INDEX IF NOT EXISTS idx_lectures_course    ON lectures(course_id);
CREATE INDEX IF NOT EXISTS idx_recordings_course  ON recordings(course_id);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect():
    """Context manager that commits on success and rolls back on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    with connect() as conn:
        conn.executescript(SCHEMA)