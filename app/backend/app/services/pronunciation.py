"""발음 시도의 생명주기 (설계서 §3.2, 계획 Task 4).

`session.py`에 이 SQL을 넣지 않는 이유는 두 가지다. ① 그 모듈은 이미 세션 수명·
저장·방송을 갖고 있어 책임이 섞인다. ② 수렴 로직은 Nova 없이 단독 테스트해야 한다.

생명주기 (설계서 §3.2의 상태 기계를 그대로 옮긴 것):

    toolUse(pending)  → INSERT (resolved_at is null)           `record_attempt`
    toolUse(판정값)    → 같은 세션의 **최신** pending을 UPDATE    `record_attempt`
                         (없으면 그 값으로 INSERT — 기록을 잃지 않는다)
    세션 종료         → 남은 pending을 incorrect로 수렴          `resolve_dangling`
    incorrect가 되면  → error_patterns 연결 (경로 불문)          `link_pattern`

수렴값은 설계서 §3.2의 `unclear`가 아니라 `incorrect`다 — 캡틴이 2026-08-28에 뒤집었고
근거는 `resolve_dangling` 주석에 있다.

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

**트랜잭션 소유권** (Task 4의 미결을 Task 7이 닫았다). **쓰기 진입점 둘 다 자기 트랜잭션을
연다** — `record_attempt`와 `resolve_dangling`. 각자 시도 기록과 `link_pattern`(패턴 upsert +
시도 UPDATE + frequency 재계산)을 한 단위로 묶어야 하고(설계서 §7 Failure), 호출자
(`audio_gateway/session.py:243`)가 `pool.acquire()` 즉 autocommit이라 맡기면 부분 실행이
생긴다(패턴 `frequency`만 오르거나 시도의 `pattern_id`가 null, 또는 패턴 없는 `incorrect` 행).
**호출자가 이미 트랜잭션 안이면 savepoint로 합성되므로** "종료 기록과 한 단위"(§3.2) 요구와
충돌하지 않는다 — `services/utterances.py:13-17`이 같은 결론을 문서화하고, 이 모듈의 원자성
테스트 2개가 savepoint·최상위 두 경로를 각각 실증한다.
"""

from __future__ import annotations

import logging
import re
from typing import Literal
from uuid import UUID

import asyncpg

from app.models.analysis import ErrorCategory
from app.models.pronunciation import PronunciationOutcome, SignalSource

logger = logging.getLogger(__name__)

# 발음 패턴이 쓰는 카테고리 코드값. SQL 리터럴로 박지 않고 이 상수를 bind 파라미터로 넘긴다 —
# 값역의 SoT는 `models/analysis.ErrorCategory`(001 CHECK와 짝)이고, 타입을 붙이면 오타를
# `ty`가 잡는다. `pronunciation`이 아니라 `pronunciation_intonation`이다.
_PRONUNCIATION_CATEGORY: ErrorCategory = "pronunciation_intonation"

# 보조 신호의 값역. `nova_tool`은 **여기 없다** — 그것은 2단계 생명주기를 갖는
# `record_attempt`의 것이고, 단발 행으로 새면 판정이 오지 않는 시도가 조용히 쌓인다.
# 값역의 SoT는 `models/pronunciation.SignalSource`(003 CHECK와 짝)이고 이것은 그 부분집합이다.
AssistSignal = Literal["korean_transcript", "agent_reprompt"]

