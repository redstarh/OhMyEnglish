"""낱말 뜻 조회 (`TASK-194` · 결정 130).

⛔ **이 갈래는 저장하지 않는다** — 표도 캐시도 없다. 그래서 이 파일에 DB 픽스처가 없고, 재는 것은
프롬프트가 무엇을 담는가와 응답을 어떻게 다듬는가 둘뿐이다.

⚠️ **문맥 문장이 프롬프트에 들어가는 것이 이 기능의 핵심 계약이다** — 낱말만 보내면 다의어에서
엉뚱한 뜻이 온다(`book` 이 「책」인지 「예약하다」인지는 문장이 정한다).
"""

from __future__ import annotations

import pytest

from app.services.vocab import build_vocab_prompt, lookup_word


class _StubClaude:
    """`ClaudeClient` 프로토콜의 최소 구현. 넘어온 프롬프트와 목적을 기록한다."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []
        self.purposes: list[str] = []

    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        self.prompts.append(prompt)
        self.purposes.append(purpose)
        return self.reply


def test_prompt_carries_the_word_and_its_sentence() -> None:
    """⛔ **문장이 없으면 다의어를 가릴 근거가 사라진다.**"""
    prompt = build_vocab_prompt(word="book", sentence="I need to book a table for two.")

    assert "book" in prompt
    assert "I need to book a table for two." in prompt


async def test_lookup_returns_a_single_line() -> None:
    """여러 줄이 와도 한 줄로 접는다 — 화면이 한 줄을 그린다.

    ⚠️ 프롬프트가 한 문장을 요구하지만 **모델이 지킨다는 보장이 없으므로** 코드가 접는다.
    """
    claude = _StubClaude("자리를 미리 잡아 두는 것\n(예: 식당 예약)")

    meaning = await lookup_word(claude, word="book", sentence="I need to book a table.")

    assert meaning == "자리를 미리 잡아 두는 것 (예: 식당 예약)"


async def test_lookup_records_its_own_purpose() -> None:
    """⛔ **`spike` 로 갈음하지 않는다** — 그 값은 「이름 없는 임시 호출」이다.

    갈래를 틀리게 적으면 비용이 틀린 축에 얹히고 그 오류는 조용하다. 값역은 028 의 CHECK 가
    가둔다 — 상수만 더하면 INSERT 가 거부되므로 둘이 한 쌍이다.
    """
    claude = _StubClaude("책")

    await lookup_word(claude, word="book", sentence="I read a book.")

    assert claude.purposes == ["vocab"]


async def test_lookup_returns_none_when_the_model_says_nothing() -> None:
    """빈 응답을 빈 문자열로 내보내지 않는다 — 화면이 「뜻이 왔다」로 읽고 빈 줄을 그린다."""
    claude = _StubClaude("   \n  ")

    assert await lookup_word(claude, word="book", sentence="I read a book.") is None


@pytest.mark.parametrize("word", ["", "   "])
async def test_blank_word_is_rejected_before_the_model_is_called(word: str) -> None:
    """⛔ **빈 낱말로 모델을 부르지 않는다** — 돈을 쓰면서 뜻 없는 답을 받는다."""
    claude = _StubClaude("무언가")

    with pytest.raises(ValueError):
        await lookup_word(claude, word=word, sentence="I read a book.")

    assert claude.prompts == []
