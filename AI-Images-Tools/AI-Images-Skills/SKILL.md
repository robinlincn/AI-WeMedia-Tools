---
name: ai-images-tools
description: AI-Images-Tools（图片制作及效果）分类技能。当前为规划占位：文生图、图生图、风格滤镜、批处理等。当用户说"做图片/文生图/图生图/图片风格化/落地 AI-Images-Tools 模块"时触发，引导用全局脚手架技能 ai-category-module-scaffold 落地。
agent_created: true
---

# AI-Images-Tools 图片制作及效果（🟡 规划中）

本目录是 **AI-Images-Tools** 分类的技能包（`AI-Images-Tools/AI-Images-Skills/`）。
当前阶段：**🟡 规划中**，可运行代码尚未落地。

## 定位
图片制作及效果：文生图、图生图、风格滤镜、批量处理、智能扩图 / 抠图等。

## 当前状态
- `AI-Images-Tools/Codes/` 尚未创建；
- 暂无采集 / 二创 / CLI，待按统一架构落地。

## 如何落地本分类
请用**全局脚手架技能** `ai-category-module-scaffold`（位于 `AI-WeMedia-Tools/AI-WeMedia-Skills/ai-category-module-scaffold/`）。它会产出：
- 采集 / 处理骨架（对应图片即为生成 / 风格化 / 批处理）；
- SQLite 持久化（sources / outputs / media）；
- mock 离线 pipeline + CLI；
- 双风格结果排版模板（图片类可沿用头条 / 公众号风格的发布稿）；
- 并内附三大已知坑（mock 改写误判标题 / 头条移动版 SSR / 导语重复）及修复。

## 全局约定（落地时务必遵守）
- 代码统一放 `AI-Images-Tools/Codes/`；
- 配置与数据库全局共享于 `AI-Global/`（Configs / Database）；
- 产物目录（如 `Images/`、`OutImages/`）加入 `.gitignore`，不入库；
- 文件 / 文件夹命名分隔符用「-」；
- `--mock` 离线可跑通全流程。

## 完成后
更新根 `README.md`「功能模块进度」表（🟡→🟢）与 `.workbuddy/memory/MEMORY.md`，提交并推 GitHub。
