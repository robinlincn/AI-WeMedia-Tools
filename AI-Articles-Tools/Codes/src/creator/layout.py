"""头条号排版：把二创正文 + 配图组合为符合头条号发文规范的 Markdown。

规范要点（尽量贴近头条号阅读体验）：
- 标题独立（frontmatter title + 正文 H1）
- 开篇一句导语，快速抓住注意力
- 段落短小、重点句加粗
- 章节之间用分隔线，配图居中并带中英文图注
- 结尾引导互动（点赞 / 评论 / 关注）
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _bold_lead(paragraph: str) -> str:
    """把每段首句做轻量加粗，增强可读性。"""
    para = paragraph.strip()
    if not para:
        return para
    # 以第一个句号/问号/感叹号切分首句
    for i, ch in enumerate(para):
        if ch in "。！？" and i > 4:
            head, tail = para[: i + 1], para[i + 1 :].strip()
            return f"**{head}**{tail}"
    return para


def compose_markdown(
    title: str,
    intro: str,
    segments: list[dict],
    cta: str = "如果觉得有用，欢迎点赞、评论、关注，后续持续分享干货。",
) -> str:
    """segments: [{text, image_path(Optional[Path]), caption_zh, caption_en}]"""
    parts = [f"# {title}", ""]
    if intro:
        parts.append(f"> {intro}")
        parts.append("")
    parts.append("---")
    parts.append("")

    for seg in segments:
        text = seg.get("text", "").strip()
        if text:
            for ln in text.split("\n"):
                ln = ln.strip()
                if ln:
                    parts.append(_bold_lead(ln))
                    parts.append("")
        img: Optional[Path] = seg.get("image_path")
        if img:
            cz = seg.get("caption_zh", "")
            ce = seg.get("caption_en", "")
            parts.append(f"![{cz or '配图'}](images/{img.name})")
            if cz or ce:
                cap = f"*{cz} / {ce}*" if (cz and ce) else f"*{cz or ce}*"
                parts.append(cap)
            parts.append("")
            parts.append("---")
            parts.append("")

    if cta:
        parts.append(cta)
    return "\n".join(parts).rstrip() + "\n"


def compose_wechat(
    title: str,
    intro: str,
    segments: list[dict],
    cta: str = "如果觉得有用，欢迎点赞、在看、分享给朋友；也欢迎关注我们，后续持续分享干货。",
) -> str:
    """公众号风格：更柔和、留白多、章节间不加分隔线，适合公众号编辑器直接粘贴。"""
    parts = [f"# {title}", ""]
    if intro:
        parts.append(f"> {intro}")
        parts.append("")
    for seg in segments:
        text = seg.get("text", "").strip()
        if text:
            for ln in text.split("\n"):
                ln = ln.strip()
                if ln:
                    parts.append(_bold_lead(ln))
                    parts.append("")
        img: Optional[Path] = seg.get("image_path")
        if img:
            cz = seg.get("caption_zh", "")
            ce = seg.get("caption_en", "")
            parts.append(f"![{cz or '配图'}](images/{img.name})")
            if cz or ce:
                cap = f"*{cz} / {ce}*" if (cz and ce) else f"*{cz or ce}*"
                parts.append(cap)
            parts.append("")
    if cta:
        parts.append(cta)
    return "\n".join(parts).rstrip() + "\n"
