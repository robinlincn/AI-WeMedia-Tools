"""离线冒烟测试：mock 模式跑通 文案/视频 采集 -> 二创 全流程。

运行：python tests/test_pipeline.py
不依赖任何 API key 与网络。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Codes

from src.config import AppConfig  # noqa: E402
from src.db import Database  # noqa: E402
from src.collector.text import TextCollector  # noqa: E402
from src.collector.video import VideoCollector  # noqa: E402
from src.collector.link import LinkCollector  # noqa: E402
from src.creator.llm import LLMClient  # noqa: E402
from src.creator.rewrite import RewriteOrchestrator  # noqa: E402


def test_link_helpers():
    """离线验证链接采集器的头条地址改写与标题去后缀（不依赖网络）。"""
    assert LinkCollector._normalize_url(
        "https://www.toutiao.com/article/7659335342427734568/"
    ) == "https://m.toutiao.com/i7659335342427734568/"
    assert LinkCollector._normalize_url(
        "https://m.toutiao.com/i7659588574035149327/"
    ) == "https://m.toutiao.com/i7659588574035149327/"  # 已是移动版，不变
    assert LinkCollector._clean_title(
        "开源 TTS 又进一步：一段文字几秒变自然人声，还能克隆你的声音 - 今日头条"
    ) == "开源 TTS 又进一步：一段文字几秒变自然人声，还能克隆你的声音"
    assert LinkCollector._clean_title("AI工具出海赚美金：一个人月入30万") == \
        "AI工具出海赚美金：一个人月入30万"
    # 文件夹前缀应为「文章链接采集」
    assert LinkCollector.prefix == "文章链接采集", "链接采集文件夹前缀应为 文章链接采集"
    print("[链接helper] URL 改写 / 标题去后缀 / 前缀 OK")


def run():
    test_link_helpers()
    tmp = tempfile.mkdtemp()
    cfg = AppConfig(provider="mock", base_dir=Path(tmp))
    cfg.articles_dir = Path("Articles")
    cfg.out_dir = Path("OutArticles")
    cfg.db_path = Path(tmp) / "test.db"  # 绝对路径，避免落入临时目录父级
    cfg.resolve_paths()
    db = Database(cfg.db_path)
    llm = LLMClient(cfg.llm, mock=True)
    orch = RewriteOrchestrator(cfg, db, llm, mock=True)

    raw = (
        "人工智能正在改变内容创作。很多自媒体人开始使用AI写作工具。"
        "但这也带来了内容同质化的问题。我们需要保持个人风格与独立思考。"
    )

    # 1) 文案采集 + 二创
    col = TextCollector(cfg, db).collect(raw, title="AI写作的利与弊")
    assert col.source_id > 0, "文案采集应返回 source_id"
    # 采集文件夹命名应为「原文案-标题-时间戳」（连字符分隔）
    assert col.folder.name.startswith("原文案-"), f"采集文件夹应用 - 分隔：{col.folder.name}"
    res = orch.create(col.title, raw, source_id=col.source_id)
    assert res.output_id > 0, "二创应返回 output_id"
    assert res.md_path.exists(), "二创 md 应存在"
    assert len(res.title) <= 30, f"标题超长({len(res.title)})：{res.title}"
    assert res.media, "应生成至少一张配图"
    assert res.similarity < 0.10, f"近似相似度过高：{res.similarity}"
    md = res.md_path.read_text(encoding="utf-8")
    assert "images/" in md, "头条风格 md 应嵌入配图"
    # 双风格：公众号风格 md 也应存在并含配图
    wmd = res.wechat_md_path.read_text(encoding="utf-8")
    assert res.wechat_md_path.exists(), "公众号风格 md 应存在"
    assert "images/" in wmd, "公众号风格 md 应嵌入配图"
    # 文件夹与文件名前缀规范（连字符 - 分隔）
    assert res.folder.name.startswith("文章二创-"), f"二创文件夹应用 - 分隔：{res.folder.name}"
    assert res.md_path.name.startswith("头条风格-"), f"头条 md 应用 - 分隔：{res.md_path.name}"
    assert res.wechat_md_path.name.startswith("公众号风格-"), f"公众号 md 应用 - 分隔：{res.wechat_md_path.name}"
    assert "-" in res.folder.name, "二创文件夹命名应包含连字符分隔"
    assert res.md_path.name.count("-") >= 2, "头条 md 文件名应包含连字符分隔（风格-标题-时间戳）"
    assert res.wechat_md_path.name.count("-") >= 2, "公众号 md 文件名应包含连字符分隔（风格-标题-时间戳）"
    # 回归：改写任务不能被误判为标题任务
    # （REWRITE_SYSTEM 曾因含“小标题”被 _mock_reply 的 `"标题" in system` 误判，
    #  导致正文被替换成“【干货】…”标题文本。此处断言正文确为改写内容。）
    assert "你有没有发现" in md, "正文中应出现改写内容，而非被替换成标题"
    body_below_h1 = "\n".join(md.split("\n")[2:])
    assert res.title not in body_below_h1, "标题不应作为正文段落出现"
    print(f"[文案] source={col.source_id} -> output={res.output_id} "
          f"title='{res.title}' sim={res.similarity} imgs={len(res.media)}")

    # 2) 视频采集(mock) + 二创
    vcol = VideoCollector(cfg, db).collect("https://example.com/v.mp4", title="示例视频", mock=True)
    assert vcol.source_id > 0
    vres = orch.create(vcol.title, "视频口播文案占位内容。", source_id=vcol.source_id)
    assert vres.md_path.exists()
    print(f"[视频] source={vcol.source_id} -> output={vres.output_id} "
          f"title='{vres.title}' sim={vres.similarity} imgs={len(vres.media)}")

    # 3) 标题长度边界
    long_title = "这是一个明显超过三十个汉字长度的超长原标题用于测试截断逻辑是否生效"
    col2 = TextCollector(cfg, db).collect("占位正文内容。", title=long_title)
    r2 = orch.create(col2.title, "占位正文内容。", source_id=col2.source_id)
    assert len(r2.title) <= 30, f"超长标题未截断：{r2.title}"
    print(f"[长标题] '{long_title[:20]}…' -> '{r2.title}' ({len(r2.title)}字)")

    print("\n✅ ALL TESTS PASSED")


if __name__ == "__main__":
    run()
