"""数据模型：采集结果与二创结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CollectionResult:
    source_id: int
    source_type: str
    title: str
    folder: Path
    md_path: Path


@dataclass
class MediaItem:
    kind: str            # cover | inline | subtitle
    path: Path
    caption_zh: str = ""
    caption_en: str = ""


@dataclass
class CreationResult:
    output_id: int
    title: str
    folder: Path
    md_path: Path            # 头条风格 md（主）
    wechat_md_path: Path     # 公众号风格 md
    similarity: float
    media: list[MediaItem] = field(default_factory=list)
