---
name: ai-musics-tools
description: AI-Musics-Tools（音乐制作）分类技能。当前为规划占位：旋律、伴奏、歌词、混音等。当用户说"做音乐/生成旋律/写歌词/落地 AI-Musics-Tools 模块"时触发，引导用全局脚手架技能 ai-category-module-scaffold 落地。
agent_created: true
---

# AI-Musics-Tools 音乐制作（🟡 规划中）

本目录是 **AI-Musics-Tools** 分类的技能包（`AI-Musics-Tools/AI-Musics-Skills/`）。
当前阶段：**🟡 规划中**，可运行代码尚未落地。

## 定位
音乐制作：旋律生成、伴奏编配、歌词创作、混音母带、风格迁移等。

## 当前状态
- `AI-Musics-Tools/Codes/` 尚未创建；
- 暂无采集 / 二创 / CLI，待按统一架构落地。

## 如何落地本分类
请用**全局脚手架技能** `ai-category-module-scaffold`（位于 `AI-WeMedia-Tools/AI-WeMedia-Skills/ai-category-module-scaffold/`）。它会产出采集 / 处理骨架、SQLite 持久化、mock 离线 pipeline + CLI、双风格结果排版模板，并内附三大已知坑及修复。

## 全局约定（落地时务必遵守）
- 代码统一放 `AI-Musics-Tools/Codes/`；
- 配置与数据库全局共享于 `AI-Global/`（Configs / Database）；
- 产物目录（如 `Musics/`、`OutMusics/`）加入 `.gitignore`，不入库；
- 文件 / 文件夹命名分隔符用「-」；
- `--mock` 离线可跑通全流程。

## 完成后
更新根 `README.md`「功能模块进度」表（🟡→🟢）与 `.workbuddy/memory/MEMORY.md`，提交并推 GitHub。
