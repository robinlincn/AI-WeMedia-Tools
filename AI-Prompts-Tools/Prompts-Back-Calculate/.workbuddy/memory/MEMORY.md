# 项目长期记忆 - AI视频提示词反推

> 这是项目的"长期记忆"，跨 session 保留。请每个 AI 助手在开始工作前读取。
> 工作日志在 `2026-07-07.md` / `2026-07-08.md` 单独按日保留。

---

## 🎯 项目目标

对视频文件（抖音/快手/YouTube/本地）做**反推提示词**（video → structured prompts），可用于：
- 复刻视频画面给 AI 绘图/视频工具
- 提取分镜、字幕文案、风格标签
- 短视频内容结构化分析

## 📂 项目结构

```
E:\自媒体\AI视频\AI视频提示词反推\
├── videos/                  ← 视频原文件
├── frames/                  ← 抽帧目录（按视频分目录）
│   ├── f_000.jpg ~ f_*.jpg  ← 旧版（深点AI）
│   └── dy2_20260708/        ← 抖音视频抽帧
├── VideoPrompt/             ← 反推提示词输出（.md）
│   └── {标题}-提示词反推-{YYYYMMDD-HHmm}.md
├── .workbuddy/
│   ├── memory/              ← 本目录 + 按日工作日志
│   │   ├── MEMORY.md        ← 本文件
│   │   ├── 2026-07-07.md
│   │   └── 2026-07-08.md
│   └── skills/              ← 项目内技能
│       └── douyin-download-correct/   ← 抖音下载（项目优化版）
│           ├── SKILL.md
│           └── scripts/download_douyin.py
└── logs/                    ← 杂项日志
```

## 🛠️ 工具链环境（已安装）

| 工具 | 路径 | 版本 |
|------|------|------|
| **ffmpeg/ffprobe** | `C:\ffmpeg\bin\` | 8.1.2 |
| **yt-dlp** | `D:\Software\Python\Python312\Scripts\yt-dlp.exe` | 2026.07.04 |
| **Python** | `D:\Software\Python\Python312\python.exe` | 3.12.7 |
| **Managed Python venv** | `C:\Users\robinlin\.workbuddy\binaries\python\envs\default\Scripts\python.exe` | 3.13.12（已装 websockets 16.0）|

PATH 已写入用户级：`C:\ffmpeg\bin` + `D:\Software\Python\Python312\Scripts`

## 📏 命名规范

### 视频文件
```
抖音-{标题前30字}-{YYYYMMDD}.mp4
```
例：`抖音-让ClaudeCode替你干一天的4个习惯-20260708.mp4`

### 抽帧目录
```
frames/{prefix}_{YYYYMMDD}/{prefix}_{0001..NNNN}.jpg
```
例：`frames/dy2_20260708/dy2_0001.jpg ~ dy2_0052.jpg`

### 反推提示词文件
```
VideoPrompt/{标题}-提示词反推-{YYYYMMDD-HHmm}.md
```
例：`深点AI宣传视频6-提示词反推-20260707-1538.md`

### 抽帧目录
```
frames/{prefix}_{YYYYMMDD}/{prefix}_{0001..NNNN}.jpg
```
**prefix = videos 视频名的"标题部分"**（去掉"抖音-"前缀和".mp4"后缀），与 videos 文件名一一对应。

例：
- videos/`抖音-让ClaudeCode替你干一天的4个习惯同样一个ClaudeCode-20260708.mp4`
- frames/`让ClaudeCode替你干一天的4个习惯同样一个ClaudeCode-20260708/让ClaudeCode..._0001.jpg ~ _0052.jpg`

### 抽帧策略（按视频时长）

| 视频时长 | 抽帧间隔 | 大概帧数 |
|---------|---------|---------|
| < 1 分钟 | `mod(n,30)` 1s/帧 | 30-60 张 |
| 1-5 分钟 | `mod(n,90-150)` 3-5s/帧 | 30-100 张 |
| 5-30 分钟 | `mod(n,150-300)` 5-10s/帧 | 50-150 张 |
| > 30 分钟 | `mod(n,600)` 20s/帧 | 视长度 |

**ffmpeg 命令模板**：
```bash
ffmpeg -y -i <input.mp4> \
  -vf "select='not(mod(n\,N))',scale=1280:-1" \
  -vsync vfr -q:v 2 \
  frames/{prefix}_%04d.jpg
