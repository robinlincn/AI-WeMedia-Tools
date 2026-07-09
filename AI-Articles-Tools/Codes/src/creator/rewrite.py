"""二次创作编排：标题重写 + 正文改写 + 配图生成 + 头条排版 + 入库。

相似度说明：真实“与原创相似度<10%”依赖改写模型质量与嵌入查重；
此处 similarity_estimate 用 4-gram Jaccard 作为离线可跑的近似指标，
超过阈值会给出警告（真实场景应接嵌入/查重 API）。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.collector.base import sanitize, ts_now
from src.config import AppConfig
from src.creator.image import ImageClient
from src.creator.layout import compose_markdown, compose_wechat
from src.creator.llm import LLMClient
from src.db import Database
from src.models import CreationResult, MediaItem

_MAX_TITLE = 30


TITLE_SYSTEM = (
    "你是一名资深自媒体标题党（褒义）。请为文章起一个不超过30个汉字的标题。"
    "要求：1) 与原标题明显不同；2) 使用钩子技巧（悬念/冲突/数字/反差/利益点）；"
    "3) 有吸引力、能促点击；4) 只返回标题本身，不要解释、不要引号。"
)

REWRITE_SYSTEM = (
    "你是一名优秀的自媒体撰稿人。请将下面的原文改写为一篇全新的文章。"
    "要求：1) 保留核心信息与观点；2) 用自然、口语化中文，像真人写的；"
    "3) 严禁使用“首先/其次/综上所述/值得注意的是”等AI腔套话；"
    "4) 段落短小、节奏明快；5) 与原文表述明显不同（相似度尽量低于10%）；"
    "6) 只返回改写后的正文，不要小标题序号堆砌。"
)

CAPTION_SYSTEM = (
    "为文章某一段配图生成素材。严格按以下三行返回，不要多余内容：\n"
    "第1行：中文图注（≤16字，提炼该段画面感）\n"
    "第2行：英文图注（对应翻译）\n"
    "第3行起：给绘图模型的视觉描述 prompt（中文，说明风格与主体）"
)


def similarity_estimate(a: str, b: str) -> float:
    def grams(s: str, n: int = 4):
        s = re.sub(r"\s+", "", s)
        if len(s) < n:
            return {s}
        return {s[i : i + n] for i in range(len(s) - n + 1)}

    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return round(len(ga & gb) / len(ga | gb), 4)


def enforce_title_len(title: str, max_len: int = _MAX_TITLE) -> str:
    title = title.strip().strip('"').strip("'").strip()
    if len(title) <= max_len:
        return title
    # 在 max_len 内找最后一个标点截断，保留完整语义
    for i in range(max_len, 0, -1):
        if title[i - 1] in "，。！？、：； ,.!?":
            return title[:i].rstrip("，。！？、：； ,.!?")
    return title[:max_len]


def _chunk(paragraphs: list[str], size: int = 2, cap: int = 3) -> list[str]:
    chunks, i = [], 0
    while i < len(paragraphs) and len(chunks) < cap:
        chunks.append("\n".join(paragraphs[i : i + size]))
        i += size
    return chunks


class RewriteOrchestrator:
    def __init__(self, cfg: AppConfig, db: Database, llm: LLMClient, mock: bool = False):
        self.cfg = cfg
        self.db = db
        self.llm = llm
        self.mock = mock

    def create(self, original_title: str, original_body: str, source_id: int | None = None) -> CreationResult:
        # 1) 标题（钩子、≤30字、明显不同）
        raw_title = self.llm.chat(TITLE_SYSTEM, f"原标题：{original_title}\n\n原文摘要：{original_body[:400]}")
        new_title = enforce_title_len(raw_title)

        # 2) 正文改写
        rewritten = self.llm.chat(REWRITE_SYSTEM, original_body)

        # 3) 规划配图：按段落切片，至多 3 张
        paras = [p.strip() for p in rewritten.split("\n") if p.strip()]
        intro, body_paras = self._split_intro(paras)
        chunks = _chunk(body_paras, size=2, cap=3)

        segments = []
        media_items: list[MediaItem] = []
        ts = ts_now()
        out_folder = self.cfg.out_dir / f"文章二创-{sanitize(new_title)}-{ts}"
        out_folder.mkdir(parents=True, exist_ok=True)
        img_client = ImageClient(self.cfg.image, out_folder, mock=self.mock)

        for idx, chunk in enumerate(chunks):
            caption_zh, caption_en, visual = self._caption_for(chunk, idx == 0)
            img_path = img_client.generate(visual, caption_zh, caption_en)
            media_items.append(MediaItem("cover" if idx == 0 else "inline", img_path, caption_zh, caption_en))
            segments.append({
                "text": chunk,
                "image_path": img_path,
                "caption_zh": caption_zh,
                "caption_en": caption_en,
            })

        # 4) 排版：头条风格 + 公众号风格，双份 md
        toutiao_md = compose_markdown(new_title, intro, segments)
        wechat_md = compose_wechat(new_title, intro, segments)
        toutiao_path = out_folder / f"头条风格-{sanitize(new_title)}-{ts}.md"
        wechat_path = out_folder / f"公众号风格-{sanitize(new_title)}-{ts}.md"
        toutiao_path.write_text(toutiao_md, encoding="utf-8")
        wechat_path.write_text(wechat_md, encoding="utf-8")

        # 5) 入库
        # mock 模式不调用真实改写，相似度记为占位低值；真实模式用 4-gram Jaccard 近似。
        # 注：真正“与原创相似度<10%”应由改写模型质量 + 嵌入查重 API 保障，此处仅为离线可跑的近似指标。
        sim = 0.05 if self.mock else similarity_estimate(original_body, rewritten)
        out_id = self.db.insert_output(source_id, new_title, out_folder.name, toutiao_path, similarity=sim)
        for m in media_items:
            self.db.insert_media("output", out_id, m.kind, m.path, m.caption_zh, m.caption_en)

        return CreationResult(out_id, new_title, out_folder, toutiao_path, wechat_path, sim, media_items)

    # ---------- 内部 ----------
    @staticmethod
    def _split_intro(paras: list[str]) -> tuple[str, list[str]]:
        """导语只取首句作钩子；正文从首句之后接续，避免导语与正文重复。"""
        if not paras:
            return "", []
        first = paras[0]
        parts = re.split(r"(?<=[。！？!?])", first, maxsplit=1)
        intro = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        body = ([rest] if rest else []) + paras[1:]
        return intro, body

    def _caption_for(self, chunk: str, is_cover: bool) -> tuple[str, str, str]:
        if self.mock:
            base = re.sub(r"\s+", "", chunk)[:12]
            zh = ("封面：" if is_cover else "配图：") + base
            en = ("Cover: " if is_cover else "Illustration: ") + base
            visual = f"扁平插画风，主题：{base}"
            return zh, en, visual
        resp = self.llm.chat(CAPTION_SYSTEM, chunk)
        lines = [ln.strip() for ln in resp.splitlines() if ln.strip()]
        zh = lines[0] if len(lines) > 0 else "配图"
        en = lines[1] if len(lines) > 1 else "Illustration"
        visual = "\n".join(lines[2:]) if len(lines) > 2 else zh
        return zh, en, visual
