"""`/ws/session` — 음성 세션 WebSocket (설계서 §5.3).

이 파일은 **얇다**. 세션 규칙은 전부 `audio_gateway.session.SessionRunner`에 있고,
여기서는 두 가지만 한다: 연결이 곧 세션 하나라는 것을 DB 행으로 만들고, 게이트웨이의
이벤트를 JSON 프레임으로 옮긴다.

프로토콜 (JSON 객체):

* 서버→클라이언트: `session_started`(session_id) · `partial` · `final`(speaker,
  sequence_no) · `audio`(base64) · `speech_start`/`speech_end`(offset_ms) ·
  `interrupted` · `session_failed`(reason) · `session_ended`
* 클라이언트→서버: `{"type":"audio","data":<base64>}` · `{"type":"end_session"}` ·
  `{"type":"shadowing_turn_start"}` · `{"type":"shadowing_turn_end"}`

**발음 전용 진입** (`TASK-10.1`·`TASK-10.2` · 결정 64): `?mode=pronunciation` 으로 붙으면 지시문이
전용 판으로 바뀌고, 오늘의 소리 후보가 있으면 `session_started` 에 `pronunciation_focus` 가 실린다.
세션 행의 `mode` 도 `pronunciation` 으로 적힌다 (`TASK-112` · 결정 67 · 014 가 값역을 열었다).
⛔ **폴백이 없다** (`TASK-128.2` · 사용자 결정 72): 소리를 고를 수 없어도 전용 모드로 간다 —
그 결정이 이 모드의 뜻을 「오늘의 소리를 다룬다」에서 **「발음만 다룬다」**로 바꿨다. 그래서 `mode`
를 적는 시점도 **「요청받은 때」**다(이전 판은 「소리가 정해진 때」였고 그 근거가 폴백이었다).
⚠️ 계획이 고른 소리는 **이름으로 지목되지 않고 후보 목록 앞에** 실린다 — 단수 지목이 되풀이의
구동부였고 그 실측은 `audio_gateway/nova._SOUND_INSTRUCTION` 위 주석이 소유한다.

**추가 학습 표시** (`TASK-10.2`): `?source=additional` 이 `learning_sessions.learning_source` 에
남는다. 주지 않으면 001 의 기본값(`recommended`)이다.

**쉐도잉 진입** (`TASK-45` · 결정 35): `?mode=shadowing` 으로 붙으면 세션이 그 모드로 열리고
클립 1개가 붙으며 `session_started` 에 `shadowing`(클립 + 재생 속도·반복 횟수)이 실린다. 말하기
세션에는 그 키가 **없다**. 낭독 턴 신호 둘은 그 모드에서만 뜻을 갖는다 — 아니면 무시된다.
⛔ **어느 화면·어느 버튼이 그 모드로 연결하는지는 `TASK-10` 이 소유한다**(결정 34·35 의 제약).

어떤 음성 구현이 붙는지 이 모듈은 모른다 — 팩토리에서 주입받는다 (G3).
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Sequence
from uuid import UUID

import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.audio_gateway.factory import create_voice_adapter
from app.audio_gateway.session import SessionRunner
from app.config import Settings, get_settings
from app.models.plan import PlanQuestion, SessionInstruction
from app.models.pronunciation import PRONUNCIATION_PATTERN_KEY_PREFIX
from app.models.scenario import SessionScenario
from app.services.pronunciation import load_known_sounds
from app.services.recordings import ShadowingTurns, load_session_clip
from app.services.sessions import (
    PreparedPlan,
    create_session,
    load_prepared_plan,
    load_session_scenario,
    mark_session_ended,
    record_drill_turns_expected,
    set_session_mode,
    start_shadowing_session,
)
from app.services.usage import pool_usage_sink

logger = logging.getLogger(__name__)

router = APIRouter()

WS_SESSION_PATH = "/ws/session"

# 쉐도잉으로 붙는 유일한 값. ⛔ **모드 값역을 여기서 열거하지 않는다** — 그것은 001 의
# `learning_sessions_mode_check` 가 가둔다. 이 상수가 아는 것은 「쉐도잉인가」 하나다.
SHADOWING_MODE = "shadowing"
# `create_session` 의 기본값과 같은 값이다. **여기 있는 이유는 경고 하나 때문이다**:
# `?mode=speaking` 은 명시적 선택이므로 「알 수 없는 mode」로 경고하면 안 된다. ⛔ 이 둘이
# 값역 전체는 아니다 — `review` 는 아직 진입점이 없고, 값역의 정본은 여전히 001 의 CHECK 다.
SPEAKING_MODE = "speaking"
# `TASK-10.1` — 발음 전용 모드로 붙는 값. 이 상수가 바꾸는 것은 **지시문**이고, `TASK-112`(결정 67 ·
# 마이그레이션 014) 이후로는 **세션 행의 `mode` 도** 같은 값으로 적힌다.
# ⚠️ **이 서술은 한 번 뒤집혔고 그 사실을 남긴다** — 처음에는 *"세션 행의 mode 를 바꾸지 않는다
# (001 값역 밖이고 값역을 늘리는 것은 이 태스크 범위 밖이다)"* 였다. 그 대가(결과 화면·집계가
# 발음 세션을 말하기로 세는 것)를 사용자가 결정 67 로 갚기로 정했다.
# ⛔ 모드 리터럴의 소유자는 여전히 결정 11 이 지목한 `TASK-27` 이다 — 014 는 값역 한 칸만 열었고
# 소유를 옮기지 않았다.
PRONUNCIATION_MODE = "pronunciation"

SESSION_CREATE_FAILED_REASON = "session_create_failed"
ADAPTER_UNAVAILABLE_REASON = "voice_adapter_unavailable"

# 단일 사용자 로컬 도구다(설계서 §2) — 인증 계층이 없어 연결의 주인이 고정이다.
# 값은 시드가 만드는 사용자 id와 같다(`scripts/migrate.py`의 `USER_ID`). 시드
# 스크립트는 앱 패키지를 import하지 않는 독립 ops 스크립트라 상수를 공유하지 못한다.
FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def _safe_close(websocket: WebSocket) -> None:
    """이미 닫혔을 수도 있는 소켓을 닫는다 — 재차 close해도 오류가 아니다."""
    with contextlib.suppress(RuntimeError):
        await websocket.close()


class WebSocketChannel:
    """`session.ClientChannel`을 starlette WebSocket 위에 얹은 어댑터.

    끊긴 소켓에 보내는 것은 **오류가 아니다** — 클라이언트가 먼저 떠난 뒤에도
    게이트웨이는 종료 절차(어댑터 close·세션 기록)를 끝내야 하므로, 방송 실패가
    그 절차를 중단시켜선 안 된다.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send_event(self, event: dict[str, object]) -> None:
        try:
            await self._websocket.send_json(event)
        except (RuntimeError, WebSocketDisconnect):
            # RuntimeError = close 이후의 send, WebSocketDisconnect = 전송 중 끊김.
            logger.debug("이미 닫힌 소켓에 %r을 보내려 했다 — 무시한다", event.get("type"))

    async def receive_event(self) -> dict[str, object] | None:
        """클라이언트 프레임을 JSON 객체로 돌려준다. 연결이 끝나면 `None`.

        해석할 수 없는 프레임(텍스트 아님/JSON 아님/객체 아님)은 빈 dict로 돌려
        러너가 "알 수 없는 메시지"로 무시하게 한다 — 프레임 하나가 깨졌다고 대화를
        끊지 않는다. `None`은 오직 "연결 종료"만 뜻한다.
        """
        try:
            message = await self._websocket.receive()
        except RuntimeError:
            # 이미 disconnect를 받은 뒤의 receive — 연결은 끝났다.
            return None
        if message["type"] == "websocket.disconnect":
            return None
        text = message.get("text")
        if text is None:
            logger.warning("텍스트가 아닌 프레임을 무시했다")
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("JSON으로 해석할 수 없는 프레임을 무시했다")
            return {}
        if not isinstance(payload, dict):
            logger.warning("JSON 객체가 아닌 프레임을 무시했다")
            return {}
        return payload


