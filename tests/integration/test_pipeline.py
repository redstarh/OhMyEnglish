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
from conftest import default_finding, job_row

from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.services.analysis import PatternRow, build_prompt, load_existing_patterns, process_analysis
from app.services.jobs import LEASE, ClaimedJob, enqueue_analyze
from app.services.utterances import (
    UtteranceRow,
    flush_pending_analysis,
    save_final_transcript,
)
from app.workers.analysis_worker import claim_one
from app.workers.claude_client import FakeClaudeClient

# 픽스처 발화의 소유자는 `app.audio_gateway.fixtures` 하나다 — 스텁이 재생하는
# 문장과 여기서 기대하는 문장이 갈라지지 않도록 문장을 다시 적지 않는다.
GYM_ANSWER = FIXTURE_TURNS[0][1]
OFFICE_ANSWER = FIXTURE_TURNS[1][1]

ARTICLE_PATTERN_KEY = "article_missing_before_place_noun"


def _response(*findings: dict[str, Any]) -> str:
    return json.dumps({"findings": list(findings)})


AGENT_ACK = "Tell me more."


async def _save(
    pool: asyncpg.Pool, session_id: UUID, text: str, *, close_turn: bool = True
) -> UtteranceRow:
    """사용자 확정 전사문 저장 + **턴 닫기**까지 (커밋된다). 반환값은 사용자 발화 행.

    I-1 이후 분석 job은 저장이 아니라 턴 경계에서 걸린다 — 사용자 발화만 저장하면
    claim할 job이 없다. 게이트웨이와 같은 순서로(`audio_gateway/session.py`) agent
    final을 하나 끼워 턴을 닫고 flush한다. 그래서 세션의 `sequence_no`는 user 1 ·
    agent 2 · user 3 …으로 번갈아 오른다. `enqueue_analyze`를 직접 부르지 않는
    이유는 그러면 병합 경로를 우회해 실제와 다른 입력을 검증하기 때문이다.

    `close_turn=False`면 턴을 열어 둔다 — 쪼개진 조각을 쌓는 시나리오용이다.
    """
    async with pool.acquire() as conn:
        row = await save_final_transcript(conn, session_id, text)
        if close_turn:
            await _close_turn(conn, session_id)
    return row


async def _close_turn(conn: asyncpg.Connection, session_id: UUID) -> None:
    await save_final_transcript(conn, session_id, AGENT_ACK, speaker="agent")
    await flush_pending_analysis(conn, session_id)


async def _claim(pool: asyncpg.Pool) -> ClaimedJob:
    job = await claim_one(pool)
    assert job is not None, "claim할 job이 없다"
    return job