# 보조 신호는 이미 일어난 관측이라 `pending`이 될 수 없다. 값역에서 빼는 이유는
# `signal_source`를 좁힌 것과 같다 — 열린 보조 신호 행이 생기면 Nova 판정이 그것을
# 닫아버려 함수를 나눈 목적이 무너진다(코드 리뷰가 실측으로 재현).
#
# **`incorrect`도 없다** (Task 7 리뷰 MEDIUM-2). 설계서 §3.2는 "`incorrect`가 되는 순간
# 패턴을 만든다"인데 보조 신호에는 `target_sound`가 없어 키를 만들 수 없다. 값역에 남겨두면
# 다음 감지기가 `incorrect`를 넘기는 순간 그 규칙이 **조용히** 깨지므로, 주석이 아니라
# 타입으로 막는다 — 005가 "규칙을 앱에 흩지 말고 제약으로"라 판정한 것과 같은 방향이다.
AssistOutcome = Literal["correct", "unclear"]

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

    기록과 **패턴 연결이 한 트랜잭션**이다 — 이 함수가 직접 연다(모듈 주석 "트랜잭션
    소유권"). 호출자가 autocommit이라 맡기면 부분 실행이 생긴다.
    """
    async with conn.transaction():
        if outcome == "pending":
            # 아직 오류가 아니라 패턴을 만들지 않는다. 이 행은 판정이 오거나
            # `resolve_dangling`이 수렴할 때 패턴을 얻는다.
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
        attempt_id = await conn.fetchval(
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
        if attempt_id is None:
            logger.info("닫을 pending 시도가 없어 판정값으로 새 행을 만든다 (세션 %s)", session_id)
            attempt_id = await _insert_attempt(
                conn,
                session_id,
                target_form=target_form,
                outcome=outcome,
                spoken_form=spoken_form,
                target_sound=target_sound,
                utterance_id=utterance_id,
                signal_source=_NOVA_TOOL,
            )

        assert isinstance(attempt_id, UUID)
        # 패턴을 만들 **조건은 SQL이 갖는다**(`incorrect` + `target_sound` 있음). 여기서 한 번
        # 더 거르지 않는 것은 위 `signal_source`와 같은 이유다 — 같은 규칙이 두 층에 흩어지면
        # 한쪽이 조용히 낡는다. 조건에 안 맞는 판정이면 이 호출은 no-op이다.
        await link_pattern(conn, attempt_id)
        return attempt_id


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

    **패턴을 만들지 않는다.** 설계서 §3.2의 "경로 불문"은 Nova 판정과 종료 수렴 두 경로를
    말한다. 보조 신호는 "어떤 소리가 틀렸다"를 짚지 못하고 "이 전사문이 이상하다"만 말하므로
    패턴 키를 만들 재료(`target_sound`)가 없다 — 설계서 §11:413이 같은 이유로 신호 행을
    nova_tool 행과 구분해 렌더하라고 요구한다.
    이 불변조건은 `AssistOutcome`이 **타입으로 잠근다** — `incorrect`가 값역에 없어서 보조
    신호는 애초에 오류 판정이 될 수 없다. 주석으로만 두면 다음 감지기가 조용히 깬다.
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
    """세션에 남은 `pending`을 `incorrect`로 수렴시키고 패턴까지 연결한다. 바뀐 행 수를 돌려준다.

    **왜 `incorrect`인가** (캡틴 결정 2026-08-28, 설계서 §3.2의 `unclear`를 뒤집음):
    학습자 관점에서 "대답을 못 한 것"은 못 한 것이다. 이후 학습도 그냥 틀림으로 본다 —
    "대답 안 함"만 따로 세는 규칙을 두지 않는다(플로우가 갈라지는 것을 막는다).

    `spoken_form`을 **비운다**: 재발화를 실제로 못 들었으므로 "학습자가 이렇게 들렸다"에
    남을 값이 없다. 비우지 않으면 Nova가 시범 시점에 넣은 placeholder
    (`"[awaiting user repetition]"`)가 결과 화면에 학습자 발음으로 표시된다.

    **패턴은 경로 불문으로 만든다** (설계서 §3.2, 계획 Task 7 정정): 판정으로 `incorrect`가
    된 행뿐 아니라 여기서 수렴된 행도 `error_patterns`에 연결된다. 경로별 예외를 두면
    "대답 안 함"만 따로 세는 규칙이 생기고 그것이 결과 화면·학습 계획으로 번진다.

    멱등이다 — 두 번 불러도 두 번째는 0이다. 이미 판정된 행은 `where` 조건 밖이라
    `correct`가 덮이지 않는다.

    세션 종료 기록과 **같은 트랜잭션**에서 불러야 한다(설계서 §3.2). 분리하면 그 사이
    크래시에서 `pending`이 영구히 남는다.

    그럼에도 **자기 트랜잭션을 연다** — savepoint로 합류하므로 호출자의 단위를 깨지 않으면서
    (그 의미론은 이 모듈의 원자성 테스트가 실증한다), 수렴 UPDATE와 그 뒤의 패턴 연결
    `1+3N` 문장이 autocommit 호출자에게서도 쪼개지지 않는다. Task 7 전에는 UPDATE 한 문장이라
    호출자에게 맡겨도 원자적이었지만 이제 아니다(리뷰 MEDIUM-3).

    ✅ **그 전제조건은 Task 6이 충족시켰다** (Task 4 시점의 ⚠️를 정정한다):
    `services/sessions.py:49`가 `end_session(conn, …)`로 연결을 받고,
    `audio_gateway/session.py:153`이 `pool.acquire()` + `conn.transaction()` 안에서 종료
    기록과 이 함수를 함께 부른다. `mark_session_ended(pool, …)`는 묶을 것이 없는 호출자용
    래퍼로 남았고 유일한 사용처(`api/ws.py:123`)는 **어댑터 생성 실패 경로**라 시도 행이
    아직 존재할 수 없다 — 그 경로가 수렴을 건너뛰어도 누수가 없다.
    """
    async with conn.transaction():
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
        for row in rows:
            await link_pattern(conn, row["id"])
        return len(rows)


# --- 패턴 연결 (R10-6 → R11-9, 설계서 §4.3, 계획 Task 7) ---

# 패턴 재료를 **인자가 아니라 저장된 행**에서 읽는다. ① 판정 tool이 `target_sound`를 다시
# 주지 않아도 시범 시점 값이 살아 있다(판정 UPDATE의 `coalesce`). ② 호출자가 outcome과
# 소리를 다시 넘기다가 행과 어긋날 여지가 없다. ③ 판정·수렴 두 경로가 같은 한 문장을 쓴다.
#
# 적용 조건이 `where`에 있어서, 조건에 안 맞는 행에 불러도 0행을 돌려준다(무해한 no-op).
#
# `target_form`(not null)에 **시범 문장을 넣지 않는다.** `docs/database-schema.md:120`이
# 이 컬럼을 "패턴 수준의 일반화된 목표 형태 — **문장이 아니다**"로 정의하고, 그 근거는
# 관측된 결함이다(1차수 F-2: 결과 조회가 대표 occurrence와 패턴 `target_form`을 독립적으로
# 골라 카드의 두 값이 서로 다른 문장을 가리켰다). 발음도 같은 구조다 — 한 패턴에 시도가
# 여럿이면 "마지막 시도의 문장"이 목표 형태로 굳는다. 문장은 이미 시도 행이 갖고 있다
# (`pronunciation_attempts.target_form`) 이므로 여기 다시 넣으면 중복 저장이기도 하다.
#
# 그래서 **정규화한 `target_sound`를 쓴다** — 문장이 달라도 흔들리지 않는 유일한 일반형이고
# 발명값이 아니다. 화면 표시 문구는 이 값이 아니라 Task 8이 `category`와 함께 정한다.
#
# `do update`는 충돌 시에도 id를 돌려받기 위한 것이다(`do nothing`은 0행 — `analysis.py:201`이
# 같은 이유를 문서화한다). 같은 `pattern_key`면 `btrim(target_sound)`도 같으므로 이 갱신은
# **항상 같은 값을 다시 쓴다** — 목표 형태가 시도마다 흔들리지 않는다.
_UPSERT_PRONUNCIATION_PATTERN_SQL = """
insert into error_patterns (user_id, category, pattern_key, target_form)
select s.user_id,
       $2,
       'pronunciation_' || btrim(a.target_sound),
       btrim(a.target_sound)
  from pronunciation_attempts a
  join learning_sessions s on s.id = a.session_id
 where a.id = $1
   and a.outcome = 'incorrect'
   and length(btrim(coalesce(a.target_sound, ''))) > 0
on conflict (user_id, pattern_key) do update
   set target_form = excluded.target_form
returning id
"""

_LINK_ATTEMPT_SQL = "update pronunciation_attempts set pattern_id = $2 where id = $1"

# `frequency`는 **시도 수**다 (설계서 §4.3) — 발음 시도는 `error_occurrences`를 만들지 않아
# 문법 경로의 occurrence 재계산을 쓸 수 없다. 그래도 `+1`이 아니라 실제 행 수에서 다시 세는
# 것은 같은 규약이다(`services/analysis.py:220` "+1 금지 — 재시도마다 부풀어 오른다"):
# 이 함수를 같은 시도에 두 번 불러도 값이 변하지 않는다.
#
# `last_seen_at`도 최대값에서 다시 얻어 멱등을 지킨다. 연결된 행은 정의상 `incorrect`라
# `resolved_at`이 non-null이다(003 CHECK).
#
# ⚠️ 이름이 `analysis.py`의 `_RECOUNT_PATTERN_SQL`과 비슷하지만 **세는 대상이 다르다**
# (그쪽은 occurrence, 이쪽은 시도). 그래서 상수 이름에 출처를 박아 둔다.
_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL = """
update error_patterns p
   set frequency    = agg.attempts,
       last_seen_at = agg.last_seen_at
  from (
         select count(*) as attempts, max(resolved_at) as last_seen_at
           from pronunciation_attempts
          where pattern_id = $1
       ) as agg
 where p.id = $1
"""


async def link_pattern(conn: asyncpg.Connection, attempt_id: UUID) -> UUID | None:
    """`incorrect`가 된 시도를 재사용 가능한 `error_patterns` 행에 연결한다.

    돌려주는 것은 패턴 id이고, 조건에 맞지 않는 시도(판정이 `incorrect`가 아니거나
    `target_sound`가 없음)면 `None`이다 — 조건 판단을 SQL이 갖기 때문에 호출자는 경로마다
    같은 한 줄을 쓴다(판정·수렴 **경로 불문**, 설계서 §3.2).

    **임계값을 두지 않는다** — `incorrect` 1회에 만든다. 문법 오류도 1회에 패턴이 생기므로
    같은 규약이다(`PRD.md:90`). "N회 이상이면 만성" 같은 수치를 발명하지 않는다.

    `pattern_key`는 `'pronunciation_' || target_sound`다(§4.3).

    ⚠️ **값역 흩어짐의 완화책은 아직 없다** (`TASKS.md` B-4는 **부분 해소**다). §5.6 규약의
    실행 기제는 "기존 키 목록을 프롬프트에 주입하고 재사용을 지시하는 것"인데, 그 주입은
    문법 경로에만 있다(`analysis.py:248`의 `load_existing_patterns`, 호출은 같은 파일 `:306`
    한 곳뿐). Nova 지시문(`audio_gateway/nova.py:126-127`)은 `th_as_s`·`f_as_p`를 **예시로
    하드코딩**할 뿐 학습자의 기존 소리를 넣지 않는다. 그래서 같은 /θ/를 Nova가 다음 세션에
    `theta_to_s`로 부르면 패턴이 갈라지고 R10-6의 "반복 오류 묶기"가 조용히 깨진다.
    빈도는 5차수 관측 대상이고, 닫는 자리는 이 함수가 아니라 지시문 가변부다.

    호출자의 트랜잭션 안에서 부른다 — 세 문장(upsert · 연결 · 재계산)이 한 단위여야
    `frequency`만 오르거나 `pattern_id`가 null인 부분 실행이 없다(설계서 §7 Failure).

    ⚠️ `frequency` 재계산은 **발음 시도 수만** 센다. 같은 `pattern_key`를 문법 경로가 만지면
    두 재계산이 서로의 값을 덮는다. **신규** 문법 키는 그 카테고리가 프롬프트에서 금지돼
    (`analysis.py:49` `UNJUDGEABLE_CATEGORY`) `pronunciation_`으로 시작할 수 없다. 남은 구멍은
    **재사용 경로**다 — `_EXISTING_PATTERNS_SQL`(`analysis.py:188`)에 카테고리 필터가 없어
    발음 키가 문법 프롬프트에 실리고, 모델이 그것을 글자 그대로 재사용하면 한 행을 두 writer가
    번갈아 덮는다. 필터는 그 모듈의 몫이라 여기서 고치지 않는다(`TASKS.md` B-10).
    """
    pattern_id = await conn.fetchval(
        _UPSERT_PRONUNCIATION_PATTERN_SQL, attempt_id, _PRONUNCIATION_CATEGORY
    )
    if pattern_id is None:
        return None
    assert isinstance(pattern_id, UUID)

    await conn.execute(_LINK_ATTEMPT_SQL, attempt_id, pattern_id)
    # 순서가 중요하다 — 이 시도를 연결한 **뒤에** 세야 자기 자신이 포함된다
    # (`services/analysis.py`도 occurrence를 넣은 뒤 재계산한다).
    #
    # 세 문장을 CTE 하나로 합치지 않는다: 데이터를 바꾸는 CTE는 서로의 결과를 보지 못하고
    # 같은 스냅샷을 읽으므로, 재계산이 방금 연결한 행을 **세지 못해** frequency가 하나 적게
    # 나온다. 문장을 나누면 같은 트랜잭션 안에서 앞 문장의 효과를 본다.
    await conn.execute(_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL, pattern_id)
    logger.info("발음 시도 %s를 패턴 %s에 연결했다", attempt_id, pattern_id)
    return pattern_id
