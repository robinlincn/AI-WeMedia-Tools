"""链接采集：抓取网页正文与图片，保存为 md。

实现：requests 下载 + BeautifulSoup(lxml) 解析。
- 标题：og:title > <title>
- 正文：优先 <article>/<main>，否则取<body>内 <p> 文本
- 图片：og:image + 正文内 <img>，转绝对地址，下载前若干张到 images/
"""
from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.collector.base import BaseCollector, sanitize, ts_now
from src.models import CollectionResult

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TIMEOUT = 20
_MAX_IMAGES = 5


class LinkCollector(BaseCollector):
    prefix = "文章采集"

    def collect(self, url: str, title: str | None = None) -> CollectionResult:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        soup = BeautifulSoup(resp.text, "lxml")

        title = title or self._extract_title(soup) or Path(urlparse(url).path).stem or "网页文章"
        body, img_urls = self._extract_content(soup, url)

        folder = self.make_folder(title)
        saved_imgs = self._download_images(folder, img_urls, url)
        md_body = self._render(body, saved_imgs)

        md_path = self.save_md(
            folder,
            title,
            md_body,
            {
                "title": title,
                "source_type": "link",
                "source_url": url,
                "collected_at": ts_now(),
            },
        )
        sid = self.record("link", title, folder, md_path, url=url, raw_text=body)
        return CollectionResult(sid, "link", title, folder, md_path)

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        if og := soup.find("meta", property="og:title"):
            if v := og.get("content"):
                return v.strip()
        if t := soup.title:
            return t.get_text(strip=True)
        return None

    def _extract_content(self, soup: BeautifulSoup, base_url: str):
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.decompose()
        container = soup.find("article") or soup.find("main") or soup.body or soup
        paras = [p.get_text(strip=True) for p in container.find_all("p")]
        paras = [t for t in paras if len(t) > 15]
        body = "\n\n".join(paras)

        img_urls = []
        if og := soup.find("meta", property="og:image"):
            if v := og.get("content"):
                img_urls.append(v)
        for img in container.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if not src:
                continue
            abs_url = urljoin(base_url, src)
            if urlparse(abs_url).scheme in ("http", "https"):
                img_urls.append(abs_url)
        # 去重
        seen, uniq = set(), []
        for u in img_urls:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        return body, uniq[:_MAX_IMAGES]

    def _download_images(self, folder: Path, img_urls: list[str], referer: str) -> list[str]:
        out = []
        for i, u in enumerate(img_urls, 1):
            try:
                r = requests.get(
                    u, headers={**_HEADERS, "Referer": referer}, timeout=_TIMEOUT
                )
                if r.status_code != 200:
                    continue
                ctype = r.headers.get("Content-Type", "")
                ext = "jpg" if "jpeg" in ctype else "png" if "png" in ctype else "img"
                # 容错：尝试从内容推断
                if r.content[:3] == b"\xff\xd8\xff":
                    ext = "jpg"
                elif r.content[:8] == b"\x89PNG\r\n\x1a\n":
                    ext = "png"
                path = folder / "images" / f"img_{i}.{ext}"
                path.write_bytes(r.content)
                out.append(path.name)
            except Exception:
                continue
        return out

    @staticmethod
    def _render(body: str, imgs: list[str]) -> str:
        blocks = []
        for name in imgs:
            blocks.append(f"![配图](images/{name})")
        if body:
            blocks.append(body)
        return "\n\n".join(blocks)
