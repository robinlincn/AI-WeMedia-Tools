# Claude Code 4 个习惯 - HyperFrames 复刻项目

> 演示"反推视频提示词 → 代码复刻 → mp4 输出"全链路。
> 反推源：`VideoPrompt/让ClaudeCode替你干一天的4个习惯同样一个ClaudeCode-提示词反推-20260708-1538.md`

## 目录

```
Codes/claude-code-4habits/
├── design.md        # 设计稿（配色 / 字体 / 通用元素）
├── package.json     # 依赖 + npm scripts
├── src/
│   └── index.html   # 根 composition（3 镜 + 1 总结）
├── assets/          # 静态资源（暂空）
├── build/           # 编译产物（暂空，hyperframes 直接渲染到 mp4）
└── node_modules/    # hyperframes@0.7.42 + 依赖
```

## 复刻范围

只复刻了反推 17 镜中的 **4 个关键场景**（约 40 秒），作为最小可行 demo：

| 场景 | 时间 | 内容 |
|---|---|---|
| 1 封面 | 0-8s | 大字"4"+"让 Claude Code 替你干一天的 4 个习惯"+橙色暖色渐变 |
| 2 习惯 1·问题 | 8-20s | Claude 回复 UI 模拟 + 关键行橙色高亮"你把那个环境变量配一下" |
| 3 习惯 1·怎么做 | 20-32s | CLAUDE.md markdown 渲染 + 两张绿色勾选卡片 |
| 4 总结 | 32-40s | 4 步流程图（待办→提醒→ultracode→常驻 Agent）+ Ali 厂长结束圆 |

## 使用

```bash
cd Codes/claude-code-4habits
npm install                       # 装 hyperframes
cd src
npx hyperframes lint              # 校验 HTML（0 errors）
npx hyperframes validate          # 跑 headless Chrome 验证
npx hyperframes render --output ../../OutVideos/claude-code-4habits-hyperframes.mp4
```

## 输出

- **文件**：`OutVideos/claude-code-4habits-hyperframes.mp4`
- **规格**：1080×1080 (1:1) · h264 / yuv420p / bt709 · 30fps · 40.0s · 2.1MB
- **渲染时间**：3 分 27 秒（hyperframes 静态帧去重 67%，1.2 万帧中 800 帧复用）

## 关键设计决策

- **1:1 正方形画布**（vs 抖音 4:3 / 16:9）—— 社交媒体（IG/朋友圈/小红书）友好
- **配色**：深蓝紫底 + 蓝/青/紫/黄/橙 5 种主题色（4 个习惯段每段一色）
- **场景切换**：JS `hidden` 属性切换 div（不靠 CSS 动画，hyperframes 帧去重能识别）
- **底部字幕条**：黄字 #FFD75E 套透明黑底，原视频风格 1:1 还原
- **GSAP 缓动**：cover/scene 进场用 `power3.out` + `back.out` 弹性，进场 0.6-0.8s
- **静态帧去重**：hyperframes 识别 67% 静态帧复用，节省 1/3 渲染时间

## 已知限制

- 视频**没有音轨**（hyperframes 不自带 TTS/配音，需要外部接入）
- 视频是 1:1 不是抖音原生 4:3 —— 老板如需 4:3/16:9，改 `data-width` / `data-height`
- 4 镜是 demo，**未做** 17 镜完整复刻（hooks 时机图、ultracode 终端框、OpenClaw 4 张卡等未做）
- 渲染中报 "Sub-composition timelines not registered after 45000ms" —— 根 timeline 是 `root`，子 scene 用了 `data-composition-id` 但没注册 `window.__timelines[name]`。功能正常但会冗余等待 45s（已被 `data-no-timeline` 提示规避的可能）

## 完整复刻待办

老板要完整 17 镜的话需要再补：
- 场景 5/6 引子段（蓝/紫/黄三胶囊）
- 场景 7-8 AI 是乘法（橙红 + 50 vs 10 对比）
- 场景 9-10 方法总览（4 张彩色卡片）
- 场景 13-16 hooks 4 步时机图 + ultracode terminal + OpenClaw
- 4:3 画布（960×720）+ 抖音原画风
