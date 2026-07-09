"""文案 / Markdown 采集：直接接收原始文案或 md 文件。

- 若 --input 是一个已存在的文件路径，则读取该文件内容；
- 否则把 --input 当作原始文案正文；
- 标题优先级：显式 --title > md 首行 # 标题 > 文件名 > 首行/前若干字。
"""
from __future__ import annotations

from pathlib import Path

from src.collector.base import BaseCollector, ts_now
from src.models import CollectionResult


class TextCollector(BaseCollector):
    prefix = "原文案"

    def collect(self, raw: str, title: str | None = None) -> CollectionResult:
        p = Path(raw)
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not title:
                title = p.stem
        else:
            text = raw

        if not title:
            title = self._derive_title(text)

        folder = self.make_folder(title)
        md_path = self.save_md(
            folder,
            title,
            text.strip(),
            {"title": title, "source_type": "text", "collected_at": ts_now()},
        )
        sid = self.record("text", title, folder, md_path, raw_text=text)
        return CollectionResult(sid, "text", title, folder, md_path)

    @staticmethod
    def _derive_title(text: str) -> str:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            if ln.startswith("# "):
                return ln[2:].strip()
        if lines:
            return lines[0][:40]
        return "未命名文案"
