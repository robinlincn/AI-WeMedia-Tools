"""视频采集：视频分享地址或本地视频文件 -> 提取口播音频 -> 语音识别(ASR) -> 文案 md。

流程：
  1. URL  -> yt-dlp 下载；本地文件 -> 复制到采集文件夹
  2. ffmpeg 提取音频（单声道 16k）
  3. ASR（OpenAI 兼容音频接口，默认 whisper-1）转写为口播文案
  mock 模式：跳过下载/转写，直接生成占位文案，便于离线验证流程。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.collector.base import BaseCollector, ts_now
from src.models import CollectionResult


def _looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


class VideoCollector(BaseCollector):
    prefix = "视频采集"

    def __init__(self, cfg, db, asr_client=None):
        super().__init__(cfg, db)
        self.asr_client = asr_client

    def collect(self, input_value: str, title: str | None = None, mock: bool = False) -> CollectionResult:
        is_url = _looks_like_url(input_value)
        if not title:
            title = self._derive_title(input_value, is_url)
        folder = self.make_folder(title)

        if mock:
            transcript = self._mock_transcript(title)
            note = "（mock 模式：未实际下载/转写）"
        else:
            video_path = self._acquire(input_value, is_url, folder)
            audio_path = self._extract_audio(video_path, folder)
            transcript = self._transcribe(audio_path)
            note = ""

        body = f"{note}\n\n{transcript}".strip()
        md_path = self.save_md(
            folder,
            title,
            body,
            {
                "title": title,
                "source_type": "video",
                "source": input_value,
                "collected_at": ts_now(),
            },
        )
        sid = self.record("video", title, folder, md_path, url=input_value if is_url else None,
                          raw_text=transcript)
        return CollectionResult(sid, "video", title, folder, md_path)

    # ---------- 内部 ----------
    def _acquire(self, input_value: str, is_url: bool, folder: Path) -> Path:
        if is_url:
            try:
                import yt_dlp  # noqa: F401
            except ImportError:
                raise RuntimeError("未安装 yt-dlp，无法下载视频，请先 pip install yt-dlp")
            out_tmpl = str(folder / "%(title)s.%(ext)s")
            subprocess.run(
                ["yt-dlp", "-f", "best", "-o", out_tmpl, input_value],
                check=True, capture_output=True, text=True,
            )
            videos = [p for p in folder.iterdir() if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".flv")]
            if not videos:
                raise RuntimeError("yt-dlp 下载完成但未发现视频文件")
            return videos[0]
        src = Path(input_value)
        if not src.is_file():
            raise RuntimeError(f"本地视频文件不存在：{input_value}")
        dest = folder / src.name
        if dest != src:
            shutil.copy2(src, dest)
        return dest

    def _extract_audio(self, video_path: Path, folder: Path) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("未检测到 ffmpeg，无法提取音频。请安装 ffmpeg 并加入 PATH。")
        audio_path = folder / "audio.mp3"
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
             "-f", "mp3", str(audio_path)],
            check=True, capture_output=True, text=True,
        )
        return audio_path

    def _transcribe(self, audio_path: Path) -> str:
        if self.asr_client is None:
            from openai import OpenAI
            self.asr_client = OpenAI(base_url=self.cfg.asr.base_url or None,
                                     api_key=self.cfg.asr.api_key)
        resp = self.asr_client.audio.transcriptions.create(
            model=self.cfg.asr.model or "whisper-1",
            file=open(audio_path, "rb"),
        )
        return getattr(resp, "text", str(resp)).strip()

    @staticmethod
    def _derive_title(input_value: str, is_url: bool) -> str:
        if is_url:
            from urllib.parse import urlparse
            seg = [s for s in urlparse(input_value).path.split("/") if s]
            return seg[-1][:40] if seg else "视频采集"
        return Path(input_value).stem[:40] or "视频采集"

    @staticmethod
    def _mock_transcript(title: str) -> str:
        return (
            f"这是《{title}》的视频口播占位文案（mock）。\n\n"
            "第一段：用一句话点出核心冲突，制造悬念。\n\n"
            "第二段：展开故事背景，交代人物与处境。\n\n"
            "第三段：给出关键转折与 actionable 的建议。\n\n"
            "结尾：用一句金句收束，引导观众评论与关注。"
        )
