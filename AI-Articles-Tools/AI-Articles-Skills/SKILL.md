---
name: ai-articles-tools
description: 使用 AI-Articles-Tools 进行文章类内容的采集（链接/文案/视频）与二次创作（双风格排版：头条风格 + 公众号风格）。支持离线 mock 全流程（无需 API key），配置与数据库全局共享于 AI-Global/。当用户说"采集文章/文案/视频""改写/二创文章""生成头条风格/公众号风格""跑通文章工具流程""把这篇链接变成能直接发的稿子"时触发。
agent_created: true
---

# AI-Articles-Tools 文章采集与二创技能（ai-articles-tools）

本技能是 **AI-Articles-Tools（文章优化及二创）** 分类的「使用 / 操作」技能：指导如何运行该分类下的代码，把任意文章类素材（网页链接、纯文案、视频口播）采集下来并二次创作为**可直接复制发布**的头条风格 / 公众号风格稿件。

> 代码本体在 `AI-Articles-Tools/Codes/`（已落地、经 3 个真实头条链接验证）。
> 若要**新建其他分类模块**（图片/音乐/视频…），请用全局脚手架技能 `ai-category-module-scaffold`，不要本技能。

## 一、何时使用

- 用户给了一个**文章链接 / 文案 / 视频**，想要采集 + 改写；
- 用户要产出**可直接粘贴发布**的头条风格或公众号风格稿件；
- 用户想在**没有 API key** 的情况下先跑通整套流程（mock 模式）；
- 用户要排查采集不到正文、二创正文变标题、导语重复等问题（见第八节）。

## 二、代码位置与环境

```
AI-WeMedia-Tools/
├── AI-Global/                 # 全局共享：配置 + 数据库
│   ├── Configs/config.toml    # 真实密钥（gitignore，本地保留）
│   └── Database/ai_articles.db# SQLite（gitignore）
└── AI-Articles-Tools/
    ├── Codes/                 # 本分类全部代码（技能操作对象）
    │   ├── src/cli.py         # 命令行入口
    │   ├── src/collector/     # text / link / video 三种采集器
    │   └── src/creator/       # llm / image / layout / rewrite 二创编排
    ├── Articles/              # 采集产物（本地生成，gitignore）
    ├── OutArticles/           # 二创产物（本地生成，gitignore）
    └── AI-Articles-Skills/    # ← 本技能目录
```

**环境**：Python 3.13 托管 venv
`C:/Users/robinlin/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
依赖：`requests`、`beautifulsoup4`、`lxml`、`toml`、`openai`；（视频采集另需 `yt-dlp` + `ffmpeg`）

运行入口统一用模块方式：`python -m src.cli <子命令>`，所有命令在 `AI-Articles-Tools/Codes/` 目录下执行。

## 三、全局配置与数据库（AI-Global）

- 真实密钥写 `AI-Global/Configs/config.toml`（已被 `.gitignore` 排除，不会入库）；
- 没有 `config.toml` 也能跑：加 `--mock` 走确定性离线返回；
- 数据库 `AI-Global/Database/ai_articles.db` 跨分类共享，文章模块写入 `sources / outputs / media` 三表；
- 配置项：`[llm]`（OpenAI 兼容，可指向 DeepSeek / SiliconFlow / 通义 / 本地）、`[image]`、`[asr]`（视频口播转写）、`[paths]`、`[app] provider = "openai" | "mock"`。

## 四、快速开始（mock 离线全流程，无需任何 key）

```bash
cd AI-Articles-Tools/Codes

# 文案：采集 + 二创（头条/公众号双风格），纯离线
python -m src.cli pipeline --type text --input "这里放你的原始文案……" --mock

# 视频：采集 + 二创（口播转写走 mock）
python -m src.cli pipeline --type video --input https://douyin.com/xxx --mock
python -m src.cli pipeline --type video --input ./local.mp4           --mock

