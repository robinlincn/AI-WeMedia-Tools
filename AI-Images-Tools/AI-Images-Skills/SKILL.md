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
2. **必要模型与自定义节点**：工作流里引用的模型文件（checkpoint / LoRA / VAE / 视频模型等）必须已存在于目标机的 `ComfyUI/models/` 下；视频类工作流还需对应的自定义节点（如 Wan2.1、HunyuanVideo、AnimateDiff 或 `ComfyUI-VideoHelperSuite` 的 `VHS_VideoCombine`）。
3. **工作流模板匹配**：`workflows/*.json` 必须是 **API 格式**（菜单 "Export (API Format)" 导出），且其中的节点 / 输入键要与对应的 `*.params.json` 映射一致。自带模板为占位示例，需按你机器实际情况替换。

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
│   ├── image_basic.json          # 图片工作流模板（API 格式，SDXL 风格示例）
│   ├── image_basic.params.json   # 逻辑参数 → 节点映射
│   ├── video_basic.json          # 视频工作流模板（占位，需替换）
│   └── video_basic.params.json
└── tests/
    ├── mock_server.py            # 本地 ComfyUI 兼容 Mock 服务（离线验证用）
    └── e2e_test.py               # 端到端测试（mock / real 两种模式）
```

产物默认落到 `AI-Images-Tools/OutImages/<prompt_id>/`（图片 `*.png`、视频 `*.mp4`），由 `config.toml` 的 `paths.output_dir` 控制。

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
python -m src.run --workflow image_basic \
    --set positive_prompt="a calm lake at dawn, cinematic" \
    --set seed=42 --set width=1024 --set height=1024

# 4) 跑视频工作流
python -m src.run --workflow video_basic \
    --set positive_prompt="gentle waves on a sunny beach" \
    --set frames=25 --set seed=7

# 5) 端到端测试（离线 mock 验证全链路 / 真实模式出图）
python -m tests.e2e_test            # 离线 mock：验证 提交→轮询→下载落盘
python -m tests.e2e_test --real     # 指向真实 ComfyUI 出图/出片
```

## 四、参数说明

### CLI 参数（`src/run.py`）
| 参数 | 说明 |
| --- | --- |
| `--config <路径>` | 指定 config.toml（默认按 `config.toml` → `config.toml.example` 顺序加载） |
| `--base-url <url>` | 覆盖配置中的 ComfyUI 地址 |
| `--workflow <名/路径>` | 工作流名（解析为 `workflows/<名>.json`）或 JSON 路径；默认 `image_basic` |
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
- **图片** `image_basic`：`positive_prompt`、`negative_prompt`、`seed`、`steps`、`cfg`、`width`、`height`
- **视频** `video_basic`：`positive_prompt`、`seed`、`frames`、`width`、`height`

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
- **视频模板为占位**：`video_basic.json` 节点名为示意，请在你机器上调好视频流程后导出覆盖，并同步更新 `video_basic.params.json`。
- **产物节点需可识别**：下载逻辑按 `SaveImage`（`images`）与 `VHS_VideoCombine`/`*VideoCombine`（`gifs`）提取；若你的保存节点命名不同，请在 `comfy_client.py` 的 `_VIDEO_KEYS` / 识别条件处微调。
- **连通性失败**：先确认目标机 `python main.py --listen 0.0.0.0` 且防火墙放行；`--ping` 是最快定位手段。
- **执行报错**：客户端会抓取 ComfyUI 返回的 `execution_error` 并抛出，按报错信息修正工作流节点/模型。

## 七、测试结果（本环境验证）

| 模式 | 图片 image_basic | 视频 video_basic | 说明 |
| --- | --- | --- | --- |
| mock（离线） | ✅ 落盘 PNG | ✅ 落盘 MP4 | 验证 提交→轮询→下载 全链路，产物写入 `AI-Images-Tools/OutImages/e2e_test/<prompt_id>/` |
| real（指向 192.168.31.243:8188） | ❌ 连通性超时 | ❌ 连通性超时 | 本执行环境不在该局域网，预期不可达；连通性检测优雅报错，无崩溃 |

> 真实出图/出片需在**连到该局域网的机器**上执行 `python -m tests.e2e_test --real`（或 `python -m src.run --workflow ...`）。
