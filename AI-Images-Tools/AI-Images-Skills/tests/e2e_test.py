"""AI-Images-Skills 端到端测试。

默认以 --mock 运行：在本地启动 ComfyUI 兼容的 Mock 服务，真实跑通
「加载工作流 → 参数化 → 提交 /prompt → 轮询 /history → 下载 /view 落盘」全链路，
并分别验证图片与视频两类产物成功写入磁盘，输出结构化摘要。

真实环境（连到局域网 ComfyUI 的机器上）用 --real 运行：
    python -m tests.e2e_test --real
将直接指向 config.toml 中的 base_url 执行真实出图/出片。

运行：
    python -m tests.e2e_test            # 离线 mock 验证（默认）
    python -m tests.e2e_test --real     # 指向真实 ComfyUI
    python -m tests.e2e_test --mock --workflows image,video
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]   # AI-Images-Skills/
sys.path.insert(0, str(SKILL_ROOT / "src"))
sys.path.insert(0, str(SKILL_ROOT / "tests"))

from comfy_client import ComfyClient, ComfyError, setup_logging  # noqa: E402
from run import load_workflow, load_param_map, apply_params, load_config  # noqa: E402

import logging  # noqa: E402
setup_logging(logging.INFO)

WORKFLOWS_DIR = SKILL_ROOT / "workflows"
OUTPUT_BASE = SKILL_ROOT.parent / "OutImages"   # AI-Images-Tools/OutImages


def run_one(base_url: str, name: str, overrides: list[str], mock: bool) -> dict:
    """对单个工作流执行完整流程，返回结构化结果。"""
    res = {"workflow": name, "mode": "mock" if mock else "real",
           "status": "fail", "elapsed": 0.0, "files": [], "error": ""}
    try:
        client = ComfyClient(base_url=base_url)
        ok, info = client.ping()
        if not ok:
            res["error"] = f"连通性检测失败: {info.get('error')}"
            return res

        wf, wf_path = load_workflow(name, WORKFLOWS_DIR)
        pmap = load_param_map(name, WORKFLOWS_DIR)
        wf2 = apply_params(wf, pmap, overrides)

        out_dir = OUTPUT_BASE / "e2e_test"
        out_dir.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        pid, files = client.run_workflow(wf2, out_dir)
        res["elapsed"] = time.time() - t0
        res["prompt_id"] = pid
        res["files"] = [str(f) for f in files]
        # 校验确实落盘
        if files and all(Path(f).exists() and Path(f).stat().st_size > 0 for f in files):
            res["status"] = "pass"
        else:
            res["error"] = "产物未落盘或大小为 0"
    except ComfyError as e:
        res["error"] = str(e)
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--real", action="store_true", help="指向真实 ComfyUI（默认 mock）")
    p.add_argument("--mock", action="store_true", help="使用本地 mock 服务（默认开启）")
    p.add_argument("--workflows", default="image,video", help="逗号分隔：image/video")
    args = p.parse_args()

    use_mock = not args.real
    names = [n.strip() for n in args.workflows.split(",") if n.strip()]

    # 映射到工作流文件名
    name_map = {"image": "image_basic", "video": "video_basic"}
    workflows = [name_map.get(n, n) for n in names]

    base_url = "http://192.168.31.243:8188"
    srv = None
    if use_mock:
        from mock_server import start_mock_server
        srv = start_mock_server("127.0.0.1", 8199)
        base_url = "http://127.0.0.1:8199"
        print(">>> 已启动本地 Mock ComfyUI @", base_url)

    overrides = {
        "image_basic": ["positive_prompt=a calm lake at dawn", "seed=42", "width=768", "height=768"],
        "video_basic": ["positive_prompt=gentle waves on a sunny beach", "seed=7", "frames=17"],
    }

    results = []
    for wf in workflows:
        ov = overrides.get(wf, [])
        r = run_one(base_url, wf, ov, mock=use_mock)
        results.append(r)

    if srv:
        srv.shutdown()

    # ---------------- 输出摘要 ----------------
    print("\n================ E2E 测试结果摘要 ================")
    passed = 0
    for r in results:
        mark = "✅ 成功" if r["status"] == "pass" else "❌ 失败"
        if r["status"] == "pass":
            passed += 1
        print(f"[{r['workflow']}] {mark} | 模式={r['mode']} | 耗时={r['elapsed']:.2f}s | 产物={len(r['files'])}个")
        for f in r["files"]:
            print(f"     - {f}")
        if r["error"]:
            print(f"     原因: {r['error']}")
    print("--------------------------------------------------")
    print(f"总计: {passed}/{len(results)} 通过")
    if use_mock:
        print("说明: 本次为 mock 模式，验证的是客户端『提交→轮询→下载落盘』代码链路；")
        print("      真实出图/出片需在连到局域网 ComfyUI 的机器上执行: python -m tests.e2e_test --real")
    else:
        if passed < len(results):
            print("说明: 真实模式存在失败项，请检查目标机是否启动、是否允许局域网访问、工作流/模型是否匹配。")
    print("==================================================\n")

    # JSON 便于程序消费
    import json as _json
    print(_json.dumps({"passed": passed, "total": len(results), "results": results},
                      ensure_ascii=False, indent=2))

    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
