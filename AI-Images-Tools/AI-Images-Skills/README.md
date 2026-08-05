# AI-Images-Skills（快速上手）

通过 HTTP API 调用局域网内 ComfyUI（`http://192.168.31.243:8188`）生成图片 / 视频。
**仅依赖 Python 标准库，无需 pip 安装。**

## 1. 准备
```bash
cd AI-Images-Tools/AI-Images-Skills
cp config.toml.example config.toml      # 按需改 base_url 等
```

## 2. 连通性自检
```bash
python -m src.run --ping
```

## 3. 出图 / 出视频
```bash
# 文生图（Boogu / Krea2，均真机验证）
python -m src.run --workflow image_boogu_image_0_1_turbo_t2i --set positive_prompt="一只戴草帽的橘猫，阳光，高清" --set seed=42
python -m src.run --workflow image_krea2_turbo_t2i --set positive_prompt="a cute orange cat" --set seed=7

# 视频（图生视频需 --set image=<本地起始帧路径>，会自动上传）
python -m src.run --workflow video_wan22_i2v        --set positive_prompt="A serene lake at dawn" --set length=49 --set fps=16
python -m src.run --workflow video_wan22_i2v_image  --set positive_prompt="..." --set image="d:/start.png" --set seed=123
python -m src.run --workflow video_minimax_h3_i2v   --set "positive_prompt=女孩在樱花树下微笑" --set image="d:/start.png"
python -m src.run --workflow video_ltx2_3_i2v       --set "positive_prompt=A woman walks in a garden" --set image="d:/start.png" --set duration=3
```
产物落在 `AI-Images-Tools/OutImages/<prompt_id>/`（图片 `*.png`、视频 `*.webm` / `*.mp4`）。

## 4. 端到端测试
```bash
python -m tests.e2e_test            # 离线 mock：验证 提交→轮询→下载落盘（图片+视频）
python -m tests.e2e_test --real     # 指向真实 ComfyUI 出图/出片
```

## 目录
- `src/comfy_client.py` 核心客户端（连通性/提交/轮询/下载/图片上传/重试/超时/日志）
- `src/run.py` CLI 入口（参数化 + 执行 + 摘要；`LoadImage` 参数自动上传本地图）
- `workflows/` 工作流模板 + 参数映射（`*.params.json`）
- `tests/` 端到端测试 + 本地 Mock 服务 + LTX 模板派生脚本

## 前置条件
- 目标机 ComfyUI 以 `--listen 0.0.0.0` 启动且防火墙放行 8188；
- 工作流引用的模型已就位（详见 [SKILL.md](./SKILL.md) 第一节「前置条件」：Boogu / Krea2 / Wan2.2 / MiniMax-H3 / LTX-2.3 各自的模型与节点）；
- `workflows/*.json` 须为 ComfyUI **API 格式**（"Export (API Format)"）。

详细参数与排错见 [SKILL.md](./SKILL.md)。