async def _load_known_sounds_or_empty(pool: asyncpg.Pool) -> list[str]:
    """학습자가 전에 놓친 소리 — 실패하면 빈 목록 (G-3, 캡틴 결정 B-4).

    **예외를 밖으로 던지지 않는다.** 이 값은 지시문에 얹는 **부가 정보**이고, 조회가 깨졌다고
    세션을 못 열면 대화 전체를 잃는다. 빈 목록이면 어댑터가 기본 문구로 진행한다 —
    `services/pronunciation.record_attempt`가 기록 실패에 같은 판단을 내린 것과 같은 규약이다.
    """
    try:
        async with pool.acquire() as conn:
            return await load_known_sounds(conn, FIXED_USER_ID)
    except Exception:
        logger.exception("기존 발음 소리를 읽지 못해 기본 지시문으로 진행한다")
        return []


def _pronunciation_candidates(
    plan: SessionInstruction | None, known_sounds: Sequence[str]
) -> list[str]:
    """발음 전용 모드에 내려보낼 **소리 후보 목록** (`TASK-128.2` · 사용자 결정 72).

    출처의 순서가 규칙이다: ① **계획의 발음 초점** ② **놓친 소리 목록**. 계획이 앞인 이유는 그것이
    복습 예정일을 근거로 «오늘» 다룰 소리를 이미 골라 둔 값이기 때문이다(`TASK-44` 이후 발음 패턴이
    `next_review_at` 을 받아 초점 후보가 된다). 목록은 「전에 놓친 것들」이라 오늘의 우선순위를 담지
    않으므로 뒤에 둔다.

    ⛔ **계획의 소리는 «앞에 오는 것»으로만 이긴다 — 이름으로 지목되지 않는다.** 이전 판
    (`_pronunciation_sound_or_none`)은 소리 하나를 골라 돌려주고 그것이 프롬프트에서
    `- Sound to coach today: "키"` 로 지목됐다. 그 단수 지목이 되풀이의 구동부였고 **더하는 방향과
    덜어내는 방향이 모두 반증됐다** — 실측의 정본은 `audio_gateway/nova._SOUND_INSTRUCTION` 위
    주석이다. ⇒ 지시문이 아니라 **재료**를 바꾼 것이 결정 72 다.

    ⛔ **목록을 계획의 소리로 덮지 않는다.** 후보 기제의 조건이 *"If one of them is off again"* 이라
    목록이 넓을수록 「실제로 들은 소리」를 그 안에서 찾을 확률이 높아진다 — 하나만 남기면 결정 72 가
    노린 값이 줄어든다.

    ⛔ **같은 키를 두 번 싣지 않는다.** 두 출처가 같은 표(`error_patterns`)에서 오므로 겹치는 것이
    평시다. 두 번 실리면 「후보가 둘」이 아니라 **그 키를 강조한 것**으로 읽혀 지금 걷어 낸 단수
    지목이 다른 모양으로 되살아난다.

    ⛔ **빈 목록을 「말하기로 떨어뜨려라」로 번역하지 않는다** — 결정 72 가 그 폴백을 없앴다. 후보가
    0건이면 조립기가 그 블록을 아예 빼고, 코치는 **실제로 들은 소리**로 시작한다.

    ⚠️ **순수 함수로 둔 이유**: 이 선택이 정책이라 회귀를 단위 테스트로 잡아야 한다. DB 를 타면
    같은 판정에 통합 픽스처가 필요해지고, 그러면 「어느 출처가 앞인가」가 조용히 바뀌어도 통과한다.
    """
    focus = [
        item.target_form
        for item in (plan.focus if plan is not None else ())
        if item.pattern_key.startswith(PRONUNCIATION_PATTERN_KEY_PREFIX)
    ]
    # `dict.fromkeys` — 순서를 지키면서 중복만 걷는다(`set` 은 순서를 잃고, 그 순서가 규칙이다).
    return list(dict.fromkeys([*focus, *known_sounds]))


