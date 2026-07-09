---
slug: douyin-download-correct
name: douyin_download_correct
display_name: 抖音视频下载（项目优化版）
description: |
  抖音无水印视频下载器，**针对本项目（E:\自媒体\AI视频\AI视频提示词反推）环境优化**。

  解决以下踩坑：
  1. 沙盒出口 IP（腾讯云机房 120.226.x.x）被抖音生态（iesdouyin / m.iesdouyin / www.douyin）全方位风控
  2. 抖音同 video_id 在 douyinvod.com / aweme/v1/play 两个端点给**不同资源**（前者长片无音轨，后者主片有声）
  3. bash 工具 `> file` 写大文件 14KB buffer 死锁（curl exit 23）
  4. f2 / yt-dlp 等通用库因云 IP 风控 + 算法过期无法跑通

  **核心方法**：长链 `www.douyin.com/video/{video_id}` → iesdouyin share 页（长链直接命中不过 301 跳短链，避云 IP 风控）→ 解析 `_ROUTER_DATA` → 拿无水印 play_url → curl/PowerShell 下载。

  当用户提到"下抖音"、"抖音无水印"、"解析视频"、"下载视频"，或直接发送抖音分享链接时触发。
version: "2.0"
author: WorkBuddy（项目内）
base_dir: douyin-download-correct
trigger:
  - 下载抖音
  - 抖音无水印
  - 解析视频
  - 抖音链接
  - 抖音视频
trigger_keywords:
  - 抖音
  - douyin
  - iesdouyin
allowed_intents:
  - video_download
  - content_extract
parameters:
  - name: share_link
    type: string
    description: 抖音分享链接（短链 v.douyin.com/xxx 或长链 www.douyin.com/video/{id}）
    required: true
  - name: output_dir
    type: string
    description: 输出目录，默认 `E:\自媒体\AI视频\AI视频提示词反推\videos`
    required: false
  - name: filename
    type: string
    description: 自定义文件名（可选，默认按规范生成：抖音-{标题}-{YYYYMMDD}.mp4）
    required: false
  - name: keep_douyinvod_fallback
    type: boolean
    description: 主流程失败时是否尝试 douyinvod.com CDN（注意：返回的是长片无音轨，不是主片；默认 False）
    required: false
    default: false
supported_tools:
  - Bash
  - PowerShell
  - Read
  - Write
  - Edit
---

# 抖音视频下载（项目优化版）— douyin-download-correct

## 🎯 核心特性（v2.0）

| 特性 | 说明 |
|------|------|
| **环境适配** | 适配沙盒 IP 风控 + bash buffer bug + Windows 路径 |
| **路径判断** | 短链走云 IP 失败；长链 `www.douyin.com/video/{id}` 可绕过风控 |
| **智能 URL** | 长链直接走；短链通过 `r.url` 跟 redirect 拿 video_id（即使 iesdouyin 返空）|
| **音轨保证** | 拿主片有声版（aweme/v1/play），不是 douyinvod 长片无音轨 |
| **FFprobe 校验** | 下载后自动校验：duration + nb_streams=2 = 正确 |
| **自动抽帧** | 抽到 `frames/{视频标题}-{日期}/`，文件命名同 prefix |
| **标题智能截断** | 按"第一个强标点 → 第一个逗号 → 50 字"层层切，干净不截词 |
| **失败兜底** | iesdouyin 拿不到时明确提示用 Chrome DevTools 抓源 |
| **命名规范** | 自动生成 `抖音-{标题}-{YYYYMMDD}.mp4` |

## 📂 目录结构

```
douyin-download-correct\
  ├── SKILL.md           ← 本文件
  └── scripts\
      └── download_douyin.py   ← 核心下载脚本（自给自足）
```

## 🚀 使用方法

### 命令行调用

```bash
# 单个下载（自动保存到默认 videos/）
python "E:\自媒体\AI视频\AI视频提示词反推\.workbuddy\skills\douyin-download-correct\scripts\download_douyin.py" "https://www.douyin.com/video/7649942475087416614"

# 指定保存目录
python "...\download_douyin.py" "https://v.douyin.com/xxxxxx" "E:\其他目录"
```

### Python 调用

```python
import subprocess, sys
script = r"E:\自媒体\AI视频\AI视频提示词反推\.workbuddy\skills\douyin-download-correct\scripts\download_douyin.py"
subprocess.run([sys.executable, script, "https://www.douyin.com/video/7649942475087416614"])
```

### 智能调用（AI 助手）

当用户在对话中说"下这个抖音视频 [URL]"，AI 应：
1. 加载本 skill
2. 调 `download_douyin.py` 下载到 `videos/`
3. 跑 ffprobe 校验（有音轨 + 4:15 量级时长）
4. 跑 ffmpeg 抽关键帧到 `frames/{prefix}_{YYYYMMDD}/`
5. 提示用户："✅ 下载完成，文件位置 X，参数 Y"

## 🛠️ 工作原理

### 流程图

