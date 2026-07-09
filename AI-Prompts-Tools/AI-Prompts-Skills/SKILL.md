---
name: ai-prompts-tools
description: AI-Prompts-Tools（关键词及关键词反推）分类技能。含已有初步实现 Prompts-Back-Calculate（关键词反推）。当用户说"关键词反推/提示词反推/优化提示词/落地 AI-Prompts-Tools 模块"时触发。
agent_created: true
---

# AI-Prompts-Tools 关键词及关键词反推（🟢 进行中）

本目录是 **AI-Prompts-Tools** 分类的技能包（`AI-Prompts-Tools/AI-Prompts-Skills/`）。
当前阶段：**🟢 进行中**（已有初步实现）。

## 定位
关键词（prompts）生成、优化与反推：
- 提示词生成 / 优化 / 风格化；
- **关键词反推**：由图片 / 视频 / 效果反推出可用的提示词（已有 `Prompts-Back-Calculate/` 初步代码）。

## 当前状态
- `AI-Prompts-Tools/Prompts-Back-Calculate/`：关键词反推已有初步实现（可运行代码）；
- 其余子方向（通用提示词生成 / 优化）待按统一架构补全。

## 如何补全 / 统一落地
- 复用已有 `Prompts-Back-Calculate/` 的逻辑，按需接入统一架构；
- 新增子方向请用**全局脚手架技能** `ai-category-module-scaffold`（位于 `AI-WeMedia-Tools/AI-WeMedia-Skills/ai-category-module-scaffold/`），产出采集 / 处理骨架、SQLite 持久化、mock 离线 pipeline + CLI、双风格结果排版模板。

## 全局约定（务必遵守）
- 代码统一放 `AI-Prompts-Tools/Codes/`（已有反推代码可保留 `Prompts-Back-Calculate/` 并逐步整合）；
- 配置与数据库全局共享于 `AI-Global/`（Configs / Database）；
- 产物目录加入 `.gitignore`，不入库；
- 文件 / 文件夹命名分隔符用「-」；
- `--mock` 离线可跑通全流程。

## 完成后
更新根 `README.md`「功能模块进度」表与 `.workbuddy/memory/MEMORY.md`，提交并推 GitHub。
