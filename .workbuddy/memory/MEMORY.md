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
- AI-Articles-Tools：🟢 进行中（采集[链接/文案/视频]+二创[标题/正文/配图/头条排版]，代码见 `AI-Articles-Tools/Codes`，SQLite 持久化）
- AI-Prompts-Tools：🟢 进行中（Prompts-Back-Calculate 已有代码）
- 其余 5 个：🟡 规划中，待落地 Skills

## 技能包布局约定
- **每个分类的使用/操作技能就近放在该分类文件夹内**：`<分类>/AI-<分类>-Skills/SKILL.md`（如 `AI-Articles-Tools/AI-Articles-Skills/SKILL.md`）。代码本体在对应 `<分类>/Codes/`，技能只沉淀方法论与避坑。
- **跨分类的「脚手架」元技能保留在 `AI-WeMedia-Skills/ai-category-module-scaffold/`**：用于为任一新分类生成完整模块骨架，不属于任何单一分类。
- 各分类占位技能（Images/Musics/Sounds/Videos/Webs）均为 🟡 规划中，引用脚手架技能落地；Articles 为 🟢 完整可用，Prompts 为 🟢 进行中（含 Prompts-Back-Calculate）。

## 关键技术约定（AI-Articles-Tools）
- 分类代码统一放在对应分类目录的 `Codes/` 子目录（如 `AI-Articles-Tools/Codes`）。
- 数据持久化用本地 SQLite（`src/db.py`：sources/outputs/media 三表）。
- 离线 mock 模式：LLM/Image 走确定性返回，`--mock` 或 `provider="mock"` 即可跑通全流程，无需 API key。
- ⚠️ 已知坑：mock `_mock_reply` 用 `"标题" in system` 判定标题任务，但 `REWRITE_SYSTEM` 含「小标题」会误判——已改为用独有的「标题党」标记判定。

## 2026-07-16 AI-Articles-Tools 排版迭代

### 真实链接端到端验证
- 跑通真实头条链接 https://www.toutiao.com/article/7662722579030966811/（港大开源VideoRAG），全程不依赖 mock。
- LLM：DeepSeek 真实 key（`config.toml` 里的 `deepseek-v4-flash` 模型名疑似笔误但实测可用）；Image：agnes-image-2.1-flash 真实接口。
- 采集：source_id=14/15，正文 + 6 张原图入库；
- 二创：output_id=11/12，新标题 25 字 ≤ 30，相似度 15.49%（仍在 4-gram Jaccard 偏严区间），3 张真实 PNG 配图入库。

### Bug 修复
- **采集 md 图片丢图**：根因是 `src/collector/link.py` 的 `_render()` 给图片块**只补图后空行、没补图前空行**，导致 Markdown 标准下图片被当成上一段文本的链接，末几张图必丢。修复：图块前若 `out[-1] != ""` 则强制补空行。
- 顺手发现：PowerShell GBK 控制台跑 CLI / 测试时，`print("⚠️")` / `print("✅")` 会 UnicodeEncodeError 崩溃（不影响产物和入库，仅打印报错）。

### 双风格排版重写（src/creator/layout.py）
参考 m.toutiao.com 移动端真实样式（抓取 7662722579030966811 的 article HTML：22 个 <p>、4 个 <strong>、1 个 <br>，无花哨 div/span），以及公众号编辑器粘贴通用规范，重写 `compose_markdown` 与 `compose_wechat`：

- **头条风格**：H1 + 加粗导语钩子 + 短段 + 每段首句加粗 + 关键名词加粗 + 配图前后各空一行 + 文末强引导句加粗；
- **公众号风格**：H1 + 整段加粗引言 + 段间双空行 + 关键句加粗 + 配图后双空行 + 文末引导卡片 `> ━━━━ 感谢阅读 ━━━━`；
- `_bold_lead()` 兜底：长段无终止符 → 整段加粗（避免漏钩子）；
- CTA 默认文案改成贴近头条原文与公众号常见口吻的固定句式。

