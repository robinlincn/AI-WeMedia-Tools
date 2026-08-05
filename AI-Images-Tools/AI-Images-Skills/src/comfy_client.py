"""ComfyUI HTTP API 客户端（仅依赖 Python 标准库）。

提供能力：
  - 连通性检测（ping / check_connectivity）
  - 提交工作流到 /prompt
  - 轮询 /history 跟踪进度，或按 prompt_id 直查
  - 从 /view 下载产物（图片 / 视频）到本地输出目录
  - 错误重试 + 退避、超时处理、结构化日志

设计目标：工作流无关。任何 ComfyUI API 格式工作流 JSON 均可提交；
产物按 history 中 outputs 的节点输出结构下载，兼容 images / gifs（视频）两种形态。
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

logger = logging.getLogger("comfy")

# 视频类产物在 history outputs 中的键名（ComfyUI 不同节点命名略有差异）
_VIDEO_KEYS = ("gifs", "videos")
_IMAGE_KEYS = ("images",)


class ComfyError(Exception):
    """ComfyUI 客户端可预期错误（重试耗尽 / 业务错误）。"""


def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> None:
    """配置控制台 + 可选文件日志。"""
    handlers: list[logging.Handler] = []
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    handlers.append(sh)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        handlers.append(fh)
    root = logging.getLogger("comfy")
    root.setLevel(level)
    # 避免重复添加 handler
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)


class ComfyClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 300,
        connect_timeout: float = 6,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        poll_interval: float = 2.0,
        max_wait: float = 900,
    ) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.poll_interval = poll_interval
        self.max_wait = max_wait

    # ------------------------------------------------------------------ #
    # 底层请求：统一重试 + 超时
    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, data=None, *, is_json: bool = True, raw: bool = False):
        url = f"{self.base}{path}"
        body = None
        headers = {"User-Agent": "ai-images-skills"}
        if data is not None:
            if is_json:
                body = json.dumps(data).encode("utf-8")
                headers["Content-Type"] = "application/json"
            else:
                body = data
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    if raw:
                        return r.read()
                    payload = r.read().decode("utf-8", "replace")
                    return json.loads(payload) if payload else {}
            except urllib.error.HTTPError as e:
                # 4xx 属客户端错误，不重试
                if 400 <= e.code < 500:
                    raise ComfyError(f"HTTP {e.code} {e.reason} @ {path}")
                last_err = e
                logger.warning("[重试 %d/%d] HTTP %d @ %s: %s",
                               attempt, self.max_retries, e.code, path, e.reason)
            except Exception as e:  # 网络错误等
                last_err = e
                logger.warning("[重试 %d/%d] %s @ %s: %s",
                               attempt, self.max_retries, type(e).__name__, path, e)
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff * attempt)
        raise ComfyError(f"请求失败(已重试{self.max_retries}次) {method} {path}: {last_err}")

    # ------------------------------------------------------------------ #
    # 连通性检测
    # ------------------------------------------------------------------ #
    def ping(self) -> tuple[bool, dict]:
        """快速探针：用短超时检测服务是否在线。返回 (ok, info)。"""
        saved = self.timeout
        self.timeout = self.connect_timeout
        try:
            info = self._request("GET", "/system_stats")
            return True, info or {}
        except ComfyError as e:
            return False, {"error": str(e)}
        except Exception as e:  # 即便非 ComfyError 也兜底
            return False, {"error": f"{type(e).__name__}: {e}"}
        finally:
            self.timeout = saved

    def check_connectivity(self) -> tuple[bool, dict]:
        """完整连通性检测（用正式超时）。返回 (ok, info)。"""
        try:
            info = self._request("GET", "/system_stats")
            return True, info or {}
        except ComfyError as e:
            return False, {"error": str(e)}
        except Exception as e:
            return False, {"error": f"{type(e).__name__}: {e}"}

    # ------------------------------------------------------------------ #
    # 提交 / 进度跟踪 / 下载
    # ------------------------------------------------------------------ #
    def queue_prompt(self, workflow: dict, client_id: str | None = None) -> str:
        """提交工作流，返回 prompt_id。"""
        cid = client_id or uuid.uuid4().hex
        payload = {"prompt": workflow, "client_id": cid}
        resp = self._request("POST", "/prompt", payload)
        pid = resp.get("prompt_id")
        if not pid:
            raise ComfyError(f"/prompt 未返回 prompt_id，响应: {resp}")
        logger.info("已提交任务 prompt_id=%s", pid)
        return pid

    def _fetch_history(self, prompt_id: str) -> dict | None:
        """优先按 prompt_id 直查 /history/<id>，失败回退全量 /history。返回该任务的 history 条目或 None。"""
        try:
            entry = self._request("GET", f"/history/{prompt_id}")
            # 直查返回 {prompt_id: {...}} 或 {}
            return entry.get(prompt_id) if isinstance(entry, dict) else None
        except ComfyError:
            full = self._request("GET", "/history")
            return full.get(prompt_id) if isinstance(full, dict) else None

    def wait_for_completion(self, prompt_id: str) -> dict:
        """轮询 /history 直到任务完成或超时。返回 history 条目（含 outputs / status）。"""
        deadline = time.time() + self.max_wait
        last_log = 0.0
        logger.info("开始跟踪进度 prompt_id=%s（最长等待 %.0f 秒）", prompt_id, self.max_wait)
        while time.time() < deadline:
            entry = self._fetch_history(prompt_id)
            if entry is not None:
                status = entry.get("status", {})
                if status.get("status_str") == "error" or status.get("completed", False) is False and status.get("messages"):
                    # 执行异常：提取异常信息
                    msgs = status.get("messages", [])
                    err_txt = ""
                    for m in msgs:
                        if isinstance(m, list) and m and m[0] == "execution_error":
                            err_txt = json.dumps(m[1], ensure_ascii=False)
                    if err_txt:
                        raise ComfyError(f"ComfyUI 执行错误: {err_txt}")
                if "outputs" in entry:
                    logger.info("任务完成 prompt_id=%s", prompt_id)
                    return entry
            now = time.time()
            if now - last_log >= 10:
                logger.info("  等待中…（已等待 %.0f 秒）", now - (deadline - self.max_wait))
                last_log = now
            time.sleep(self.poll_interval)
        raise ComfyError(f"任务超时（>{self.max_wait}秒）未完成 prompt_id={prompt_id}")

    def download_outputs(self, prompt_id: str, outputs: dict, output_dir: str | Path) -> list[Path]:
        """下载 history 条目中的全部产物到 output_dir/<prompt_id>/。返回落盘文件路径列表。"""
        out_root = Path(output_dir) / prompt_id
        out_root.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for node_id, node_out in outputs.items():
            if not isinstance(node_out, dict):
                continue
            # 收集需要下载的条目：images / gifs(视频) / 其他含 filename 的列表
            items = []
            for key in (*_IMAGE_KEYS, *_VIDEO_KEYS):
                items.extend(node_out.get(key, []) or [])
            # 兜底：某些自定义节点直接把列表放在其它键
            for k, v in node_out.items():
                if isinstance(v, list):
                    for it in v:
                        if isinstance(it, dict) and "filename" in it and it not in items:
                            items.append(it)
            for it in items:
                fname = it.get("filename")
                if not fname:
                    continue
                sub = it.get("subfolder", "") or ""
                ftype = it.get("type", "output") or "output"
                params = urllib.parse.urlencode({"filename": fname, "subfolder": sub, "type": ftype})
                try:
                    data = self._request("GET", f"/view?{params}", raw=True)
                except ComfyError as e:
                    logger.error("下载失败 node=%s file=%s: %s", node_id, fname, e)
                    continue
                # 避免同名冲突：前缀节点 id
                dest = out_root / f"{node_id}_{Path(fname).name}"
                if sub:
                    dest = out_root / sub / f"{node_id}_{Path(fname).name}"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                saved.append(dest)
                kind = "视频" if any(k in node_out for k in _VIDEO_KEYS) else "图片"
                logger.info("已下载%s: %s (%.1f KB)", kind, dest, len(data) / 1024)
        return saved

    # ------------------------------------------------------------------ #
    # 便捷组合：提交 → 跟踪 → 下载
    # ------------------------------------------------------------------ #
    def run_workflow(self, workflow: dict, output_dir: str | Path) -> tuple[str, list[Path]]:
        """端到端执行：提交、等待、下载。返回 (prompt_id, 落盘文件列表)。"""
        pid = self.queue_prompt(workflow)
        entry = self.wait_for_completion(pid)
        files = self.download_outputs(pid, entry.get("outputs", {}), output_dir)
        return pid, files
