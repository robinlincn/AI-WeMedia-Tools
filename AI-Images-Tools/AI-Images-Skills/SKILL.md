---
name: ai-images-tools
description: 通过 HTTP API 调用局域网内另一台机器上的 ComfyUI（默认 http://192.168.31.243:8188）执行工作流，生成图片与视频。支持工作流参数化（提示词/尺寸/种子/帧数）、提交到 /prompt、轮询 /history 跟踪进度、从 /view 下载产物，具备连通性检测、重试、超时与清晰日志。（支持文生图 / 文生视频 / 图生视频 I2V；已适配 Boogu、Krea2、Wan2.2、MiniMax-H3、LTX-2.3 等模型；含数字人说话视频模板）当用户说"用 ComfyUI 出图/出视频""调用局域网 ComfyUI""跑工作流生成图片/视频""提交 ComfyUI 任务并下载产物""图生视频/用图片生成视频""做数字人/对口型视频/让图片里的人说话"时触发。
agent_created: true
---

# AI-Images-Skills（调用局域网 ComfyUI 生成图片/视频）

本技能包把"在局域网另一台机器上运行的 ComfyUI"封装成可复用调用能力：
加载并参数化工作流 JSON → 提交到 `/prompt` → 轮询 `/history` 跟踪进度 → 从 `/view` 下载产物到本地。
**仅依赖 Python 标准库（urllib / tomllib / json / logging），无需 pip 安装任何第三方包。**

## 一、前置条件

在能真正出图/出片之前，必须满足：

1. **网络可达**：运行本技能包的机器与目标 ComfyUI 机器（默认 `192.168.31.243:8188`）处于同一局域网，且能 TCP 连通 8188 端口。
   - 目标机需**允许局域网访问**：ComfyUI 启动时建议用 `--listen 0.0.0.0`（而非仅 `127.0.0.1`），并确认防火墙放行 8188。
   - 可用 `python -m src.run --ping` 自检连通性。
2. **必要模型与自定义节点（本机 192.168.31.243:8188 已验证）**：
   - **Boogu 文生图**（`image_boogu_image_0_1_turbo_t2i`）：需要 `UNETLoader` 的 `boogu_image_turbo_fp8_scaled.safetensors`、`CLIPLoader(type='boogu', clip_name='qwen3vl_8b_fp8_scaled.safetensors')`、VAE `ae.safetensors`；负向条件用 `ConditioningZeroOut` 置零；分辨率由 `ResolutionSelector`(1:1 / 1MP) 给出；采样器 `KSampler(steps=4, cfg=1, sampler='lcm')`。均为 ComfyUI 原生节点。
   - **Krea2 文生图**（`image_krea2_turbo_t2i`）：需要 `UNETLoader` 的 `krea2_turbo_fp8_scaled.safetensors`、`CLIPLoader(type='krea2', clip_name='qwen3vl_4b_fp8_scaled.safetensors')`、VAE `qwen_image_vae.safetensors`；`KSampler(steps=8, cfg=1, sampler='euler')` 出图。原生节点。
   - **Wan2.2 视频**：需要 `UNETLoader` 的 `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`（14B，fp8）、`CLIPLoader(type='wan', clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors')`、VAE `Wan2_1_VAE_bf16.safetensors`。
     - 文生视频 `video_wan22_i2v`：`WanImageToVideo` 生成 latent → 标准 `KSampler` → `VAEDecode` → `SaveWEBM` 落盘（webm）。
     - **图生视频（I2V）`video_wan22_i2v_image`**：在文生视频基础上加 `LoadImage` 节点并把输出连到 `WanImageToVideo.start_image`（可选 IMAGE 输入）即起帧成片；`--set image=<本地图片路径>` 会自动上传到 ComfyUI `input/` 目录。
   - **MiniMax-H3 图生视频**（`video_minimax_h3_i2v`）：需要 `UNETLoader` 的 `minimax_h3_fl2va_pruned_int8_convrot.safetensors`（int8，较轻）、`CLIPLoader(type='minimax', clip_name='qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors')`、视频 VAE `minimax_h3_video_vae_fp16.safetensors` + 音频 VAE `minimax_h3_audio_vae_fp32.safetensors`；`MiniMaxH3ImageToVideo(first_frame=LoadImage)` 起帧 → `SamplerCustomAdvanced` → `VAEDecode` + `VAEDecodeAudio` → `CreateVideo` → `SaveVideo` 落盘（mp4，含音轨）。
   - **LTX-2.3 图生视频**（`video_ltx2_3_i2v`）：需要 `CheckpointLoaderSimple` 的 `ltx-2.3-22b-dev-fp8.safetensors`（**22B，fp8，约 11GB，需 ≥16GB 显存**）、`LTXAVTextEncoderLoader` 的 `gemma_3_12B_it_fp4_mixed.safetensors`、`LTXVAudioVAELoader` 的同源 ckpt；图经 `LTXVPreprocess` → `LTXVImgToVideoInplace` 转视频 latent → `SamplerCustomAdvanced` → `VAEDecodeTiled` → `CreateVideo` → `SaveVideo` 落盘（webm，含音轨）。**22B 模型显存占用大，建议在更高显存机器上跑；在低显存卡上可能 OOM。**
   - 工作流里引用的模型文件必须已存在于目标机 `ComfyUI/models/` 下；若使用其它模型，请按实际文件名替换模板中的 `unet_name` / `clip_name` / `vae_name` / `ckpt_name`。
