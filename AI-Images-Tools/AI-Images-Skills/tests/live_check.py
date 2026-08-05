import sys, logging
from pathlib import Path
SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "src"))
from comfy_client import ComfyClient, setup_logging

setup_logging(logging.INFO)
URL = "http://192.168.31.243:8188"

c = ComfyClient(URL, timeout=15)
ok, info = c.check_connectivity()
print("连通性:", "OK" if ok else "FAIL", "| device:", (info.get("devices") or [{}])[0].get("name") if ok else info)
# 再看队列接口（证明 /queue 也能被我的客户端正常访问）
try:
    q = c._request("GET", "/queue")
    print("/queue 可访问:", q)
except Exception as e:
    print("/queue 访问异常:", e)
