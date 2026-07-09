"""LLM 客户端：OpenAI 兼容协议，可指向 DeepSeek / SiliconFlow / 通义 / 本地模型。

- 真实模式：使用 openai SDK（base_url / api_key / model 来自配置）
- mock 模式：离线返回确定性、明显改写过的文本，便于跑通流程与测试
"""
from __future__ import annotations

from src.config import ProviderConfig


def build_client(pc: ProviderConfig):
    from openai import OpenAI
    return OpenAI(base_url=pc.base_url or None, api_key=pc.api_key)


class LLMClient:
    def __init__(self, pc: ProviderConfig, mock: bool = False):
        self.pc = pc
        self.mock = mock
        self._client = None

    def _real(self):
        if self._client is None:
            self._client = build_client(self.pc)
        return self._client

    def chat(self, system: str, user: str, temperature: float | None = None, max_tokens: int | None = None) -> str:
        if self.mock:
            return self._mock_reply(system, user)
        resp = self._real().chat.completions.create(
            model=self.pc.model or "gpt-4o-mini",
            temperature=temperature if temperature is not None else 0.85,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()

    # ---------- mock ----------
    @staticmethod
    def _mock_reply(system: str, user: str) -> str:
        # 根据 system 指令区分任务，给出可辨识的确定性改写。
        # 注意：必须用标题任务独有的标记「标题党」判定，不能用「标题」——
        # 否则 REWRITE_SYSTEM 里的「小标题」会被误判为标题任务，导致正文被替换成标题。
        if "标题党" in system:
            base = user.split("\n")[0].replace("原标题：", "").replace("原文摘要：", "").strip()[:12]
            return f"【干货】{base}？"
        # 通用改写：返回与原文明显不同的占位文本，保证近似相似度足够低
        return (
            "你有没有发现，最近这件事一直在被人反复提起。\n\n"
            "其实背后的逻辑很简单，只是大多数人没点破。\n\n"
            "换个说法讲，核心就一句话：别被表面带节奏。\n\n"
            "落到自己身上，先把信息拆开看，再决定信不信。"
        )