```
用户分享链接（v.douyin.com/xxx 或 www.douyin.com/video/{id}）
  ↓
1. URL 类型判断
  ├─ 长链 www.douyin.com/video/{id} → 直接进入
  └─ 短链 v.douyin.com/xxx → 尝试 302 重定向（沙盒可能失败）→ 失败提示用户用长链
  ↓
2. GET https://www.iesdouyin.com/share/video/{id}/
  （mobile Android Chrome 116 UA + Referer 抖音移动端）
  ↓
3. 正则提取 window._ROUTER_DATA JSON
  ↓
4. 解析 loaderData → videoInfoRes.item_list[0].video.play_addr.uri
  ↓
5. 构造无水印源：https://www.douyin.com/aweme/v1/play/?video_id={uri}
  ↓
6. 用 PowerShell Invoke-WebRequest 下载（绕开 bash 14KB buffer bug）
  ↓
7. ffprobe 校验：nb_streams=2（video + audio）+ duration < 10min
  ↓
8. 重命名为规范文件名：抖音-{标题（按第一个逗号切）}-{YYYYMMDD}.mp4
  ↓
9. 抽帧到 frames/{标题}-{日期}/ 目录，文件名同 prefix
```

### 关键 Headers

```python
{
  "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
  "Referer": "https://www.douyin.com/?is_from_mobile_home=1&recommend=1"
}
```

## ⚠️ 已踩坑 & 解决（必读）

### 坑 1：沙盒 IP（腾讯云机房）被抖音生态风控
- **现象**：短链 `v.douyin.com/xxx` → 302 到 iesdouyin → 200 OK SIZE=0；m.iesdouyin.com → TCP 拒绝
- **解决**：用长链 `www.douyin.com/video/{id}` 直接命中 iesdouyin，绕开短链 301 跳短链的云 IP 风控

### 坑 2：bash `> file` 写大文件 14KB buffer 死锁
- **现象**：`curl -o file URL` 写到 14KB 后报 `curl: (23) client returned ERROR on write of 14654 bytes`
- **解决**：用 PowerShell `Invoke-WebRequest -OutFile` 一次性写完整文件
- **本 skill 已内置**：下载核心步骤全部走 PowerShell

### 坑 3：抖音同 video_id 给不同资源
- **现象 1**：douyinvod.com `media-video-avc1` 给**长片无音轨**（1024×576 / 26:41 / 111MB / vid=`v0300fg*`）
- **现象 2**：aweme/v1/play 给**主片有声**（960×720 / 4:15 / 10MB / vid=`v0d00fg*`）
- **解决**：默认走主片路径（aweme/v1/play）；用户需要长片时再走 douyinvod

### 坑 4：f2 v0.0.1.7 X-Bogus 算法 bug
- **现象**：`md5_str_to_array` 在 hex 字符外越界，导致 f2 抖音 API 全部走不通
- **解决**：不用 f2，用本 skill 自带的 requests 链路（更稳）

### 坑 5：yt-dlp 2026.07.04 是最新 stable
- 抖音 extractor 失效，generic extractor 走不通
- 解决：本 skill 不依赖 yt-dlp，直接用 requests + iesdouyin HTML 解析

## 📋 命名规范

**所有抖音下载视频必须按此命名：**
```
抖音-{标题前30字}-{YYYYMMDD}.mp4
```

示例：
- `抖音-让ClaudeCode替你干一天的4个习惯-20260708.mp4`
- `抖音-XXX-20260715.mp4`

**抽帧目录规范：**
```
frames/{prefix}_{YYYYMMDD}/{prefix}_{0001..NNNN}.jpg
```

示例：
- `frames/dy2_20260708/dy2_0001.jpg ~ dy2_0052.jpg`

## ✅ 校验清单（下载后必跑）

- [ ] `ffprobe` 确认 `nb_streams=2`（video + audio）
- [ ] `ffprobe` 确认 `duration` 与抖音 app 主片显示一致（一般 < 10 分钟）
- [ ] 文件大小与码率匹配（10MB / 4min = ~330kbps 是正常分享版；111MB / 26min = ~580kbps 是长片）
- [ ] 文件名按 `抖音-标题-YYYYMMDD.mp4` 规范
- [ ] 配套抽帧到 `frames/{prefix}_{YYYYMMDD}/`

## 🔄 实时更新规则

本 skill **必须随项目环境变化实时更新**：
- 抖音接口改版 → 更新 `_ROUTER_DATA` 解析逻辑
- 沙盒 IP 段变化 → 更新 IP 风控应对策略
- f2 / yt-dlp 库更新 → 评估是否替换本 skill
- 新增项目级 download 工具 → 在本 SKILL.md 补充

**更新方式**：直接编辑 `SKILL.md` 和 `scripts/download_douyin.py`，同时更新 `E:\自媒体\AI视频\AI视频提示词反推\.workbuddy\memory\MEMORY.md` 的"项目约定"小节。

## 📞 与其他技能配合

| 配套技能 | 时机 |
|---------|------|
| `video-prompt-reverse` | 下载完跑反推提示词 |
| `video-frames` (skill) | 用 ffmpeg 抽关键帧 |
| `douyin-copy-extract` | 提取口播文案 |

## 输出示例

```
[+] 正在解析链接: https://www.douyin.com/video/7649942475087416614
[+] 视频ID: 7649942475087416614
[+] 视频: 让 Claude Code 替你干一天的 4 个习惯 | 作者: Ali厂长
[+] 正在下载 (用 PowerShell 绕开 bash 14KB buffer) ...
[OK] 下载完成: E:\自媒体\AI视频\AI视频提示词反推\videos\抖音-让ClaudeCode替你干一天的4个习惯-20260708.mp4
[+] ffprobe 校验: nb_streams=2 (video + aac audio) duration=255.17s
[✅] 主片有声版校验通过
```