3. **工作流模板匹配**：`workflows/*.json` 必须是 **API 格式**（菜单 "Export (API Format)" 导出），且其中的节点 / 输入键要与对应的 `*.params.json` 映射一致。本技能包已内置两个**经真机验证**的模板（见下），可直接用或在此基础上替换模型。

## 二、目录结构

```
AI-Images-Tools/AI-Images-Skills/
├── SKILL.md                      # 本说明
├── README.md                     # 快速上手
├── config.toml.example          # 配置示例（复制为 config.toml 后生效）
├── src/
│   ├── comfy_client.py           # 核心客户端：连通性/提交/轮询/下载/重试/超时/日志
│   └── run.py                    # CLI 入口：加载+参数化+执行+摘要
├── workflows/
│   ├── image_boogu_image_0_1_turbo_t2i.json   # ✅ Boogu 文生图（真机验证）
│   ├── image_boogu_image_0_1_turbo_t2i.params.json
│   ├── image_krea2_turbo_t2i.json             # ✅ Krea2 文生图（真机验证）
│   ├── image_krea2_turbo_t2i.params.json
│   ├── video_wan22_i2v.json                    # ✅ Wan2.2 文生视频（真机验证，webm）
│   ├── video_wan22_i2v.params.json
│   ├── video_wan22_i2v_image.json             # ✅ Wan2.2 图生视频 I2V（真机验证，webm，start_image 起帧）
│   ├── video_wan22_i2v_image.params.json
│   ├── video_minimax_h3_i2v.json              # ✅ MiniMax-H3 图生视频 I2V（真机验证，mp4 含音轨）
│   ├── video_minimax_h3_i2v.params.json
│   ├── video_ltx2_3_i2v.json                  # ✅ LTX-2.3 图生视频 I2V（22B，真机验证）
│   ├── video_ltx2_3_i2v.params.json
│   ├── digital_human_talking.json            # ✅ 数字人说话视频（MiniMax-H3 I2V 竖屏，真机验证）
│   └── digital_human_talking.params.json
└── tests/
    ├── mock_server.py            # 本地 ComfyUI 兼容 Mock 服务（离线验证用）
    ├── e2e_test.py               # 端到端测试（mock / real 两种模式）
    ├── gen_ltx_template.py       # 从 ComfyUIWorkFlow/ 源派生 LTX 模板的脚本
    └── attempt_video.py          # 临时试跑脚本（复用 ComfyClient 真机调试）
```

