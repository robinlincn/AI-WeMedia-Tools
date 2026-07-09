"""SQLite 持久化：sources / outputs / media 三张表。

- sources：采集记录（链接 / 文案 / 视频）
- outputs：二创记录（标题、相似度、产物路径）
- media ：图片等媒体资源（含中英文副标题）
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    title       TEXT,
    url         TEXT,
    folder_name TEXT NOT NULL,
    md_path     TEXT NOT NULL,
    raw_text    TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outputs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER,
    title       TEXT,
    folder_name TEXT NOT NULL,
    md_path     TEXT NOT NULL,
    similarity  REAL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE TABLE IF NOT EXISTS media (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_type  TEXT NOT NULL,
    owner_id    INTEGER,
    kind        TEXT,
    path        TEXT NOT NULL,
    caption_zh  TEXT,
    caption_en  TEXT,
    created_at  TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- sources ----
    def insert_source(self, source_type, title, folder_name, md_path, url=None, raw_text=None):
        cur = self.conn.execute(
            "INSERT INTO sources(source_type,title,url,folder_name,md_path,raw_text,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (source_type, title, url, folder_name, str(md_path), raw_text, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_source(self, sid: int):
        return self.conn.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()

    def list_sources(self):
        return self.conn.execute("SELECT * FROM sources ORDER BY id DESC").fetchall()

    # ---- outputs ----
    def insert_output(self, source_id, title, folder_name, md_path, similarity=None):
        cur = self.conn.execute(
            "INSERT INTO outputs(source_id,title,folder_name,md_path,similarity,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (source_id, title, folder_name, str(md_path), similarity, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_outputs(self):
        return self.conn.execute("SELECT * FROM outputs ORDER BY id DESC").fetchall()

    # ---- media ----
    def insert_media(self, owner_type, owner_id, kind, path, caption_zh=None, caption_en=None):
        cur = self.conn.execute(
            "INSERT INTO media(owner_type,owner_id,kind,path,caption_zh,caption_en,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (owner_type, owner_id, kind, str(path), caption_zh, caption_en, _now()),
        )
        self.conn.commit()
        return cur.lastrowid
