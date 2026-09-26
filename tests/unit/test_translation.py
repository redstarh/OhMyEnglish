"""튜터 발화 한국어 번역의 프롬프트와 응답 다듬기 (`TASK-275`).

⚠️ HTTP 표면·저장·재사용은 `tests/integration/test_translation_api.py` 가 소유한다.
"""

from __future__ import annotations

import pytest

from app.models.usage import PURPOSE_TRANSLATION
from app.services.translation import build_translation_prompt, translate_to_korean


class _StubClaude:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []
        self.purposes: list[str] = []

    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        self.prompts.append(prompt)
        self.purposes.append(purpose)
        return self.reply


def test_the_prompt_carries_the_sentence():
    assert "What drink would you like?" in build_translation_prompt("What drink would you like?")


async def test_translation_records_its_own_purpose():
    """⛔ `spike` 로 갈음하지 않는다 — 제품 기능의 비용이 「임시 호출」 축에 얹힌다.

    `vocab` 과 같은 판단이다.
    """
    claude = _StubClaude("어떤 음료를 드릴까요?")

    await translate_to_korean(claude, "What drink would you like?")

    assert claude.purposes == [PURPOSE_TRANSLATION]


async def test_translation_folds_lines_into_one():
    claude = _StubClaude("어떤 음료를\n드릴까요?")

    assert (
        await translate_to_korean(claude, "What drink would you like?") == "어떤 음료를 드릴까요?"
    )


async def test_an_empty_reply_is_none():
    assert await translate_to_korean(_StubClaude("  \n "), "Hello.") is None


async def test_a_blank_sentence_does_not_call_the_model():
    claude = _StubClaude("무언가")

    with pytest.raises(ValueError):
        await translate_to_korean(claude, "   ")
    assert claude.prompts == []
