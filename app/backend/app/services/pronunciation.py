"""발음 시도의 생명주기 (설계서 §3.2, 계획 Task 4).

`session.py`에 이 SQL을 넣지 않는 이유는 두 가지다. ① 그 모듈은 이미 세션 수명·
저장·방송을 갖고 있어 책임이 섞인다. ② 수렴 로직은 Nova 없이 단독 테스트해야 한다.

생명주기 (설계서 §3.2의 상태 기계를 그대로 옮긴 것):

    toolUse(pending)  → INSERT (resolved_at is null)           `record_attempt`
    toolUse(판정값)    → 같은 세션의 **최신** pending을 UPDATE    `record_attempt`
                         (없으면 그 값으로 INSERT — 기록을 잃지 않는다)
    세션 종료         → 남은 pending을 unclear로 수렴            `resolve_dangling`

마지막 규칙이 핵심 방어다. `pending`을 영구히 남기면 "판정되지 않은 시도"가 조용히
쌓여 숙련도 계산을 왜곡한다. 학습자가 대답하지 않고 세션을 끝낸 것도 정보이므로
없는 일로 만들지 않는다.

**진입점이 둘인 이유.** `record_attempt`는 위 생명주기이고, `record_signal`은 보조
신호 1건(설계서 §7 Failure: "tool이 오지 않음 → 보조 신호가 떴다면 unclear 행을
남긴다")이다. 보조 신호는 열린 pending을 닫지 않는다 — 닫으면 그 행의 `signal_source`가
`nova_tool`로 남아 "Nova가 놓쳐서 보조 신호로 잡았다"는 사실이 사라지고,
`signal_source`를 둔 이유(R10-4)가 무의미해진다. 이 판단을 인자값으로 분기하지 않고
**함수 이름으로** 표현하는 이유는 호출부(`session.py`, 계획 Task 6)에서 무엇이 일어나는지
보이게 하기 위해서다. 설계서 §6.1이 `signal_source`를 "이 행이 무엇 때문에 생겼는지"라는
**서술 컬럼**으로 정의한 것과도 맞는다 — 제어 흐름 의미를 얹지 않는다.

**정렬은 `attempt_seq`가 강제한다** (004 마이그레이션). `created_at`은 `now()`, 즉
트랜잭션 시각이라 한 트랜잭션에서 만든 두 행이 동값이고 "최신 pending"을 고를 수 없다 —
실측으로 3회 중 1회 잘못된 행을 닫았다. 앱에서 `clock_timestamp()`로 덮지 않은 이유는
004 주석에 있다(요지: 규약은 표를 직접 쓰는 다른 writer를 구속하지 못하고, 벽시계는
순서의 대리일 뿐이어서 동값 tie-break가 난수 uuid로 떨어진다).

⚠️ **미결 — 트랜잭션 소유권.** 지금은 호출자의 트랜잭션을 그대로 쓴다. 계획 Task 7이
`link_pattern`(패턴 upsert + 시도 UPDATE)을 더하면 설계서 §7 Failure의 "시도 INSERT와
패턴 upsert를 한 트랜잭션에 둔다"를 **이 함수가** 보장해야 한다 — Task 6의 호출자가
`pool.acquire()`(autocommit)라 호출자에게 맡기면 부분 실행이 생긴다. 그때
`async with conn.transaction():`을 여기서 열어라(`services/utterances.py:13-17`이 같은
결론을 이미 문서화한다). 지금 미리 넣지 않는 이유는 실패하는 테스트를 붙일 수 없어서다 —
Task 4에는 한 단위로 묶일 두 번째 문장이 없다.
"""

from __future__ import annotations

import logging
import re
from typing import Literal
from uuid import UUID

import asyncpg

from app.models.pronunciation import PronunciationOutcome, SignalSource

logger = logging.getLogger(__name__)