# 链接：想跑真实网络内容，去掉 --mock 并先配置好 config.toml
python -m src.cli pipeline --type link --input https://www.toutiao.com/article/xxxx/
```

跑完会打印：采集文件夹、`source_id`、二创文件夹、头条风格 MD 路径、公众号风格 MD 路径、配图张数。

## 五、命令参考

| 子命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `collect` | 仅采集，不二创 | `--type text\|link\|video`、`--input <URL/路径/文案>`、`--title`（可选） |
| `pipeline` | 采集 + 二创 一步到位 | 同上 |
| `create` | 对**已有**采集源做二创 | `--source <source_id>` |
| `list` | 列出所有 sources / outputs | — |

公共参数（所有子命令继承）：
- `--mock`：强制离线，LLM / 图片 / ASR 全部走确定性返回，**无需任何 API key**；
- `--config <路径>`：指定 config.toml（默认读全局 `AI-Global/Configs/config.toml`，缺失则退回 `config.example.toml`）。

分步示例：
```bash
python -m src.cli collect  --type text --input "文案"
python -m src.cli create   --source 1      # 用上一步的 source_id 二创
python -m src.cli list                    # 查看全部采集源与二创产物
```

## 六、产物结构与命名规范（分隔符「-」）

采集产物（`AI-Articles-Tools/Articles/`）：
```
文章链接采集-标题-YYYYMMDD_HHMMSS/   ← 链接
原文案-标题-YYYYMMDD_HHMMSS/         ← 文案
视频采集-标题-YYYYMMDD_HHMMSS/       ← 视频
    └── <标题>.md
```

二创产物（`AI-Articles-Tools/OutArticles/`）：
```
文章二创-标题-YYYYMMDD_HHMMSS/
    ├── 头条风格-标题-YYYYMMDD_HHMMSS.md
    ├── 公众号风格-标题-YYYYMMDD_HHMMSS.md
    └── images/                         ← 配图（相对路径引用，可直接复制进编辑器）
