# AI-WeMedia-Skills

本目录存放 **AI-WeMedia-Tools（自媒体工具箱）** 的**全局 / 跨分类** Skills 技能包。

> 各**分类自己的使用技能**已分开放到各自分类文件夹内（如 `AI-Articles-Tools/AI-Articles-Skills/`）。
> 本目录只保留**不属于任何单一分类**的「元技能」——即「如何脚手架一个新的分类模块」。

## 技能清单

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| `ai-category-module-scaffold` | `ai-category-module-scaffold/SKILL.md` | 为某个 `AI-*-Tools` 分类脚手架「采集 → 二创 → SQLite 持久化 → mock 离线 pipeline → CLI → 测试」完整模块。覆盖目录约定、命名规范（`-` 分隔）、全局 config/db（AI-Global）、三类采集器、双风格二创排版，并内附三大已知坑（mock 改写误判标题 / 头条移动版 SSR / 导语重复）及修复。 |

## 各分类技能包所在位置

| 分类 | 技能包路径 |
| --- | --- |
| `AI-Articles-Tools` | `AI-Articles-Tools/AI-Articles-Skills/SKILL.md` |
| `AI-Images-Tools` | `AI-Images-Tools/AI-Images-Skills/SKILL.md`（🟢 进行中：已接入 ComfyUI，Boogu 文生图 + Wan2.2 视频真机验证） |
| `AI-Musics-Tools` | `AI-Musics-Tools/AI-Musics-Skills/SKILL.md` |
| `AI-Prompts-Tools` | `AI-Prompts-Tools/AI-Prompts-Skills/SKILL.md` |
| `AI-Sounds-Tools` | `AI-Sounds-Tools/AI-Sounds-Skills/SKILL.md` |
| `AI-Videos-Tools` | `AI-Videos-Tools/AI-Videos-Skills/SKILL.md` |
| `AI-Webs-Tools` | `AI-Webs-Tools/AI-Webs-Skills/SKILL.md` |

## 设计原则

- **分类技能就近放**：每个分类的可运行代码在对应 `AI-*-Tools/Codes/`，其使用技能就在同分类的 `AI-*-Tools/AI-*-Skills/`，一眼可定位。
- **全局资源共享**：配置与数据库统一在 `AI-Global/`（Configs / Database），新分类直接复用。
- **离线可跑**：mock 模式无需任何 API key 即可验证全流程；真实 key 通过 `AI-Global/Configs/config.toml` 或环境变量注入。
- **脚手架复用**：新分类不要从零写，调用 `ai-category-module-scaffold` 按其步骤与「已知坑」落地即可，避免重踩已修复的坑。

## 使用方式

- 要**用**某个分类工具：直接命中该分类的技能（如「采集这篇文章并二创」命中 `ai-articles-tools`）。
- 要**新建**一个分类模块：命中 `ai-category-module-scaffold`，按其步骤落地。