# 보조 신호의 값역. `nova_tool`은 **여기 없다** — 그것은 2단계 생명주기를 갖는
# `record_attempt`의 것이고, 단발 행으로 새면 판정이 오지 않는 시도가 조용히 쌓인다.
# 값역의 SoT는 `models/pronunciation.SignalSource`(003 CHECK와 짝)이고 이것은 그 부분집합이다.
AssistSignal = Literal["korean_transcript", "agent_reprompt"]

# 보조 신호는 이미 일어난 관측이라 `pending`이 될 수 없다. 값역에서 빼는 이유는
# `signal_source`를 좁힌 것과 같다 — 열린 보조 신호 행이 생기면 Nova 판정이 그것을
# 닫아버려 함수를 나눈 목적이 무너진다(코드 리뷰가 실측으로 재현). SQL 쪽 2차 방어는
# `record_attempt`의 `signal_source = 'nova_tool'` 필터다.
AssistOutcome = Literal["correct", "incorrect", "unclear"]

_NOVA_TOOL: SignalSource = "nova_tool"

# 한글 음절 블록. ASR 언어 판별이 뒤집히면 영어 문장이 이렇게 전사된다 — 4차수 P4 실측
# (`p1k` → '아이싱크 아이파운드 …'). 문구가 아니라 문자를 보므로 결정론적이다.
_HANGUL = re.compile(r"[가-힣]")

# 한글 전사 신호 행의 `target_form`. Nova가 시범한 문장이 아니라 "왜 이 행이 생겼는지"라서
# 문장 자리에 설명이 들어간다. ⚠️ 결과 화면(계획 Task 8)이 `target_form`을 학습자에게
# 보여주므로, 그 화면은 `signal_source`로 nova_tool 행과 구분해 렌더해야 한다.
KOREAN_TRANSCRIPT_TARGET_FORM = "(전사문이 한국어로 인식되었습니다)"


async def _insert_attempt(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    target_form: str,
    outcome: PronunciationOutcome,
    spoken_form: str | None,
    target_sound: str | None,
    utterance_id: UUID | None,
    signal_source: SignalSource,
) -> UUID:
    """행을 새로 만든다. `resolved_at`은 `outcome`에 맞춰 채운다 — 표의
    CHECK(`pending` ⇔ `resolved_at is null`)가 어긋난 조합을 거부한다.

    `created_at`·`attempt_seq`는 주지 않는다. 전자는 DEFAULT가 채우고 후자는
    `generated always`라 앱이 줄 수 없다(004).
    """
    attempt_id = await conn.fetchval(
        """
        insert into pronunciation_attempts
            (session_id, utterance_id, target_form, spoken_form, target_sound,
             outcome, signal_source, resolved_at)
        values ($1, $2, $3, $4, $5, $6, $7,
                case when $6 = 'pending' then null else clock_timestamp() end)
        returning id
        """,
        session_id,
        utterance_id,
        target_form,
        spoken_form,
        target_sound,
        outcome,
        signal_source,
    )
    assert attempt_id is not None, "insert ... returning produced no row"
    return attempt_id


