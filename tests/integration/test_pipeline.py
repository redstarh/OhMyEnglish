"""Task 6 — 분석 파이프라인 통합 테스트 (AC W1 후반·W2·W3, 설계서 §5.2·§5.4).

`db_conn`(롤백되는 단일 트랜잭션)이 아니라 `db_pool` + `committed_session`을
쓴다. `process_analysis`는 **자기 트랜잭션을 여러 개** 연다(입력 읽기 → Claude
호출 → 결과 저장+complete) — 그게 §5.4의 요구사항이므로, 커밋 경계를 흉내내지
않고 실제로 커밋시켜야 검증이 성립한다. `committed_session`이 teardown에서
사용자를 지우고 cascade가 나머지를 걷어간다.

실제 Bedrock은 호출하지 않는다 — `fake_claude` 대역이 응답을 고정한다.
시간에 의존하는 검증(lease 만료)은 SQL로 `locked_at`을 과거로 밀어 만든다.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from app.services.analysis import PatternRow, build_prompt, load_existing_patterns, process_analysis
from app.services.jobs import LEASE, ClaimedJob, claim_next, enqueue_analyze
from app.services.utterances import UtteranceRow, save_final_transcript
from app.workers.claude_client import FakeClaudeClient

GYM_ANSWER = "I usually go to gym after work."
OFFICE_ANSWER = "I usually go to office by subway."

ARTICLE_PATTERN_KEY = "article_missing_before_place_noun"


def _finding(**overrides: Any) -> dict[str, Any]:
    finding = {
        "category": "article",
        "pattern_key": ARTICLE_PATTERN_KEY,
        "target_form": "go to the gym",
        "original_span": "go to gym",
        "correction": "go to the gym",
        "severity": "medium",
        "confidence": 0.9,
    }
    finding.update(overrides)
    return finding


def _response(*findings: dict[str, Any]) -> str:
    return json.dumps({"findings": list(findings)})


async def _save(pool: asyncpg.Pool, session_id: UUID, text: str) -> UtteranceRow:
    """확정 전사문 저장 + job 등록 (커밋된다)."""
    async with pool.acquire() as conn:
        return await save_final_transcript(conn, session_id, text)


async def _claim(pool: asyncpg.Pool) -> ClaimedJob:
    async with pool.acquire() as conn, conn.transaction():
        job = await claim_next(conn)
    assert job is not None, "claim할 job이 없다"
    return job


async def _occurrences(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            select eo.pattern_id, eo.original_span, eo.correction, eo.severity, eo.confidence,
                   u.sequence_no
              from error_occurrences eo
              join utterances u on u.id = eo.utterance_id
             where u.session_id = $1
             order by u.sequence_no, eo.created_at
            """,
            session_id,
        )


async def _patterns(pool: asyncpg.Pool, user_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select id, category, pattern_key, target_form, frequency, last_seen_at "
            "from error_patterns where user_id = $1 order by pattern_key",
            user_id,
        )


async def _job_row(pool: asyncpg.Pool, job_id: UUID) -> asyncpg.Record:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select status, attempts, last_error, locked_by from analysis_jobs where id = $1",
            job_id,
        )
    assert row is not None
    return row


