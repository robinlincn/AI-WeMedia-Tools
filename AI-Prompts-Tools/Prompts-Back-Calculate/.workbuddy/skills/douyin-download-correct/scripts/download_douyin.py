# -*- coding: utf-8 -*-
"""
抖音无水印视频下载器 v2.0 - 项目优化版
针对沙盒（腾讯云机房）IP 风控 + bash 14KB buffer bug 优化。

V2 新增：
- 短链/长链智能识别（短链通过 r.url 跟 redirect 拿 video_id，即使 iesdouyin 返空也能跑通）
- 自动抽帧到 frames/{视频标题}-{日期}/ 目录（与 videos 文件名同步）
- 一键完成：下载 → 校验 → 抽帧

用法：
  python download_douyin.py <分享链接或文本> [输出目录]
  示例: python download_douyin.py "https://v.douyin.com/Fl5IoRTOtfI/"
        python download_douyin.py "https://www.douyin.com/video/7649942475087416614"
"""
import sys
import os
import re
import json
import subprocess
import shutil
import time
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/116.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/?is_from_mobile_home=1&recommend=1",
}

# 项目根目录
PROJECT_ROOT = r"E:\自媒体\AI视频\AI视频提示词反推"
DEFAULT_VIDEOS_DIR = os.path.join(PROJECT_ROOT, "videos")
DEFAULT_FRAMES_DIR = os.path.join(PROJECT_ROOT, "frames")


def extract_url(text: str):
    """从分享文本中提取抖音链接（短链或长链）"""
    m = re.search(r"https?://v\.douyin\.com/[a-zA-Z0-9\-_.]+", text)
    if m:
        url = m.group(0)
        return url if url.endswith("/") else url + "/"
    m = re.search(r"https?://(?:www\.)?douyin\.com/(?:video|note)/[0-9]+", text)
    if m:
        return m.group(0)
    return None


def get_real_url_smart(share_url: str):
    """
    V2 智能 URL 解析：
    - 长链（/video/{id}）直接返回，不走 301
    - 短链（v.douyin.com/{code}）跟 redirect 拿 r.url，即使 iesdouyin 返 200 SIZE=0
      也能从 URL 路径里提取 video_id
    返回 (final_url, video_id)
    """
    # 长链：直接解析
    if "douyin.com/video/" in share_url or "douyin.com/note/" in share_url:
        vid = get_video_id(share_url)
        if vid:
            return share_url, vid

    # 短链：跟 redirect
    try:
        import requests
        r = requests.get(share_url, headers=HEADERS, allow_redirects=True, timeout=10)
        final_url = r.url
        vid = get_video_id(final_url)
        if vid:
            return final_url, vid
        print(f"[!] 短链跟 redirect 后未拿到 video_id, final_url={final_url[:100]}")
    except Exception as e:
        print(f"[!] 短链跟 redirect 失败: {e}")

    # 兜底：从原始 share_url 提取
    vid = get_video_id(share_url)
    if vid:
        return share_url, vid

    return None, None


def get_video_id(url: str):
    """从 URL 中提取视频 ID（兼容 modal_id/note_id/item_id/video_id/路径）"""
    if not url:
        return None
    for param in ["modal_id", "note_id", "item_id", "video_id"]:
        m = re.search(rf"{param}=([0-9]+)", url)
        if m:
            return m.group(1)
    m = re.search(r"/(?:video|note|share/video)/([0-9]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/([0-9]{15,})", url)
    if m:
        return m.group(1)
    return None


def fetch_router_data(video_id: str):
    """
    GET iesdouyin.com/share/video/{id}/  拿 _ROUTER_DATA JSON
    注意：沙盒云 IP 对 m.iesdouyin.com 拒连、对 www.iesdouyin.com 返 200 SIZE=0
          → 实际 iesdouyin share 页对沙盒云 IP 是被风控的，本函数大概率返 None
          → 这时要走 doynload-url 直连兜底（用户提供 douyinvod.com URL）
    """
    try:
        import requests
        url = f"https://www.iesdouyin.com/share/video/{video_id}/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200 or len(r.text) < 1000:
            print(f"[!] iesdouyin 返 {r.status_code} / body {len(r.text)} bytes（沙盒云 IP 可能被风控）")
            return None
        m = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", r.text, re.DOTALL)
        if not m:
            return None
        return json.loads(m.group(1).strip())
    except Exception as e:
        print(f"[!] iesdouyin 请求失败: {e}")
        return None