async def _load_shadowing_turns_or_none(
    pool: asyncpg.Pool, session_id: UUID, settings: Settings
) -> ShadowingTurns | None:
    """세션이 고른 클립 + 설정값 3종 — 없거나 읽지 못하면 `None` (설계서 §12 요구 5).

    **예외를 밖으로 던지지 않는다** — `_load_known_sounds_or_empty` 와 같은 분업이다. 클립을 못
    읽어도 세션은 열린다: 「클립이 0행이어도 세션을 연다」가 `start_shadowing_session` 의 계약이고,
    여기서 터뜨리면 조회 한 번의 실패로 쉐도잉 진입이 **전부** 막힌다.

    ⛔ **값의 정본은 `Settings` 다** — 화면이 자기 기본값을 갖지 않고 전달만 받는다(§7).
    """
    try:
        async with pool.acquire() as conn:
            clip = await load_session_clip(conn, session_id)
    except Exception:
        logger.exception("쉐도잉 클립을 읽지 못해 낭독 재료 없이 진행한다")
        return None
    if clip is None:
        return None
    return ShadowingTurns(
        clip=clip,
        audio_root=settings.shadowing_audio_root,
        playback_rate=settings.shadowing_playback_rate,
        repeat_count=settings.shadowing_repeat_count,
    )