```
时间戳格式 `YYYYMMDD_HHMMSS`；标题经 `sanitize()` 清洗（替换非法字符、≤40 字）。两份 md 的配图用相对路径 `images/xxx.jpg` 引用，复制整份文件夹进对应编辑器即可发布。

## 七、双风格排版差异（贴合真实平台样式）

排版参考了 m.toutiao.com 移动端真实文章（<strong> 加粗位置、段落字数、文末互动语）和微信公众号编辑器粘贴效果，由 `src/creator/layout.py` 的 `compose_markdown` / `compose_wechat` 实现。

**头条风格（`compose_markdown`）**：
- 标题 H1 + 开头强钩子（**加粗**的导语，点出痛点/反差）；
- 段落短小（30~100 字），段间空行；每段首句自动加粗吸引首屏；
- 关键名词（项目名、功能名）**加粗**对应原文 `<strong>`；
- 配图居中，前后各空一行（Markdown 标准），图注「中文 / 英文」对照；
- 文末固定强引导句（**加粗**）："好了，分享到这里，希望对你有所启发和帮助。觉得不错可以点个赞、转发给需要的朋友，关注我，后续持续分享更多干货~"；
- 不强制分隔线（头条原文通常不用）。

**公众号风格（`compose_wechat`）**：
- 标题 H1（编辑器自动转大字号）+ 开头整段加粗作为引言小标题；
- 段间**双空行**留白（公众号阅读节奏舒缓）；关键句加粗；
- 配图后双空行（避免被编辑器挤压）；图注对照；
- 文末固定引导卡片："> ━━━━ 感谢阅读 ━━━━" + "> 互动语"（点赞 / 在看 / 分享 / 关注）。

两者正文同源改写，标题独立生成（≤30 字、钩子技巧、明显区别于原标题）；
配图按段落切片至多 3 张，每张带「中文图注 / 英文图注 / 绘图 prompt」三行（mock 模式为占位 SVG，真实模式为 PNG）。

### ⚠️ 已知坑 4：采集 md 图片丢图
- **现象**：采集下来的 md 在编辑器里看不到最后几张内联图片。
- **根因**：原 `_render` 只在图片块后补一行空行，**图片前**没有空行，Markdown 渲染器会把图片当成上一段正文的链接文本，导致最后一张图必丢。
- **✅ 现状**：已在 `_render` 里给 `img` 块**强制**补图前空行（`out[-1] != ""` 时追加），现在所有图片在 Typora / VS Code / GitHub 预览都正常显示。

### ⚠️ 已知坑 5：md 复制到第三方编辑器图片"Load image failed"
- **现象**：采集的 md 用相对路径 `images/xxx.jpg`，在 Typora / VS Code 本地打开正常；复制到飞书、Notion、自媒体工具等**第三方编辑器**时，编辑器无法访问本地 `images/` 文件夹，所有图片报 "Load image failed" / "Embed Link"，原 CDN URL 也可能失效。
- **根因**：相对路径只能跟随整份文件夹一起移动；一旦 md 被单独复制（粘贴正文 / 单独上传），图片就丢了。
- **✅ 现状**：`LinkCollector.collect()` 已默认开启 `embed_inline=True`，`_render` 把图片 base64 内联为 `data:image/png;base64,...` 写入 md，**产物 md 自包含**，复制到任何编辑器都能直接显示图片。代价是 md 体积会从 KB 级涨到 MB 级（与原图总和相当），单图 >5MB 走兜底（仍写相对路径）。本地 `images/` 文件夹仍保留，方便用户二次编辑。


### 提示词母版
- 改写 / 标题 / 图注三套 system 提示词统一从 `AI-Articles-Tools/AI-Articles-Prompts/Role.md` 读取（`src/creator/rewrite.py` 启动时加载，作为角色定位追加在 system 末尾）。
- 用户改 Role.md 即可让后续所有二创沿用新的角色风格；保留原有硬编码 system 里的格式约束（≤30 字标题、相似度 ≤10%、去 AI 腔等）。
- **注意**：Role.md 内不要写"标题党"这个字面词——`src/creator/llm.py` 的 mock 用 `"标题党" in system` 判定标题任务分支，注入后会把改写误判为标题任务。已统一使用"标题感"代替。


> **Fallback 链（按顺序找第一个存在且非空的文件）**：1) `AI-Global/Prompts/Role.md`（全局共享，用户维护点） → 2) `AI-Articles-Tools/AI-Articles-Prompts/Role.md`（分类私有，回退）。改 Role.md 时优先改全局版。

### 本地产物清理
- 采集 + 二创产物（base64 内嵌图后单篇可达 MB）已通过 `.gitignore` 排除，但仍占本地磁盘。
- 工具：`scripts/cleanup_local_products.py`，默认清 5 天前，支持 `--dry-run` / `--days N` / `--yes`；作用域仅限 `AI-Articles-Tools/Articles/` 与 `AI-Articles-Tools/OutArticles/`。
## 八、⚠️ 已知坑与排错（务必先看）

### 坑 1：二创正文整段变成标题文本
- **现象**：输出 md 里正文是一句「【干货】…」式标题党话术。
- **根因**：mock 的 `_mock_reply` 用子串 `"标题" in system` 判定任务，而 `REWRITE_SYSTEM` 含「小标题」三字 → 改写被误判成标题任务。
- **✅ 现状**：已修复，判定标记改为标题任务独有的「标题党」。若你改 prompt 复现，务必用专属标记或显式 `task` 参数区分，别靠子串猜。

### 坑 2：头条桌面版是 JS 渲染壳，抓不到正文
- **现象**：正文 0 字、标题退化成文章 ID、0 图。
- **根因**：`www.toutiao.com/article/xxx` 是 JS 壳；`m.toutiao.com/i{id}/` 才是服务端渲染，能拿到真实标题与正文。
- **✅ 现状**：链接采集已自动改写移动版地址 + 移动 UA + 标题去「- 今日头条」后缀。其他站点若也 0 文本，优先怀疑 SSR / 懒加载（`data-src` 取真图、跳过 1×1 占位 gif）。

### 坑 3：导语与正文首句重复
- **现象**：blockquote 导语和正文第一段首句一字不差。
- **✅ 现状**：`_split_intro()` 只取首句作导语钩子，正文从首句之后接续，已修复。

## 九、接真实 key 验证（可选）

1. 在 `AI-Global/Configs/config.toml` 填好 `[llm]/[image]/[asr]`（或设环境变量）；
2. 跑真实链接 / 视频，去掉 `--mock`；
3. 验收：标题 ≤30 字、正文口语化去 AI 腔、配图带中英文图注、双风格 md 可直接复制发布；
4. 产物落在 `Articles/OutArticles`，库写入 `AI-Global/Database/`。

> 相似度：mock 记为 0.05；真实模式用 4-gram Jaccard 近似（会把保留专名也计入重复，对忠实改写偏严）。真要「相似度 <10%」应接嵌入 / 查重 API。

## 十、交付与版本管理

- 技能只沉淀「怎么用 / 怎么排错」，代码在 `AI-Articles-Tools/Codes/`；
- 提交时 **不要** add `config.toml`、`*.db`、`Articles/`、`OutArticles/`（均 gitignore）；
- 改了本技能或代码后，`git commit` + `git push -u origin main` 保持 GitHub 一致；
- 进度同步更新根 `README.md`「功能模块进度」表与 `.workbuddy/memory/MEMORY.md`。
