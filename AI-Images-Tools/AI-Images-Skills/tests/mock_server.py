"""本地 ComfyUI 兼容的 Mock 服务（仅供端到端测试离线验证用）。

实现最小可用的 /system_stats、/prompt、/history/<id>、/history、/view，
让 comfy_client 的真实代码路径（提交 → 轮询 → 下载）在本机即可得到产物落盘，
无需连到真实局域网 ComfyUI。

用法（在 e2e_test.py 中以线程方式启动，无需手动运行）：
    from mock_server import start_mock_server
    srv = start_mock_server("127.0.0.1", 8199)
    ... 客户端 base_url = "http://127.0.0.1:8199" ...
    srv.shutdown()
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 1x1 合法 PNG（可直接打开）
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f3f0000000049454e44ae426082"
)
_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 2048


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _send(self, code, obj=None, raw=None, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if raw is not None:
            self.wfile.write(raw)
        elif obj is not None:
            self.wfile.write(json.dumps(obj).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/system_stats", "/"):
            self._send(200, {"status": "ok",
                             "devices": [{"name": "mock-gpu", "type": "cuda",
                                          "vram_total": 24_000_000_000,
                                          "vram_free": 20_000_000_000}]})
            return
        if path == "/history":
            self._send(200, self.server.hist)
            return
        if path.startswith("/history/"):
            pid = path.split("/history/", 1)[1]
            self._send(200, {pid: self.server.hist.get(pid, {})})
            return
        if path.startswith("/view"):
            q = urllib.parse.parse_qs(parsed.query)
            fname = q.get("filename", ["mock.bin"])[0]
            data = _MP4 if (fname.endswith(".mp4") or fname.endswith(".webm")) else _PNG
            self._send(200, raw=data, ctype="application/octet-stream")
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/prompt":
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            wf = body.get("prompt", {})
            pid = uuid.uuid4().hex
            image_nodes = [nid for nid, n in wf.items() if n.get("class_type") == "SaveImage"]
            video_nodes = [nid for nid, n in wf.items()
                           if ("VideoCombine" in n.get("class_type", "")
                               or "VHS" in n.get("class_type", ""))]
            outputs = {}
            for nid in image_nodes:
                outputs[nid] = {"images": [{"filename": "ComfyUI_mock_image.png",
                                            "subfolder": "", "type": "output"}]}
            for nid in video_nodes:
                outputs[nid] = {"gifs": [{"filename": "ComfyUI_mock_video.mp4",
                                          "subfolder": "", "type": "output"}]}
            if not outputs:  # 兜底
                outputs["out1"] = {"images": [{"filename": "ComfyUI_mock.png",
                                               "subfolder": "", "type": "output"}]}
            entry = {"outputs": outputs, "status": {"status_str": "success", "completed": True}}
            self.server.pending[pid] = entry

            def _complete():
                time.sleep(0.3)
                self.server.hist[pid] = entry

            threading.Thread(target=_complete, daemon=True).start()
            self._send(200, {"prompt_id": pid})
            return
        self._send(404, {"error": "not found"})


def start_mock_server(host: str = "127.0.0.1", port: int = 8199) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), _Handler)
    server.hist: dict = {}
    server.pending: dict = {}
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