async def _load_prepared_plan_or_none(pool: asyncpg.Pool) -> PreparedPlan | None:
    """직전 세션이 준비해 둔 오늘의 계획 — 없거나 읽지 못하면 `None` (설계서 §3.3).

    ⛔ **`PreparedPlan`을 그대로 돌려준다 — `.instruction`만 꺼내지 않는다.** 이전 판은
    지시문만 돌려주고 계획 객체를 **버렸고**, 그 상태에서는 오늘의 질문 3~5개가 어댑터까지
    실릴 자리가 **아예 없었다**(설계서 §2.1의 C-1). 질문을 여기서 다시 조회하면 조회가 둘로
    갈라져 「지시문이 가리키는 계획」과 「질문이 온 계획」이 달라질 수 있다.

    **계획 조회 실패를 세션 시작 실패로 번역하지 않는다** — `_load_known_sounds_or_empty`와
    같은 규약이다. 계획은 지시문에 얹는 **부가 정보**이고, 조회가 깨졌다고 세션을 못 열면
    대화 전체를 잃는다.

    계획이 없는 것과 조회가 실패한 것을 **여기서 구분하지 않는다**: 둘 다 "오늘은 고정
    지시문으로 시작한다"로 수렴하고, 그것이 §3.3이 정한 동작이다. 구분이 필요한 신호는
    로그가 담당한다 — `load_prepared_plan`은 부재를 조용히 `None`으로 돌려주고, 여기 걸리는
    것은 조회 자체가 깨진 경우뿐이다.
    """
    try:
        async with pool.acquire() as conn:
            return await load_prepared_plan(conn, FIXED_USER_ID)
    except Exception:
        logger.exception("준비된 계획을 읽지 못해 계획 없이 시작한다")
        return None


async def _load_scenario_or_none(pool: asyncpg.Pool, session_id: UUID) -> SessionScenario | None:
    """이 세션이 올라선 무대 — 없거나 읽지 못하면 `None` (설계서 §2.1, `TASK-25` AC#1·#3).

    위 두 함수와 **글자 그대로 같은 실패 규약**이다: 조회 실패를 세션 시작 실패로 번역하지 않고,
    로그를 남기고 무대 없이 진행한다. 무대는 지시문에 얹는 **부가 정보**이고, 조회가 깨졌다고
    세션을 못 열면 대화 전체를 잃는다.

    무대가 없는 것(`scenario_id` null)과 조회가 깨진 것을 여기서 구분하지 않는 것도 같다 —
    둘 다 "무대 블록 없이 시작한다"로 수렴한다. 구분은 로그가 담당한다.
    """
    try:
        async with pool.acquire() as conn:
            return await load_session_scenario(conn, session_id)
    except Exception:
        logger.exception("이 세션의 무대를 읽지 못해 무대 없이 진행한다")
        return None


async def _record_drill_turns_or_continue(
    pool: asyncpg.Pool,
    session_id: UUID,
    *,
    questions: Sequence[PlanQuestion],
    settings: Settings,
) -> None:
    """기대 exchange 수를 세션에 남긴다 — 실패하면 로그만 남기고 진행한다 (캡틴 결정 16).

    같은 실패 규약을 잇는다: 이 값은 **관측용 부가 정보**이고, UPDATE가 깨졌다고 대화를 못 열면
    손해가 더 크다. ⚠️ 다만 조회와 달리 **잃는 것이 있다** — 기대값은 복원 불가라서(계획 조회가
    「최신 1건」이다) 이 UPDATE를 놓친 세션은 영구히 관측 대상에서 빠진다. 그래서 `exception`으로
    찍는다: 문서가 지정한 실행이 `--log-level warning`이라 그 아래는 한 줄도 보이지 않는다(H-Z).
    """
    try:
        async with pool.acquire() as conn:
            await record_drill_turns_expected(
                conn,
                session_id,
                questions=questions,
                drill_count=settings.drill_count,
                drill_turns_min=settings.drill_turns_min,
            )
    except Exception:
        logger.exception("세션 %s의 기대 exchange 수를 남기지 못해 그대로 진행한다", session_id)