def parse_video_info(data: dict):
    """从 _ROUTER_DATA JSON 提取 desc/nickname/无水印源 URL"""
    try:
        loader_data = data.get("loaderData", {})
        video_info_res = None
        for key, value in loader_data.items():
            if isinstance(value, dict) and "videoInfoRes" in value:
                video_info_res = value["videoInfoRes"]
                break
        if not video_info_res:
            return None
        item_list = video_info_res.get("item_list", [])
        if not item_list:
            return None
        video_item = item_list[0]
        desc = video_item.get("desc", "无标题")
        nickname = video_item.get("author", {}).get("nickname", "未知作者")
        uri = video_item.get("video", {}).get("play_addr", {}).get("uri")
        if not uri:
            return None
        return {
            "desc": desc,
            "nickname": nickname,
            "download_url": f"https://www.douyin.com/aweme/v1/play/?video_id={uri}",
        }
    except Exception as e:
        print(f"[!] 解析视频信息出错: {e}")
        return None


def download_via_powershell(url: str, output_path: str) -> bool:
    """
    用 PowerShell Invoke-WebRequest 下载（绕开 bash 14KB buffer bug）
    """
    if os.path.exists(output_path):
        os.remove(output_path)
    ps_script = f"""
$ErrorActionPreference = "Stop"
$url = "{url}"
$out = "{output_path}"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try {{
    Invoke-WebRequest -Uri $url -OutFile $out -Headers @{{"User-Agent"="Mozilla/5.0"}} -UseBasicParsing -TimeoutSec 600
    $sw.Stop()
    $sz = (Get-Item $out).Length
    Write-Host "OK size=$sz time=$($sw.Elapsed.TotalSeconds)s"
}} catch {{
    $sw.Stop()
    Write-Host "ERR: $($_.Exception.Message)"
    exit 1
}}
"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=700,
        )
        out = (result.stdout or "") + (result.stderr or "")
        if "OK size=" in out:
            sz_line = [l for l in out.splitlines() if "OK size=" in l][0]
            print(f"  {sz_line.strip()}")
            return True
        print(f"  PowerShell 下载失败: {out[:300]}")
        return False
    except Exception as e:
        print(f"  PowerShell 调用异常: {e}")
        return False


def ffprobe_check(file_path: str) -> dict:
    """用 ffprobe 校验下载的视频，返回校验信息"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        for p in [r"C:\ffmpeg\bin\ffprobe.exe", r"D:\Software\ffmpeg\bin\ffprobe.exe"]:
            if os.path.exists(p):
                ffprobe = p
                break
        else:
            return {"ok": False, "reason": "ffprobe 未找到"}

    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", "-i", file_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"ok": False, "reason": f"ffprobe 错误: {result.stderr[:200]}"}
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        duration = float(data.get("format", {}).get("duration", 0))
        size = int(data.get("format", {}).get("size", 0))
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        width = v_stream.get("width", 0)
        height = v_stream.get("height", 0)
        return {
            "ok": has_video and has_audio and duration < 1800,
            "has_video": has_video, "has_audio": has_audio,
            "duration": duration, "size": size,
            "width": width, "height": height,
            "nb_streams": len(streams),
            "reason": "" if (has_video and has_audio) else "缺少视频或音轨",
        }
    except Exception as e:
        return {"ok": False, "reason": f"ffprobe 异常: {e}"}


def safe_title(desc: str, max_len: int = 50) -> str:
    """
    生成干净的视频标题（用于命名文件 / 目录）：
    1. 先按强标点（。！？;\\n）切第一段
    2. 如果切出来仍 > max_len，按逗号切
    3. 多次反复：直到 <= max_len 或没标点可切
    4. 截 max_len + 去特殊字符 + 去空格
    """
    if not desc:
        return "video"
    s = desc.strip()
    # 反复切：先强标点，再逗号
    for splitter in [r'[。！？;\n]', '，']:
        if len(s) > max_len and splitter in s:
            s = re.split(splitter, s, maxsplit=1)[0] if splitter.startswith('[') else s.split(splitter, 1)[0]
    # 去特殊字符 + 去空格
    safe = re.sub(r'[\\/*?:"<>|\r\n\t]', "", s).strip().replace(" ", "")
    return safe[:max_len] or "video"


def extract_frames(video_path: str, frames_dir: str, title_prefix: str, mod_n: int = 150) -> int:
    """
    用 ffmpeg 抽关键帧到 frames_dir
    - mod_n: 每 mod_n 帧取一帧（30fps 下 mod_n=150 ≈ 5s/帧）
    - 文件名：{title_prefix}_{0001..NNNN}.jpg
    返回抽帧数量
    """
    if not os.path.exists(video_path):
        print(f"[!] 视频文件不存在: {video_path}")
        return 0

    os.makedirs(frames_dir, exist_ok=True)

    # 先清空目录里的旧文件（避免重复抽）
    for f in os.listdir(frames_dir):
        if f.lower().endswith(".jpg"):
            os.remove(os.path.join(frames_dir, f))

    out_pattern = os.path.join(frames_dir, f"{title_prefix}_%04d.jpg")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"select='not(mod(n\\,{mod_n}))',scale=1280:-1",
        "-vsync", "vfr", "-q:v", "2",
        out_pattern,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # 数抽出的帧
        frames = [f for f in os.listdir(frames_dir) if f.startswith(title_prefix) and f.endswith(".jpg")]
        return len(frames)
    except Exception as e:
        print(f"[!] 抽帧失败: {e}")
        return 0