产物默认落到 `AI-Images-Tools/OutImages/<prompt_id>/`（图片 `*.png`、视频 `*.webm`），由 `config.toml` 的 `paths.output_dir` 控制。

## 三、快速开始

```bash
cd AI-Images-Tools/AI-Images-Skills

# 1) 准备配置：复制示例并按需修改（主要是 base_url）
cp config.toml.example config.toml

# 2) 连通性自检（无需任何工作流）
python -m src.run --ping
#   ✅ 连通 -> http://192.168.31.243:8188
#   ❌ 不可达 -> 检查目标机是否启动 / 是否 --listen 0.0.0.0 / 防火墙

# 3) 跑图片工作流
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i --set positive_prompt="一只戴草帽的橘猫，阳光，高清" --set seed=42   # Boogu 文生图
python -m src.run --workflow image_krea2_turbo_t2i   --set positive_prompt="a cute orange cat wearing sunglasses" --set seed=7       # Krea2 文生图

# 4) 跑视频工作流（图生视频需 --set image=<本地图片路径>，会自动上传到 ComfyUI）
python -m src.run --workflow video_wan22_i2v          --set positive_prompt="A serene lake at dawn" --set length=49 --set fps=16     # Wan2.2 文生视频
python -m src.run --workflow video_wan22_i2v_image    --set positive_prompt="..." --set image="d:/start.png" --set seed=123           # Wan2.2 图生视频 I2V
python -m src.run --workflow video_minimax_h3_i2v     --set "positive_prompt=女孩在樱花树下微笑" --set image="d:/start.png"            # MiniMax-H3 图生视频(含音轨)
python -m src.run --workflow video_ltx2_3_i2v         --set "positive_prompt=A young woman walks in a garden" --set image="d:/start.png" --set duration=3  # LTX-2.3 图生视频

# 5) 端到端测试（离线 mock 验证全链路 / 真实模式出图）
python -m tests.e2e_test            # 离线 mock：验证 提交→轮询→下载落盘
python -m tests.e2e_test --real     # 指向真实 ComfyUI 出图/出片
```

> **图生视频（I2V）的 `image` 参数**：指向**本地图片路径**；`run.py` 检测到目标节点是 `LoadImage` 时，会自动 `POST /upload/image` 上传到 ComfyUI 的 `input/` 目录，并把 `LoadImage.image` 替换为服务器文件名，无需手动上传。

## 三-B、调用示例（均在 192.168.31.243:8188 真机验证通过）

### 示例 1：Boogu 文生图（`image_boogu_image_0_1_turbo_t2i`）

该工作流是 ComfyUI 上保存的工作流（Boogu 专属 DiT）：`CLIPLoader(type='boogu')` + 标准 `CLIPTextEncode` 编码提示词，负向条件用 `ConditioningZeroOut` 置零，`ResolutionSelector` 给定 1:1 / 1MP 分辨率，`KSampler(steps=4, cfg=1, sampler='lcm')` 出图。

```bash
# 使用工作流内置提示词与种子（直接出图）
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i

# 换提示词 + 固定种子
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i \
    --set positive_prompt="一只戴草帽的橘猫，阳光，高清" \
    --set seed=42

# 改分辨率比例（由 ResolutionSelector 控制宽高，如 16:9）
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i \
    --set aspect_ratio="16:9 (Landscape)"
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/33_Boogu_00010_.png`（1024×1024，PNG 签名校验通过）。

### 示例 2：Wan2.2 图生视频（`video_wan22_i2v`，输出 webm）

该工作流用原生 Wan2.2 节点：`UNETLoader(wan2.2_i2v_low_noise_14B)` 加载 14B 模型 → `CLIPLoader(type='wan')` 编码提示词 → `WanImageToVideo` 生成视频 latent → 标准 `KSampler` 采样 → `VAEDecode` → `SaveWEBM` 落盘。

