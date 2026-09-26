"""튜터 발화 번역 엔드포인트 (`TASK-275`).

⛔ **실물 Claude 를 부르지 않는다** — `app.state.claude` 를 대역으로 갈아 끼운다
(`test_vocab_api.py` 와 같은 규약).
재는 것: HTTP 형태 · 번역이 발화 행에 저장되고 두 번째 요청이 모델을 부르지 않는 것 ·
실패가 화면을 막지 않는 것.
"""

from __future__ import annotations

import asyncpg
import httpx
import pytest_asyncio
from conftest import CommittedSession

from app.api.main import app


class _CountingClaude:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        self.calls += 1
        return self.reply


class _BoomClaude:
    async def analyze(self, prompt: str, *, purpose: str = "spike", job_id: object = None) -> str:
        raise RuntimeError("Bedrock 이 응답하지 않았다")


@pytest_asyncio.fixture
async def agent_utterance(
    db_pool: asyncpg.Pool, committed_session: CommittedSession
) -> CommittedSession:
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into utterances (session_id, speaker, transcript, sequence_no)"
            " values ($1, 'agent', 'What drink would you like?', 1),"
            "        ($1, 'user', 'I want an apple juice.', 2),"
            "        ($1, 'agent', 'Great choice.', 3)",
            committed_session.session_id,
        )
    return committed_session


def _url(session: CommittedSession, seq: int) -> str:
    return f"/api/sessions/{session.session_id}/utterances/{seq}/translation"


async def test_translation_is_returned_and_stored(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession, db_pool: asyncpg.Pool
) -> None:
    app.state.claude = _CountingClaude("어떤 음료를 드릴까요?")

    response = await api_client.post(_url(agent_utterance, 1))

    assert response.status_code == 200
    assert response.json() == {"translation": "어떤 음료를 드릴까요?"}
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select translation_ko from utterances where session_id = $1 and sequence_no = 1",
            agent_utterance.session_id,
        )
    assert stored == "어떤 음료를 드릴까요?"
    # 저장이 그 한 행에만 닿는다 — 다른 순번의 행은 그대로 비어 있어야 한다.
    async with db_pool.acquire() as conn:
        others = await conn.fetch(
            "select translation_ko from utterances where session_id = $1 and sequence_no <> 1",
            agent_utterance.session_id,
        )
    assert [row["translation_ko"] for row in others] == [None, None]


async def test_a_second_request_reuses_the_stored_translation(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession
) -> None:
    """⛔ 같은 발화를 두 번 눌러도 모델은 한 번만 부른다 — 두 번째는 저장된 값이다."""
    claude = _CountingClaude("어떤 음료를 드릴까요?")
    app.state.claude = claude

    first = await api_client.post(_url(agent_utterance, 1))
    second = await api_client.post(_url(agent_utterance, 1))

    assert first.json() == second.json() == {"translation": "어떤 음료를 드릴까요?"}
    assert claude.calls == 1


async def test_an_unknown_utterance_is_404(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession
) -> None:
    app.state.claude = _CountingClaude("무언가")

    response = await api_client.post(_url(agent_utterance, 99))

    assert response.status_code == 404


async def test_a_model_failure_is_not_a_500_and_stores_nothing(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession, db_pool: asyncpg.Pool
) -> None:
    """실패를 저장하지 않는다 — 저장하면 다시 눌러도 영원히 번역이 오지 않는다."""
    app.state.claude = _BoomClaude()

    response = await api_client.post(_url(agent_utterance, 1))

    assert response.status_code == 200
    assert response.json() == {"translation": None}
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select translation_ko from utterances where session_id = $1 and sequence_no = 1",
            agent_utterance.session_id,
        )
    assert stored is None


async def test_no_credentials_answers_503(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession
) -> None:
    app.state.claude = None

    response = await api_client.post(_url(agent_utterance, 1))

    assert response.status_code == 503


async def test_a_learner_utterance_is_not_translated(
    api_client: httpx.AsyncClient, agent_utterance: CommittedSession
) -> None:
    """⛔ 튜터 발화만 번역한다 — 학습자 문장을 「코치가 한 말」로 속여 모델을 부르지 않는다.

    `TASK-275` 리뷰 MEDIUM 이 잡았다.
    """
    claude = _CountingClaude("사과 주스를 원해요.")
    app.state.claude = claude

    response = await api_client.post(_url(agent_utterance, 2))

    assert response.status_code == 404
    assert claude.calls == 0
