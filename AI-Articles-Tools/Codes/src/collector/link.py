"""链接采集：抓取网页正文与图片，保存为 md。

实现：requests 下载 + BeautifulSoup(lxml) 解析。
- 标题：og:title > <title>，并去除站点后缀
- 正文：按文档顺序遍历，保留 标题层级(h1-h6) / 段落 / 列表 / 引用 / 内联图片
- 图片：og:image 封面 + 正文内懒加载图(data-src 真地址)，下载到 images/ 后内联引用
- 头条桌面版为纯 JS 渲染，自动改写移动版服务端渲染地址 + 移动 UA
"""
from __future__ import annotations

import re
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
# 头条等站点桌面版是纯 JS 渲染（requests 抓不到正文），移动版为服务端渲染，
# 故对头条强制改用移动 UA + 移动版地址。
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
_TOUTIAO_RE = re.compile(r"(?:www\.)?toutiao\.com/(?:article/|i)?(\d{15,})")
_TITLE_SUFFIX_RE = re.compile(r"\s*[-—_|]\s*(今日头条|头条|Toutiao)\s*$", re.I)
_TIMEOUT = 20

# 页面 UI 噪点文本（正文提取时跳过）
_NOISE_HINTS = (
    "打开App", "查看全文", "相关推荐", "扫码", "下载App", "登录后",
    "评论区", "广告", "点击展开", "展开阅读", "免责声明", "声明：",
)


class LinkCollector(BaseCollector):
    prefix = "文章链接采集"

    def collect(self, url: str, title: str | None = None) -> CollectionResult:
        url = self._normalize_url(url)
        headers = {"User-Agent": _MOBILE_UA} if "m.toutiao.com" in url else _HEADERS
        resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        soup = BeautifulSoup(resp.text, "lxml")

        raw_title = title or self._extract_title(soup) or Path(urlparse(url).path).stem or "网页文章"
        title = self._clean_title(raw_title)
        blocks, img_map = self._extract_content(soup, url)

        folder = self.make_folder(title)
        for u, name in img_map.items():
            self._download_one(folder, u, name, url)

        md_body = self._render(blocks, img_map)
        raw_text = self._to_raw_text(blocks)

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
        sid = self.record("link", title, folder, md_path, url=url, raw_text=raw_text)
        return CollectionResult(sid, "link", title, folder, md_path)

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        if og := soup.find("meta", property="og:title"):
            if v := og.get("content"):
                return v.strip()
        if t := soup.title:
            return t.get_text(strip=True)
        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        """头条桌面版为 JS 渲染（抓不到正文），统一改写为移动版服务端渲染地址。"""
        m = _TOUTIAO_RE.search(url)
        if m and "m.toutiao.com" not in url:
            return f"https://m.toutiao.com/i{m.group(1)}/"
        return url

    @staticmethod
    def _clean_title(title: str) -> str:
        """去掉标题尾部站点后缀，如「 - 今日头条」。"""
        return _TITLE_SUFFIX_RE.sub("", title).strip()

    # ---------- 正文提取 ----------
    def _extract_content(self, soup: BeautifulSoup, base_url: str):
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "button", "iframe"]):
            tag.decompose()
        container = soup.find("article") or soup.find("main") or soup.body or soup

        blocks: list = []
        img_order: list = []
        seen: set = set()

        def add_img(src):
            if not src or src.startswith("data:"):
                return
            abs_url = urljoin(base_url, src)
            if urlparse(abs_url).scheme not in ("http", "https"):
                return
            # 跳过 App UI 资源（logo / 头像 / loading 图）
            if "toutiaostatic.com/obj/toutiao-duanwai" in abs_url:
                return
            if "user-avatar" in abs_url:
                return
            if abs_url in seen:
                return
            seen.add(abs_url)
            img_order.append(abs_url)
            blocks.append(("img", abs_url))

        # 封面图（og:image）作为首图
        if og := soup.find("meta", property="og:image"):
            if v := og.get("content"):
                add_img(v)

        self._walk(container, blocks, add_img)
        img_map = {u: f"img_{i + 1}{self._ext(u)}" for i, u in enumerate(img_order)}
        return blocks, img_map

    def _walk(self, node, blocks: list, add_img):
        for child in node.children:
            name = getattr(child, "name", None)
            if name is None:  # 文本节点
                continue
            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                txt = child.get_text(strip=True)
                if txt:
                    blocks.append(("h", (int(name[1]), txt)))
            elif name == "p":
                # 段落内可能嵌图（懒加载 data-src）
                for img in child.find_all("img"):
                    add_img(img.get("data-src") or img.get("src"))
                txt = child.get_text(strip=True)
                if txt and len(txt) >= 2 and not self._is_noise(txt):
                    blocks.append(("p", txt))
            elif name == "img":
                add_img(child.get("data-src") or child.get("src"))
            elif name in ("ul", "ol"):
                items = [li.get_text(strip=True) for li in child.find_all("li")]
                items = [it for it in items if it and not self._is_noise(it)]
                if items:
                    blocks.append(("list", items))
            elif name == "blockquote":
                txt = child.get_text(strip=True)
                if txt and not self._is_noise(txt):
                    blocks.append(("quote", txt))
            else:
                # div / section / figure 等容器：递归
                self._walk(child, blocks, add_img)

    @staticmethod
    def _is_noise(txt: str) -> bool:
        return any(h in txt for h in _NOISE_HINTS)

    @staticmethod
    def _ext(url: str) -> str:
        p = urlparse(url).path.lower()
        if p.endswith(".png"):
            return ".png"
        if p.endswith(".webp"):
            return ".webp"
        if p.endswith(".gif"):
            return ".gif"
        if p.endswith(".jpg") or p.endswith(".jpeg"):
            return ".jpg"
        return ".jpg"

    @staticmethod
    def _to_raw_text(blocks: list) -> str:
        parts = []
        for kind, data in blocks:
            if kind == "p":
                parts.append(data)
            elif kind == "quote":
                parts.append(data)
            elif kind == "h":
                parts.append(data[1])
        return "\n".join(parts).strip()

    def _download_one(self, folder: Path, url: str, name: str, referer: str) -> None:
        try:
            r = requests.get(url, headers={**_HEADERS, "Referer": referer}, timeout=_TIMEOUT)
            if r.status_code != 200:
                return
            ctype = r.headers.get("Content-Type", "")
            ext = "jpg" if "jpeg" in ctype else "png" if "png" in ctype else "webp" if "webp" in ctype else "img"
            if r.content[:3] == b"\xff\xd8\xff":
                ext = "jpg"
            elif r.content[:8] == b"\x89PNG\r\n\x1a\n":
                ext = "png"
            path = folder / "images" / f"{Path(name).stem}.{ext}"
            path.write_bytes(r.content)
        except Exception:
            return

    @staticmethod
    def _render(blocks: list, img_map: dict) -> str:
        out: list = []
        for kind, data in blocks:
            if kind == "h":
                level, txt = data
                hashes = "#" * max(2, min(level, 4))  # h1->##, h2->### ...
                out.append(f"{hashes} {txt}")
            elif kind == "p":
                out.append(data)
            elif kind == "img":
                nm = img_map.get(data)
                if nm:
                    out.append(f"![配图](images/{nm})")
            elif kind == "list":
                for it in data:
                    out.append(f"- {it}")
            elif kind == "quote":
                out.append(f"> {data}")
            out.append("")  # 块间空行
        return "\n".join(out).strip()