```bash
# 最简：用模板内置提示词出一段 49 帧 / 16fps 视频
python -m src.run --workflow video_wan22_i2v

# 自定义提示词 + 帧数 + 帧率
python -m src.run --workflow video_wan22_i2v \
    --set positive_prompt="A serene lake at dawn, gentle mist rising, cinematic" \
    --set length=49 --set fps=16 --set seed=7

# 调低分辨率 / 步数以加速（14B 在 5070 Ti 上较慢，约 7 分钟/49 帧）
python -m src.run --workflow video_wan22_i2v \
    --set width=512 --set height=288 --set length=17 --set steps=15
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/9_WanI2V_00001_.webm`（vp9，832×480，约 3 秒）。

> **提速提示**：`length`（帧数）与 `width/height` 对耗时影响最大；`steps` 可降到 15 仍可用。

### 示例 3：Krea2 文生图（`image_krea2_turbo_t2i`）

Krea2 是写实风格 DiT：`CLIPLoader(type='krea2', clip_name='qwen3vl_4b_fp8_scaled')` 编码提示词，VAE 用 `qwen_image_vae.safetensors`，`KSampler(steps=8, cfg=1, sampler='euler')` 出图，分辨率由 `ResolutionSelector` 控制。

```bash
# 最简：用模板内置提示词出一张 1:1 图
python -m src.run --workflow image_krea2_turbo_t2i

# 自定义提示词 + 16:9
python -m src.run --workflow image_krea2_turbo_t2i \
    --set "positive_prompt=a cinematic portrait of a woman in neon light, 85mm lens" \
    --set aspect_ratio="16:9 (Landscape)" --set seed=2024
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/10_Krea2_turbo_00009_.png`。

### 示例 4：Wan2.2 图生视频 I2V（`video_wan22_i2v_image`）

在文生视频基础上加 `LoadImage` 并把输出连到 `WanImageToVideo.start_image`，即可从一张图片起帧生成视频。`--set image=` 传**本地路径**，会自动上传。

```bash
python -m src.run --workflow video_wan22_i2v_image \
    --set "positive_prompt=a serene lake at dawn, gentle mist, slow camera push-in" \
    --set image="d:/start_frame.png" --set seed=123 --set length=49 --set fps=16
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/10_WanI2V_00002_.webm`（vp9 视频，首帧即所给图片）。

### 示例 5：MiniMax-H3 图生视频（`video_minimax_h3_i2v`）

MiniMax-H3 节点 `MiniMaxH3ImageToVideo(first_frame=LoadImage)` 从首帧生成视频，并**自带音轨**（音频 VAE 合成）。模型为 int8 较轻量。

```bash
python -m src.run --workflow video_minimax_h3_i2v \
    --set "positive_prompt=女孩在樱花树下微笑，微风轻轻拂过她的发丝，电影感镜头" \
    --set image="d:/start_frame.png" --set seed=99 --set length=124 --set fps=24
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/15_MiniMax_H3_00001_.mp4`（含音轨，宽高默认 1344×768）。

### 示例 6：LTX-2.3 图生视频（`video_ltx2_3_i2v`）

LTX-2.3 为 22B 音视频联合模型，`LTXVImgToVideoInplace` 由图片转视频 latent，输出含音轨。默认 `duration=3`（帧数 = duration×fps+1）、`width=1024`、`height=576`，便于在 16GB 卡上验证；质量档可上调（见下）。

```bash
# 轻量验证（默认 3 秒 / 1024×576）
python -m src.run --workflow video_ltx2_3_i2v \
    --set "positive_prompt=A young woman in a linen dress walks through a sunlit garden" \
    --set image="d:/start_frame.png" --set seed=42 --set duration=3

# 质量档（更长更清晰，显存占用更大）
python -m src.run --workflow video_ltx2_3_i2v \
    --set image="d:/start_frame.png" --set duration=8 --set width=1280 --set height=720
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/15_LTX_2_3_i2v_00001_.webm`（含音轨）。

> **LTX 显存提示**：22B fp8 约 11GB，叠加文本编码器/VAE 后需 ≥16GB 显存；若 ComfyUI 报 OOM，请降低 `width/height/duration` 或改用更高显存机器。

