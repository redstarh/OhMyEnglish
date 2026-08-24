"""Task 8 — `GET /api/sessions/{id}/results` 테스트 (AC R1~R3, 설계서 §5.5).

워커를 돌리지 않는다 — `analysis_jobs`/`error_patterns`/`error_occurrences`는
이 테스트가 SQL로 직접 세팅한다(태스크 지시: "워커는 이 태스크와 무관"). FastAPI
는 실서버를 띄우지 않고 `httpx.ASGITransport`로 ASGI 앱에 직접 붙는다 — `app`의
`lifespan`(DB pool 생성·분석 워커 기동)은 실행하지 않고, 라우터가 읽는
`app.state.db_pool`만 테스트 풀로 주입한다.

`db_pool` + `committed_session`(둘 다 `tests/conftest.py`)을 쓴다: 라우터가
연 커넥션은 테스트가 쓴 커넥션과 별개이므로, 롤백되는 `db_conn` 트랜잭션은
라우터 쪽에 보이지 않는다 — 커밋되는 픽스처가 필수다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest_asyncio

from app.api.main import app

# --- DB 직접 세팅 헬퍼 (워커를 거치지 않고 원하는 상태를 바로 만든다) ---


async def _utterance(
    conn: asyncpg.Connection, session_id: UUID, sequence_no: int, transcript: str
) -> UUID:
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no) "
        "values ($1, 'user', $2, $3) returning id",
        session_id,
        transcript,
        sequence_no,
    )
    assert utterance_id is not None
    return utterance_id


async def _job(conn: asyncpg.Connection, utterance_id: UUID, status: str) -> UUID:
    job_id = await conn.fetchval(
        "insert into analysis_jobs (job_type, utterance_id, status) "
        "values ('analyze_utterance', $1, $2) returning id",
        utterance_id,
        status,
    )
    assert job_id is not None
    return job_id


async def _pattern(
    conn: asyncpg.Connection,
    user_id: UUID,
    *,
    category: str,
    pattern_key: str,
    target_form: str,
    frequency: int,
) -> UUID:
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form, frequency) "
        "values ($1, $2, $3, $4, $5) returning id",
        user_id,
        category,
        pattern_key,
        target_form,
        frequency,
    )
    assert pattern_id is not None
    return pattern_id


async def _occurrence(
    conn: asyncpg.Connection,
    utterance_id: UUID,
    pattern_id: UUID,
    *,
    original_span: str,
    correction: str,
    severity: str,
    confidence: str,
) -> None:
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, severity, confidence) "
        "values ($1, $2, $3, $4, $5, $6)",
        utterance_id,
        pattern_id,
        original_span,
        correction,
        severity,
        Decimal(confidence),
    )


@pytest_asyncio.fixture
async def api_client(db_pool: asyncpg.Pool) -> AsyncIterator[httpx.AsyncClient]:
    """실제 서버를 기동하지 않는다 — ASGI 트랜스포트로 앱에 직접 붙고, lifespan이
    여는 DB pool·워커는 건너뛴 채 라우터가 읽는 `app.state.db_pool`만 주입한다."""
    app.state.db_pool = db_pool
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ① 3패턴 검출 세션 → 정확히 2개, high가 medium보다 먼저 (R1 ordinal — 텍스트 desc면
# 'medium' > 'low' > 'high'로 순서가 뒤집히는 함정을 여기서 잡는다).
async def test_top_two_corrections_ranked_by_severity_ordinal_not_text(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(
            conn, committed_session.session_id, 1, "I go to gym and finish report yesterday."
        )
        await _job(conn, utterance_id, "done")

        medium_id = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_medium",
            target_form="go to the gym",
            frequency=1,
        )
        high_id = await _pattern(
            conn,
            committed_session.user_id,
            category="verb_tense",
            pattern_key="verb_tense_high",
            target_form="I finished the report",
            frequency=1,
        )
        low_id = await _pattern(
            conn,
            committed_session.user_id,
            category="word_order",
            pattern_key="word_order_low",
            target_form="finish the report quickly",
            frequency=1,
        )
        # 텍스트 desc라면 'medium'(0.95) > 'low'(0.99) > 'high'(0.5) 순이 된다.
        # ordinal desc라면 'high'(0.5) > 'medium'(0.95) > 'low'(0.99) 순이어야 한다.
        await _occurrence(
            conn,
            utterance_id,
            medium_id,
            original_span="go to gym",
            correction="go to the gym",
            severity="medium",
            confidence="0.95",
        )
        await _occurrence(
            conn,
            utterance_id,
            high_id,
            original_span="finish report yesterday",
            correction="finished the report",
            severity="high",
            confidence="0.50",
        )
        await _occurrence(
            conn,
            utterance_id,
            low_id,
            original_span="finish report quickly",
            correction="finish the report quickly",
            severity="low",
            confidence="0.99",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "final"
    assert body["partial_failure"] is False
    corrections = body["corrections"]
    assert len(corrections) == 2, "3패턴 중 상위 2개만 반환해야 한다"
    assert [c["pattern_key"] for c in corrections] == [
        "verb_tense_high",
        "article_missing_medium",
    ], "high가 medium보다 먼저 와야 한다 — ordinal desc, 텍스트 desc가 아니다"


# ② non-terminal job 존재 → analyzing + corrections 키 자체 없음 (R2 규칙 3)
async def test_non_terminal_job_yields_analyzing_without_corrections_key(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(
            conn, committed_session.session_id, 1, "I go to gym after work."
        )
        await _job(conn, utterance_id, "pending")

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "analyzing"
    assert body["partial_failure"] is False
    assert "corrections" not in body


# ③ job 0건 세션 → no_utterances
async def test_zero_jobs_yields_no_utterances(api_client: httpx.AsyncClient, committed_session):
    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_utterances"
    assert body["partial_failure"] is False
    assert "corrections" not in body


# ④ learning_sessions.status='failed' → connection_failed (job이 done이어도 우선한다)
async def test_failed_session_yields_connection_failed_even_with_done_job(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(
            conn, committed_session.session_id, 1, "I go to gym after work."
        )
        await _job(conn, utterance_id, "done")
        pattern_id = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_gym",
            target_form="go to the gym",
            frequency=1,
        )
        await _occurrence(
            conn,
            utterance_id,
            pattern_id,
            original_span="go to gym",
            correction="go to the gym",
            severity="medium",
            confidence="0.9",
        )
        await conn.execute(
            "update learning_sessions set status = 'failed' where id = $1",
            committed_session.session_id,
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connection_failed"
    assert body["partial_failure"] is False
    assert "corrections" not in body


# ⑤ failed job 1 + done 2 → partial_failure + 성공분 교정 포함 (R2 규칙 4, R3)
async def test_partial_failure_includes_successful_corrections(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        done_1 = await _utterance(conn, committed_session.session_id, 1, "I go to gym after work.")
        done_2 = await _utterance(
            conn, committed_session.session_id, 2, "I go to office by subway."
        )
        failed_utterance = await _utterance(
            conn, committed_session.session_id, 3, "I need to finish my homework tonight."
        )
        await _job(conn, done_1, "done")
        await _job(conn, done_2, "done")
        await _job(conn, failed_utterance, "failed")

        gym_pattern = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_gym",
            target_form="go to the gym",
            frequency=1,
        )
        office_pattern = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_office",
            target_form="go to the office",
            frequency=1,
        )
        await _occurrence(
            conn,
            done_1,
            gym_pattern,
            original_span="go to gym",
            correction="go to the gym",
            severity="medium",
            confidence="0.9",
        )
        await _occurrence(
            conn,
            done_2,
            office_pattern,
            original_span="go to office",
            correction="go to the office",
            severity="high",
            confidence="0.8",
        )
        # failed job의 발화는 분석이 끝나지 않았으므로 occurrence가 없다 — 만들지 않는다.

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_failure"
    assert body["partial_failure"] is True
    corrections = body["corrections"]
    assert {c["pattern_key"] for c in corrections} == {
        "article_missing_before_gym",
        "article_missing_before_office",
    }


# ⑥ 존재하지 않는 세션 → 404
async def test_unknown_session_returns_404(api_client: httpx.AsyncClient):
    response = await api_client.get(f"/api/sessions/{uuid4()}/results")

    assert response.status_code == 404


# ⑦ frequency=0으로 남은(occurrence 없는) 패턴은 결과에 나오지 않는다 (T6 다운스트림 계약)
async def test_frequency_zero_pattern_without_occurrence_does_not_appear(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(
            conn, committed_session.session_id, 1, "I go to office by subway."
        )
        await _job(conn, utterance_id, "done")

        # 재분석으로 사라진 패턴 — 행은 남지만(§5.2) 이 세션(혹은 전체)에 occurrence가 없다.
        await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_gym",
            target_form="go to the gym",
            frequency=0,
        )
        office_pattern = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_office",
            target_form="go to the office",
            frequency=1,
        )
        await _occurrence(
            conn,
            utterance_id,
            office_pattern,
            original_span="go to office",
            correction="go to the office",
            severity="medium",
            confidence="0.9",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "final"
    corrections = body["corrections"]
    assert [c["pattern_key"] for c in corrections] == ["article_missing_before_office"]


# ⑧ analyzing 상태는 이미 done인 성공 교정이 있어도 응답에서 완전히 숨긴다
# (규칙 3이 규칙 4/5보다 먼저 매칭되어야 함을 별도로 고정 — ②는 "숨길 것이 없는"
# 단순 케이스라, 실제로 있는 결과를 감추는지는 이 테스트가 잡는다).
async def test_analyzing_hides_already_available_corrections(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        done_utterance = await _utterance(
            conn, committed_session.session_id, 1, "I go to gym after work."
        )
        pending_utterance = await _utterance(
            conn, committed_session.session_id, 2, "I go to office by subway."
        )
        await _job(conn, done_utterance, "done")
        await _job(conn, pending_utterance, "pending")

        pattern_id = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_gym",
            target_form="go to the gym",
            frequency=1,
        )
        await _occurrence(
            conn,
            done_utterance,
            pattern_id,
            original_span="go to gym",
            correction="go to the gym",
            severity="medium",
            confidence="0.9",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "analyzing"
    assert body["partial_failure"] is False
    assert "corrections" not in body