# ① 두 발화에 같은 pattern_key → patterns 1행 / occurrences 2행 / frequency 2 (W2)
async def test_same_pattern_in_two_utterances_merges_into_one_pattern(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    first = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    second = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    claude = fake_claude(
        _response(_finding()),
        _response(_finding(original_span="go to office", correction="go to the office")),
    )

    for _ in range(2):
        job = await _claim(db_pool)
        await process_analysis(db_pool, claude, job)

    patterns = await _patterns(db_pool, committed_session.user_id)
    assert [record["pattern_key"] for record in patterns] == [ARTICLE_PATTERN_KEY]
    assert patterns[0]["frequency"] == 2
    occurrences = await _occurrences(db_pool, committed_session.session_id)
    assert [record["original_span"] for record in occurrences] == ["go to gym", "go to office"]
    assert {record["pattern_id"] for record in occurrences} == {patterns[0]["id"]}
    assert occurrences[0]["confidence"] == Decimal("0.90")
    # 두 job 모두 done이어야 결과 화면이 확정 표시로 넘어간다 (§5.5).
    async with db_pool.acquire() as conn:
        statuses = await conn.fetch(
            "select j.status from analysis_jobs j join utterances u on u.id = j.utterance_id "
            "where u.session_id = $1 order by u.sequence_no",
            committed_session.session_id,
        )
    assert [record["status"] for record in statuses] == ["done", "done"]
    assert first.sequence_no == 1 and second.sequence_no == 2


# ② 결과 저장 후 status 갱신 전에 죽은 job을 재실행 → 중복 없음, last_seen_at 불변 (W3)
async def test_reprocessing_the_same_utterance_is_idempotent(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    utterance = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    office_finding = _finding(original_span="go to office", correction="go to the office")
    claude = fake_claude(
        _response(_finding()),
        _response(office_finding),
        _response(office_finding),  # 재실행 — 같은 결과를 다시 받는다
    )
    for _ in range(2):
        await process_analysis(db_pool, claude, await _claim(db_pool))
    before = (await _patterns(db_pool, committed_session.user_id))[0]

    # done 이후 재등록은 허용된다(partial unique는 pending/running만) — 크래시 후
    # 같은 발화가 다시 분석되는 상황과 동일한 입력이다.
    async with db_pool.acquire() as conn, conn.transaction():
        assert await enqueue_analyze(conn, utterance.id) is not None
    await process_analysis(db_pool, claude, await _claim(db_pool))

    after = (await _patterns(db_pool, committed_session.user_id))[0]
    assert len(await _occurrences(db_pool, committed_session.session_id)) == 2
    assert after["frequency"] == 2, "frequency를 +1로 올리면 재시도마다 부풀어 오른다"
    assert after["last_seen_at"] == before["last_seen_at"], "last_seen_at은 발화 시각 기준이다"
    assert after["last_seen_at"].tzinfo is not None
    assert len(await _patterns(db_pool, committed_session.user_id)) == 1


# ③ 프롬프트에 기존 pattern_key가 주입된다 (§5.6 재사용 우선)
async def test_prompt_carries_the_users_existing_pattern_keys(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    claude: FakeClaudeClient = fake_claude(
        _response(_finding()),
        _response(_finding(original_span="go to office", correction="go to the office")),
    )

    for _ in range(2):
        await process_analysis(db_pool, claude, await _claim(db_pool))

    first_prompt, second_prompt = claude.prompts
    # 첫 발화 시점에는 기존 패턴이 없고, 두 번째 발화는 첫 분석의 산출물을 본다.
    assert ARTICLE_PATTERN_KEY not in first_prompt
    assert GYM_ANSWER in first_prompt
    assert ARTICLE_PATTERN_KEY in second_prompt
    assert OFFICE_ANSWER in second_prompt
    async with db_pool.acquire() as conn:
        rows = await load_existing_patterns(conn, committed_session.user_id)
    assert rows == [
        PatternRow(category="article", pattern_key=ARTICLE_PATTERN_KEY, target_form="go to the gym")
    ]
    assert second_prompt == build_prompt(OFFICE_ANSWER, rows)


# ④ 검증 실패 응답 → fail_or_retry 경로 (W7 연동). 결과는 하나도 쓰이지 않는다.
@pytest.mark.parametrize(
    "raw",
    [
        '{"findings": [{"category": "noun", "pattern_key": "noun_x", "target_form": "x", '
        '"original_span": "x", "correction": "y", "severity": "medium", "confidence": 0.5}]}',
        "여기 분석 결과입니다: 관사가 빠졌습니다.",
        '{"findings": [{"category": "article", "pattern_key": "article_a", "target_form": "x", '
        '"original_span": "x", "correction": "y", "severity": "critical", "confidence": 0.5}]}',
    ],
)
async def test_invalid_claude_output_sends_the_job_through_fail_or_retry(
    db_pool: asyncpg.Pool, committed_session, fake_claude, raw: str
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    job = await _claim(db_pool)

    await process_analysis(db_pool, fake_claude(raw), job)

    row = await _job_row(db_pool, job.id)
    assert row["status"] == "pending"  # 상한 미달이므로 백오프 후 재시도
    assert row["last_error"] is not None
    assert row["locked_by"] is None
    assert await _occurrences(db_pool, committed_session.session_id) == []
    assert await _patterns(db_pool, committed_session.user_id) == []


# ④ 보강 — Claude 호출 자체가 터져도 워커로 예외가 새지 않고 큐에 보고된다
async def test_claude_call_failure_is_reported_to_the_queue(
    db_pool: asyncpg.Pool, committed_session
):
    class _ExplodingClaude:
        async def analyze(self, prompt: str) -> str:
            raise TimeoutError("bedrock read timeout")

    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    job = await _claim(db_pool)

    await process_analysis(db_pool, _ExplodingClaude(), job)

    row = await _job_row(db_pool, job.id)
    assert row["status"] == "pending"
    assert "bedrock read timeout" in row["last_error"]


# ⑤ 한 발화에 같은 패턴 2건 → occurrences 2행 보존 (replace가 복수 발생을 유지한다)
async def test_two_findings_of_one_pattern_in_a_single_utterance_are_both_kept(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, "I go to gym and go to office.")
    claude = fake_claude(
        _response(
            _finding(),
            _finding(original_span="go to office", correction="go to the office"),
        )
    )

    await process_analysis(db_pool, claude, await _claim(db_pool))

    occurrences = await _occurrences(db_pool, committed_session.session_id)
    assert [record["original_span"] for record in occurrences] == ["go to gym", "go to office"]
    patterns = await _patterns(db_pool, committed_session.user_id)
    assert len(patterns) == 1
    assert patterns[0]["frequency"] == 2


# 오류 0건도 정상 done이다 — 검증 거부와 구분된다. 그리고 이전 결과는 지워지고
# frequency가 다시 계산된다(재분석에서 사라진 패턴이 옛 발생 수를 남기면 안 된다).
async def test_zero_findings_completes_the_job_and_clears_previous_occurrences(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(_finding()), _response())
    await process_analysis(db_pool, claude, await _claim(db_pool))
    assert (await _patterns(db_pool, committed_session.user_id))[0]["frequency"] == 1

    async with db_pool.acquire() as conn, conn.transaction():
        await enqueue_analyze(conn, utterance.id)
    second_job = await _claim(db_pool)
    await process_analysis(db_pool, claude, second_job)

    assert (await _job_row(db_pool, second_job.id))["status"] == "done"
    assert await _occurrences(db_pool, committed_session.session_id) == []
    pattern = (await _patterns(db_pool, committed_session.user_id))[0]
    assert pattern["frequency"] == 0
    assert pattern["last_seen_at"] is None


# lease를 잃은 워커의 결과는 통째로 버려진다 (§5.4) — complete가 False면 롤백이다.
async def test_result_write_is_rolled_back_when_the_lease_was_lost(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    stale = await _claim(db_pool)
    # lease 만료 → 다른 claim이 job을 회수한다(실시간 대기 없이 SQL로 만든다).
    async with db_pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set locked_at = now() - $2::interval where id = $1",
            stale.id,
            LEASE * 2,
        )
    current = await _claim(db_pool)
    assert current.id == stale.id
    assert current.lease_token != stale.lease_token

    await process_analysis(db_pool, fake_claude(_response(_finding())), stale)

    assert await _occurrences(db_pool, committed_session.session_id) == []
    assert await _patterns(db_pool, committed_session.user_id) == []
    row = await _job_row(db_pool, stale.id)
    assert row["status"] == "running"  # 낡은 시도가 상태를 오염시키지 않았다
    assert row["locked_by"] == current.lease_token


# 신규 key가 형식을 어기면 저장하지 않는다 — 규격 밖 key는 다음 세션에 병합되지
# 않는 쌍둥이 패턴을 만든다 (§5.6).
async def test_new_pattern_key_violating_the_format_is_rejected(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    job = await _claim(db_pool)

    await process_analysis(
        db_pool, fake_claude(_response(_finding(pattern_key="missing_article_before_gym"))), job
    )

    row = await _job_row(db_pool, job.id)
    assert row["status"] == "pending"
    assert "missing_article_before_gym" in row["last_error"]
    assert await _patterns(db_pool, committed_session.user_id) == []


# 기존 key 재사용은 형식을 보지 않는다 — 근거 문서의 `past_tense_in_work_update`처럼
# 접두 형식이 아닌 key가 이미 있을 수 있고, 거부하면 재사용 규칙과 충돌한다.
async def test_existing_pattern_key_is_reused_regardless_of_its_format(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    legacy_key = "past_tense_in_work_update"
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'verb_tense', $2, 'I finished the report')",
            committed_session.user_id,
            legacy_key,
        )
    await _save(db_pool, committed_session.session_id, "I finish the report yesterday.")
    job = await _claim(db_pool)

    await process_analysis(
        db_pool,
        fake_claude(
            _response(
                _finding(
                    category="verb_tense",
                    pattern_key=legacy_key,
                    target_form="I finished the report",
                    original_span="I finish the report yesterday",
                    correction="I finished the report yesterday",
                )
            )
        ),
        job,
    )

    assert (await _job_row(db_pool, job.id))["status"] == "done"
    patterns = await _patterns(db_pool, committed_session.user_id)
    assert [record["pattern_key"] for record in patterns] == [legacy_key]
    assert patterns[0]["frequency"] == 1


# 대상 발화가 없는 job(`summarize_session`)은 이번 파이프라인이 처리할 수 없다.
# 조용히 넘기면 job이 영원히 running으로 남아 결과 API가 세션을 "분석 중"에 고정한다.
async def test_job_without_an_utterance_target_is_reported_as_failed(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into analysis_jobs (job_type, session_id) values ('summarize_session', $1)",
            committed_session.session_id,
        )
    job = await _claim(db_pool)
    assert job.utterance_id is None
    claude: FakeClaudeClient = fake_claude()

    await process_analysis(db_pool, claude, job)

    row = await _job_row(db_pool, job.id)
    assert row["status"] == "pending"
    assert "no utterance target" in row["last_error"]
    assert claude.prompts == [], "처리할 수 없는 job으로 Claude를 호출하면 안 된다"