### 示例 7：数字人说话视频（`digital_human_talking`，基于 MiniMax-H3 I2V）

让一张人物图"开口说话"：复用 MiniMax-H3 的 `MiniMaxH3ImageToVideo(first_frame=LoadImage)` 起帧，并**内置音轨**（模型按 prompt 合成语音+氛围音），竖屏 832×1152 适合头像/手机短视频。

```bash
# 商务自我介绍（竖屏，约 3.4 秒）
python -m src.run --workflow digital_human_talking \
    --set image="d:/character.png" \
    --set "positive_prompt=一位戴眼镜的3D卡通商务男士正对镜头自信讲话，面带微笑，时而点头、用手势强调，口型自然开合，仿佛在说：'大家好，我是您的AI助手，很高兴为您服务。' 背景简洁浅灰，电影级画质，超清" \
    --set width=832 --set height=1152 --set length=81 --set fps=24

# 换说法/换图：只改 image 与 positive_prompt 即可，分辨率与帧数可保持或微调
```

产物：`AI-Images-Tools/OutImages/<prompt_id>/15_DigitalHuman_Talking_00001_.mp4`（h264+aac，竖屏 832×1152，~3.75s，含语音音轨）。

> **说明**：这是"语义级口型"——人物会动嘴、有自然语音，但不是逐帧精确对口型（精确 lip-sync 见下"⚠️ 已知坑：云端对口型节点"）。要更长/更高清，调大 `length`/`width`/`height`，但受 16GB 显存上限约束（建议 `length≤141`）。

## 四、参数说明

### CLI 参数（`src/run.py`）
| 参数 | 说明 |
| --- | --- |
| `--config <路径>` | 指定 config.toml（默认按 `config.toml` → `config.toml.example` 顺序加载） |
| `--base-url <url>` | 覆盖配置中的 ComfyUI 地址 |
| `--workflow <名/路径>` | 工作流名（解析为 `workflows/<名>.json`）或 JSON 路径；默认 `image_boogu_image_0_1_turbo_t2i` |
| `--set key=value` | 参数覆盖，**可重复**。值自动按 int/float/str 推断 |
| `--ping` | 仅做连通性检测后退出 |
| `--verbose` | 调试级日志 |

### 逻辑参数（经 `*.params.json` 映射到工作流节点）
`*.params.json` 把"人类可读的参数名"映射到"工作流节点 ID + 输入键"，例如：
```json
{ "positive_prompt": {"node":"2","input":"text"},
  "seed":           {"node":"4","input":"seed"},
  "width":          {"node":"7","input":"width"},
  "height":         {"node":"7","input":"height"} }
```
自带模板支持的逻辑参数：
- **图片 · Boogu** `image_boogu_image_0_1_turbo_t2i`：`positive_prompt`、`seed`、`aspect_ratio`（如 `1:1 (Square)` / `16:9`，由 `ResolutionSelector` 决定宽高）
- **图片 · Krea2** `image_krea2_turbo_t2i`：`positive_prompt`、`seed`、`aspect_ratio`
- **视频 · Wan2.2 文生视频** `video_wan22_i2v`：`positive_prompt`、`seed`、`width`、`height`、`length`（帧数，需为 4n+1，如 49）、`fps`、`steps`、`cfg`
- **视频 · Wan2.2 图生视频 I2V** `video_wan22_i2v_image`：上述全部 + `image`（本地起始帧路径，自动上传）
- **视频 · MiniMax-H3 I2V** `video_minimax_h3_i2v`：`positive_prompt`、`seed`、`image`、`width`、`height`、`length`（帧数，step 17，默认 124）、`fps`
- **视频 · LTX-2.3 I2V** `video_ltx2_3_i2v`：`positive_prompt`、`seed`、`image`、`duration`（秒，帧数=duration×fps+1）、`fps`、`width`、`height`
- **数字人 · MiniMax-H3 I2V（竖屏说话）** `digital_human_talking`：复用 MiniMax-H3 模板，`positive_prompt`（含台词描述）、`seed`、`image`（本地人物图，自动上传）、`width`、`height`（默认 832×1152 竖屏）、`length`（帧数，step 默认 17）、`fps`

