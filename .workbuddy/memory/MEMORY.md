# AI-WeMedia-Tools 长期规划（产品记忆）

> 本文件为项目长期记忆，与仓库根目录 `README.md` 保持同步。每次规划变更请同步更新两处。

## 项目定位
面向自媒体创作者的 AI 工具箱。把文章、图片、音乐、关键词、声音、视频、网页等创作环节，逐步沉淀为可用工具，最终整合为统一的「AI-WeMedia-Tools（自媒体工具箱）」大型软件。

## 目录结构（7 个分目录）
- `AI-Articles-Tools`：文章优化及二创
- `AI-Images-Tools`：图片制作及效果
- `AI-Musics-Tools`：音乐制作
- `AI-Prompts-Tools`：关键词及关键词反推（含 `Prompts-Back-Calculate/` 已有初步实现）
- `AI-Sounds-Tools`：声音及声效制作
- `AI-Videos-Tools`：视频及教学制作
- `AI-Webs-Tools`：网站页面制作

## 演进路线图（三阶段）
1. **阶段一 Skills 技能化（当前）**：逐个分目录落地，功能先以 WorkBuddy Skills 技能形式实现，验证可行性、积累经验。
2. **阶段二 独立小软件**：Skills 成熟后沉淀为可独立运行的小软件。
3. **阶段三 整合大型工具箱**：所有小软件整合进统一的「AI-WeMedia-Tools（自媒体工具箱）」大型软件。

## 版本管理
- 仓库：https://github.com/robinlincn/AI-WeMedia-Tools （SSH: git@github.com:robinlincn/AI-WeMedia-Tools.git）
- 规划同步保存于 README.md 与 .workbuddy/memory/MEMORY.md。
- 已通过 .gitignore 排除 node_modules / videos / frames / OutVideos / logs 等大体积产物（Prompts-Back-Calculate 内 node_modules 达 7.3GB，严禁提交）。

## 模块进度
- AI-Prompts-Tools：🟢 进行中（Prompts-Back-Calculate 已有代码）
- 其余 6 个：🟡 规划中，待落地 Skills
