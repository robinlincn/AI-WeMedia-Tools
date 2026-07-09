"""AI-Articles-Tools 命令行入口。

用法示例：
  # 文案采集 + 二创（离线 mock，无需 API key）
  python -m src.cli pipeline --type text --input "你的原始文案..." --mock

  # 链接采集 + 二创（需配置 LLM/图片/ASR key）
  python -m src.cli pipeline --type link --input https://example.com/article

  # 视频采集 + 二创
  python -m src.cli pipeline --type video --input https://douyin.com/xxx  --mock
  python -m src.cli pipeline --type video --input ./local.mp4          --mock

  # 分步：先采集，再基于 source_id 二创
  python -m src.cli collect  --type text --input "文案"
  python -m src.cli create  --source 1
  python -m src.cli list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 让 `python -m src.cli` 能找到同包模块
ROOT = Path(__file__).resolve().parents[2]  # AI-Articles-Tools
if str(ROOT / "Codes") not in sys.path:
    sys.path.insert(0, str(ROOT / "Codes"))

from src.config import load_config  # noqa: E402
from src.db import Database  # noqa: E402
from src.collector.text import TextCollector  # noqa: E402
from src.collector.link import LinkCollector  # noqa: E402
from src.collector.video import VideoCollector  # noqa: E402
from src.creator.llm import LLMClient  # noqa: E402
from src.creator.rewrite import RewriteOrchestrator  # noqa: E402


def _build(args) -> tuple:
    cfg = load_config(args.config)
    cfg.base_dir = ROOT
    cfg.resolve_paths()
    mock = args.mock or cfg.provider == "mock"
    db = Database(cfg.db_path)
    llm = LLMClient(cfg.llm, mock=mock)
    orch = RewriteOrchestrator(cfg, db, llm, mock=mock)
    return cfg, db, mock, orch


def cmd_collect(args):
    cfg, db, mock, _ = _build(args)
    if args.type == "text":
        r = TextCollector(cfg, db).collect(args.input, args.title)
    elif args.type == "link":
        r = LinkCollector(cfg, db).collect(args.input, args.title)
    elif args.type == "video":
        r = VideoCollector(cfg, db).collect(args.input, args.title, mock=mock)
    else:
        print("未知类型，仅支持 text/link/video"); sys.exit(2)
    print(f"[采集完成] source_id={r.source_id} type={r.source_type} title={r.title}")
    print(f"  文件夹: {r.folder}")
    print(f"  MD    : {r.md_path}")
    return r


def cmd_create(args):
    cfg, db, mock, orch = _build(args)
    sid = int(args.source)
    row = db.get_source(sid)
    if not row:
        print(f"未找到 source_id={sid}"); sys.exit(2)
    body = row["raw_text"] or Path(row["md_path"]).read_text(encoding="utf-8")
    res = orch.create(row["title"] or "未命名", body, source_id=sid)
    _print_result(res)
    return res


def cmd_pipeline(args):
    r = cmd_collect(args)
    cfg, db, mock, orch = _build(args)
    row = db.get_source(r.source_id)
    body = row["raw_text"] or Path(row["md_path"]).read_text(encoding="utf-8")
    res = orch.create(row["title"] or "未命名", body, source_id=r.source_id)
    _print_result(res)
    return res


def cmd_list(args):
    _, db, _, _ = _build(args)
    print("=== 采集源 sources ===")
    for s in db.list_sources():
        print(f"  [{s['id']}] {s['source_type']:5} | {s['title']} | {s['folder_name']}")
    print("=== 二创产物 outputs ===")
    for o in db.list_outputs():
        sim = o["similarity"]
        sim_s = f"{sim*100:.1f}%" if sim is not None else "n/a"
        print(f"  [{o['id']}] {o['title']} | 相似度 {sim_s} | {o['folder_name']}")


def _print_result(res):
    print(f"[二创完成] output_id={res.output_id} title={res.title}")
    print(f"  相似度(近似): {res.similarity*100:.2f}%")
    if res.similarity and res.similarity >= 0.10:
        print("  ⚠️ 近似相似度≥10%，建议加强改写或接入嵌入查重")
    print(f"  文件夹      : {res.folder}")
    print(f"  头条风格 MD : {res.md_path}")
    print(f"  公众号风格 MD: {res.wechat_md_path}")
    print(f"  配图        : {len(res.media)} 张")


def main():
    p = argparse.ArgumentParser(description="AI-Articles-Tools：文章采集与二次创作")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="config.toml 路径")
    common.add_argument("--mock", action="store_true", help="离线 mock 模式（无需 API key）")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("collect", parents=[common], help="仅采集")
    pc.add_argument("--type", required=True, choices=["text", "link", "video"])
    pc.add_argument("--input", required=True, help="URL / 文件路径 / 原始文案")
    pc.add_argument("--title", help="自定义标题")
    pc.set_defaults(func=cmd_collect)

    pk = sub.add_parser("pipeline", parents=[common], help="采集 + 二创")
    pk.add_argument("--type", required=True, choices=["text", "link", "video"])
    pk.add_argument("--input", required=True, help="URL / 文件路径 / 原始文案")
    pk.add_argument("--title", help="自定义标题")
    pk.set_defaults(func=cmd_pipeline)

    pk2 = sub.add_parser("create", parents=[common], help="对已有采集源做二创")
    pk2.add_argument("--source", required=True, help="source_id")
    pk2.set_defaults(func=cmd_create)

    pl = sub.add_parser("list", parents=[common], help="列出采集源与二创产物")
    pl.set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
