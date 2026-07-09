# AI-WeMedia-Skills

本目录存放 **AI-WeMedia-Tools（自媒体工具箱）** 项目沉淀的可复用 Skills 技能包。
每个子目录是一个独立技能，含 `SKILL.md`（技能说明 + 触发条件 + 实现规范 + 已知坑）。

## 技能清单

| 技能 | 路径 | 用途 |
| --- | --- | --- |
| `ai-category-module-scaffold` | `ai-category-module-scaffold/SKILL.md` | 为某个 `AI-*-Tools` 分类脚手架「采集 → 二创 → SQLite 持久化 → mock 离线 pipeline → CLI → 测试」完整模块。覆盖目录约定、命名规范（`-` 分隔）、全局 config/db（AI-Global）、三类采集器、双风格二创排版，并内附三大已知坑（mock 改写误判标题 / 头条移动版 SSR / 导语重复）及修复。 |

## 设计原则

- **代码落地于分类目录**：每个分类功能的可运行代码在对应 `AI-*-Tools/Codes/`，技能包只沉淀「怎么做」的方法论与避坑经验，不重复装代码。
- **全局资源共享**：配置与数据库统一在 `AI-Global/`（Configs / Database），新分类直接复用。
- **离线可跑**：mock 模式无需任何 API key 即可验证全流程；真实 key 通过 `AI-Global/Configs/config.toml` 或环境变量注入。

## 使用方式

在 WorkBuddy 中调用本技能（如「搭建 AI-Videos-Tools 模块」会自动命中 `ai-category-module-scaffold`），
按其步骤与「已知坑」落地即可，避免重踩已修复的坑。
