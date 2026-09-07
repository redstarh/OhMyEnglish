"""Task 8 — `GET /api/sessions/{id}/results` 테스트 (AC R1~R3, 설계서 §5.5).

워커를 돌리지 않는다 — `analysis_jobs`/`error_patterns`/`error_occurrences`는
이 테스트가 SQL로 직접 세팅한다(태스크 지시: "워커는 이 태스크와 무관"). FastAPI
는 실서버를 띄우지 않고 `httpx.ASGITransport`로 ASGI 앱에 직접 붙는다 — 그 배선은
`tests/conftest.py`의 `api_client`가 소유한다(계획 조회 테스트와 공유한다).

`db_pool` + `committed_session`(둘 다 `tests/conftest.py`)을 쓴다: 라우터가
연 커넥션은 테스트가 쓴 커넥션과 별개이므로, 롤백되는 `db_conn` 트랜잭션은
라우터 쪽에 보이지 않는다 — 커밋되는 픽스처가 필수다.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest

from app.services.results import logger as results_logger

# --- DB 직접 세팅 헬퍼 (워커를 거치지 않고 원하는 상태를 바로 만든다) ---


async def _utterance(
    conn: asyncpg.Connection,
    session_id: UUID,
    sequence_no: int,
    transcript: str,
    *,
    speaker: str = "user",
    utterance_type: str = "learning",
) -> UUID:
    """발화 1행. `speaker`·`utterance_type`의 기본값은 분석 대상 발화다.

    드릴 exchange 절(파일 끝)이 두 값을 바꿔 가며 쓴다 — 세는 규칙이 그 두 열에 걸려 있다.
    """
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
        "values ($1, $2, $3, $4, $5) returning id",
        session_id,
        speaker,
        utterance_type,
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
    explanation: str = "학습자용 한 줄 설명 (테스트 기본값)",
) -> None:
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, $3, $4, $5, $6, $7)",
        utterance_id,
        pattern_id,
        original_span,
        correction,
        explanation,
        severity,
        Decimal(confidence),
    )


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
            explanation="어제 일어난 일이므로 과거형 finished를 씁니다.",
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
    # AC U2: 결과 카드가 "원문 → 교정문 → 한 줄 이유"를 요구한다 — 대표 occurrence의
    # explanation이 reason으로 응답에 실려야 한다.
    assert corrections[0]["reason"] == "어제 일어난 일이므로 과거형 finished를 씁니다."


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


# ⑨ Fix round 1 (I-2 ①) — severity·confidence가 같을 때 3차 정렬 기준
# `occurrence_count desc`가 실제로 동작하는지 (지금까지 어떤 테스트도 이 축을
# 단독으로 검증하지 않았다). 두 패턴 모두 severity="high", confidence=0.80으로
# 동일하게 두고 발생 수만 다르게 한다 — 그 축이 아니면 순서를 정할 수 없다.
async def test_top_corrections_tiebreak_by_occurrence_count_when_severity_and_confidence_tie(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        two_occurrences = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_more_occurrences",
            target_form="go to the gym",
            frequency=2,
        )
        one_occurrence = await _pattern(
            conn,
            committed_session.user_id,
            category="verb_tense",
            pattern_key="verb_tense_fewer_occurrences",
            target_form="I finished the report",
            frequency=1,
        )

        first = await _utterance(conn, committed_session.session_id, 1, "I go to gym after work.")
        second = await _utterance(
            conn, committed_session.session_id, 2, "I go to office by subway."
        )
        third = await _utterance(
            conn, committed_session.session_id, 3, "I finish report yesterday."
        )
        await _job(conn, first, "done")
        await _job(conn, second, "done")
        await _job(conn, third, "done")

        await _occurrence(
            conn,
            first,
            two_occurrences,
            original_span="go to gym",
            correction="go to the gym",
            severity="high",
            confidence="0.80",
        )
        await _occurrence(
            conn,
            second,
            two_occurrences,
            original_span="go to office",
            correction="go to the office",
            severity="high",
            confidence="0.80",
        )
        await _occurrence(
            conn,
            third,
            one_occurrence,
            original_span="finish report yesterday",
            correction="finished the report",
            severity="high",
            confidence="0.80",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    corrections = response.json()["corrections"]
    assert [c["pattern_key"] for c in corrections] == [
        "article_missing_more_occurrences",
        "verb_tense_fewer_occurrences",
    ], "severity·confidence가 같으면 발생 수(occurrence_count desc)가 순서를 정해야 한다"
    assert corrections[0]["occurrences"] == 2
    assert corrections[1]["occurrences"] == 1


# ⑩ Fix round 1 (I-1 회귀 방어, I-2 ②) — 같은 발화의 같은 패턴에 occurrence 2건을
# **한 트랜잭션에서** insert해 프로덕션 경계를 재현한다: PostgreSQL `now()`는
# 트랜잭션 시작 시각으로 고정되므로 두 `error_occurrences.created_at`이 마이크로초까지
# 동일해진다(§5.2 `_replace_occurrences`가 findings 전체를 한 트랜잭션에서 insert하는
# 것과 같은 상황). representative CTE의 tie-break가 `eo.id`까지 내려가지 않으면
# 대표 문구 선택이 물리 스캔 순서에 좌우된다 — 결과 조회를 두 번 해서 같은 문구가
# 나오는지로 안정성을 고정한다.
async def test_representative_correction_is_stable_when_occurrences_tie_on_created_at(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(
            conn, committed_session.session_id, 1, "I go to gym and go to office."
        )
        await _job(conn, utterance_id, "done")
        pattern_id = await _pattern(
            conn,
            committed_session.user_id,
            category="article",
            pattern_key="article_missing_before_place_noun",
            target_form="go to the place",
            frequency=2,
        )
        # 같은 트랜잭션 안에서 두 occurrence를 insert — created_at이 완전히 같아진다.
        async with conn.transaction():
            await _occurrence(
                conn,
                utterance_id,
                pattern_id,
                original_span="go to gym",
                correction="go to the gym",
                severity="high",
                confidence="0.90",
            )
            await _occurrence(
                conn,
                utterance_id,
                pattern_id,
                original_span="go to office",
                correction="go to the office",
                severity="high",
                confidence="0.90",
            )

    first_response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")
    second_response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_corrections = first_response.json()["corrections"]
    second_corrections = second_response.json()["corrections"]
    assert len(first_corrections) == 1
    assert first_corrections[0]["original_span"] in {"go to gym", "go to office"}
    assert first_corrections == second_corrections, (
        "동일한 tie 상황에서 반복 조회가 다른 대표 문구를 돌려주면 안 된다 "
        "(I-1: representative tie-break가 eo.id까지 내려가야 한다)"
    )


# --- Task 8: 발음 카드 (PS9 · 설계서 §10 미결 4 결정 · TASKS.md A-2 후단) ---


async def _attempt(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    target_form: str,
    outcome: str,
    spoken_form: str | None = None,
    target_sound: str | None = None,
    signal_source: str = "nova_tool",
) -> UUID:
    """발음 시도 1행을 직접 만든다 (Nova 어댑터·세션 배선을 거치지 않는다).

    `resolved_at`은 003의 `pronunciation_attempts_resolved_consistency`가 `outcome`과
    짝을 강제하므로(pending이면 null, 판정됐으면 반드시 값) SQL 안에서 함께 정한다 —
    호출부가 매번 기억해야 하는 규약으로 남기지 않는다.
    """
    attempt_id = await conn.fetchval(
        "insert into pronunciation_attempts (session_id, target_form, spoken_form, "
        "target_sound, outcome, signal_source, resolved_at) "
        "values ($1, $2, $3, $4, $5, $6, case when $5 = 'pending' then null else now() end) "
        "returning id",
        session_id,
        target_form,
        spoken_form,
        target_sound,
        outcome,
        signal_source,
    )
    assert attempt_id is not None
    return attempt_id


# ⑪ 발음 시도가 있는 세션의 결과에 `pronunciation` 배열이 실린다 (PS9 단정 1).
# 같은 테스트가 **표시 규약 결정**(설계서 §10 미결 4)도 고정한다: 기계 키
# (`target_sound` = 패턴 `target_form`의 재료)는 응답 어디에도 나오지 않는다.
# 계획서 `:1352`가 적은 `target_sound` 필드는 그 결정으로 폐기됐다 — 관측된 키가
# 0건인 상태에서 화면에 내보내면 학습자가 `th_as_s`를 읽는다.
async def test_pronunciation_attempts_appear_in_results_without_machine_key(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(conn, committed_session.session_id, 1, "I think it's 3.")
        await _job(conn, utterance_id, "done")
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="I think it's three.",
            spoken_form="I sink it's sree.",
            target_sound="th_as_s",
            outcome="incorrect",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    assert response.json()["pronunciation"] == [
        {
            "target_form": "I think it's three.",
            "spoken_form": "I sink it's sree.",
            "outcome": "incorrect",
            "signal_source": "nova_tool",
        }
    ]
    assert "th_as_s" not in response.text, (
        "기계 키는 응답에 실리지 않는다 (설계서 §10 미결 4 — 실물 왕복 0회라 "
        "표시 규칙이 발명값이다)"
    )


# ⑫ `pending`은 결과에 포함하지 않는다 (PS9 단정 3) — 미판정을 학습자에게 보이지 않는다.
# `"pending"이 없다`는 부재 단정만으로는 red가 되지 않는다(구현 전에는 배열 자체가 없어
# 자동 통과한다). 그래서 **판정된 1건만 실린다**를 양성으로 단정한다.
async def test_pending_attempt_is_excluded_and_resolved_one_remains(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="Could you say water again?",
            outcome="pending",
        )
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="I drink water every morning.",
            spoken_form="I drink water every morning.",
            target_sound="w_as_b",
            outcome="correct",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    pronunciation = response.json()["pronunciation"]
    assert [item["outcome"] for item in pronunciation] == ["correct"]
    assert pronunciation[0]["target_form"] == "I drink water every morning."


# ⑬ `incorrect`인데 `spoken_form`이 null인 행은 **대답 없이 끝난 시도**다
# (TASKS.md A-2 후단 ②, 종료 수렴 §3.2). 키를 지우면 프론트가 "들린 발음"을
# 빈 문자열로 렌더할지 생략할지 구분할 수 없으므로 **키는 있고 값이 null**이다.
async def test_unanswered_attempt_keeps_spoken_form_key_as_null(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="I think it's three.",
            target_sound="th_as_s",
            outcome="incorrect",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    item = response.json()["pronunciation"][0]
    assert item["outcome"] == "incorrect"
    assert "spoken_form" in item
    assert item["spoken_form"] is None


# ⑭ 신호 행은 `signal_source`로 구분된다 (TASKS.md A-2 후단 ①). 신호 행의
# `target_form`은 Nova가 시범한 문장이 아니라 **설명 문구**라서, 구분 없이 렌더하면
# 학습자에게 그 문구가 "이렇게 발음해야 합니다"로 보인다.
async def test_signal_row_is_distinguishable_by_signal_source(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="(전사문이 한국어로 인식되었습니다)",
            outcome="unclear",
            signal_source="korean_transcript",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    item = response.json()["pronunciation"][0]
    assert item["signal_source"] == "korean_transcript"
    assert item["target_form"] == "(전사문이 한국어로 인식되었습니다)"


# ⑮ `analyzing` 중에도 발음 배열은 실린다 — 계획서 `:1371` "발음 배열은 그 판정과
# **독립적으로** 실린다". R2 규칙 3이 막는 것은 *비동기 분석이 끝나지 않은* 문법 교정의
# 잠정 노출이고, 발음 시도 행은 종료 수렴이 `pending`을 없애므로 구조적으로 확정값이다.
# `corrections` 키가 여전히 없는 것을 함께 단정해 규칙 3을 건드리지 않았음을 고정한다.
async def test_pronunciation_is_included_while_grammar_is_still_analyzing(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_id = await _utterance(conn, committed_session.session_id, 1, "I think it's 3.")
        await _job(conn, utterance_id, "pending")
        await _attempt(
            conn,
            committed_session.session_id,
            target_form="I think it's three.",
            spoken_form="I sink it's sree.",
            target_sound="th_as_s",
            outcome="incorrect",
        )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "analyzing"
    assert "corrections" not in body
    assert len(body["pronunciation"]) == 1


# ⑯ 카드 순서는 **삽입 순**이다(시도 1건 = 1카드, 설계서 §10 미결 4). 두 시도를
# **한 트랜잭션에서** 만들어 `created_at`을 마이크로초까지 동률로 만든다 — `now()`가
# 트랜잭션 시각으로 고정되기 때문이다(004가 `attempt_seq`를 신설한 바로 그 이유).
# 이 상황에서 순서를 정할 수 있는 것은 `attempt_seq`뿐이다.
#
# ⚠️ `attempt_seq`는 표 전역 identity라 롤백이 번호에 구멍을 낸다(004 경고) — 정렬에만
# 쓰고 번호 자체는 응답에 싣지 않는다. 학습자에게 보이는 순번은 배열 위치가 만든다.
async def test_pronunciation_ordered_by_insertion_when_created_at_ties(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await _attempt(
                conn,
                committed_session.session_id,
                target_form="I think it's three.",
                spoken_form="I sink it's sree.",
                target_sound="th_as_s",
                outcome="incorrect",
            )
            await _attempt(
                conn,
                committed_session.session_id,
                target_form="Coffee, please.",
                spoken_form="Copi, please.",
                target_sound="f_as_p",
                outcome="incorrect",
            )

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    pronunciation = response.json()["pronunciation"]
    assert [item["target_form"] for item in pronunciation] == [
        "I think it's three.",
        "Coffee, please.",
    ]


# --- 드릴 exchange 관측 (설계서 §2.3 · 캡틴 결정 10·16 · 009 컬럼) ---
#
# 세는 것은 **「코치 발화 바로 뒤에 온 사용자 발화」**다. 설계 3판은 이 방향이 반대였고
# 4판이 고쳤다 — 두 방향은 **세션이 학습자 발화로 끝날 때 1만큼 갈라지고** 그것이 정상
# 종료 모양이라(`audio_gateway/stub.py`의 재생 순서) 완전 순응 세션이 매번 미달로 세어졌다.
# ⑤가 그 tripwire다: 3판 방향으로 세면 12 대신 11이 나와 FAIL 한다.

# `(speaker, utterance_type)` 조합에 이름을 붙인다 — 세는 규칙이 그 두 열에만 걸려 있으므로
# 테스트 본문이 발화 **순서**만 보이게 한다.
COACH = ("agent", "learning")
LEARNER = ("user", "learning")
LEARNER_COMMAND = ("user", "voice_command")
COACH_CONFIRMATION = ("agent", "command_confirmation")

# 로거 이름을 문자열로 박지 않는다 — 박으면 모듈이 옮겨졌을 때 「기록 0건」 단정이 조용히
# 항진명제가 된다. 구현이 쓰는 로거를 그대로 가리킨다.
RESULTS_LOGGER = results_logger.name


async def _turns(
    conn: asyncpg.Connection, session_id: UUID, turns: Sequence[tuple[str, str]]
) -> list[UUID]:
    """`(speaker, utterance_type)`을 순서대로 넣는다 — `sequence_no`는 1부터 붙는다."""
    return [
        await _utterance(
            conn,
            session_id,
            sequence_no,
            f"{speaker}/{utterance_type} {sequence_no}",
            speaker=speaker,
            utterance_type=utterance_type,
        )
        for sequence_no, (speaker, utterance_type) in enumerate(turns, start=1)
    ]


async def _set_drill_expected(conn: asyncpg.Connection, session_id: UUID, expected: int) -> None:
    """세션 시작이 남긴 기대값(009)을 직접 박는다.

    `sessions.record_drill_turns_expected`를 거치지 않는 것이 의도다 — 그 함수는 계획과
    설정값에서 값을 **만드는** 쪽이고, 이 절이 재는 것은 그 값을 **읽는** 경로다. 계획을
    세팅해 값을 유도하면 조립 실패와 조회 실패가 같은 red로 보인다.
    """
    await conn.execute(
        "update learning_sessions set drill_turns_expected = $2 where id = $1",
        session_id,
        expected,
    )


def _results_logs(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """`services/results`가 낸 기록만 고른다 — 다른 모듈의 경고를 이 단정에 섞지 않는다."""
    return [record for record in caplog.records if record.name == RESULTS_LOGGER]


def _labeled_number(message: str, label: str) -> str | None:
    """로그 줄에서 **그 라벨이 가리키는** 수를 꺼낸다. 없으면 `None`.

    `\\D*`가 숫자를 건너뛰지 못하므로 라벨 **바로 다음** 수만 잡는다 — 두 수가 뒤바뀌면
    각 라벨이 다른 수를 가리키게 되어 단정이 FAIL 한다.

    ⚠️ **문구(라벨)에 결합하는 쪽을 골랐다 — 취약성을 알고 받아들였다.** 라벨을 바꾸면 이
    테스트가 깨진다. 그래도 그렇게 한 이유: **어느 수가 관측이고 어느 수가 기대인지 말하는
    것은 라벨뿐**이라, 순서만 재는 단정(`index("2") < index("8")`)은 포맷 문자열의 라벨을
    뒤집는 결함(`"기대 %d / 관측 %d"` + 같은 인자)을 **통과시킨다** — 두 무력화를 실제로
    돌려 확인했다. 판별력을 취약성 위에 둔다: 깨지면 시끄럽게 깨지고, 통과하면 그 이유가
    맞다. 라벨을 고칠 사람은 이 테스트도 함께 고친다.
    """
    found = re.search(rf"{label}\D*(\d+)", message)
    return found.group(1) if found else None


# ① 코치 발화가 **연속 2건**(질문 + 힌트)이어도 학습자 답이 1건이면 `1`이다.
# H-3이 뚫은 자리: `count(*) where speaker='agent'`로 세면 2가 되고, 그때 턴은 닫히지
# 않았으므로(`session.py`의 `_flush_analysis`가 no-op) **막혀서 힌트만 반복된 세션이
# 「달성」으로 통과한다.** SYSTEM_PROMPT 규칙 2·5가 그 힌트를 **명령**하므로 이 경로는
# 엣지 케이스가 아니다.
async def test_drill_counts_one_exchange_when_the_coach_speaks_twice_before_the_answer(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, COACH, LEARNER])
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "final"
    assert body["drill"] == {"exchanges_observed": 1, "exchanges_expected": 8}, (
        "힌트가 exchange 수를 올렸다 — 세는 것은 코치 발화가 아니라 「코치 뒤에 온 사용자 발화」다"
    )


# ② 사용자 발화가 0건이고 코치 발화만 있는 세션 → `0`. H-3이 뚫은 바로 그 자리다.
#
# ⚠️ **이 세션 상태는 인공이다.** 프로덕션에서는 사용자 learning 발화가 0건이면 분석 job도
# 0건이라(`services/utterances.flush_pending_analysis`가 그 두 열로 묶음을 고른다) 상태가
# `no_utterances`가 되고 키가 빠진다. 여기서 재는 것은 **세는 규칙**이고, 그것을 키가 실리는
# 상태에서 관측하려면 job을 손으로 걸어야 한다 — 그래서 코치 발화에 걸었다.
async def test_drill_counts_zero_when_only_the_coach_spoke(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, COACH, COACH])
        await _job(conn, utterance_ids[0], "done")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "final"
    assert body["drill"] == {"exchanges_observed": 0, "exchanges_expected": 8}, (
        "코치 발화만 있는 세션이 exchange를 얻었다 — 힌트 반복이 「달성」으로 통과하는 H-3이다"
    )


# ③ `utterance_type != 'learning'` 행은 세지 않는다 — 세어지지도, 직전 발화로 인정되지도 않는다.
# 배치는 두 경로를 동시에 재도록 골랐다: 필터가 없으면 `user/voice_command`가 스스로 1건을
# 만들어 **2**가 된다(관례의 정본은 `plan_input.py`·`utterances.py`의 두 SQL이다).
async def test_drill_ignores_rows_that_are_not_learning_utterances(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(
            conn,
            committed_session.session_id,
            [COACH, LEARNER_COMMAND, COACH_CONFIRMATION, LEARNER],
        )
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["drill"] == {"exchanges_observed": 1, "exchanges_expected": 8}, (
        "음성 명령·확인 발화가 exchange로 세어졌다 — `utterance_type = 'learning'` 필터가 없다"
    )


# ④ 사용자 발화만 있는 세션 → `0`. 직전이 코치 발화가 아니면 전이가 아니다.
async def test_drill_counts_zero_when_only_the_learner_spoke(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [LEARNER, LEARNER])
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["drill"] == {"exchanges_observed": 0, "exchanges_expected": 8}, (
        "직전이 코치 발화가 아닌 사용자 발화가 세어졌다"
    )


# ⑤ ⛔ **단위 일치 tripwire (4판이 고친 자리)** — 정확히 12 라운드를 채우고 **사용자 발화로
# 끝난** 세션이 `12`를 낸다. 3판 방향(`speaker='agent' and prev='user'`)으로 세면 `A2…A12`의
# **11**이 나와 이 단정이 FAIL 한다. 그것이 이 테스트의 존재 이유다: 없으면 완전 순응 세션이
# 매 세션 미달로 세어지고, 결정 10이 그 미달을 「지시문을 고치는 입력」으로 쓰므로
# **산식 오차가 지시문 수정을 유도한다.**
# 미달이 아니므로 **경고도 나지 않는다** — 그 짝을 여기서 함께 고정한다.
async def test_drill_counts_twelve_for_exactly_twelve_rounds_ending_with_the_learner(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    caplog: pytest.LogCaptureFixture,
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, LEARNER] * 12)
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 12)

    with caplog.at_level(logging.INFO, logger=RESULTS_LOGGER):
        response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["drill"] == {"exchanges_observed": 12, "exchanges_expected": 12}, (
        "정확히 12 라운드를 채운 세션이 12를 내지 못했다 — 3판 방향으로 세면 11이 나온다"
    )
    assert _results_logs(caplog) == [], "미달이 아닌데 기록이 났다"


# 계획 없이 시작한 세션은 기대값이 null이라 **관측 대상이 아니다** → 응답에 `drill` 키가 없다.
# `corrections`가 실려 있는 것을 함께 단정한다 — 응답이 정상적으로 만들어진 상태에서
# 키만 빠진 것임을 고정하려면 양성 짝이 필요하다(부재 단정 하나로는 공허하게 통과한다).
async def test_drill_key_is_absent_when_the_session_started_without_a_plan(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, LEARNER])
        await _job(conn, utterance_ids[-1], "done")
        # `drill_turns_expected`를 쓰지 않는다 — 계획 없이 시작한 세션의 모양이다.

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "final"
    assert "corrections" in body
    assert "drill" not in body, "기대값이 null인데 drill 키가 실렸다 — 관측 대상이 아니다"


# ⛔ R2 상태 3개에서는 **기대값이 있어도** 키가 빠지고 **로그도 나지 않는다**(D5-4 + critic B-4).
# 리퍼가 닫은 세션도 기대값은 이미 쓰여 있고 그 `'failed'`는 `connection_failed`로 매핑되므로,
# 막지 않으면 **연결 실패마다 미달이 API와 로그에 쌓여** 결정 10이 쓰겠다는 신호가 오염된다.
# 세 테스트 모두 미달 상태(관측 1 · 기대 12)로 세팅한다 — 억제가 없으면 반드시 발동하는 모양이다.
async def test_drill_key_and_log_are_absent_in_connection_failed(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    caplog: pytest.LogCaptureFixture,
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, LEARNER])
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 12)
        await conn.execute(
            "update learning_sessions set status = 'failed' where id = $1",
            committed_session.session_id,
        )

    with caplog.at_level(logging.INFO, logger=RESULTS_LOGGER):
        response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connection_failed"
    assert "drill" not in body, "connection_failed에 drill이 실렸다 (D5-4)"
    assert _results_logs(caplog) == [], "연결 실패 세션의 미달이 로그에 쌓였다 (critic B-4)"


async def test_drill_key_and_log_are_absent_in_analyzing(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    caplog: pytest.LogCaptureFixture,
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(conn, committed_session.session_id, [COACH, LEARNER])
        await _job(conn, utterance_ids[-1], "pending")
        await _set_drill_expected(conn, committed_session.session_id, 12)

    with caplog.at_level(logging.INFO, logger=RESULTS_LOGGER):
        response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "analyzing"
    assert "drill" not in body, "analyzing에 drill이 실렸다 — 잠정 노출 금지"
    assert _results_logs(caplog) == [], "분석이 끝나지 않은 세션의 미달이 로그에 쌓였다"


async def test_drill_key_and_log_are_absent_in_no_utterances(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    caplog: pytest.LogCaptureFixture,
):
    async with db_pool.acquire() as conn:
        # 발화는 있지만 job이 0건이다 — 규칙 2의 모양이고, 억제가 없으면 미달이 세어진다.
        await _turns(conn, committed_session.session_id, [COACH, LEARNER])
        await _set_drill_expected(conn, committed_session.session_id, 12)

    with caplog.at_level(logging.INFO, logger=RESULTS_LOGGER):
        response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_utterances"
    assert "drill" not in body, "no_utterances에 drill이 실렸다 — 잠정 노출 금지"
    assert _results_logs(caplog) == [], "분석 대상이 없는 세션의 미달이 로그에 쌓였다"


# 미달이면 `warning` 한 줄에 두 수가 실린다. ⛔ `INFO`가 아닌 이유는 **H-Z** — 문서가 지정한
# 실행에서 INFO는 보이지 않는다. 그래서 레벨을 등호로 못박고, 캡처는 INFO까지 열어 둔다
# (구현이 INFO로 내면 기록은 잡히고 레벨 단정이 FAIL 한다 — 그것이 이 단정의 판별력이다).
#
# ⛔ **두 수의 「있음」만 재지 않는다 — 라벨↔숫자 결합을 잰다** (픽스 라운드 1).
# `"2" in message and "8" in message`는 **순서에 눈이 멀어** `logger.warning`의 뒤 두 인자를
# 뒤집어 *"관측 8건 / 기대 2건"*이 되어도 통과했다. API 페이로드 단정은 `DrillTurns` 생성만
# 보고 **로그 포맷은 보지 않으므로** 그 스왑을 잡는 테스트가 0건이었다. 캡틴 결정 10이
# 소비하는 것이 정확히 이 줄이라, 스왑이 들어가면 읽는 사람이 **미달을 초과로** 읽고 그
# 잘못된 신호로 지시문을 고친다 — 게이트는 초록인 채로.
async def test_drill_shortfall_logs_a_warning_carrying_both_numbers(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    caplog: pytest.LogCaptureFixture,
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(
            conn, committed_session.session_id, [COACH, LEARNER, COACH, LEARNER]
        )
        await _job(conn, utterance_ids[-1], "done")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    with caplog.at_level(logging.INFO, logger=RESULTS_LOGGER):
        response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    assert response.json()["drill"] == {"exchanges_observed": 2, "exchanges_expected": 8}
    records = _results_logs(caplog)
    assert len(records) == 1, f"미달 기록이 1건이 아니다 — {[r.getMessage() for r in records]}"
    assert records[0].levelno == logging.WARNING, (
        "미달을 WARNING이 아닌 레벨로 냈다 — H-Z: INFO는 문서가 지정한 실행에서 보이지 않는다"
    )
    message = records[0].getMessage()
    assert _labeled_number(message, "관측") == "2", (
        f"미달 로그의 「관측」이 2가 아니다 — 인자 순서나 라벨이 뒤집혔다: {message!r}"
    )
    assert _labeled_number(message, "기대") == "8", (
        f"미달 로그의 「기대」가 8이 아니다 — 인자 순서나 라벨이 뒤집혔다: {message!r}"
    )


# `partial_failure`는 `corrections`가 실리는 상태다 → `drill`도 함께 실린다.
# 같은 R2 규약을 따른다는 것이 「셋에서 뺀다」와 「둘에서 싣는다」의 두 짝으로만 고정된다.
async def test_drill_key_rides_with_partial_failure_like_corrections(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session
):
    async with db_pool.acquire() as conn:
        utterance_ids = await _turns(
            conn, committed_session.session_id, [COACH, LEARNER, COACH, LEARNER]
        )
        await _job(conn, utterance_ids[1], "done")
        await _job(conn, utterance_ids[-1], "failed")
        await _set_drill_expected(conn, committed_session.session_id, 8)

    response = await api_client.get(f"/api/sessions/{committed_session.session_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_failure"
    assert "corrections" in body
    assert body["drill"] == {"exchanges_observed": 2, "exchanges_expected": 8}