新增/改名参数：编辑对应 `*.params.json` 即可，无需改代码。

### 配置项（`config.toml`）
`[comfyui]`：`base_url` / `username` / `password` / `timeout` / `connect_timeout` / `max_retries` / `retry_backoff` / `poll_interval` / `max_wait`
- **Basic Auth**：若 ComfyUI 安装了鉴权插件（如 ComfyUI-Basic-Auth），在 `[comfyui]` 填写 `username` / `password` 即可，客户端会自动在每次请求（含 `/prompt`、`/history`、`/view`、`/upload/image`）携带 `Authorization: Basic` 头。两者留空则按无认证调用（兼容未加插件的实例）。
`[paths]`：`workflows_dir` / `output_dir` / `log_file`
`[defaults]`：`workflow` 及各项默认参数（被 CLI `--set` 覆盖）

## 五、实现能力（comfy_client.py）

- **连通性检测**：`ping()` / `check_connectivity()` 用短超时探 `/system_stats`，返回 `(ok, info)`。
- **图片上传**：`upload_image(local_path)` → `POST /upload/image`（multipart），返回服务器侧文件名；供 `LoadImage` / 图生视频（I2V）起始帧使用。`run.py` 在参数目标是 `LoadImage` 时自动调用。
- **提交**：`queue_prompt(workflow)` → `POST /prompt`，返回 `prompt_id`。
- **进度跟踪**：`wait_for_completion(prompt_id)` 轮询 `/history/<id>`（不支持时回退全量 `/history`），识别执行错误并抛出，超时（默认 900s）判定失败。
- **下载产物**：`download_outputs(...)` 遍历 outputs 的 `images` / `videos` / `gifs` 等键，按 `/view?filename=&subfolder=&type=` 拉取字节落盘到 `<output_dir>/<prompt_id>/`；另对含 `filename` 的未知键做兜底收集。
- **重试与超时**：`_request()` 对网络错误 / 5xx 重试（默认 3 次，指数退避），4xx 不重试；每次 HTTP 受 `timeout` 约束。
- **日志**：`setup_logging()` 输出带时间戳的 `[INFO]/[WARNING]/[重试]` 日志，可同时写文件（`paths.log_file`）。

> 进度跟踪采用**轮询 `/history`**（零额外依赖）。若需更低延迟，可后续接入 `/ws` WebSocket（在 `wait_for_completion` 之外另起通道推送进度）。

## 六、已知限制与排错

- **工作流必须 API 格式**：UI 直接保存的 `workflow.json`（含 `nodes`/`links`）不能直接提交，需用 "Export (API Format)"。
- **产物节点需可识别**：下载逻辑按 `SaveImage`（`images`）与 `SaveWEBM`/`SaveVideo`/`*VideoCombine`/`VHS_*`（`videos`/`gifs`）提取；若你的保存节点输出键不同，请在 `comfy_client.py` 的 `_VIDEO_KEYS` / 识别条件处微调。
- **Wan2.2 为双模型架构**：本模板仅用 `wan2.2_i2v_low_noise_14B` 低噪模型即出片正常；如需更高画质可叠加 `wan2.2_i2v_high_noise_14B` 做两阶段采样（需自行扩展图）。
- **视频编码**：默认 `SaveWEBM(codec=vp9)`，若播放器兼容性差，可改用 `SaveAnimatedWEBP` 或 `SaveVideo`。
- **连通性失败**：先确认目标机 `python main.py --listen 0.0.0.0` 且防火墙放行；`--ping` 是最快定位手段。
- **执行报错**：客户端会抓取 ComfyUI 返回的 `execution_error` 并抛出，按报错信息修正工作流节点/模型（常见：模型名不符、CLIP `type` 选错、`length` 非 4n+1）。

