"""从 ComfyUIWorkFlow/ 源文件派生 LTX 2.3 I2V 参数化模板。

策略：保留原图（已在该服务器验证可用），仅做最小改动 —
  1) 关闭「LLM 提示词增强」开关(320:328=false) → 使用字面提示词 320:319；
  2) 设定合理默认值（提示词/尺寸/时长/帧率/种子），运行时可用 --set 覆盖；
  3) 输出 workflows/video_ltx2_3_i2v.json + 同名 .params.json。

注：LTX 2.3 为 22B 音视频联合模型，默认 duration=3 / 1024x576 用于轻量验证；
    质量档可上调（详见 SKILL.md）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # AI-Images-Tools/
SRC = ROOT / "ComfyUIWorkFlow" / "video_ltx2_3_i2v（图生视频）.json"
WF_DIR = ROOT / "AI-Images-Skills" / "workflows"

with open(SRC, "r", encoding="utf-8") as f:
    wf = json.load(f)

# 1) 关闭 LLM 提示词增强（switch=false → 使用字面提示词 320:319）
assert "320:328" in wf, "源文件结构变化：缺少 320:328"
wf["320:328"]["inputs"]["value"] = False

# 2) 设定默认值（可被 --set 覆盖）
DEFAULT_PROMPT = ("A young woman in a linen dress walks through a sunlit garden, "
                  "soft breeze moves her hair, cinematic handheld shot, graceful motion.")
wf["320:319"]["inputs"]["value"] = DEFAULT_PROMPT
wf["320:276"]["inputs"]["noise_seed"] = 42      # 主采样器使用
wf["320:277"]["inputs"]["noise_seed"] = 42      # 同步另一分支，保持可复现
wf["320:301"]["inputs"]["value"] = 3            # Duration(秒) → 帧数 = 3*25+1 = 76
wf["320:300"]["inputs"]["value"] = 25           # Frame Rate
wf["320:312"]["inputs"]["value"] = 1024         # Width
wf["320:299"]["inputs"]["value"] = 576          # Height
# 起始帧占位（运行时 --set image=本地路径 会触发上传并覆盖）
wf["269"]["inputs"]["image"] = "START_IMAGE.png"

out_wf = WF_DIR / "video_ltx2_3_i2v.json"
with open(out_wf, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
print("已写出模板:", out_wf)

params = {
    "positive_prompt": {"node": "320:319", "input": "value"},
    "seed": {"node": "320:276", "input": "noise_seed"},
    "image": {"node": "269", "input": "image"},
    "duration": {"node": "320:301", "input": "value"},
    "fps": {"node": "320:300", "input": "value"},
    "width": {"node": "320:312", "input": "value"},
    "height": {"node": "320:299", "input": "value"},
}
out_pm = WF_DIR / "video_ltx2_3_i2v.params.json"
with open(out_pm, "w", encoding="utf-8") as f:
    json.dump(params, f, ensure_ascii=False, indent=2)
print("已写出参数映射:", out_pm)
