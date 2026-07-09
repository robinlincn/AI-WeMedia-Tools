# Claude Code 4 个习惯 - HyperFrames 复刻设计稿

> 来源：原视频《让 Claude Code 替你干一天的 4 个习惯》反推（VideoPrompt/让ClaudeCode...提示词反推-20260708-1538.md）
> 复刻范围：**Demo 3 镜**（封面镜 01 / 习惯 1·问题 镜 05 / 习惯 1·怎么做 镜 06 / 总结镜 17），约 30-40 秒
> 输出：1080×1080（正方形，社交媒体友好）+ mp4

## 视觉系统

### 配色
- **bg-primary**: `#0E0E1F` 深夜蓝紫（封面/总结/方法总览段主色）
- **bg-section-1**: `#1A0E2E` 习惯 1 段深紫底
- **bg-section-3**: `#2A1A0E` 习惯 3 段深棕紫底
- **text-primary**: `#FFFFFF`
- **text-secondary**: `#A0A0C0`（次要说明文）
- **accent-cyan**: `#5DD9F4`（高亮/链接）
- **accent-purple**: `#A56BFF`（习惯 3 主题）
- **accent-yellow**: `#FFD75E`（底部字幕条 + 习惯 4）
- **accent-orange**: `#FF8A3D`（AI 乘法段 + 警示高亮）
- **accent-green**: `#5CE4A1`（勾选 / 积极）

### 字体
- **headline**: `"Noto Sans SC"` 系统默认，bold，60-120px
- **body**: `"Noto Sans SC"` regular，20-42px
- **code**: `"JetBrains Mono"` fallback `"Consolas"`，16-20px
- **subtitle-bar**: `"Noto Sans SC"` bold，36-42px，黄色 `#FFD75E`

### 通用元素
- **底部字幕条**：宽 100%，高 80-100px，背景 `rgba(0,0,0,0.7)` + 黄色文字 `#FFD75E`
- **卡片**：圆角 16-24px，背景 `rgba(255,255,255,0.06)`，边框 `1px solid rgba(255,255,255,0.12)`
- **进场动画**：slide-up + fade，0.6-0.8s，ease `power3.out`，stagger 0.15s
- **段间切换**：crossfade，0.4s
