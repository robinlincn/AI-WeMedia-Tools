#!/usr/bin/env python
"""清理 AI-Articles-Tools 本地运行产物（Articles/ 与 OutArticles/）。

作用：避免采集/二创产物（md + base64 内嵌图片，单篇可达 MB 级）日积月累占满磁盘。
本工具**只**作用于 gitignored 目录，**不会**误删入库文件。

使用：
    python scripts/cleanup_local_products.py                # 默认清 5 天前的
    python scripts/cleanup_local_products.py --days 30       # 清 30 天前的
    python scripts/cleanup_local_products.py --dry-run      # 只看不动手
    python scripts/cleanup_local_products.py --yes          # 跳过确认提示

退出码：0=成功（包含 dry-run）、1=用户中断、2=参数错误、3=运行异常。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET_DIRS = [
    PROJECT_ROOT / "AI-Articles-Tools" / "Articles",
    PROJECT_ROOT / "AI-Articles-Tools" / "OutArticles",
]

DENY_SUBSTR = ("AI-Global", "Codes", ".git", ".workbuddy")


def _scan(root, cutoff):
    if not root.exists():
        return []
    stale = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if any(s in p.as_posix() for s in DENY_SUBSTR):
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        if mtime < cutoff:
            stale.append(p)
    return stale


def _fmt_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _human_age(mtime, now):
    delta = now - mtime
    days = delta.days
    if days >= 1:
        return f"{days}d"
    hours = delta.seconds // 3600
    return f"{hours}h"


def main():
    p = argparse.ArgumentParser(description="清理 AI-Articles-Tools 本地运行产物")
    p.add_argument("--days", type=int, default=5, help="删除超过 N 天的产物目录（默认 5）")
    p.add_argument("--dry-run", action="store_true", help="只打印待删清单，不真正删除")
    p.add_argument("--yes", action="store_true", help="跳过交互确认")
    args = p.parse_args()

    if args.days < 0:
        print("error: --days 必须 >= 0", file=sys.stderr)
        return 2

    now = datetime.now()
    cutoff = now - timedelta(days=args.days)

    print(f"扫描根目录（mtime < {cutoff:%Y-%m-%d %H:%M}）：")
    all_stale = []
    for root in TARGET_DIRS:
        print(f"  - {root.relative_to(PROJECT_ROOT)}")
        for p in _scan(root, cutoff):
            all_stale.append((p, datetime.fromtimestamp(p.stat().st_mtime)))

    if not all_stale:
        print(f"\n没有超过 {args.days} 天的产物，无需清理。")
        return 0

    total_size = 0
    print(f"\n待删清单（{len(all_stale)} 个，{args.days} 天前）：")
    for p, mtime in all_stale:
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        total_size += size
        rel = p.relative_to(PROJECT_ROOT)
        print(f"  [{_human_age(mtime, now):>4}]  {rel}    ({_fmt_size(size)})")
    print(f"\n预计释放空间：{_fmt_size(total_size)}")

    if args.dry_run:
        print("\n[dry-run] 未执行任何删除。")
        return 0

    if not args.yes:
        print(f"\n确认删除上述 {len(all_stale)} 个目录？[y/N] ", end="", flush=True)
        try:
            ans = input().strip().lower()
        except EOFError:
            ans = ""
        if ans != "y":
            print("已取消。")
            return 1

    failed = 0
    for p, _ in all_stale:
        try:
            shutil.rmtree(p)
            rel = p.relative_to(PROJECT_ROOT)
            print(f"  OK deleted {rel}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {p}: {e}", file=sys.stderr)

    if failed:
        print(f"\n清理完成，但 {failed} 个目录失败。", file=sys.stderr)
        return 3
    print(f"\n清理完成：{len(all_stale)} 个目录已删除。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断。")
        sys.exit(1)