async def record_attempt(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    target_form: str,
    outcome: PronunciationOutcome,
    spoken_form: str | None = None,
    target_sound: str | None = None,
    utterance_id: UUID | None = None,
) -> UUID:
    """Nova tool 시도를 기록하고 그 행의 id를 돌려준다 (`signal_source='nova_tool'`).

    `pending`이면 새 행을 연다. 판정값이면 같은 세션의 **최신 pending을 닫고**, 닫을
    것이 없으면 그 값으로 새 행을 만든다 — Nova가 시범 없이 판정만 보내도 기록을 잃지
    않는다(설계서 §3.2의 "없으면 새 행을 그 outcome으로 INSERT").
    """
    if outcome == "pending":
        return await _insert_attempt(
            conn,
            session_id,
            target_form=target_form,
            outcome=outcome,
            spoken_form=spoken_form,
            target_sound=target_sound,
            utterance_id=utterance_id,
            signal_source=_NOVA_TOOL,
        )

    # 판정값 — 가장 최근 pending을 닫는다. `coalesce`라서 판정이 값을 안 주면 시범
    # 시점의 값이 남는다(빈 판정이 기록을 지우지 않는다).
    #
    # `signal_source`를 **필터하지 않는다.** 005 제약이 "pending은 nova_tool만"을 표에서
    # 강제하므로 열린 행은 정의상 Nova 것이다 — 앱에서 한 번 더 거르면 같은 규칙이 두 층에
    # 흩어진다.
    #
    # ⚠️ `for update`는 두 판정이 동시에 들어올 때 같은 행을 닫는 것을 막는다. 그런데
    # **패자가 새 행을 만드는 것이 아니다** — 잠금이 풀리면 EPQ 재검사가 이미 닫힌 행을
    # 떨어뜨리고 서브쿼리가 **그 다음 pending으로 전진**해 무관한 시도를 닫는다(리뷰가
    # 연결 2개로 실측). 지금은 `_pump_adapter_events`가 이벤트를 순차 await해 도달
    # 불가다 — 발음 기록을 `create_task`로 띄우면 즉시 도달하므로 띄우지 않는다.
    updated = await conn.fetchval(
        """
        update pronunciation_attempts set
            outcome      = $2,
            spoken_form  = coalesce($3, spoken_form),
            target_sound = coalesce($4, target_sound),
            utterance_id = coalesce($5, utterance_id),
            resolved_at  = clock_timestamp()
        where id = (
            select id from pronunciation_attempts
             where session_id = $1 and outcome = 'pending'
             order by attempt_seq desc
             limit 1
             for update
        )
        returning id
        """,
        session_id,
        outcome,
        spoken_form,
        target_sound,
        utterance_id,
    )
    if updated is not None:
        return updated

    logger.info("닫을 pending 시도가 없어 판정값으로 새 행을 만든다 (세션 %s)", session_id)
    return await _insert_attempt(
        conn,
        session_id,
        target_form=target_form,
        outcome=outcome,
        spoken_form=spoken_form,
        target_sound=target_sound,
        utterance_id=utterance_id,
        signal_source=_NOVA_TOOL,
    )


async def record_signal(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    target_form: str,
    outcome: AssistOutcome,
    signal_source: AssistSignal,
    spoken_form: str | None = None,
    target_sound: str | None = None,
    utterance_id: UUID | None = None,
) -> UUID:
    """Nova가 놓쳤을 때 잡은 보조 신호 1건을 남긴다 (R10-4, 설계서 §7 Failure).

    **열린 pending을 닫지 않는다** — 이 행은 Nova 시도의 판정이 아니라 별개의 관측이다.
    Nova의 pending은 `resolve_dangling`이 세션 종료 때 처리한다.

    **이 행은 항상 판정된 상태로 태어난다** (`AssistOutcome`에 `pending`이 없다). 열린
    보조 신호 행을 만들면 `record_attempt`가 그것을 닫아 이 분리의 목적이 무너진다.
    """
    return await _insert_attempt(
        conn,
        session_id,
        target_form=target_form,
        outcome=outcome,
        spoken_form=spoken_form,
        target_sound=target_sound,
        utterance_id=utterance_id,
        signal_source=signal_source,
    )


