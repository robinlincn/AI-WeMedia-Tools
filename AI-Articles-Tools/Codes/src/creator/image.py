"""图片生成客户端：OpenAI 兼容图像接口。

说明：AI 绘图模型对“在图中渲染文字”支持不稳定，因此“中英文副标题”以
图文下方的 caption 形式呈现（存储于 media 表并在 md 中展示），图片本身由
视觉描述 prompt 生成。

- 真实模式：client.images.generate（gpt-image-1 / dall-e-3 等），保存为 png
- mock 模式：生成带中英文副标题的 SVG 占位图，离线可跑
"""
from __future__ import annotations

import re
from pathlib import Path

from src.config import ProviderConfig


def slugify(s: str, max_len: int = 30) -> str:
    s = re.sub(r"[^\w一-鿿]+", "_", s).strip("_")
    return s[:max_len] or "img"


class ImageClient:
    def __init__(self, pc: ProviderConfig, out_folder: Path, mock: bool = False):
        self.pc = pc
        self.out_folder = Path(out_folder)
        self.img_dir = self.out_folder / "images"
        self.img_dir.mkdir(parents=True, exist_ok=True)
        self.mock = mock
        self._client = None

    def _real(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.pc.base_url or None, api_key=self.pc.api_key)
        return self._client

    def generate(self, visual_prompt: str, caption_zh: str, caption_en: str) -> Path:
        if self.mock:
            return self._mock_svg(visual_prompt, caption_zh, caption_en)
        resp = self._real().images.generate(
            model=self.pc.model or "gpt-image-1",
            prompt=visual_prompt,
            size="1024x1024",
            n=1,
        )
        item = resp.data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            import base64
            data = base64.b64decode(b64)
            ext = "png"
        elif getattr(item, "url", None):
            import requests
            data = requests.get(item.url).content
            ext = "png"
        else:
            raise RuntimeError("图像接口未返回可用内容")
        path = self.img_dir / f"{slugify(caption_zh)}.{ext}"
        path.write_bytes(data)
        return path

    def _mock_svg(self, visual_prompt: str, caption_zh: str, caption_en: str) -> Path:
        safe_zh = (caption_zh or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_en = (caption_en or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450">
  <rect width="800" height="450" fill="#2b6cb0"/>
  <text x="40" y="210" fill="#ffffff" font-size="28" font-family="sans-serif">{safe_zh}</text>
  <text x="40" y="250" fill="#cbe3ff" font-size="18" font-family="sans-serif">{safe_en}</text>
</svg>"""
        path = self.img_dir / f"{slugify(caption_zh)}.svg"
        path.write_text(svg, encoding="utf-8")
        return path
