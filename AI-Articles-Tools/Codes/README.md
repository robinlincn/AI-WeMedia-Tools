# AI-Articles-Tools · 文章采集与二次创作

面向自媒体创作者的「内容采集 + 二次创作」工具。支持三种采集输入，并自动改写为
符合头条号发文规范的二创文章，全程数据持久化到本地 SQLite。

> 模块归属：`AI-WeMedia-Tools` 项目第一阶段（Skills 技能化）落地的第一个分类能力。

---

## 一、功能概览

### 内容采集模块（统一存入 `Articles/`）
| 输入类型 | 触发 | 文件夹命名 | 说明 |
| --- | --- | --- | --- |
| 链接采集 | `--type link` | `文章采集+标题+时间戳` | 抓取页面文案与图片，存储为 `.md` |
| 直接文案/MD | `--type text` | `原文案+标题+时间戳` | 接收原始文案或 `.md` 文件 |
| 视频采集 | `--type video` | `视频采集+标题+时间戳` | 提取口播音频与字幕文案 |

### 二次创作模块（输出到 `OutArticles/`）
- 标题 ≤30 字，与原标题明显不同，使用钩子技巧、有吸引力
- 根据内容自动生成配图，图注含中英文副标题，嵌入正文
- 排版符合头条号发文规范
- 与原文近似相似度 <10%（mock 模式标记为 0.05；真实模式用 4-gram Jaccard 近似估算，
  真正合规应由改写模型质量 + 嵌入/查重 API 保障）
- 去 AI 痕迹，自然语言风格
- 结果以 `.md` 存储，文件夹命名 `二创+标题+时间戳`

---

## 二、目录结构

```
AI-Articles-Tools/
├── Codes/                  # 本模块全部代码
│   ├── config.example.toml
│   ├── requirements.txt
│   ├── src/
│   │   ├── cli.py          # 命令行入口（collect / pipeline / create / list）
│   │   ├── config.py       # 配置加载（环境变量 > config.toml）
│   │   ├── db.py           # SQLite 持久化（sources / outputs / media）
│   │   ├── models.py       # 数据类
│   │   ├── collector/      # 三种采集器
│   │   │   ├── base.py     # 文件夹命名 / 清洗 / 落盘
│   │   │   ├── text.py     # 文案采集
│   │   │   ├── link.py     # 链接采集（requests + BeautifulSoup）
│   │   │   └── video.py    # 视频采集（yt-dlp + ffmpeg + ASR）
│   │   └── creator/        # 二次创作
│   │       ├── llm.py      # LLM 客户端（OpenAI 兼容 + mock）
│   │       ├── image.py    # 配图生成（mock 输出 SVG 占位）
│   │       ├── layout.py   # 头条号排版
│   │       └── rewrite.py  # 编排：标题/正文/配图/排版/入库
│   └── tests/
│       └── test_pipeline.py # 离线冒烟测试（mock）
├── Articles/               # 采集产物（本地运行生成，不入库）
└── OutArticles/            # 二创产物（本地运行生成，不入库）
```

---

## 三、安装与运行

```bash
# 1) 准备隔离 Python 环境（推荐，避免污染系统）
python -m venv <venv>
<venv>/Scripts/python -m pip install -r AI-Articles-Tools/Codes/requirements.txt

# 2) 配置（可选，mock 模式无需任何密钥）
cp AI-Articles-Tools/Codes/config.example.toml AI-Articles-Tools/Codes/config.toml
# 编辑 config.toml 填入 LLM / 图片 / ASR 的 base_url、api_key、model

# 3) 离线 mock 跑通全流程（无需 API key）
python -m src.cli pipeline --type text --input "你的原始文案..." --mock
```

> 提示：所有 `*API` 均兼容 OpenAI 协议，可指向 DeepSeek / SiliconFlow / 通义 / 本地模型等。
> 环境变量（`ARTICLES_LLM_API_KEY` 等）优先级高于 `config.toml`。

---

## 四、命令参考

```bash
# 采集 + 二创（一步到位）
python -m src.cli pipeline --type text  --input "文案..."           --mock
python -m src.cli pipeline --type link  --input https://example.com/a
python -m src.cli pipeline --type video --input https://douyin.com/x --mock
python -m src.cli pipeline --type video --input ./local.mp4          --mock

# 分步：先采集，再基于 source_id 二创
python -m src.cli collect --type text --input "文案"
python -m src.cli create  --source 1

# 查看采集源与二创产物
python -m src.cli list
```

`--config <path>` 可指定配置；`--mock` 强制离线模式。

---

## 五、测试

```bash
python AI-Articles-Tools/Codes/tests/test_pipeline.py
```

不依赖任何 API key 与网络，覆盖：文案/视频采集 → 二创全流程、标题长度、
配图嵌入、相似度阈值，以及「改写任务不被误判为标题任务」的回归断言。

---

## 六、实现说明与已知边界

- **相似度指标**：`similarity_estimate` 用 4-gram Jaccard 作为离线可跑的近似，
  真实生产应接入嵌入向量 / 查重 API，并以模型改写质量兜底。
- **配图**：`mock` 模式输出带图注的 SVG 占位图（AI 绘图模型对中文图注渲染不稳定，
  故真实模式也建议把中英文图注作为 `.md` 图注文字而非烧录进图片）。
- **ASR**：视频采集在 `mock` 模式返回占位文案；真实模式走 yt-dlp 下载 + ffmpeg
  抽音频 + ASR 转写。
- **路径**：产物默认落在 `AI-Articles-Tools/Articles` 与 `AI-Articles-Tools/OutArticles`，
  由配置 `paths.articles_dir` / `paths.out_dir` 与运行根目录（`AI-Articles-Tools`）决定。