@router.websocket(WS_SESSION_PATH)
async def session_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    channel = WebSocketChannel(websocket)
    pool: asyncpg.Pool = websocket.app.state.db_pool
    # 살아있는 세션 레지스트리를 **세션 행을 만들기 전에** 집는다 (I-4). `create_app()`을
    # 우회한 배선이면 여기서 `AttributeError`로 끝나는데, 그 시점에는 아직 세션 행이 없어
    # `active` 고아를 남기지 않는다 — 뒤로 밀면 행을 만든 뒤 터져서 고아가 생긴다.
    live_sessions: set[UUID] = websocket.app.state.live_sessions

    # 쉐도잉 진입 (`TASK-45` · 결정 35). ⛔ **값역을 여기서 복제하지 않는다** — 아는 것은
    # 「쉐도잉인가 아닌가」 하나고, 나머지는 `learning_sessions_mode_check` 가 가둔다. 알 수 없는
    # 값은 말하기로 떨어진다: 거부하면 그 값역이 이 파일에 복제되고 두 곳이 갈라진다.
    # ⚠️ 대가를 명시한다 — 오타 난 링크로 붙으면 조용히 말하기 세션을 받으므로 경고를 남긴다.
    requested_mode = websocket.query_params.get("mode")
    shadowing_requested = requested_mode == SHADOWING_MODE
    # `TASK-10.1` — 발음 전용 모드는 **세션 행을 바꾸지 않고 지시문만 바꾼다**(상수 위 주석).
    # 그래서 위 `shadowing_requested` 와 달리 `create_session` 분기에 끼어들지 않는다.
    pronunciation_requested = requested_mode == PRONUNCIATION_MODE
    if requested_mode not in (None, SHADOWING_MODE, SPEAKING_MODE, PRONUNCIATION_MODE):
        # ⚠️ `?mode=speaking` 은 **알 수 없는 값이 아니다** — 명시적으로 그것을 고른 것이므로
        # 경고하지 않는다(2026-09-09 리뷰 지적). 경고는 오타·낡은 링크만 가리켜야 값을 한다.
        logger.warning("알 수 없는 mode=%r — 말하기 세션으로 진행한다", requested_mode)

    # `TASK-10.2` — 추가 학습 진입이 자기를 표시하는 자리(`?source=additional`). ⛔ **값역을
    # 여기서 열거하지 않는다**: 001 의 `learning_sessions_learning_source_check` 가 가두고, 값이
    # 그 값역 밖이면 아래 `asyncpg.PostgresError` 경로로 떨어져 세션 실패를 알린다. 넘기지 않으면
    # 001 의 기본값(`recommended`)이 쓰인다 — 즉 **모르는 값을 조용히 추천으로 바꾸지 않는다.**
    requested_source = websocket.query_params.get("source")
    try:
        session_id = (
            await start_shadowing_session(pool, FIXED_USER_ID, learning_source=requested_source)
            if shadowing_requested
            else await create_session(pool, FIXED_USER_ID, learning_source=requested_source)
        )
    except asyncpg.PostgresError:
        # 시드가 없으면(고정 사용자 부재) 여기서 걸린다 — 연결을 조용히 매달아두지
        # 않고 실패를 알린 뒤 닫는다.
        logger.exception("세션 행을 만들 수 없어 연결을 닫는다")
        await channel.send_event({"type": "session_failed", "reason": SESSION_CREATE_FAILED_REASON})
        await _safe_close(websocket)
        return

    # 이 세션은 살아 있다 — 고아 세션 리퍼(I-4)가 닫아선 안 된다는 표시다. 세션 행 생성
    # **직후**, 다음 `await`보다 **앞**에서 등록하는 것이 계약이다: 바로 아래에서 pool acquire를
    # **여러 번** await하므로(소진되면 길어진다) 등록을 그 뒤로 밀면 리퍼가 볼 수 있는 진짜 창이
    # 열린다. 그 창은 기능이 붙을수록 늘어나므로 등록이 앞에 있어야 한다는 근거는 약해지지 않는다.
    # ⚠️ **여기에 개수를 적지 않는다** — 이전 판이 「네 개」로 세어 뒀다가 쉐도잉 경로가 붙으며
    # 낡았고(2026-09-09 리뷰가 잡았다), 그 수를 고치는 순간 결정 37 로 다시 낡았다. **근거는 개수가
    # 아니라 「await 가 여럿이다」**이므로 세지 않는 서술이 옳다.
    # ⚠️ **"갓 만든 세션이 즉시 리핑된다"는 위험은 없다** — `started_at`이 `now()` 기본값이라
    # 나이가 0초이고 유예를 만족할 수 없다. 이 순서의 근거는 유예가 아니라 위의 await 창이다.
    # 해제는 어떤 경로로 끝나든 아래 `finally`가 한다.
    live_sessions.add(session_id)
    try:
        known_sounds = await _load_known_sounds_or_empty(pool)
        # 무대는 **세션 행에 박힌 것**을 읽으므로 `create_session` 뒤여야 한다(설계서 §2.1).
        scenario = await _load_scenario_or_none(pool, session_id)
        prepared = await _load_prepared_plan_or_none(pool)
        # 팩토리로 가는 것은 **데이터**다(G-3): 지시문과 질문 목록을 따로 넘긴다. `PreparedPlan`
        # 자체를 넘기면 `factory`·`nova`가 `services`를 import해 의존 방향이 뒤집힌다.
        plan = prepared.instruction if prepared is not None else None
        questions = prepared.questions if prepared is not None else []
        settings = get_settings()
        # 질문 수를 알아야 계산하므로 계획 조회 **뒤**다. 계획이 없으면 아무것도 쓰지 않는다 →
        # 컬럼이 null로 남고 그것이 「관측 대상 아님」이다(캡틴 결정 16).
        # ⛔ **쉐도잉 세션에는 쓰지 않는다** (캡틴 결정 37). 그 값은 **말하기 관측 지표**이고
        # `TASK-36`(기대 exchange 상한이 10분 세션에서 실현 가능한지)이 읽는다 — 쉐도잉에 쓰면
        # 아직 돌리지도 않은 관측이 오염된 데이터를 본다. null 이 「관측 대상 아님」을 뜻하는 것은
        # 결정 16 이 이미 세운 계약이므로 여기서는 그 계약을 그대로 쓰는 것이다.
        # `TASK-10.1` — 발음 전용 모드에도 쓰지 않는다. 근거가 쉐도잉과 **같다**(결정 37): 이 모드의
        # 지시문에는 **질문이 실리지 않으므로** 기대 exchange 수가 애초에 성립하지 않고, 그 값을
        # 쓰면 `TASK-36`(기대 상한이 10분 세션에서 실현 가능한가)이 아직 돌리지도 않은 관측이
        # 오염된 데이터를 본다. null 이 「관측 대상 아님」인 것은 결정 16 이 세운 계약이다.
        if not shadowing_requested and not pronunciation_requested:
            await _record_drill_turns_or_continue(
                pool, session_id, questions=questions, settings=settings
            )

        # 결정 72 — 계획이 고른 소리를 **이름으로 주지 않고** 후보 목록 앞에 더한다.
        # ⛔ **후보가 0건이어도 말하기로 떨어뜨리지 않는다** — 그 폴백을 없앤 것이 이 결정이다.
        pronunciation_candidates = (
            _pronunciation_candidates(plan, known_sounds) if pronunciation_requested else []
        )
        # 화면에 실을 **오늘의 소리**는 후보의 첫 항목이다(`session_started`). ⚠️ 이 값이 없는 것은
        # 이제 「말하기로 떨어졌다」가 아니라 **「후보가 아직 없다」**만 뜻한다 — 화면이 아직 그것을
        # 폴백으로 읽으므로 문구를 고치는 것은 `TASK-128.4` 가 갖는다.
        pronunciation_focus = pronunciation_candidates[0] if pronunciation_candidates else None
        # `TASK-112`(결정 67) — 세션 행이 자기가 발음 세션임을 적는다. ⛔ **적는 조건이 결정 72 로
        # 「요청받았는가」가 됐다.** 이전 판은 「소리가 정해졌는가」였고 근거는 **폴백의 존재**였다
        # (폴백으로 말하기가 된 세션까지 발음으로 집계하면 결정 67 이 닫으려던 결함의 반대 방향
        # 변종이 됐다). 폴백이 사라졌으므로 그 근거도 사라졌다 — 요청한 세션은 실제로 발음 세션이다.
        # 실패해도 대화를 막지 않는다(`_record_drill_turns_or_continue` 와 같은 규약) — 다만
        # `exception`·`warning` 으로 갚는다. 값역 밖 값은 애초에 상수라 오지 않고, 그런 일이 나면
        # 그것은 값역이 갈라졌다는 신호이므로 로그가 그것을 가리켜야 한다.
        if pronunciation_requested:
            try:
                if not await set_session_mode(pool, session_id, mode=PRONUNCIATION_MODE):
                    logger.warning(
                        "세션 %s 의 mode 를 %s 로 적지 못했다 — 그 사이 세션이 닫혔다",
                        session_id,
                        PRONUNCIATION_MODE,
                    )
            except asyncpg.PostgresError:
                logger.exception(
                    "세션 %s 의 mode 를 %s 로 적을 수 없다 — 집계가 이 세션을 말하기로 센다",
                    session_id,
                    PRONUNCIATION_MODE,
                )

        try:
            adapter = create_voice_adapter(
                settings,
                # ⚠️ **전용 모드에는 후보 목록을 넘긴다**(결정 72) — 일반 세션은 계획 블록이 소리를
                # 따로 싣지 않게 됐으므로 놓친 소리 목록을 그대로 준다. 즉 이 인자의 «내용»이
                # 모드마다 다르고, 조립기는 그것을 「후보」로만 읽는다.
                known_sounds=pronunciation_candidates if pronunciation_requested else known_sounds,
                plan=plan,
                questions=questions,
                scenario=scenario,
                pronunciation_mode=pronunciation_requested,
                # ⛔ **이 인자를 빼면 Nova 토큰 기록이 조용히 꺼진다** (`TASK-124` · 결정 68).
                # 어댑터의 기본값이 `None`(기록 없음)이고 실물 배선은 여기 하나뿐이다 — `main.py` 의
                # `usage_sink` 와 같은 부류의 위험이고 같은 방식으로 게이트 테스트가 못 박는다.
                usage_sink=pool_usage_sink(pool),
            )
        except Exception:
            # 어댑터를 만들지도 못했다(설정 오타/구현 부재). 세션 행은 이미 있으므로
            # `active` 고아로 두지 않고 failed로 닫는다 — 결과 화면이 "연결 실패"를
            # 표시할 근거가 그 status다 (R2 규칙 1).
            logger.exception("음성 어댑터를 만들 수 없어 세션 %s를 failed로 닫는다", session_id)
            await mark_session_ended(pool, session_id, "failed")
            await channel.send_event(
                {"type": "session_failed", "reason": ADAPTER_UNAVAILABLE_REASON}
            )
            return

        # 쉐도잉 재료는 **세션 시작이 읽어 넘긴다** — 러너가 스스로 조회하면 게이트웨이가
        # `services` 를 더 깊이 알게 되어 의존 방향이 뒤집힌다(`ShadowingTurns` docstring).
        shadowing = (
            await _load_shadowing_turns_or_none(pool, session_id, settings)
            if shadowing_requested
            else None
        )
        runner = SessionRunner(
            adapter,
            pool,
            session_id,
            client=channel,
            shadowing=shadowing,
            pronunciation_sound=pronunciation_focus,
        )
        try:
            await runner.run()
        except Exception:
            # 세션 하나의 사고가 소켓을 close 프레임 없이 끊게 두지 않는다.
            logger.exception("세션 %s가 예외로 끝났다", session_id)
    finally:
        # 소켓을 닫기 **전에** 해제한다 — 순서가 뒤집히면 소켓이 이미 닫힌 세션이
        # 잠깐 live로 남아 리퍼 면제 대상이 된다. 해제를 빠뜨리면 그 세션은 영구히
        # 면제되어, 정작 고아가 됐을 때 아무도 닫지 않는다.
        live_sessions.discard(session_id)
        await _safe_close(websocket)
