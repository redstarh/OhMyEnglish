"""발음 패턴의 복습 주기 — 설계서 `2026-09-08-pronunciation-review-cycle-design.md`.

`TASK-44`가 닫는 것은 하나다: **발음 패턴의 `next_review_at`이 항상 비어 있어 복습 목록에
못 들어오고, 그래서 초점 후보에서도 구조적으로 제외되던 것.**

세 층으로 나눠 본다.

1. **이력 쿼리 분기** — `recompute`가 `category`를 읽고 발음 이력을 쓰는가(§5.2·§5.3).
   `fold_stages`는 순수 함수라 이미 `test_review.py`가 간격 경계를 전부 덮었다 —
   **여기서 간격 산수를 다시 세지 않는다.** 이 파일이 재는 것은 *어느 표에서 읽는가*다.
2. **재계산 트리거** — `correct` 판정이 재계산을 발화시키는가(§5.5). 그것이 이 설계가
   닫는 「구현 공백 ④」의 실제 자리다.
3. **프롬프트 문구** — 발음이 초점 원천이 아니라는 문장이 교체됐는가(§5.6 ①).

⚠️ **시각을 테스트가 정한다.** 발음 경로의 앵커는 `resolved_at`이고(§3.3) 그것이
`utterances.created_at`이 아닌 것이 이 설계의 판정 하나다 — 시각을 통제하지 않으면
어느 컬럼을 읽는지 단정할 수 없다. **발화 행을 아예 만들지 않는 테스트가 그 증거다.**
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.plan import build_plan_prompt
from app.services.pronunciation import record_attempt, refresh_review, resolve_dangling
from app.services.review import STAGE_DAYS, load_due_reviews, recompute

USER_ID = UUID("00000000-0000-0000-0000-000000000044")
SOUND = "an_as_a"
PATTERN_KEY = f"pronunciation_{SOUND}"
# 시범 문장. ⛔ 이것이 `scenario_context`에 들어가야 한다 — 소리 키(`an_as_a`)가 아니다(§5.4).
SENTENCE = "I had a project meeting yesterday."
# KST 정오라 어느 타임존으로 읽어도 달력 날짜가 갈리지 않는다.
T0 = datetime.fromisoformat("2026-09-01T12:00:00+09:00")

_SEQ = iter(range(1, 10_000))


async def _seed(conn: asyncpg.Connection) -> UUID:
    """user → session 한 벌. 패턴은 테스트가 필요할 때 따로 만든다."""
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Pronunciation Review', 'Asia/Seoul', 'A2')",
        USER_ID,
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    assert isinstance(session_id, UUID)
    return session_id


async def _pronunciation_pattern(conn: asyncpg.Connection) -> UUID:
    """`link_pattern`의 upsert가 만드는 것과 **같은 모양**의 행. `target_form`이 소리 키다."""
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'pronunciation_intonation', $2, $3) returning id",
        USER_ID,
        PATTERN_KEY,
        SOUND,
    )
    assert isinstance(pattern_id, UUID)
    return pattern_id


async def _attempt(
    conn: asyncpg.Connection,
    session_id: UUID,
    outcome: str,
    at: datetime | None,
    *,
    pattern_id: UUID | None = None,
    sound: str = SOUND,
    sentence: str = SENTENCE,
) -> UUID:
    """발음 시도 1행.

    ⚠️ `pattern_id`의 기본값이 `None`인 것이 의도다 — 실제로 `correct` 행은 `pattern_id`가
    **영원히 null**이고(§2의 ④) 그래서 이력 쿼리가 `target_sound`로 이어야 한다.
    ⚠️ 발화 행을 만들지 않는다(`utterance_id` null). 앵커가 `resolved_at`이라는 §3.3의
    판정이 이 부재로 증명된다 — `created_at`을 읽으면 이 테스트들이 통과할 수 없다.
    """
    attempt_id = await conn.fetchval(
        "insert into pronunciation_attempts "
        "(session_id, pattern_id, target_form, target_sound, outcome, resolved_at) "
        "values ($1, $2, $3, $4, $5, $6) returning id",
        session_id,
        pattern_id,
        sentence,
        sound,
        outcome,
        at,
    )
    assert isinstance(attempt_id, UUID)
    return attempt_id


async def _pattern_row(conn: asyncpg.Connection, pattern_id: UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        "select next_review_at, mastery_score from error_patterns where id = $1", pattern_id
    )
    assert row is not None
    return row


async def _task_rows(conn: asyncpg.Connection, pattern_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "select review_stage, status, due_at, scenario_context, task_type from review_tasks "
        "where pattern_id = $1 order by review_stage",
        pattern_id,
    )


def _stages(rows: list[asyncpg.Record]) -> list[tuple[int, str]]:
    return [(row["review_stage"], row["status"]) for row in rows]


# ── ① 이력 쿼리 분기 (§5.2·§5.3) ─────────────────────────────────────────────


# 이 설계가 닫는 것의 핵심 한 줄: 발음 `incorrect` 하나로 예정일이 생긴다.
# 지금은 `_HISTORY_SQL`이 `error_occurrences`·`pattern_attempts`만 보므로 relapse가 없다.
@pytest.mark.asyncio
async def test_an_incorrect_pronunciation_attempt_schedules_the_first_stage(
    db_conn: asyncpg.Connection,
):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, pattern_id=pattern_id)

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == T0 + timedelta(days=STAGE_DAYS[0])
    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] == T0 + timedelta(days=STAGE_DAYS[0])


# `correct` 행은 `pattern_id`가 null이다 — `target_sound`로 잇지 않으면 단계가 오르지 않는다.
@pytest.mark.asyncio
async def test_a_correct_attempt_without_a_pattern_id_still_advances_the_stage(
    db_conn: asyncpg.Connection,
):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, pattern_id=pattern_id)
    due = T0 + timedelta(days=STAGE_DAYS[0])
    await _attempt(db_conn, session_id, "correct", due)  # pattern_id 없음 — 실제 모양

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 2
    assert state.next_review_at == due + timedelta(days=STAGE_DAYS[1])


# `pending`·`unclear`는 양쪽에서 빠진다(§3.2). `pending`은 CHECK 때문에 `resolved_at`이 null이다.
@pytest.mark.asyncio
async def test_pending_and_unclear_attempts_do_not_schedule_anything(
    db_conn: asyncpg.Connection,
):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "pending", None, pattern_id=pattern_id)
    await _attempt(db_conn, session_id, "unclear", T0, pattern_id=pattern_id)

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at is None
    assert await _task_rows(db_conn, pattern_id) == []


# 다른 소리의 시도가 이 패턴의 이력에 섞이지 않는다.
@pytest.mark.asyncio
async def test_another_sound_does_not_leak_into_this_pattern(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, sound="th_as_s", sentence="Thanks a lot.")

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at is None


# `target_sound`의 앞뒤 공백은 upsert가 `btrim`으로 정규화한다 — 이력 쿼리도 같아야 한다.
@pytest.mark.asyncio
async def test_the_history_query_trims_the_target_sound(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, sound=f"  {SOUND} ")

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at == T0 + timedelta(days=STAGE_DAYS[0])


# ⛔ §5.4 — 연습할 것은 **문장**이다. 소리 키를 넣으면 1차수 F-2와 같은 부류의 오류다.
@pytest.mark.asyncio
async def test_the_review_task_carries_the_sentence_not_the_sound_key(
    db_conn: asyncpg.Connection,
):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, pattern_id=pattern_id)

    await recompute(db_conn, pattern_id)

    rows = await _task_rows(db_conn, pattern_id)
    assert len(rows) == 1
    assert rows[0]["scenario_context"] == SENTENCE
    assert rows[0]["scenario_context"] != SOUND
    assert rows[0]["task_type"] == "rephrase"  # 기존 값역 — 마이그레이션 없음(§5.4)


# 가장 **최근** incorrect의 문장이 실린다 — 문법이 최신 `original_span`을 쓰는 것과 같은 자리.
@pytest.mark.asyncio
async def test_the_task_uses_the_most_recent_incorrect_sentence(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, sentence="An older sentence.")
    later = T0 + timedelta(days=2)
    await _attempt(db_conn, session_id, "incorrect", later, sentence=SENTENCE)

    await recompute(db_conn, pattern_id)

    rows = await _task_rows(db_conn, pattern_id)
    assert rows[0]["scenario_context"] == SENTENCE


# 문법 패턴은 건드리지 않는다 — 분기가 발음에만 걸리는지 본다(무회귀).
@pytest.mark.asyncio
async def test_a_grammar_pattern_still_uses_the_utterance_history(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    grammar_id = await db_conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_missing', 'go to the + 장소') returning id",
        USER_ID,
    )
    utterance_id = await db_conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'I go to gym.', $2, $3) returning id",
        session_id,
        next(_SEQ),
        T0,
    )
    await db_conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        grammar_id,
    )
    # 같은 학습자의 발음 시도가 있어도 문법 패턴의 이력에 섞이지 않는다
    await _attempt(db_conn, session_id, "incorrect", T0 + timedelta(days=5))

    state = await recompute(db_conn, grammar_id)

    assert state.next_review_at == T0 + timedelta(days=STAGE_DAYS[0])
    assert state.scenario_context == "go to gym"


# ── ② 초점 경로가 열린다 (§5.1) ──────────────────────────────────────────────


# `_DUE_REVIEWS_SQL`에 카테고리 필터가 없으므로 `next_review_at`이 채워지면 그대로 들어온다.
@pytest.mark.asyncio
async def test_a_pronunciation_pattern_enters_the_due_review_list(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    # 예정일이 이미 지난 시각으로 넣는다 — 실측 데이터(§4.4)와 같은 모양이다
    long_ago = datetime.now(T0.tzinfo) - timedelta(days=10)
    await _attempt(db_conn, session_id, "incorrect", long_ago, pattern_id=pattern_id)
    await recompute(db_conn, pattern_id)

    due = await load_due_reviews(db_conn, USER_ID)

    assert [r.pattern_id for r in due] == [pattern_id]
    assert due[0].category == "pronunciation_intonation"


# ── ③ 재계산 트리거 — 「구현 공백 ④」를 닫는 자리 (§5.5) ─────────────────────


# `correct`가 이 경로로 처음 재계산을 발화시킨다. 그것이 ④의 해소다.
@pytest.mark.asyncio
async def test_refresh_review_recomputes_after_a_correct_attempt(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, pattern_id=pattern_id)
    await recompute(db_conn, pattern_id)
    due = T0 + timedelta(days=STAGE_DAYS[0])
    correct_id = await _attempt(db_conn, session_id, "correct", due)

    await refresh_review(db_conn, correct_id)

    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] == due + timedelta(days=STAGE_DAYS[1])


# 한 번도 틀린 적 없는 소리를 맞힌 것은 **아무 것도 만들지 않는다** — 패턴을 만들지 않는다.
@pytest.mark.asyncio
async def test_refresh_review_is_a_noop_for_a_sound_that_was_never_wrong(
    db_conn: asyncpg.Connection,
):
    session_id = await _seed(db_conn)
    correct_id = await _attempt(db_conn, session_id, "correct", T0, sound="am_as_i_m")

    await refresh_review(db_conn, correct_id)

    count = await db_conn.fetchval(
        "select count(*) from error_patterns where user_id = $1", USER_ID
    )
    assert count == 0


# 존재하지 않는 시도 id로 불러도 죽지 않는다 — 판정 경로가 이 함수 하나에 걸리기 때문이다.
@pytest.mark.asyncio
async def test_refresh_review_survives_a_missing_attempt(db_conn: asyncpg.Connection):
    await _seed(db_conn)

    assert await refresh_review(db_conn, uuid4()) is None


# `target_sound`가 null인 시도(한글 전사 보조 신호)도 no-op이다.
@pytest.mark.asyncio
async def test_refresh_review_is_a_noop_when_the_sound_is_missing(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    attempt_id = await db_conn.fetchval(
        "insert into pronunciation_attempts "
        "(session_id, target_form, target_sound, outcome, resolved_at, signal_source) "
        "values ($1, $2, null, 'unclear', $3, 'korean_transcript') returning id",
        session_id,
        SENTENCE,
        T0,
    )

    assert await refresh_review(db_conn, attempt_id) is None


# 판정 경로가 **스스로** 재계산을 발화시킨다 — 호출자가 한 줄을 따로 쓰지 않는다.
# ⚠️ 이것이 배선 테스트다. 위 `refresh_review` 단독 테스트가 통과해도 두 진입점이 그것을
# 부르지 않으면 예정일은 영원히 비어 있다 — 실제로 그것이 「구현 공백 4」의 모양이었다.
@pytest.mark.asyncio
async def test_record_attempt_refreshes_the_review_state(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    pattern_id = await _pronunciation_pattern(db_conn)
    await _attempt(db_conn, session_id, "incorrect", T0, pattern_id=pattern_id)
    await recompute(db_conn, pattern_id)
    before = (await _pattern_row(db_conn, pattern_id))["next_review_at"]
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(1, "pending")]

    # 판정 경로를 그대로 탄다. ⚠️ `resolved_at`을 테스트가 정할 수 없다 —
    # `record_attempt`가 `clock_timestamp()`로 채운다. 그래서 **간격 산수를 재지 않고
    # 단계가 올랐는지만** 잰다(간격은 `test_review.py`가 순수 함수로 덮었다). T0가
    # 과거라 이 정답은 1단계 예정일을 지난 것이 되어 단계를 올린다.
    await record_attempt(
        db_conn,
        session_id,
        target_form=SENTENCE,
        outcome="correct",
        target_sound=SOUND,
    )

    after = (await _pattern_row(db_conn, pattern_id))["next_review_at"]
    assert after is not None
    assert after > before  # 재계산이 실제로 돌았다
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(2, "pending")]


# 수렴 경로(대답 없이 끝난 시도를 `incorrect`로 닫는 것)도 예정일을 만든다.
@pytest.mark.asyncio
async def test_resolve_dangling_schedules_the_review(db_conn: asyncpg.Connection):
    session_id = await _seed(db_conn)
    # `pending` 하나만 남기고 세션이 끝난 모양
    await _attempt(db_conn, session_id, "pending", None)

    closed = await resolve_dangling(db_conn, session_id)

    assert closed == 1
    pattern_id = await db_conn.fetchval(
        "select id from error_patterns where user_id = $1 and pattern_key = $2",
        USER_ID,
        PATTERN_KEY,
    )
    assert pattern_id is not None  # 수렴이 패턴을 만들었다
    assert (await _pattern_row(db_conn, pattern_id))["next_review_at"] is not None


# ── ④ 프롬프트 문구 (§5.6 ①·③) ──────────────────────────────────────────────


def _section_header(prompt: str, anchor: str) -> str:
    """절 제목 **전체**. `test_plan.py`의 같은 이름 헬퍼와 같은 계약이다 (그 docstring이 근거를
    소유한다): 고정 길이 창은 자기순환이고, 발음 절 제목은 **두 줄**이라 한 줄만 자르면 거짓
    실패가 난다. 네 절 제목이 모두 `):`로 끝나므로 거기까지 자른다.
    """
    start = prompt.index(anchor)
    return prompt[start : prompt.index("):", start) + 2]


# 「발음은 초점 원천이 아니다」가 거짓이 됐다 — 복습 목록을 통해 들어온다.
#
# ⚠️ **발음 절 제목만 잰다.** `never a focus source`는 「Recent learner utterances」 절에도
# 있고 **그쪽은 여전히 참이다** — 그 절은 pattern_id를 아예 싣지 않는다. 프롬프트 전체에서
# 그 문구의 부재를 단정하면 이 설계의 범위 밖 문장까지 지우게 된다(§5.6이 ②를 "고치지
# 않는다"로 판정한 것과 같은 이유).
def test_the_prompt_no_longer_calls_pronunciation_never_a_focus_source(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())
    header = _section_header(prompt, "Pronunciation attempts")

    assert "never a focus source" not in header
    # 대신 **왜** 이 절에서 고르지 않는지를 말한다: 여기 실린 값에 pattern_id가 없다
    assert "carry no pattern_id" in header
    # 그리고 어디로 들어오는지 이름으로 지목한다
    assert "Due for review today" in header
    # `test_plan.py:108`이 재는 규약을 깨지 않는다 — 첫 줄에 "context only"가 남는다
    assert "context only" in header
    # 범위 밖은 그대로다 — 이 단정이 §5.6 ②의 "고치지 않는다"를 코드로 지킨다
    assert "never a focus source" in _section_header(prompt, "Recent learner utterances")


# 복습 줄이 발음 패턴을 **소리**로 부른다 — 설계서 §5.6 ④(유도, §9-4).
#
# ⚠️ 이 유도가 **이 태스크로 살아 있는 문제가 됐다.** 그전에는 발음 패턴이 복습 목록에 아예
# 못 들어와 이 줄을 타지 않았다. 이제 들어오는데 `target form "an_as_a"`로 나가면 모델이 소리
# 키를 **연습할 문장으로** 읽을 여지가 생긴다 — 설계서가 두 번 경고한 1차수 F-2와 같은 부류다.
# `category`가 이미 그 줄에 실리므로 분기 재료는 있다. 뒤집으려면 이 테스트와 그 분기만 지운다.
def test_the_due_line_calls_a_pronunciation_pattern_a_sound(plan_input_factory):
    prompt = build_plan_prompt(
        plan_input_factory(due_keys=["article_missing"], due_pronunciation=[PATTERN_KEY])
    )

    assert f'target sound "{SOUND}"' in prompt
    # 문법 줄은 그대로 "target form"이다 — 분기가 발음에만 걸린다
    assert 'target form "target form for article_missing"' in prompt
    # 발음 줄에 "target form"이 남아 있지 않다
    pronunciation_line = next(
        line for line in prompt.splitlines() if PATTERN_KEY in line and "pattern_id" in line
    )
    assert "target form" not in pronunciation_line
