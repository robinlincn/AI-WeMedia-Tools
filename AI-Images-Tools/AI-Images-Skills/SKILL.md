---
name: ai-images-tools
description: 通过 HTTP API 调用局域网内另一台机器上的 ComfyUI（默认 http://192.168.31.243:8188）执行工作流，生成图片与视频。支持工作流参数化（提示词/尺寸/种子/帧数）、提交到 /prompt、轮询 /history 跟踪进度、从 /view 下载产物，具备连通性检测、重试、超时与清晰日志。当用户说"用 ComfyUI 出图/出视频""调用局域网 ComfyUI""跑工作流生成图片/视频""提交 ComfyUI 任务并下载产物"时触发。
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
   - **Boogu 文生图**（`image_boogu_image_0_1_turbo_t2i`）：需要 `UNETLoader` 的 `boogu_image_turbo_fp8_scaled.safetensors`、`CLIPLoader(type='boogu', clip_name='qwen3vl_8b_fp8_scaled.safetensors')`、VAE `ae.safetensors`；负向条件用 `ConditioningZeroOut` 置零；分辨率由 `ResolutionSelector`(1:1 / 1MP) 给出；采样器 `KSampler(steps=4, cfg=1, sampler='lcm')`。均为 ComfyUI 原生节点，无需额外自定义包。
   - **Wan2.2 图生视频**（`video_wan22_i2v`）：需要 `UNETLoader` 的 `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`（14B，fp8）、`CLIPLoader(type='wan', clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors')`、VAE `Wan2_1_VAE_bf16.safetensors`；视频经 `WanImageToVideo` 生成 latent → 标准 `KSampler` 采样 → `VAEDecode` → `SaveWEBM` 落盘（原生节点，无需 `ComfyUI-VideoHelperSuite`）。
   - 工作流里引用的模型文件必须已存在于目标机 `ComfyUI/models/` 下；若使用其它模型，请按实际文件名替换模板中的 `unet_name` / `clip_name` / `vae_name`。
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
│   ├── video_wan22_i2v.json                    # ✅ Wan2.2 图生视频（真机验证，输出 webm）
│   └── video_wan22_i2v.params.json
└── tests/
    ├── mock_server.py            # 本地 ComfyUI 兼容 Mock 服务（离线验证用）
    ├── e2e_test.py               # 端到端测试（mock / real 两种模式）
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

# 3) 跑图片工作流（Boogu 文生图）
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i \
    --set positive_prompt="一只戴草帽的橘猫，阳光，高清" \
    --set seed=42

# 4) 跑视频工作流（Wan2.2 图生视频，输出 webm）
python -m src.run --workflow video_wan22_i2v \
    --set positive_prompt="A serene lake at dawn, gentle mist, cinematic" \
    --set seed=7 --set length=49 --set fps=16

# 5) 端到端测试（离线 mock 验证全链路 / 真实模式出图）
python -m tests.e2e_test            # 离线 mock：验证 提交→轮询→下载落盘
python -m tests.e2e_test --real     # 指向真实 ComfyUI 出图/出片
```

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

> **提速提示**：`length`（帧数）与 `width/height` 对耗时影响最大；`steps` 可降到 15 仍可用。若需从图片起帧做 I2V，额外加 `LoadImage` 节点并把输出连到 `WanImageToVideo.start_image` 即可。

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
- **图片** `image_boogu_image_0_1_turbo_t2i`（Boogu 文生图）：`positive_prompt`（正提示词）、`seed`（随机种子）、`aspect_ratio`（分辨率比例，如 `1:1 (Square)` / `16:9`；由 `ResolutionSelector` 决定宽高）
- **视频** `video_wan22_i2v`（Wan2.2 图生视频）：`positive_prompt`、`seed`、`width`、`height`、`length`（帧数，需为 4n+1，如 49）、`fps`（输出帧率）、`steps`（采样步数）、`cfg`（引导系数）

新增/改名参数：编辑对应 `*.params.json` 即可，无需改代码。

### 配置项（`config.toml`）
`[comfyui]`：`base_url` / `timeout` / `connect_timeout` / `max_retries` / `retry_backoff` / `poll_interval` / `max_wait`
`[paths]`：`workflows_dir` / `output_dir` / `log_file`
`[defaults]`：`workflow` 及各项默认参数（被 CLI `--set` 覆盖）

## 五、实现能力（comfy_client.py）

- **连通性检测**：`ping()` / `check_connectivity()` 用短超时探 `/system_stats`，返回 `(ok, info)`。
- **提交**：`queue_prompt(workflow)` → `POST /prompt`，返回 `prompt_id`。
- **进度跟踪**：`wait_for_completion(prompt_id)` 轮询 `/history/<id>`（不支持时回退全量 `/history`），识别执行错误并抛出，超时（默认 900s）判定失败。
- **下载产物**：`download_outputs(...)` 遍历 outputs 的 `images` / `gifs`（视频）两类，按 `/view?filename=&subfolder=&type=` 拉取字节落盘到 `<output_dir>/<prompt_id>/`。
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

## 七、测试结果（本环境验证）

| 模式 | 图片 `image_boogu_image_0_1_turbo_t2i` | 视频 `video_wan22_i2v` | 说明 |
| --- | --- | --- | --- |
| mock（离线） | ✅ 落盘 PNG | ✅ 落盘 WEBM | 验证 提交→轮询→下载 全链路，产物写入 `AI-Images-Tools/OutImages/e2e_test/<prompt_id>/` |
| real（192.168.31.243:8188） | ✅ 1024×1024 PNG，~145s | ✅ 832×480 webm(49帧/3s)，~433s | 真机端到端打通：提交→轮询→下载落盘，文件有效（PNG/EBML 签名校验通过） |

> 真实出图/出片的耗时含模型首次加载；模型驻留显存后后续任务明显更快。视频因 14B fp8 在 5070 Ti 上较大，可通过降低 `length`/`width`/`steps` 提速。