## 七、测试结果（本环境真机验证，服务器 192.168.31.243:8188 / RTX 5070 Ti 16GB）

| 模板 | 类型 | 真机结果 | 产物样例 | 备注 |
| --- | --- | --- | --- | --- |
| `image_boogu_image_0_1_turbo_t2i` | 文生图 | ✅ 1024×1024 PNG | `33_Boogu_00010_.png` | Boogu 0.1 turbo，~145s（含首加载） |
| `image_krea2_turbo_t2i` | 文生图 | ✅ 1024×1024 PNG | `10_Krea2_turbo_00009_.png` | Krea2 turbo，8 步 |
| `video_wan22_i2v` | 文生视频 | ✅ 832×480 WEBM（49 帧 / 3s） | `9_WanI2V_00001_.webm` | Wan2.2 14B fp8 |
| `video_wan22_i2v_image` | 图生视频 I2V | ✅ 832×480 WEBM | `10_WanI2V_00002_.webm` | 加 `LoadImage` → `WanImageToVideo.start_image` 起帧 |
| `video_minimax_h3_i2v` | 图生视频 I2V | ✅ 1024×576 MP4（h264+aac，56 帧 / 2.33s） | `15_MiniMax_H3_00001_.mp4` | 含音轨；32B 文本编码器较重，建议 `length≤48` |
| `video_ltx2_3_i2v` | 图生视频 I2V | ✅ 1024×576 MP4（h264，73 帧 / 2.92s） | `LTX_2.3_i2v_00003_.mp4` | LTX-2.3 22B 音视频联合，默认 3s |
| `digital_human_talking` | 数字人说话视频 I2V | ✅ 832×1152 MP4（h264+aac，90 帧 / 3.75s） | `15_DigitalHuman_Talking_00001_.mp4` | 复用 MiniMax-H3；竖屏；含语音台词+氛围音；语义级口型 |

- **离线 mock**：`python -m tests.e2e_test` 验证 提交→轮询→下载 全链路，产物落 `AI-Images-Tools/OutImages/e2e_test/<prompt_id>/`。
- **I2V 起帧**：`image` 参数传本地图片路径，客户端自动 `POST /upload/image` 上传并替换为服务器文件名（对应 `LoadImage` 节点），无需手动预上传。
- **已知坑（操作）**：若前序任务异常退出，ComfyUI 执行线程可能卡在 `queue_running` 的「幽灵」任务（VRAM=0 却不执行，新任务一直 `running` 无进度）。解决：连续 `POST /interrupt` + `POST /queue {"clear":true}`，等待约 10–15s 队列排空即可恢复。本次 minimax / ltx 真机验证即曾因此卡住，清队后正常出片（工作流本身无问题）。
- 真实出图/出片耗时含模型首次加载；模型驻留显存后后续任务明显更快。视频类可在 16GB 卡上通过降低 `length`/`width`/`steps` 提速。
- **⚠️ 已知坑（云端对口型节点）**：本机 ComfyUI 装了 HeyGen（`HeyGenTalkingPhotoNode`）、Kling（`KlingAvatarNode`/`KlingLipSync*`）、Sync.so（`SyncTalkingImageNode`）等"图片/音频→对口型视频"节点，其 `speech`/`voice`/`model` 等参数均为 **`COMFY_DYNAMICCOMBO_V3` 动态组合类型**——该类型专为 ComfyUI **Web UI 前端**设计，通过纯 API（`POST /prompt`）提交时序列化格式不匹配，参数会丢失、节点拿不到文字/音色，**无法在本技能包里直接驱动**（已实测 HeyGen 多次失败）。若以后要做"逐帧精确对口型"，需从 Web UI 手动导出一次真实 API 格式工作流，或用其官方 Python SDK/HTTP API，而非本技能包的 `/prompt` 直驱。当前"数字人说话"用 `digital_human_talking`（MiniMax-H3 I2V）实现语义级口型+语音，已验证可用。
