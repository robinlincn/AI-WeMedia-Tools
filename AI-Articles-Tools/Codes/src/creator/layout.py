"""双风格排版：把二创正文 + 配图组合为可直接发布到头条号 / 微信公众号的 Markdown。

两份模板均参考了 m.toutiao.com 移动版真实文章样式（分段、<strong> 加粗位置、
段落字数、互动语结尾）以及微信公众号编辑器粘贴后样式（留白、加粗钩子、引用块）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _bold_lead(paragraph: str) -> str:
    """把段落切成钩子 + 余句，钩子加粗；保留整段加粗兜底（短段或无终止符）。"""
    para = paragraph.strip()
    if not para:
        return para
    for i, ch in enumerate(para):
        if ch in "。！？" and i >= 6:
            head, tail = para[: i + 1], para[i + 1 :].strip()
            return f"**{head}**{tail}"
    # 兜底：长段无终止符 → 整段加粗（公众号 / 头条首屏钩子）
    if len(para) >= 18:
        return f"**{para}**"
    return para


def compose_markdown(
    title: str,
    intro: str,
    segments: list[dict],
    cta: str = "好了，分享到这里，希望对你有所启发和帮助。觉得不错可以点个赞、转发给需要的朋友，关注我，后续持续分享更多干货～",
) -> str:
    """头条号风格（贴合 m.toutiao.com 移动版样式）：
    - 标题 H1
    - 开头一句强钩子（加粗），点出痛点/反差
    - 段落短小（30~100 字），段间空行
    - 每段首句加粗，吸引首屏
    - 关键名词加粗（对应原文 <strong>：项目名、功能名）
    - 配图居中，前后各空一行（图注中英对照）
    - 文末固定强引导句
    """
    parts = [f"# {title}", ""]

    if intro:
        parts.append(f"> **{intro}**")
        parts.append("")

    for seg in segments:
        text = seg.get("text", "").strip()
        if text:
            for ln in text.split("\n"):
                ln = ln.strip()
                if not ln:
                    continue
                parts.append(_bold_lead(ln))
                parts.append("")  # 段间空行（头条移动端断句呼吸）

        img: Optional[Path] = seg.get("image_path")
        if img:
            parts.append("")  # 图前空行，确保渲染器识别图片块
            cz = seg.get("caption_zh", "")
            ce = seg.get("caption_en", "")
            parts.append(f"![{cz or '配图'}](images/{img.name})")
            if cz or ce:
                cap = f"*{cz} / {ce}*" if (cz and ce) else f"*{cz or ce}*"
                parts.append(cap)
            parts.append("")  # 图后空行

    if cta:
        parts.append("")
        parts.append(f"**{cta}**")
    return "\n".join(parts).rstrip() + "\n"


def compose_wechat(
    title: str,
    intro: str,
    segments: list[dict],
    cta: str = "如果觉得这篇对你有帮助，欢迎点赞、在看、分享给身边的朋友。关注我，后续持续分享更多 AI 实战干货～",
) -> str:
    """公众号风格（贴合微信公众号编辑器粘贴效果）：
    - 标题 H1（编辑器自动转大字号）
    - 开头整段加粗作为引言小标题
    - 段间两行空行留白（公众号阅读节奏舒缓）
    - 关键句加粗、引用用 > 块（编辑器自动套样式）
    - 配图后空两行，避免被编辑器挤压
    - 文末固定引导卡片（感谢阅读 + 互动）
    """
    parts = [f"# {title}", ""]

    if intro:
        parts.append(f"> **{intro}**")
        parts.append("")

    for seg in segments:
        text = seg.get("text", "").strip()
        if text:
            for ln in text.split("\n"):
                ln = ln.strip()
                if not ln:
                    continue
                parts.append(_bold_lead(ln))
                parts.append("")
                parts.append("")  # 公众号：段间多一行空行

        img: Optional[Path] = seg.get("image_path")
        if img:
            parts.append("")
            parts.append("")
            cz = seg.get("caption_zh", "")
            ce = seg.get("caption_en", "")
            parts.append(f"![{cz or '配图'}](images/{img.name})")
            if cz or ce:
                cap = f"*{cz} / {ce}*" if (cz and ce) else f"*{cz or ce}*"
                parts.append(cap)
            parts.append("")
            parts.append("")  # 图后空两行

    if cta:
        parts.append("")
        parts.append("> ━━━━ 感谢阅读 ━━━━")
        parts.append(f"> {cta}")
    return "\n".join(parts).rstrip() + "\n"