async def note_transcript(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    transcript: str,
    utterance_id: UUID,
) -> UUID | None:
    """확정된 **학습자** 전사문을 보고, 발음 신호가 보이면 시도 1건을 남긴다.

    감지기를 늘리거나 줄이는 일이 `session.py`에 닿지 않게 하는 단일 진입점이다 —
    호출자는 "이 전사문을 봐 달라"만 하고 무엇을 어떻게 보는지는 이 모듈이 안다.
    신호가 없으면 `None`을 돌려준다.

    **agent 발화는 넣지 않는다.** 신호는 학습자 발음에 대한 것이고, agent 문구를 보고
    판단하는 감지기는 두지 않는다(캡틴 결정 2026-08-28: 문구 매칭은 케이스가 불어난다).

    지금 감지기는 하나다 — 한글 전사. 4차수 P4 실측: 한국어 억양이 강하면 ASR 언어
    판별이 뒤집혀 영어 문장이 `'아이싱크 아이파운드 …'`로 전사된다. 글자만 보면 되므로
    결정론적이고, 모델 문구가 바뀌어도 깨지지 않는다.
    """
    if not _HANGUL.search(transcript):
        return None
    logger.info("전사문이 한글로 인식됐다 — 발음 신호로 기록한다 (세션 %s)", session_id)
    return await record_signal(
        conn,
        session_id,
        target_form=KOREAN_TRANSCRIPT_TARGET_FORM,
        outcome="unclear",
        signal_source="korean_transcript",
        spoken_form=transcript,
        utterance_id=utterance_id,
    )


async def resolve_dangling(conn: asyncpg.Connection, session_id: UUID) -> int:
    """세션에 남은 `pending`을 `incorrect`로 수렴시킨다. 바뀐 행 수를 돌려준다.

    **왜 `incorrect`인가** (캡틴 결정 2026-08-28, 설계서 §3.2의 `unclear`를 뒤집음):
    학습자 관점에서 "대답을 못 한 것"은 못 한 것이다. 이후 학습도 그냥 틀림으로 본다 —
    "대답 안 함"만 따로 세는 규칙을 두지 않는다(플로우가 갈라지는 것을 막는다).

    `spoken_form`을 **비운다**: 재발화를 실제로 못 들었으므로 "학습자가 이렇게 들렸다"에
    남을 값이 없다. 비우지 않으면 Nova가 시범 시점에 넣은 placeholder
    (`"[awaiting user repetition]"`)가 결과 화면에 학습자 발음으로 표시된다.

    멱등이다 — 두 번 불러도 두 번째는 0이다. 이미 판정된 행은 `where` 조건 밖이라
    `correct`가 덮이지 않는다.

    세션 종료 기록과 **같은 트랜잭션**에서 불러야 한다(설계서 §3.2). 분리하면 그 사이
    크래시에서 `pending`이 영구히 남는다 — 그래서 자기 트랜잭션을 열지 않고 호출자의
    것에 합류한다.

    ⚠️ **그 전제조건을 지금은 어느 호출자도 만족시킬 수 없다.**
    `services/sessions.py:49-54`의 `mark_session_ended(pool, session_id, status)`가 `pool`을
    받아 **자기 연결을 acquire**한다(`audio_gateway/session.py:148`에서 호출) — 합류할
    트랜잭션이 없다. 계획 Task 6 (d) "세션 상태를 기록하는 트랜잭션에 붙인다"도 같은 이유로
    현 구조에서 불가능하다. `pool.acquire()`로 이 함수를 부르면 문법도 테스트도 통과하지만
    원자성이 **조용히 없고**, 그 사이 크래시에서 `pending`이 영구 잔존한다 — 설계서가
    "핵심 방어"라 부른 것의 실패다. 고칠 자리는 이 모듈이 아니라 `mark_session_ended`의
    시그니처(`pool` → `conn`)와 `_close_and_record`가 `db.tx()`를 여는 것이다.
    """
    rows = await conn.fetch(
        """
        update pronunciation_attempts
           set outcome     = 'incorrect',
               spoken_form = null,
               resolved_at = clock_timestamp()
         where session_id = $1 and outcome = 'pending'
        returning id
        """,
        session_id,
    )
    if rows:
        logger.info(
            "대답 없이 끝난 발음 시도 %d건을 incorrect로 수렴했다 (세션 %s)",
            len(rows),
            session_id,
        )
    return len(rows)
