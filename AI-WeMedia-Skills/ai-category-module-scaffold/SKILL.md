---
name: ai-category-module-scaffold
description: 为 AI-WeMedia-Tools 项目脚手架一个新的自媒体分类能力模块（如 AI-Images-Tools、AI-Musics-Tools、AI-Videos-Tools、AI-Webs-Tools 等）。产出：采集器 + 二次创作（双风格排版）+ SQLite 持久化 + mock 离线 pipeline + CLI + 离线测试，全部代码落在对应分类目录的 Codes/ 下；配置与数据库全局共享于 AI-Global/。当用户说"搭建/落地 XX-Tools 模块""新增一个分类工具""给 AI-XXX-Tools 写采集与二创""脚手架一个自媒体分类能力"时触发。
agent_created: true
---

# AI 分类模块脚手架（ai-category-module-scaffold）

为 `AI-WeMedia-Tools` 仓库新增一个自媒体分类能力（文章/图片/音乐/声音/视频/网页/关键词…），
复用已落地的 `AI-Articles-Tools` 架构，保证各分类结构一致、可维护、可整合到未来的大型工具箱。

> 本技能沉淀自真实落地 `AI-Articles-Tools` 的全过程（含 3 个真实头条链接的采集/二创实测），
> 其中「三大已知坑」是反复踩过、已定位根因并修复的，新模块请直接规避。

## 何时使用
- 用户要在某个 `AI-*-Tools` 分类下新建功能模块
- 需要"采集/输入 → 处理/二创 → 持久化 → CLI → 离线测试"的完整骨架
- 希望不依赖任何 API key 即可本地跑通流程（mock 模式）

## 一、目录约定（必须遵守）

```
AI-WeMedia-Tools/                      # 项目根
├── AI-Global/                         # 全局共享资源（跨分类）
│   ├── Configs/                       #   config.toml（含密钥，gitignore）+ config.example.toml（入库）
│   └── Database/                      #   *.db（SQLite，gitignore）+ .gitkeep（入库）
├── AI-Articles-Tools/                # 某分类（文章）
│   ├── Codes/                         #   本分类全部代码
│   │   ├── config.example.toml        # （可选，仅本分类特有项；一般直接复用全局配置）
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── cli.py                 # argparse 子命令 collect/pipeline/create/list
│   │   │   ├── config.py              # AppConfig；load_config 默认读全局配置
│   │   │   ├── db.py                  # Database：sources / outputs / media 三表
│   │   │   ├── models.py              # CollectionResult / MediaItem / CreationResult
│   │   │   ├── collector/
│   │   │   │   ├── base.py            # 文件夹命名（前缀-标题-时间戳）、sanitize、save_md
│   │   │   │   ├── text.py            # 文案采集
│   │   │   │   ├── link.py            # 链接采集（移动版 SSR + 内联图提取）
│   │   │   │   └── video.py           # 视频采集（yt-dlp + ffmpeg + ASR）
│   │   │   └── creator/
│   │   │       ├── llm.py             # LLM 客户端（OpenAI 兼容 + mock）
│   │   │       ├── image.py           # 配图生成（mock 输出 SVG 占位）
│   │   │       ├── layout.py          # compose_markdown（头条）/ compose_wechat（公众号）
│   │   │       └── rewrite.py         # RewriteOrchestrator：标题/正文/配图/双风格排版/入库
│   │   └── tests/test_pipeline.py     # 离线冒烟测试（mock）+ 回归断言
│   ├── Articles/                      # 采集产物（本地生成，gitignore）
│   └── OutArticles/                   # 二创产物（本地生成，gitignore）
├── AI-Images-Tools/  …（其余分类同构）
└── …（共 7 个分类目录）
```

**关键原则**
- 分类代码统一放在 `<分类>/Codes/`，例如 `AI-Images-Tools/Codes/`
- `config.toml` 与 `*.db` **全局共享**于 `AI-Global/`，便于集中管理；各分类的 `Articles/OutArticles` 独立
- 数据持久化用**本地 SQLite**（不要联网数据库）
- 生成的 `Articles/`、`OutArticles/`、`*.db`、`config.toml` 必须加入仓库 `.gitignore`（本地保留、不入库）；`.gitkeep` 入库保证空目录留存

## 二、命名规范（分隔符用「-」）

| 类型 | 文件夹命名 | 文件名 |
| --- | --- | --- |
| 链接采集 | `文章链接采集-标题-YYYYMMDD_HHMMSS` | `<标题>.md` |
| 文案采集 | `原文案-标题-YYYYMMDD_HHMMSS` | `<标题>.md` |
| 视频采集 | `视频采集-标题-YYYYMMDD_HHMMSS` | `<标题>.md` |
| 二创产物 | `文章二创-标题-YYYYMMDD_HHMMSS` | `头条风格-标题-YYYYMMDD_HHMMSS.md`<br>`公众号风格-标题-YYYYMMDD_HHMMSS.md` |

