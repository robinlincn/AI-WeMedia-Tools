# AI-WeMedia-Tools（自媒体工具箱）

> 一个面向自媒体创作者的 AI 工具箱。目标是把 **文章、图片、音乐、关键词、声音、视频、网页** 等自媒体创作环节，逐步沉淀为可用工具，并最终整合为一个统一的大型「AI-WeMedia-Tools（自媒体工具箱）」软件。

---

## 🎯 项目愿景

把分散在各处的 AI 创作能力，收敛成一套 **可成长、可复用、可整合** 的自媒体工具体系：

- 创作不再依赖零散的提示词和临时脚本；
- 每个能力先以轻量方式验证，成熟后再产品化；
- 最终所有能力在一个入口内打通，形成一站式创作工具箱。

---

## 📁 目录结构

```
AI-WeMedia-Tools/
├── AI-Global/                # 全局共享资源（所有分类共用）
│   ├── Configs/              # 全局配置 config.toml（含密钥，gitignore）+ config.example.toml
│   └── Database/             # 全局 SQLite 数据库（各分类共享，gitignore）
├── AI-Articles-Tools/        # 文章优化及二创
├── AI-Images-Tools/          # 图片制作及效果
├── AI-Musics-Tools/          # 音乐制作
├── AI-Prompts-Tools/         # 关键词及关键词反推
│   └── Prompts-Back-Calculate/   # 关键词反推（已有初步实现）
├── AI-Sounds-Tools/          # 声音及声效制作
├── AI-Videos-Tools/          # 视频及教学制作
└── AI-Webs-Tools/            # 网站页面制作
```

> 约定：各分类的**代码**放在自己的 `Codes/` 目录；**配置与数据库**统一放在 `AI-Global/`
> （`Configs/`、`Database/`），便于所有分类共享与集中管理。

| 分目录 | 定位 | 说明 |
|--------|------|------|
| `AI-Articles-Tools` | 文章优化及二创 | 改写、润色、扩写、摘要、风格化等 |
| `AI-Images-Tools` | 图片制作及效果 | 文生图、图生图、风格滤镜、批处理等 |
| `AI-Musics-Tools` | 音乐制作 | 旋律、伴奏、歌词、混音等 |
| `AI-Prompts-Tools` | 关键词及关键词反推 | 提示词生成、优化、反推（含 `Prompts-Back-Calculate`） |
| `AI-Sounds-Tools` | 声音及声效制作 | 配音、音效、降噪、变声等 |
| `AI-Videos-Tools` | 视频及教学制作 | 剪辑、字幕、教学短片、特效等 |
| `AI-Webs-Tools` | 网站页面制作 | 落地页、作品集、工具页等 |

---

## 🗺️ 演进路线图（三阶段）

整体采用 **「先技能、再软件、后整合」** 的渐进式演进策略，逐个文件夹落地，边用边完善。

### 阶段一：Skills 技能化（当前阶段）
- 逐个分目录落地，每个目录内的功能先以 **WorkBuddy Skills 技能** 形式实现；
- 快速验证功能可行性、积累真实使用经验、打磨稳定工作流；
- 交付物：各模块的 Skills 技能（`SKILL.md` + 脚本/参考）。

### 阶段二：独立小软件
- 当某个 Skills 技能 **成熟、需求稳定** 后，将其沉淀为 **独立的小软件**；
- 脱离对话环境，作为可直接运行的轻量应用使用；
- 交付物：一个个可独立使用的小工具（CLI / 桌面 / 网页）。

### 阶段三：整合大型工具箱
- 将所有独立小软件整合进统一的 **「AI-WeMedia-Tools（自媒体工具箱）」大型软件**；
- 统一入口、一致交互、共享资源与配置；
- 交付物：一体化自媒体创作工具箱。

```
阶段一 Skills  ──▶  阶段二 独立小软件  ──▶  阶段三 整合大型工具箱
（逐个目录验证）      （能力产品化）          （一站式入口）
```

---

## 📊 功能模块进度

| 模块 | 方向 | 当前阶段 | 说明 |
|------|------|----------|------|
| `AI-Articles-Tools` | 文章优化及二创 | 🟢 进行中 | 采集（链接/文案/视频）+ 二创（标题/正文/配图/头条排版）已落地，代码见 `AI-Articles-Tools/Codes` |
| `AI-Images-Tools` | 图片制作及效果 | 🟡 规划中 | 待落地 Skills |
| `AI-Musics-Tools` | 音乐制作 | 🟡 规划中 | 待落地 Skills |
| `AI-Prompts-Tools` | 关键词及反推 | 🟢 进行中 | `Prompts-Back-Calculate` 已有初步代码 |
| `AI-Sounds-Tools` | 声音及声效 | 🟡 规划中 | 待落地 Skills |
| `AI-Videos-Tools` | 视频及教学 | 🟡 规划中 | 待落地 Skills |
| `AI-Webs-Tools` | 网站页面制作 | 🟡 规划中 | 待落地 Skills |

> 图例：🟢 进行中 · 🟡 规划中 · 🔵 已出小软件 · ⚪ 已整合

---

## 🔄 更新与版本管理

- **代码仓库**：<https://github.com/robinlincn/AI-WeMedia-Tools>
- 本规划 **同时** 保存在仓库根目录 `README.md` 与 `.workbuddy/memory/MEMORY.md`（长期记忆），两者保持同步；
- 每次有新功能落地或阶段推进，请 **更新本文件对应进度表**，并提交到 GitHub 以保持版本一致；
- 依赖（`node_modules`）、视频/帧/日志等生成产物已通过 `.gitignore` 排除，避免仓库体积膨胀。

---

## 📝 更新日志

- **2026-07-09**：初始化项目规划，建立目录结构与三阶段演进路线图，首次提交并推送至 GitHub。
- **2026-07-09**：落地 `AI-Articles-Tools` 模块——内容采集（链接/文案/视频）+ 二次创作（标题/正文/配图/头条排版），数据持久化到 SQLite；新增模块 `Codes/README.md` 与离线冒烟测试，修复 mock 改写任务被误判为标题任务的 bug。
