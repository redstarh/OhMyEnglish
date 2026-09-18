"""낱말 뜻 조회 엔드포인트 (`TASK-194` · 결정 130).

⚠️ **재는 것은 라우터의 몫뿐이다** — 프롬프트와 응답 다듬기는 `tests/unit/test_vocab.py` 가 소유한다.
여기서는 그 산출물이 HTTP 로 나가는 형태와 **실패가 화면을 막지 않는 것**을 잰다.

⛔ **실물 Claude 를 부르지 않는다** — `app.state.claude` 를 대역으로 갈아 끼운다. 부르면 테스트가
돈을 쓰고 자격증명에 매인다.
"""

from __future__ import annotations

import httpx

from app.api.main import app


class _StubClaude:
    """뜻을 하나 돌려주는 대역."""

    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        return self.reply


class _BoomClaude:
    """모델 호출이 터지는 대역 — 낱말 하나를 못 물은 것으로 화면이 깨지지 않아야 한다."""

    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        raise RuntimeError("Bedrock 이 응답하지 않았다")


async def test_lookup_returns_a_single_line_meaning(api_client: httpx.AsyncClient) -> None:
    """뜻 한 줄이 그대로 나간다."""
    app.state.claude = _StubClaude("자리를 미리 잡아 두는 것")

    response = await api_client.post(
        "/api/vocab/lookup",
        json={"word": "book", "sentence": "I need to book a table for two."},
    )

    assert response.status_code == 200
    assert response.json() == {"meaning": "자리를 미리 잡아 두는 것"}


async def test_a_model_failure_is_not_a_500(api_client: httpx.AsyncClient) -> None:
    """⛔ **모델 실패가 화면을 깨뜨리지 않는다** — `meaning=null` 로 내보낸다.

    ⚠️ 「뜻을 모른다」와 「호출이 터졌다」가 화면에서 같게 보인다 — 그 구분이 학습자에게 값을 주지
    않으므로 합쳤고, 필요해지면 사유 코드를 더한다(라우터 docstring 이 그 판단을 가진다).
    """
    app.state.claude = _BoomClaude()

    response = await api_client.post(
        "/api/vocab/lookup",
        json={"word": "book", "sentence": "I read a book."},
    )

    assert response.status_code == 200
    assert response.json() == {"meaning": None}


async def test_a_blank_word_is_rejected_by_validation(api_client: httpx.AsyncClient) -> None:
    """빈 낱말은 모델에 닿기 전에 막힌다 — 돈을 쓰면서 뜻 없는 답을 받지 않는다."""
    app.state.claude = _StubClaude("무언가")

    response = await api_client.post(
        "/api/vocab/lookup",
        json={"word": "", "sentence": "I read a book."},
    )

    assert response.status_code == 422


async def test_an_overlong_sentence_is_rejected(api_client: httpx.AsyncClient) -> None:
    """⚠️ 길이 상한은 **모델 호출 비용의 상한**이다 — 문장 하나를 넘는 입력을 받지 않는다."""
    app.state.claude = _StubClaude("무언가")

    response = await api_client.post(
        "/api/vocab/lookup",
        json={"word": "book", "sentence": "x" * 601},
    )

    assert response.status_code == 422