```

⚠️ **ffmpeg 抽帧用 PowerShell 调**（沙盒环境下 bash 调 ffmpeg 可能丢中间产物）

## 🧠 关键技术经验（重要，跨 session 复用）

### 抖音下载：双资源问题（2026-07-08 教训）
**抖音同 video_id 在不同端点给不同资源**：
- **douyinvod.com** `media-video-avc1` → **长片无声**（1024×576 / 26:41 / 111MB / vid=`v0300fg*`）❌
- **aweme/v1/play** → **主片有声**（960×720 / 4:15 / 10MB / vid=`v0d00fg*`）✅

**判断标准**：`ffprobe` 看 `duration` + `nb_streams=2`（有音轨）
- 跟抖音 app 显示时长一致 + 有 aac 音轨 = 正确
- 时长 20+ 分钟 + 无音轨 = 错版（是 douyinvod 长片）

### 抖音下载：沙盒 IP 风控
- **沙盒出口 IP 是腾讯云机房**（120.226.x.x），被抖音生态全方位风控
- **短链** `v.douyin.com/xxx` → 302 到 iesdouyin → 200 OK SIZE=0 ❌
- **长链** `www.douyin.com/video/{id}` → iesdouyin 直接命中 → 拿 _ROUTER_DATA ✅
- m.iesdouyin.com → TCP 拒绝（HTTP=000）

### 抖音下载：bash 14KB buffer bug
- **现象**：`curl -o file URL` 写到 14KB 后报 `curl: (23) client returned ERROR on write of 14654 bytes`
- **解决**：用 PowerShell `Invoke-WebRequest -OutFile`（一次性写完整文件）

### 通用：HTTP 代理限速
- 本环境走代理，单连接被限速到 ~50KB/s（GitHub 完全不可达）
- **大文件下载姿势**：用 bash 后台作业 `( curl -r START-END -o part_i URL ) &` + `wait` 做 8 并发
- **Range 验证**：`curl -sI -H "Range: bytes=0-1024" URL` 看是否返 206 Partial Content

### 通用：f2 v0.0.1.7 抖音有 bug
- XBogus 算法 `md5_str_to_array` 在 hex 字符外越界
- 不要用 f2 跑抖音 API（除非升到修了的版本）

## 🎬 视频类型 ↔ 复刻工具矩阵

| 视频类型 | 典型特征 | 复刻工具 | 难度 | 工时 |
|---|---|---|---|---|
| **PPT 字幕流** | 深色底+大字+彩色卡片+字幕条 | **hyperframes** ⭐ | 中 | 1.5-2 天 |
| **同上传配音+纯字幕** | PPT 字幕流+口播 | claude-video-promo / hyperframes | 低 | 1 天 |
| **数据可视化** | 图表+数字动画 | remotion（图表生态强）| 中高 | 3-5 天 |
| **实拍+UI 录屏** | 真人+屏幕录制 | 摄像机+OBS+ffmpeg 合成 | 高 | 一周+ |
| **AI 生成视频** | Runway/Sora/Veo | 视频生成 API | 中 | 看模型 |
| **3D / VFX** | Three.js / Shader | remotion（3D 规则）/ Three.js | 高 | 一周+ |

**判断"原视频是否用代码工具做的"4 个信号**（**反向判断**）：
1. 字幕字体 = 平台生态标准字体（如抖音的思源黑体变种）→ 不是
2. UI/代码/终端内容 = 真实截图 → 不是
3. 段间切换 = 0.2-0.3s 硬切 + 简单淡入 → 不是（GSAP/Remotion 默认 spring 曲线）
4. N 张并列元素用 N 种不同主色 → 模板工具（剪映/PPT）的典型做法

## 🎯 工作流程（标准 SOP）

### 1. 下抖音视频（**v2.0 自动化全流程**）
```bash
# 老板只需发任意形式的链接（短链/长链/分享文本），一行命令搞定
python "E:\自媒体\AI视频\AI视频提示词反推\.workbuddy\skills\douyin-download-correct\scripts\download_douyin.py" "<URL或分享文本>"
```
→ 自动：智能解析 URL（短链跟 redirect / 长链直接）→ iesdouyin 拿 _ROUTER_DATA → PowerShell 下载 → ffprobe 校验 → 抽帧到 frames/ → 全套规范命名

### 2. 抽关键帧（如已下过视频，仅补抽帧）
```bash
# PowerShell 调 ffmpeg（避免 bash 14KB buffer bug）
powershell -Command "& 'C:\ffmpeg\bin\ffmpeg.exe' -y -hide_banner -loglevel warning -i <input.mp4> -vf \"select='not(mod(n\,N))',scale=1280:-1\" -vsync vfr -q:v 2 <output_pattern>"
```

### 3. 反推提示词
加载 `video-prompt-reverse` skill，喂 4-5 张/批给多模态模型分析 → 输出到 `VideoPrompt/`

### 4. 提交交付
- `present_files` 主交付物（mp4 / md）
- `Edit` 更新 `memory/{YYYY-MM-DD}.md` 简记做了什么
- 必要时 `Edit` 更新 `MEMORY.md` 沉淀新经验

## 🤖 与 AI 助手协作约定

- 用户称呼：**老板**
- 风格：**幽默但不贫嘴，靠谱但不死板**（来自 SOUL.md）
- 错误不藏：删文件前确认（避免 sandbox 异常丢两边）
- 重要决策：先沟通方案再执行（避免重复劳动）
- **跨目录操作安全姿势**：先 `cp` 再 `rm`，别直接 `mv` 到不同父目录

## 📞 项目级 Skills

| Skill | 用途 |
|-------|------|
| `douyin-download-correct` | 抖音无水印下载（含 PowerShell 兜底 + 智能 URL 解析）|
| `hyperframes-4habits`（项目内案例）| HyperFrames 复刻 4 习惯 demo，参考 `Codes/claude-code-4habits/` |

## 🎬 HyperFrames 复刻 SOP（PPT 字幕流视频，1-2 天出片）

**适用场景**：反推得到的纯字幕流/卡片/UI 模拟类视频（如"4 个习惯"）

### 4 步流程

| 步骤 | 命令 | 产出 |
|---|---|---|
| 1. 建项目 | `mkdir <project> && cd <project> && npm init -y && npm install hyperframes@0.7.42` | package.json + node_modules |
| 2. 写设计稿 | `design.md`（配色 / 字体 / 通用元素）| 一份 markdown 规范 |
| 3. 写 index.html | 根 composition（4-5 镜 / 30-60 秒）| src/index.html |
| 4. 渲染 mp4 | `cd src && npx hyperframes render --output xxx.mp4` | mp4（默认 30fps） |

### 4 个常见 lint 错（必避）

| 错误 | 修复 |
|---|---|
| `querySelector uses a template literal variable` | 改字符串拼接：`'[data-composition-id="' + name + '"]'` |
| `root_composition_missing_data_start` | 根 composition 加 `data-start="0"` |
| `font_family_without_font_face` | 加 `@font-face { font-family: "X"; src: local("X"); }`（系统字体用 `local()`）|
| `sub-composition timelines not registered` | 告警级，可忽略（场景切换靠 `hidden` 属性 + 根 tl.call）|

### 性能优化

- **多场景切换**：靠 JS `div.hidden = true/false` 切换，不用 CSS opacity
- **进场动画**：`gsap.from(el, { y, opacity: 0, duration: 0.6, ease: 'power3.out' })`（不同元素用不同 ease）
- **静态帧去重**：hyperframes 自动识别 60-80% 静态帧复用，1-3 分钟可渲染 40-120 秒 mp4
- **静态字体用 `src: local(...)` 兜底**：避免字体文件下载拖慢渲染

### 视频规格

- **正方形 1080×1080** —— 社交媒体（IG/小红书/朋友圈）通用
- **4:3 960×720** —— 抖音主片尺寸（如果要还原抖音原画风）
- **16:9 1920×1080** —— YouTube/B站 横屏

### 复刻一个视频的代码量

| 镜数 | HTML 行数 | 工时 |
|---|---|---|
| 1-3 镜（demo）| 200-400 | 1-2 小时 |
| 4-6 镜（短片）| 400-800 | 4-6 小时 |
| 10-17 镜（完整）| 800-1500 | 1-2 天 |

## 📞 全局可用的 skills（精选）

| Skill | 用途 |
|-------|------|
| `video-prompt-reverse` | 视频反推提示词（喂 17 张关键帧，按模板输出）|
| `video-frames` | ffmpeg 抽帧封装 |
| `claude-video-download` | yt-dlp 通用下载 |
| `douyin-downloader-skill` | 抖音下载（已验证长链路径可跑通）|
| `claude-video-caption` | Whisper 转字幕 |
| `claude-video-shorts` | 长视频抽短视频 |
| `claude-video-analyze` | FFprobe/VMAF 视频分析 |

## 🔄 实时更新规则

**本文件 + SKILL.md 必须随项目环境变化实时更新**：
- 工具链版本变更 → 更新"工具链环境"表
- 新踩坑 → 更新"关键技术经验"
- 新约定 → 更新"与 AI 助手协作约定"
- 新 skill → 更新"已有 skills"表
- 命名规范变更 → 更新"命名规范"

**更新频率**：每次任务有"复用价值"的新经验沉淀时，立即更新。

---

**维护者**：阿福 (WorkBuddy)
**最后更新**：2026-07-08