- 时间戳格式 `YYYYMMDD_HHMMSS`（`base.py` 的 `TS_FMT = "%Y%m%d_%H%M%S"`）
- 标题用 `sanitize()` 清洗：替换 `\/ : * ? " < > |` 等非法字符，过长截断（≤40）
- 二创文件夹内含两份 md + `images/` 配图目录；两份 md 的配图用相对路径 `images/xxx.jpg` 引用，可直接复制进对应编辑器发布

## 三、全局配置 / 数据库模式（AI-Global）

**config.py 关键实现**
```python
# 项目根目录：config.py 位于 <root>/AI-Articles-Tools/Codes/src/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
GLOBAL_CONFIG_DIR = PROJECT_ROOT / "AI-Global" / "Configs"
GLOBAL_CONFIG = GLOBAL_CONFIG_DIR / "config.toml"
EXAMPLE_CONFIG = GLOBAL_CONFIG_DIR / "config.example.toml"

class AppConfig:
    db_path: Path = Path("AI-Global/Database/ai_articles.db")
    articles_dir: Path = Path("Articles")
    out_dir: Path = Path("OutArticles")

    def resolve_paths(self) -> "AppConfig":
        self.base_dir = self.base_dir.resolve()
        project_root = self.base_dir.parent          # 分类目录的父级 = 项目根
        if not self.db_path.is_absolute():
            self.db_path = (project_root / self.db_path).resolve()   # db 锚定项目根
        if not self.articles_dir.is_absolute():
            self.articles_dir = (self.base_dir / self.articles_dir).resolve()  # 产物锚定分类目录
        if not self.out_dir.is_absolute():
            self.out_dir = (self.base_dir / self.out_dir).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return self

def load_config(config_path=None):
    # 未指定时优先全局 config.toml，否则退回 config.example.toml
    path = GLOBAL_CONFIG if GLOBAL_CONFIG.exists() else EXAMPLE_CONFIG
    ...
```

**cli.py 关键实现**
```python
def _build(args):
    cfg = load_config(args.config)
    if args.mock:
        cfg.provider = "mock"           # --mock 强制离线，无需任何配置/密钥
    cfg.base_dir = ROOT                 # ROOT = Path(__file__).resolve().parents[2]（分类目录）
    cfg.resolve_paths()
    mock = args.mock or cfg.provider == "mock"
    ...
```
- 子命令必须 `parents=[common]` 才能继承 `--mock/--config`，否则子解析器不识别父参数
- `--mock` 时即使没有 `config.toml` 也能跑通全流程（LLM/Image 走确定性返回）

**config.example.toml 结构**
```toml
[llm]      base_url / api_key / model / temperature
[image]    base_url / api_key / model
[asr]      base_url / api_key / model      # 视频口播转写
[paths]    db / articles_dir / out_dir
[app]      provider = "openai" | "mock"
```
所有 `*API` 兼容 OpenAI 协议，可指向 DeepSeek / SiliconFlow / 通义 / 本地模型等。

## 四、SQLite 表结构（db.py）

```sql
CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source_type TEXT, title TEXT, url TEXT,
    folder_name TEXT, md_path TEXT, raw_text TEXT, created_at TEXT);
CREATE TABLE outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER, title TEXT,
    folder_name TEXT, md_path TEXT, similarity REAL, created_at TEXT);
CREATE TABLE media (
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_type TEXT, owner_id INTEGER,
    kind TEXT, path TEXT, caption_zh TEXT, caption_en TEXT, created_at TEXT);
```
`Database` 类 `CREATE TABLE IF NOT EXISTS`，路径随 `resolve_paths` 解析；入库在流程末尾。`media` 表记录配图的中英文副标题，供复盘与查重用。

## 五、二次创作编排（rewrite.py 要点）

- **标题**：`TITLE_SYSTEM` 要求 ≤30 字、钩子技巧、明显区别于原标题；`enforce_title_len()` 超限智能截断
- **正文改写**：`REWRITE_SYSTEM` 要求口语化、去 AI 腔、与原文明显不同
- **配图**：按段落切片 `_chunk(paras, size=2, cap=3)` 至多 3 张；`CAPTION_SYSTEM` 让 LLM 返回「中文图注 / 英文图注 / 绘图 prompt」三行
- **导语去重**（必做）：用 `_split_intro()` 只取首句作导语钩子，正文从首句之后接续，避免「导语=正文首句」重复
- **双风格排版**：`compose_markdown()`（头条：导语 + 加粗首句 + 分隔线 + 互动「点赞/评论/关注」）与 `compose_wechat()`（公众号：柔和留白、无分隔线、互动「点赞/在看/分享/关注」）
- **入库**：`mock` 相似度记为 0.05；真实模式用 `similarity_estimate()`（4-gram Jaccard 近似）。⚠️ 真正「相似度<10%」应接嵌入/查重 API，Jaccard 会把保留专名也计入重复、对忠实改写过度惩罚