async def _occurrences(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            select eo.id, eo.pattern_id, eo.original_span, eo.correction, eo.severity,
                   eo.confidence, u.sequence_no
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
        return await job_row(conn, job_id)


# I-1 T0③ — 쪼개진 사용자 final 묶음은 **이어붙인 한 문장**으로 분석된다.
# 조각을 따로 보내면 분석기가 "주어 없음"·"목적어 없음"을 찾아낸다 — 주어가 앞
# 조각에 있으니 당연하고, 그래서 실물 마이크 1회에서 오탐 패턴 2개가 생겼다.
async def test_fragmented_finals_are_analyzed_as_one_merged_transcript(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    fragments = ("I will plan the", "active plan", "for the client.")
    for fragment in fragments:
        await _save(db_pool, committed_session.session_id, fragment, close_turn=False)
    async with db_pool.acquire() as conn:
        await _close_turn(conn, committed_session.session_id)
    claude = fake_claude(_response())

    await process_analysis(db_pool, claude, await _claim(db_pool))

    assert len(claude.prompts) == 1, "묶음 하나에 Claude 호출은 1회다"
    assert " ".join(fragments) in claude.prompts[0]


# I-1 경계 — 분석 대상이 **아닌** 발화에 직접 등록된 job은 병합하지 않는다.
# `_LOAD_INPUT_SQL`의 `else t.sequence_no` 분기가 지키는 "이전 동작 유지"다. 그 분기를
# `else 1`로 바꿔도 전체 스위트가 통과했으므로(코드 리뷰 실측) 여기서 못 박는다 —
# 그 뮤테이션은 "세션 처음부터 그 발화까지 전부 병합"이라는 명백한 오답이다.
async def test_a_job_on_non_analyzable_speech_reads_only_that_utterance(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER, close_turn=False)
    await _save(db_pool, committed_session.session_id, OFFICE_ANSWER, close_turn=False)
    async with db_pool.acquire() as conn:
        agent = await save_final_transcript(
            conn, committed_session.session_id, AGENT_ACK, speaker="agent"
        )
        async with conn.transaction():
            assert await enqueue_analyze(conn, agent.id) is not None
    claude = fake_claude(_response())

    await process_analysis(db_pool, claude, await _claim(db_pool))

    assert AGENT_ACK in claude.prompts[0]
    assert GYM_ANSWER not in claude.prompts[0], "분석 대상이 아닌 발화에 앞 묶음이 붙었다"
    assert OFFICE_ANSWER not in claude.prompts[0]


# ⚠️ **`_LOAD_INPUT_SQL`의 `order by u.sequence_no`에는 테스트가 없다 — 지우지 말 것.**
# 뮤테이션(order by 제거)이 전체 스위트를 통과한다(실측). 그래서 테스트를 만들려고
# 뒤 조각을 먼저 insert해 힙 순서를 역전시켜 봤지만 **그래도 통과한다**: 계획은 Seq Scan
# 인데(`explain` 확인) 앞선 테스트가 지운 행의 빈 공간을 FSM이 재사용하므로 물리 순서를
# 테스트에서 통제할 수 없다. 즉 이 가드는 **위반을 공개 경로로 재현할 수 없는** 종류다 —
# 커버리지가 없다는 것이 불필요하다는 뜻이 아니다. 계획이 병렬 Seq Scan이나 Bitmap Heap
# Scan으로 바뀌면 어순이 실제로 깨지고, 그때 학습자는 뒤섞인 문장으로 교정을 받는다.


# ① 두 발화에 같은 pattern_key → patterns 1행 / occurrences 2행 / frequency 2 (W2)
async def test_same_pattern_in_two_utterances_merges_into_one_pattern(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    first = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    second = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    claude = fake_claude(
        _response(default_finding()),
        _response(default_finding(original_span="go to office", correction="go to the office")),
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
    # 턴마다 agent final이 하나 끼므로 사용자 발화는 1·3번이다 (`_save` docstring).
    assert first.sequence_no == 1 and second.sequence_no == 3


# ② 결과 저장 후 status 갱신 전에 죽은 job을 재실행 → 중복 없음, last_seen_at 불변 (W3)
async def test_reprocessing_the_same_utterance_is_idempotent(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    utterance = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    office_finding = default_finding(original_span="go to office", correction="go to the office")
    claude = fake_claude(
        _response(default_finding()),
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
        _response(default_finding()),
        _response(default_finding(original_span="go to office", correction="go to the office")),
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


# G-8 — **발음 패턴은 문법 프롬프트 재료에 실리지 않는다.** `error_patterns.frequency`를 두 writer가
# 서로 다른 규약으로 센다 — 문법은 `error_occurrences` 행 수, 발음은 시도 수를 다시 센다.
# 발음 키가 프롬프트에 실리면 모델이 그것을 글자 그대로 재사용할 수 있고, 그러면 한 행을 두 writer가
# 번갈아 덮는다. 캡틴 결정(2026-08-31 "두 번 틀리면 두 번 틀린 것으로 기록") → **(나) 경로 분리**:
# 스키마를 바꾸지 않고 충돌 경로 자체를 없앤다. 제외 카테고리의 소유자는
# `services/analysis.py`의 `UNJUDGEABLE_CATEGORY`다.
async def test_existing_patterns_exclude_the_pronunciation_category(db_pool, committed_session):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'article', 'article_missing_before_place_noun', 'go to the gym'), "
            "       ($1, 'pronunciation_intonation', 'pronunciation_th_as_s', 'think')",
            committed_session.user_id,
        )

        rows = await load_existing_patterns(conn, committed_session.user_id)

    assert [row.pattern_key for row in rows] == ["article_missing_before_place_noun"], (
        "발음 패턴이 문법 프롬프트 재료에 실렸다 — frequency 이중 writer 충돌 경로가 열린다"
    )


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
            default_finding(),
            default_finding(original_span="go to office", correction="go to the office"),
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
    claude = fake_claude(_response(default_finding()), _response())
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
# Fix round 1 (M-8): **이미 확정된 결과가 보존되는지**까지 단정한다. 그래서 낡은 시도를
# 재분석 job으로 만든다 — replace의 delete가 트랜잭션을 벗어나면(부분 롤백) 새 결과는
# 안 남고 기존 결과만 지워져, 그 발화의 교정이 조용히 사라진다. 처음 분석되는 발화로는
# 지울 것이 없어 이 버그를 못 잡는다.
async def test_result_write_is_rolled_back_when_the_lease_was_lost(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(
        _response(default_finding()),
        _response(default_finding(original_span="go to gym", correction="go to the gym")),
    )
    await process_analysis(db_pool, claude, await _claim(db_pool))  # 1차 분석 성공
    before_occurrences = await _occurrences(db_pool, committed_session.session_id)
    before_pattern = (await _patterns(db_pool, committed_session.user_id))[0]
    assert len(before_occurrences) == 1

    # 같은 발화의 재분석 job(크래시 후 재실행 상황)을 claim한 뒤 lease를 잃는다.
    async with db_pool.acquire() as conn, conn.transaction():
        await enqueue_analyze(conn, utterance.id)
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

    await process_analysis(db_pool, claude, stale)

    # 낡은 시도는 아무 흔적도 남기지 않는다 — 지우지도, 새로 쓰지도 못한다.
    after_occurrences = await _occurrences(db_pool, committed_session.session_id)
    assert [record["id"] for record in after_occurrences] == [
        record["id"] for record in before_occurrences
    ], "롤백이 부분적이어서 이미 확정된 occurrence가 지워졌다"
    after_pattern = (await _patterns(db_pool, committed_session.user_id))[0]
    assert after_pattern["id"] == before_pattern["id"]
    assert after_pattern["frequency"] == before_pattern["frequency"] == 1
    assert after_pattern["last_seen_at"] == before_pattern["last_seen_at"]
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

    claude = fake_claude(_response(default_finding(pattern_key="missing_article_before_gym")))
    await process_analysis(db_pool, claude, job)

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
                default_finding(
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


# --- Fix round 1 ---

# I-2 회귀 방어: Claude 호출은 트랜잭션 **밖**이어야 한다 (§5.4). 호출을 트랜잭션
# 안으로 옮기는 변형(뮤테이션)이 기존 테스트를 모두 통과했으므로, 호출 시점에
# "트랜잭션을 연 채 대기하는 커넥션이 없다"를 직접 관측해 고정한다.
_IDLE_IN_TRANSACTION_SQL = """
select count(*)
  from pg_stat_activity
 where state = 'idle in transaction'
   and datname = current_database()
   and pid <> pg_backend_pid()
"""


class _TransactionSpyClaude:
    """analyze 시점의 `idle in transaction` 커넥션 수를 기록하는 Claude 대역."""

    def __init__(self, pool: asyncpg.Pool, response: str) -> None:
        self._pool = pool
        self._response = response
        self.idle_in_transaction: int | None = None
        self.prompts: list[str] = []

    async def analyze(self, prompt: str) -> str:
        self.prompts.append(prompt)
        async with self._pool.acquire() as conn:
            self.idle_in_transaction = await conn.fetchval(_IDLE_IN_TRANSACTION_SQL)
        return self._response


async def test_claude_is_called_outside_any_open_transaction(
    db_pool: asyncpg.Pool, committed_session
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = _TransactionSpyClaude(db_pool, _response(default_finding()))

    await process_analysis(db_pool, claude, await _claim(db_pool))

    assert claude.idle_in_transaction == 0, (
        "Claude 호출 동안 트랜잭션을 연 커넥션이 있다 — 그 시간 내내 행 잠금과 "
        "스냅샷을 붙들어 다른 claim을 막는다 (설계서 §5.4)"
    )
    assert len(await _occurrences(db_pool, committed_session.session_id)) == 1


# I-3 Ruling: 빈/공백 전사문은 "분석할 것이 없다 = 오류 0건"이다. Claude를 호출하지
# 않고 replace로 정리한 뒤 done으로 끝낸다 — 결정론적으로 실패하는 입력을 5회
# 재시도한 끝에 partial_failure로 표시하는 것은 사용자에게 거짓 신호다.
@pytest.mark.parametrize("transcript", ["", "   ", "\n"])
async def test_blank_transcript_completes_with_zero_findings(
    db_pool: asyncpg.Pool, committed_session, fake_claude, transcript: str
):
    await _save(db_pool, committed_session.session_id, transcript)
    job = await _claim(db_pool)
    claude: FakeClaudeClient = fake_claude()

    await process_analysis(db_pool, claude, job)

    assert (await _job_row(db_pool, job.id))["status"] == "done"
    assert await _occurrences(db_pool, committed_session.session_id) == []
    assert claude.prompts == [], "빈 전사문으로 토큰을 태우면 안 된다"


async def test_blank_transcript_still_replaces_previous_occurrences(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    # 발화가 재전사되어 빈 문자열로 바뀐 경우에도 replace 규칙은 그대로다.
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding()))
    await process_analysis(db_pool, claude, await _claim(db_pool))
    assert len(await _occurrences(db_pool, committed_session.session_id)) == 1
    async with db_pool.acquire() as conn, conn.transaction():
        await conn.execute("update utterances set transcript = '' where id = $1", utterance.id)
        await enqueue_analyze(conn, utterance.id)

    await process_analysis(db_pool, fake_claude(), await _claim(db_pool))

    assert await _occurrences(db_pool, committed_session.session_id) == []
    pattern = (await _patterns(db_pool, committed_session.user_id))[0]
    assert pattern["frequency"] == 0
    assert pattern["last_seen_at"] is None


# I-5: 공백·대소문자만 다른 pattern_key는 기존 패턴으로 병합된다. 실측으로는 앞공백
# 하나에 신규 key로 판정되어 형식 검증에서 거부됐고, 그 발화는 5회 재시도 후 failed가
# 됐다 — 병합이 앱의 핵심 약속이므로 표기 흔들림이 그것을 깨서는 안 된다.
@pytest.mark.parametrize(
    "returned_key",
    [
        f"  {ARTICLE_PATTERN_KEY}",
        f"{ARTICLE_PATTERN_KEY}\n",
        "Article_Missing_Before_Place_Noun",
        " ARTICLE_MISSING_BEFORE_PLACE_NOUN ",
    ],
)
async def test_case_and_whitespace_variants_merge_into_the_existing_pattern(
    db_pool: asyncpg.Pool, committed_session, fake_claude, returned_key: str
):
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    claude = fake_claude(
        _response(default_finding()),
        _response(
            default_finding(
                pattern_key=returned_key,
                original_span="go to office",
                correction="go to the office",
            )
        ),
    )

    for _ in range(2):
        await process_analysis(db_pool, claude, await _claim(db_pool))

    patterns = await _patterns(db_pool, committed_session.user_id)
    assert [record["pattern_key"] for record in patterns] == [ARTICLE_PATTERN_KEY]
    assert patterns[0]["frequency"] == 2
    assert len(await _occurrences(db_pool, committed_session.session_id)) == 2


# --- Fix round 3 (F-2) ---
#
# `target_form`은 **패턴 수준의 일반형**이고 문장별 교정은 `error_occurrences.correction`이
# 담당한다(캡틴 결정 선택지 B). 두 값은 서로 다른 테이블에서 독립적으로 선택되므로
# (패턴 테이블 vs 대표 occurrence — `services/results.py`), 한 발화에서 같은 패턴이 두 번
# 나올 때 저장이 둘을 뒤섞지 않는다는 것을 고정한다.
#
# 이 테스트는 프롬프트 수정 **전에도 통과한다** — F-2의 원인은 저장 로직이 아니라 Claude가
# 내놓은 `target_form`의 내용(문장별 교정문)이었기 때문이다. 그래서 이 파일이 막는 것은
# "앞으로 누군가 `target_form`을 occurrence의 `correction`에서 채우는 것"이고, 의미 자체의
# red-green 근거는 프롬프트 계약 테스트(`tests/unit/test_analysis.py`)에 있다.
VERB_TENSE_PATTERN_KEY = "verb_tense_past_simple_yesterday"
# 1차수 F-2가 관측된 그 발화. 한 문장에 verb_tense 오류가 두 곳 있다.
TWO_ERROR_UTTERANCE = "Yesterday I go to the client meeting and present the project status."
GENERALIZED_TARGET_FORM = "Yesterday + 동사 과거형"


async def test_pattern_target_form_is_not_any_occurrence_correction(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, TWO_ERROR_UTTERANCE)
    claude = fake_claude(
        _response(
            default_finding(
                category="verb_tense",
                pattern_key=VERB_TENSE_PATTERN_KEY,
                target_form=GENERALIZED_TARGET_FORM,
                original_span="Yesterday I go",
                correction="Yesterday I went",
            ),
            default_finding(
                category="verb_tense",
                pattern_key=VERB_TENSE_PATTERN_KEY,
                target_form=GENERALIZED_TARGET_FORM,
                original_span="and present",
                correction="and presented",
            ),
        )
    )

    await process_analysis(db_pool, claude, await _claim(db_pool))

    patterns = await _patterns(db_pool, committed_session.user_id)
    assert [record["pattern_key"] for record in patterns] == [VERB_TENSE_PATTERN_KEY]
    assert patterns[0]["frequency"] == 2
    assert patterns[0]["target_form"] == GENERALIZED_TARGET_FORM
    occurrences = await _occurrences(db_pool, committed_session.session_id)
    # 문장별 교정은 occurrence마다 그대로 남고, 패턴의 목표 형태는 그 어느 쪽도 아니다 —
    # 대표 occurrence가 어느 것으로 뽑혀도 카드의 목표 형태가 다른 문장을 가리키지 않는다.
    assert [record["correction"] for record in occurrences] == [
        "Yesterday I went",
        "and presented",
    ]
    assert patterns[0]["target_form"] not in {record["correction"] for record in occurrences}


# 다음 발화의 프롬프트에 그 일반형이 그대로 주입돼야 재사용(§5.6)이 성립한다.
async def test_the_next_prompt_carries_the_stored_generalized_target_form(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    await _save(db_pool, committed_session.session_id, TWO_ERROR_UTTERANCE)
    claude = fake_claude(
        _response(
            default_finding(
                category="verb_tense",
                pattern_key=VERB_TENSE_PATTERN_KEY,
                target_form=GENERALIZED_TARGET_FORM,
                original_span="Yesterday I go",
                correction="Yesterday I went",
            )
        )
    )
    await process_analysis(db_pool, claude, await _claim(db_pool))

    async with db_pool.acquire() as conn:
        existing = await load_existing_patterns(conn, committed_session.user_id)
    prompt = build_prompt(GYM_ANSWER, existing)

    assert GENERALIZED_TARGET_FORM in prompt
    assert VERB_TENSE_PATTERN_KEY in prompt


# ── 슬라이스 1 — 연습 상황 저장 (AS9, 학습 코치 설계서 §8.2) ────────────────────

PRACTICE_CONTEXTS = [
    "퇴근 후 운동 계획 말하기",
    "동료에게 오늘 일정 알려주기",
    "회의에서 진행 상황 한 줄 보고",
]


async def _stored_contexts(pool: asyncpg.Pool, utterance_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select suggested_contexts from error_occurrences where utterance_id = $1",
            utterance_id,
        )


# AS9 전단 — 모델이 낸 상황 3개가 보존된다. 없으면 슬라이스 2가 질문을 만들 재료가 없고
# 소급도 불가능하다(§8.2).
async def test_analysis_stores_the_suggested_contexts_of_a_finding(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding(suggested_contexts=PRACTICE_CONTEXTS)))

    await process_analysis(db_pool, claude, await _claim(db_pool))

    rows = await _stored_contexts(db_pool, utterance.id)
    assert [json.loads(row["suggested_contexts"]) for row in rows] == [PRACTICE_CONTEXTS]


# 없음은 null 하나다 — 빈 배열도 함께 쓰면 "모델이 안 냈다"와 "빈 배열을 냈다"가 갈린다.
async def test_analysis_leaves_suggested_contexts_null_when_the_model_omits_them(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding()))

    await process_analysis(db_pool, claude, await _claim(db_pool))

    rows = await _stored_contexts(db_pool, utterance.id)
    assert [row["suggested_contexts"] for row in rows] == [None]


# AS9 후단 — "재분석(replace) 후에도 최신 값이 남는다". 이것이 없으면 replace가 낡은 값을
# 남겨도 게이트가 통과한다.
async def test_reanalysis_replaces_the_stored_suggested_contexts(
    db_pool: asyncpg.Pool, committed_session, fake_claude
):
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    first = ["퇴근 후 운동 계획 말하기"]
    await process_analysis(
        db_pool,
        fake_claude(_response(default_finding(suggested_contexts=first))),
        await _claim(db_pool),
    )

    async with db_pool.acquire() as conn:
        await enqueue_analyze(conn, utterance.id)
    await process_analysis(
        db_pool,
        fake_claude(_response(default_finding(suggested_contexts=PRACTICE_CONTEXTS))),
        await _claim(db_pool),
    )

    rows = await _stored_contexts(db_pool, utterance.id)
    assert len(rows) == 1, "replace가 이전 occurrence를 남겼다"
    assert json.loads(rows[0]["suggested_contexts"]) == PRACTICE_CONTEXTS
