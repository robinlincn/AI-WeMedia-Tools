"""临时：用原生 Wan2.2 I2V 节点真机试跑一版图，观察服务器报错以校准接线。"""
import sys, time, logging
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "src"))
from comfy_client import ComfyClient, ComfyError, setup_logging

setup_logging(logging.INFO)

PROMPT = (
    "A serene lake at dawn, gentle mist rising, soft golden light, "
    "cinematic slow camera, highly detailed, 4k."
)

wf = {
    "1": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {
        "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "type": "wan", "device": "default"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "Wan2_1_VAE_bf16.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["2", 0]}},
    "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
    "6": {"class_type": "WanImageToVideo", "inputs": {
        "positive": ["4", 0], "negative": ["5", 0], "vae": ["3", 0],
        "width": 832, "height": 480, "length": 49, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["6", 0], "negative": ["6", 1],
        "latent_image": ["6", 2], "seed": 12345, "steps": 20, "cfg": 6.0,
        "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveWEBM", "inputs": {
        "images": ["8", 0], "filename_prefix": "WanI2V", "fps": 16.0,
        "crf": 32.0, "codec": "vp9"}},
}

client = ComfyClient(base_url="http://192.168.31.243:8188", timeout=600, max_wait=900,
                     poll_interval=3.0)
ok, info = client.ping()
print("连通:", ok, info.get("devices", [{}])[0].get("name") if ok else info)
if not ok:
    print("不可达，退出"); sys.exit(1)

t0 = time.time()
try:
    pid, files = client.run_workflow(wf, SKILL_ROOT.parent / "OutImages")
    print(f"\n✅ 成功 prompt_id={pid} 耗时={time.time()-t0:.1f}s")
    for f in files:
        print("   ->", f, f"({f.stat().st_size/1024:.1f} KB)" if f.exists() else "")
except ComfyError as e:
    print(f"\n❌ 失败({time.time()-t0:.1f}s): {e}")