### 三处文档同步
- 根 `README.md`：进度行 + 更新日志（2026-07-16）已同步；
- `AI-Articles-Tools/AI-Articles-Skills/SKILL.md` 第七节已重写，并新增"⚠️ 已知坑 4：采集 md 图片丢图"及修复说明；
- 本长期记忆文件新增本章节。

### 待办
- 跑通 `tests/test_pipeline.py` 全部绿（已验证）。
- 真实链接跑完后产物已落入 `Articles/` 与 `OutArticles/`，均 gitignore 不入库；
- 仍未提交 git（等用户确认）。

## 2026-07-16 二次迭代：采集 md 图片 base64 内嵌

### 问题
- 用户反馈：采集下来的 md 复制到第三方编辑器（飞书、Notion、自媒体工具）后图片报 "Load image failed" / "Embed Link: images/img_3.jpg"。
- 之前的修复只补了图片前后空行，让本地打开 OK；但**相对路径无法跨域传输**，第三方编辑器从它自己服务器抓不到本地 `images/` 里的文件。

### 解法
- 改 `src/collector/link.py`：
  - 新增 `_embed_data_url()`：读本地图片 → base64 → `data:image/<mime>;base64,...`；
  - `_render()` 加 `embed_inline` 参数，开启时图片用 data URL；
  - `collect()` 调用前设置 `self._current_folder` 并传 `embed_inline=True`（采集默认开启）；
  - 用 `glob("stem.*")` 匹配实际落盘文件（绕开 `_download_one` 按 Content-Type 重写扩展名导致的不一致）。
- 兜底：单图 >5MB 走相对路径（避免 md 爆炸且部分编辑器有大小限制）。

### 验证
- 重跑 `collect --type link`：md 大小 3KB → 2.3MB（含 6 张原图 base64），所有图片行 `![]`(data:image/png;base64,...)。
- `tests/test_pipeline.py` 仍全绿（mock 不走 link.collect 的图片下载路径）。
- 产物在 `AI-Articles-Tools/Articles/`（gitignore），体积增大但不入库。

### 同步
- `AI-Articles-Skills/SKILL.md` 新增"⚠️ 已知坑 5"及修复说明。
- 本长期记忆新增本章节。

## 2026-07-16 三次迭代：Role.md 注入二创

### 改动
- `AI-Articles-Tools/AI-Articles-Prompts/Role.md` 优化（1084 字节 → 2513 字节）：
  - 修正 Markdown 标题层级、加粗关键约束、加 frontmatter 说明用途；
  - 把"标题党"改成"标题感"——绕开 `llm.py` mock 的 `"标题党" in system` 判定陷阱（坑6）；
  - 强化"加钩子 + 加血肉 + 口语化 + ≤30 字标题"等可执行要点。
- `src/creator/rewrite.py` 启动时读 Role.md 并拼接到 TITLE_SYSTEM / REWRITE_SYSTEM / CAPTION_SYSTEM 末尾；
  - `_ROLE_MD_PATH = parents[3] / "AI-Articles-Prompts" / "Role.md"`；
  - 文件缺失/为空时静默跳过，不阻塞 pipeline。

### 验证
- 真实链接 7662722579030966811 重跑：output_id=14，新标题"港大开源VideoRAG：别拖进度条，直接和AI聊长视频"（22 字），相似度 12.19%；
- 对比前几次产物：本次二创明显出现"金鱼脑"等原创比喻、"你/咱们"等口语化表达，符合 Role.md 强调的"加血肉+去 AI 腔"；
- `tests/test_pipeline.py` 全绿（mock 判定未被 Role.md 误触发）。

### 同步
- `AI-Articles-Skills/SKILL.md` 新增"提示词母版"章节，说明 Role.md → system 注入链路；
- 本长期记忆新增本章节。
