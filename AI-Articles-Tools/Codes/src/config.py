"""配置加载：环境变量优先，其次 config.toml。AI 提供商可插拔（openai / mock）。

环境变量覆盖规则：
  ARTICLES_PROVIDER
  ARTICLES_LLM_BASE_URL / ARTICLES_LLM_API_KEY / ARTICLES_LLM_MODEL
  ARTICLES_IMAGE_BASE_URL / ARTICLES_IMAGE_API_KEY / ARTICLES_IMAGE_MODEL
  ARTICLES_ASR_BASE_URL  / ARTICLES_ASR_API_KEY  / ARTICLES_ASR_MODEL
  ARTICLES_DB_PATH / ARTICLES_ARTICLES_DIR / ARTICLES_OUT_DIR
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import toml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = ""


@dataclass
class AppConfig:
    provider: str = "openai"  # openai | mock
    db_path: Path = Path("DataBase/ai_articles.db")
    articles_dir: Path = Path("Articles")
    out_dir: Path = Path("OutArticles")
    llm: ProviderConfig = field(default_factory=ProviderConfig)
    image: ProviderConfig = field(default_factory=ProviderConfig)
    asr: ProviderConfig = field(default_factory=ProviderConfig)
    base_dir: Path = field(default_factory=Path.cwd)

    def resolve_paths(self) -> "AppConfig":
        self.base_dir = self.base_dir.resolve()
        for name in ("db_path", "articles_dir", "out_dir"):
            p: Path = getattr(self, name)
            if not p.is_absolute():
                setattr(self, name, (self.base_dir / p).resolve())
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        # 数据库文件落在 DataBase/ 内：确保父目录存在（文件本身由 Database 类创建）
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return self


def _env(prefix: str, key: str, default: str) -> str:
    return os.environ.get(f"{prefix}_{key}", default)


def load_config(config_path: str | None = None) -> AppConfig:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    cfg = AppConfig()

    # 1) 从 config.toml 读取
    if path.exists():
        data = toml.load(path)
        app = data.get("app", {})
        cfg.provider = app.get("provider", cfg.provider)
        paths = data.get("paths", {})
        cfg.db_path = Path(paths.get("db", cfg.db_path))
        cfg.articles_dir = Path(paths.get("articles_dir", cfg.articles_dir))
        cfg.out_dir = Path(paths.get("out_dir", cfg.out_dir))
        for section, attr in (("llm", "llm"), ("image", "image"), ("asr", "asr")):
            if section in data:
                src = data[section]
                pc: ProviderConfig = getattr(cfg, attr)
                pc.base_url = src.get("base_url", pc.base_url)
                pc.api_key = src.get("api_key", pc.api_key)
                pc.model = src.get("model", pc.model)

    # 2) 环境变量覆盖（优先级最高）
    cfg.provider = _env("ARTICLES", "PROVIDER", cfg.provider)
    cfg.llm.base_url = _env("ARTICLES_LLM", "BASE_URL", cfg.llm.base_url)
    cfg.llm.api_key = _env("ARTICLES_LLM", "API_KEY", cfg.llm.api_key)
    cfg.llm.model = _env("ARTICLES_LLM", "MODEL", cfg.llm.model)
    cfg.image.base_url = _env("ARTICLES_IMAGE", "BASE_URL", cfg.image.base_url)
    cfg.image.api_key = _env("ARTICLES_IMAGE", "API_KEY", cfg.image.api_key)
    cfg.image.model = _env("ARTICLES_IMAGE", "MODEL", cfg.image.model)
    cfg.asr.base_url = _env("ARTICLES_ASR", "BASE_URL", cfg.asr.base_url)
    cfg.asr.api_key = _env("ARTICLES_ASR", "API_KEY", cfg.asr.api_key)
    cfg.asr.model = _env("ARTICLES_ASR", "MODEL", cfg.asr.model)
    if os.environ.get("ARTICLES_DB_PATH"):
        cfg.db_path = Path(os.environ["ARTICLES_DB_PATH"])
    if os.environ.get("ARTICLES_ARTICLES_DIR"):
        cfg.articles_dir = Path(os.environ["ARTICLES_ARTICLES_DIR"])
    if os.environ.get("ARTICLES_OUT_DIR"):
        cfg.out_dir = Path(os.environ["ARTICLES_OUT_DIR"])

    # 不在此时 resolve_paths：调用方（如 cli）会设置 base_dir 后再解析，
    # 避免相对路径被提前绑定到 cwd。
    return cfg