## 六、⚠️ 三大已知坑（必须规避）

### 坑 1：mock 改写任务被误判成标题任务
- **现象**：二创正文整段变成标题文本「【干货】…」
- **根因**：mock 的 `_mock_reply` 用 `if "标题" in system:` 判定任务类型，而 `REWRITE_SYSTEM` 第 6 条含「**小标题**」三字 → 子串「标题」命中，改写被当成标题任务返回标题模板
- **✅ 修复**：判定标记改为标题任务独有的「**标题党**」（仅 `TITLE_SYSTEM` 含此词）。或显式传 `task` 参数区分，不要靠子串猜
- **回归测试**：断言正文出现改写内容、且标题不得作为正文段落出现

### 坑 2：头条桌面版是纯 JS 渲染壳，requests 抓不到正文
- **现象**：正文 0 字、标题退化成文章 ID、0 图
- **根因**：`www.toutiao.com/article/xxx` 是 JS 壳；`m.toutiao.com/i{id}/` 是**服务端渲染**，能拿到真实标题与正文
- **✅ 修复**：链接采集自动改写移动版地址 + 移动 UA + 标题去「- 今日头条」后缀
  ```python
  _TOUTIAO_RE = re.compile(r"(?:www\.)?toutiao\.com/(?:article/|i)?(\d{15,})")
  def _normalize_url(url):
      m = _TOUTIAO_RE.search(url)
      if m and "m.toutiao.com" not in url:
          return f"https://m.toutiao.com/i{m.group(1)}/"
      return url
  ```
- **正文提取**：`soup.find("article") or soup.find("main")` 为容器；按文档顺序 `_walk()` 保留 `h1-h6`/段落/列表/引用/内联图；正文插图多是**懒加载**（取 `data-src` 真地址，跳过 `src` 的 1×1 占位 gif）；过滤页脚/导航噪点（`_NOISE_HINTS`：打开App/相关推荐/…）；封面图走 `og:image`

### 坑 3：导语与正文首句重复
- **现象**：blockquote 导语和正文第一段首句一字不差，啰嗦
- **✅ 修复**：`_split_intro()` 只取首句（按句号切）作导语，正文从首句之后接续

## 七、落地步骤（建议顺序）

1. 建目录骨架（复制本技能的目录结构，或参考 `AI-Articles-Tools/Codes/`）
2. 写 `config.py`（全局路径解析）+ `config.example.toml`（若本分类无特殊项，可直接复用 `AI-Global/Configs/config.example.toml`）
3. 写 `db.py`（三表）+ `models.py`
4. 写 `collector/`：`base.py` → `text.py` / `link.py` / `video.py`（按需裁剪）
5. 写 `creator/`：`llm.py` → `image.py` → `layout.py`（双风格）→ `rewrite.py`（编排）
6. 写 `cli.py`（collect/pipeline/create/list + `--mock` + `parents=[common]`）
7. 写 `tests/test_pipeline.py`：mock 跑通 文案/视频 全流程 + 命名/双风格/回归断言
8. 跑通 mock：`python -m src.cli pipeline --type text --input "..." --mock`
9. 接真实 key（写 `AI-Global/Configs/config.toml` 或设环境变量）后跑真实链接/视频验证

## 八、验收清单

- [ ] `python tests/test_pipeline.py` 全绿，且含回归断言（正文非标题、双风格 md 存在、命名用 `-` 分隔）
- [ ] `python -m src.cli pipeline --type text --input "..." --mock` 端到端跑通
- [ ] 真实链接采集能抓到完整正文（验证坑 2 已规避）
- [ ] 真实二创：标题≤30字、正文口语化、配图带中英文图注、双风格 md 可直接复制发布
- [ ] 产物落在 `<分类>/Articles` 与 `<分类>/OutArticles`；库写入 `AI-Global/Database/`
- [ ] 更新根 `README.md`「功能模块进度」表（🟡规划中 → 🟢进行中）与 `.workbuddy/memory/MEMORY.md`

## 九、完成后

- 同步根 `README.md` 进度表 + `.workbuddy/memory/MEMORY.md`
- `git add` 代码/技能包/配置示例/记忆日志（**不要** add `config.toml`、`*.db`、`Articles/`、`OutArticles/`）
- `git commit` + `git push -u origin main`，保持 GitHub 版本一致

## 附：复用提示

- 本技能对应代码已在 `AI-Articles-Tools/Codes/` 完整落地（经真实 3 篇头条链接验证），新模块可直接 `cp -r` 后改分类名与采集/创作逻辑
- 环境：Python 3.13 托管 venv（`C:/Users/robinlin/.workbuddy/binaries/python/envs/default/Scripts/python.exe`）；依赖 requests/beautifulsoup4/lxml/toml/openai/yt-dlp；视频采集另需 ffmpeg + yt-dlp
