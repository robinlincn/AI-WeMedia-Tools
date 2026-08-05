"""AI-Images-Skills 命令行入口。

加载工作流 JSON + 参数映射，按 CLI / 配置参数化（提示词 / 尺寸 / 种子 / 帧数…），
提交到 ComfyUI、轮询进度、下载产物到输出目录，并输出结构化摘要。

用法示例：
  # 跑图片工作流（需连到局域网 ComfyUI）
  python -m src.run --workflow image_basic \
      --set positive_prompt="a cat" --set seed=123 --set width=1024 --set height=1024

  # 跑视频工作流
  python -m src.run --workflow video_basic --set positive_prompt="waves on beach" --set frames=25

  # 仅做连通性检测
  python -m src.run --ping
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tomllib
from pathlib import Path

# 让 `python -m src.run` 能找到同包模块
SKILL_ROOT = Path(__file__).resolve().parents[1]   # AI-Images-Skills/
if str(SKILL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT / "src"))

from comfy_client import ComfyClient, ComfyError, setup_logging  # noqa: E402

logger = logging.getLogger("comfy")


# ---------------------------------------------------------------------- #
# 配置加载
# ---------------------------------------------------------------------- #
def load_config(config_path: str | None = None) -> dict:
    """加载配置：config.toml（优先） → config.toml.example → 内置默认。"""
    candidates: list[Path] = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.append(SKILL_ROOT / "config.toml")
    candidates.append(SKILL_ROOT / "config.toml.example")
    for p in candidates:
        if p.exists():
            try:
                with open(p, "rb") as f:
                    cfg = tomllib.load(f)
                logger.info("已加载配置: %s", p)
                return cfg
            except Exception as e:
                logger.warning("配置解析失败 %s: %s", p, e)
    logger.warning("未找到任何配置文件，使用内置默认值")
    return {}


def _resolve(path_str: str, base: Path) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (base / path_str).resolve()


def _coerce(value: str):
    """把 CLI 字符串值尽量转为 int / float / str。"""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


# ---------------------------------------------------------------------- #
# 工作流加载与参数化
# ---------------------------------------------------------------------- #
def load_workflow(name_or_path: str, workflows_dir: Path) -> tuple[dict, Path]:
    p = Path(name_or_path)
    if not p.exists():
        p = workflows_dir / f"{name_or_path}.json"
    if not p.exists():
        raise FileNotFoundError(f"工作流不存在: {name_or_path}（查找过 {p}）")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f), p


def load_param_map(name_or_path: str, workflows_dir: Path) -> dict:
    """加载逻辑参数→节点映射。默认同名的 <name>.params.json。"""
    p = Path(name_or_path)
    if p.exists() and p.suffix == ".json":
        # 若直接给了 params 文件路径
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    # 否则按工作流名推导
    stem = Path(name_or_path).stem if Path(name_or_path).exists() else name_or_path
    pm = workflows_dir / f"{stem}.params.json"
    if pm.exists():
        with open(pm, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def apply_params(workflow: dict, param_map: dict, overrides: list[str]) -> dict:
    """把 --set key=value 应用到 workflow。返回更新后的 workflow（深拷贝）。"""
    wf = json.loads(json.dumps(workflow))  # 深拷贝，避免污染模板
    for kv in overrides:
        if "=" not in kv:
            logger.warning("忽略无效 --set（缺少 '='）: %s", kv)
            continue
        key, raw = kv.split("=", 1)
        key = key.strip()
        if key not in param_map:
            logger.warning("参数 '%s' 未在 param map 中定义，已跳过（可用参数: %s）",
                           key, ", ".join(param_map) or "（空）")
            continue
        spec = param_map[key]
        node = str(spec["node"])
        inp = spec["input"]
        if node not in wf:
            logger.warning("param map 指向的节点 %s 不在工作流中，跳过 '%s'", node, key)
            continue
        val = _coerce(raw)
        wf[node]["inputs"][inp] = val
        logger.info("参数化 %s -> 节点%s.%s = %r", key, node, inp, val)
    return wf


# ---------------------------------------------------------------------- #
# 组合执行
# ---------------------------------------------------------------------- #
def build_and_run(args, cfg: dict) -> dict:
    comfy_cfg = cfg.get("comfyui", {})
    paths_cfg = cfg.get("paths", {})
    defs = cfg.get("defaults", {})

    workflows_dir = _resolve(paths_cfg.get("workflows_dir", "workflows"), SKILL_ROOT)
    output_dir = _resolve(paths_cfg.get("output_dir", "../OutImages"), SKILL_ROOT)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = ComfyClient(
        base_url=args.base_url or comfy_cfg.get("base_url", "http://192.168.31.243:8188"),
        timeout=float(comfy_cfg.get("timeout", 300)),
        connect_timeout=float(comfy_cfg.get("connect_timeout", 6)),
        max_retries=int(comfy_cfg.get("max_retries", 3)),
        retry_backoff=float(comfy_cfg.get("retry_backoff", 2.0)),
        poll_interval=float(comfy_cfg.get("poll_interval", 2.0)),
        max_wait=float(comfy_cfg.get("max_wait", 900)),
    )

    # 连通性
    ok, info = client.ping()
    if not ok:
        raise ComfyError(f"无法连接 ComfyUI（{client.base}）：{info.get('error')}")

    workflow_name = args.workflow or defs.get("workflow", "image_basic")
    workflow, wf_path = load_workflow(workflow_name, workflows_dir)
    param_map = load_param_map(workflow_name, workflows_dir)

    # 合并默认参数 + CLI 覆盖
    overrides = list(args.set or [])
    for k, v in defs.items():
        if k in ("workflow",):
            continue
        # 仅追加未在 --set 中出现过的默认参数
        if not any(o.split("=", 1)[0].strip() == k for o in overrides):
            overrides.append(f"{k}={v}")

    wf = apply_params(workflow, param_map, overrides)

    t0 = __import__("time").time()
    pid, files = client.run_workflow(wf, output_dir)
    elapsed = __import__("time").time() - t0

    return {
        "prompt_id": pid,
        "workflow": workflow_name,
        "workflow_path": str(wf_path),
        "output_dir": str(output_dir / pid),
        "files": [str(f) for f in files],
        "elapsed": elapsed,
    }


def print_summary(result: dict) -> None:
    print("\n================ 执行摘要 ================")
    print(f"工作流      : {result['workflow']}")
    print(f"prompt_id   : {result['prompt_id']}")
    print(f"产物目录    : {result['output_dir']}")
    print(f"耗时        : {result['elapsed']:.1f} 秒")
    print(f"落盘文件({len(result['files'])}):")
    for f in result["files"]:
        print(f"   - {f}")
    print("==========================================\n")


# ---------------------------------------------------------------------- #
# CLI
# ---------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description="AI-Images-Skills：调用局域网 ComfyUI 生成图片/视频")
    p.add_argument("--config", help="config.toml 路径")
    p.add_argument("--base-url", help="ComfyUI 地址（覆盖配置）")
    p.add_argument("--workflow", help="工作流名或路径（默认 image_basic）")
    p.add_argument("--set", action="append", metavar="key=value",
                   help="参数覆盖，可重复，如 --set positive_prompt='a cat' --set seed=123")
    p.add_argument("--ping", action="store_true", help="仅做连通性检测后退出")
    p.add_argument("--verbose", action="store_true", help="调试日志")
    args = p.parse_args()

    cfg = load_config(args.config)
    paths_cfg = cfg.get("paths", {})
    log_file = paths_cfg.get("log_file")
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO,
                  log_file=str(_resolve(log_file, SKILL_ROOT)) if log_file else None)

    if args.ping:
        client = ComfyClient(base_url=args.base_url or cfg.get("comfyui", {}).get("base_url", "http://192.168.31.243:8188"),
                             connect_timeout=float(cfg.get("comfyui", {}).get("connect_timeout", 6)))
        ok, info = client.ping()
        print(("✅ 连通" if ok else "❌ 不可达") + f" -> {client.base}")
        if ok:
            print(json.dumps(info, ensure_ascii=False)[:500])
        sys.exit(0 if ok else 1)

    try:
        result = build_and_run(args, cfg)
    except ComfyError as e:
        logger.error("执行失败: %s", e)
        sys.exit(2)
    print_summary(result)


if __name__ == "__main__":
    main()