def auto_frame_interval(duration_sec: float) -> int:
    """根据视频时长自动选抽帧间隔（30fps 下）"""
    if duration_sec <= 60:
        return 30       # 1s/帧
    elif duration_sec <= 300:  # 5min
        return 150      # 5s/帧
    elif duration_sec <= 1800:  # 30min
        return 300      # 10s/帧
    else:
        return 600      # 20s/帧


def run(raw_input: str, output_dir: str = None, auto_frame: bool = True) -> bool:
    """主流程"""
    if output_dir is None:
        output_dir = DEFAULT_VIDEOS_DIR
    os.makedirs(output_dir, exist_ok=True)

    share_url = extract_url(raw_input)
    if not share_url:
        print(f"[!] 未在输入中找到有效链接: {raw_input}")
        return False

    print(f"[+] 解析链接: {share_url}")

    # 1. 智能解析 URL（短链/长链都支持）
    final_url, video_id = get_real_url_smart(share_url)
    if not video_id:
        print("[!] 无法提取视频ID（短链 redirect 失败且无长链）")
        return False
    print(f"[+] 视频ID: {video_id}")

    # 2. 走 iesdouyin 拿元数据 + 无水印源
    data = fetch_router_data(video_id)
    if not data:
        print("[!] iesdouyin 拿不到 _ROUTER_DATA（沙盒云 IP 风控）")
        print("    💡 兜底方案：用本机 Chrome 打开链接 → F12 → Network 抓 .mp4 源 URL 贴回")
        print("    （注意：可能是 douyinvod.com 长片，验过时长/音轨再保留）")
        return False

    info = parse_video_info(data)
    if not info:
        print("[!] 解析视频信息失败")
        return False

    print(f"[+] 视频: {info['desc'][:60]}")
    print(f"[+] 作者: {info['nickname']}")

    # 3. 规范命名：抖音-{标题}-{日期}.mp4
    today = time.strftime("%Y%m%d")
    safe_title_str = safe_title(info["desc"])
    final_name = f"抖音-{safe_title_str}-{today}.mp4"
    final_path = os.path.join(output_dir, final_name)

    # 已存在则跳过
    if os.path.exists(final_path) and os.path.getsize(final_path) > 1000:
        print(f"[=] 文件已存在，跳过下载: {final_path}")
    else:
        print(f"[+] PowerShell 下载 ...")
        ok = download_via_powershell(info["download_url"], final_path)
        if not ok:
            return False

    # 4. ffprobe 校验
    print(f"[+] ffprobe 校验 ...")
    check = ffprobe_check(final_path)
    if check.get("ok"):
        print(f"[OK] 校验通过: video={'✓' if check.get('has_video') else '✗'} / audio={'✓' if check.get('has_audio') else '✗'}")
        print(f"     时长 {check.get('duration', 0):.1f}s / {check.get('width')}x{check.get('height')} / {check.get('size', 0)/1024/1024:.1f}MB")
    else:
        print(f"[!] 校验失败: {check.get('reason', 'unknown')}")
        print(f"     文件保留: {final_path}")
        return False

    # 5. 自动抽帧到 frames/{标题}-{日期}/
    if auto_frame:
        frames_subdir = f"{safe_title_str}-{today}"
        frames_dir = os.path.join(DEFAULT_FRAMES_DIR, frames_subdir)
        mod_n = auto_frame_interval(check.get("duration", 60))
        print(f"[+] 抽帧 → frames/{frames_subdir}/ (mod={mod_n}, 30fps 下 ≈ {mod_n//30}s/帧)")
        n = extract_frames(final_path, frames_dir, safe_title_str, mod_n=mod_n)
        if n > 0:
            print(f"[OK] 抽帧 {n} 张")
            print(f"[✅] 全部完成:")
            print(f"     视频: {final_path}")
            print(f"     抽帧: {frames_dir}/")
        else:
            print(f"[!] 抽帧 0 张（可能 ffmpeg 路径问题）")
    else:
        print(f"[✅] 下载完成: {final_path}")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python download_douyin.py <分享链接或文本> [输出目录]")
        print("  示例:")
        print("    python download_douyin.py 'https://v.douyin.com/Fl5IoRTOtfI/'")
        print("    python download_douyin.py 'https://www.douyin.com/video/7649942475087416614'")
        print("    python download_douyin.py '9.94 pQk:/ s@r.eb ... v.douyin.com/Fl5IoRTOtfI/ ...'")
        sys.exit(1)

    link = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    success = run(link, out)
    sys.exit(0 if success else 1)
