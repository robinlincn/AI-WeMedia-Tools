"""采集基类：负责文件夹命名、md 写入、记录入库。

文件夹命名规则（满足需求：「类型-标题-时间戳」）：
  链接采集 -> 文章链接采集-标题-YYYYMMDD_HHMMSS
  文案采集 -> 原文案-标题-YYYYMMDD_HHMMSS
  视频采集 -> 视频采集-标题-YYYYMMDD_HHMMSS
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.config import AppConfig
from src.db import Database

TS_FMT = "%Y%m%d_%H%M%S"


def sanitize(name: str, max_len: int = 40) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r\t]+', "_", name).strip()
    name = name.strip(". ")
    if len(name) > max_len:
        name = name[:max_len].rstrip("_")
    return name or "untitled"


def ts_now() -> str:
    return datetime.now().strftime(TS_FMT)


class BaseCollector:
    prefix = "采集"  # 子类覆盖：文章采集 / 原文案 / 视频采集

    def __init__(self, cfg: AppConfig, db: Database):
        self.cfg = cfg
        self.db = db

    def make_folder(self, title: str) -> Path:
        folder = self.cfg.articles_dir / f"{self.prefix}-{sanitize(title)}-{ts_now()}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "images").mkdir(exist_ok=True)
        return folder

    def save_md(self, folder: Path, title: str, body: str, frontmatter: dict) -> Path:
        md = folder / f"{sanitize(title)}.md"
        fm = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        content = f"---\n{fm}\n---\n\n# {title}\n\n{body}\n"
        md.write_text(content, encoding="utf-8")
        return md

    def record(self, source_type, title, folder, md_path, url=None, raw_text=None):
        return self.db.insert_source(
            source_type, title, folder.name, md_path, url, raw_text
        )
