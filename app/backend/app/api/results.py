"""조회 엔드포인트 — `GET /api/sessions/{id}/results`(설계서 §5.5, R1~R3)와 `/next-plan`.

`/next-plan`의 계약은 그 함수의 docstring이 소유한다 (R11-3 — 추천 이유를 화면에서 볼 수
있어야 한다). 아래 서술은 결과 조회의 것이다.

라우터는 판정 로직을 갖지 않는다 — `services.results.get_session_result`가
R2 우선순위를 전부 결정하고, 여기서는 그 결과를 HTTP로 옮기기만 한다:

* 세션이 없으면(`None`) `404`.
* `SessionResult.corrections`가 `None`이면 응답 JSON에 `corrections` 키
  **자체를 넣지 않는다**(생략 — `null`도 아니다). `analyzing`/`connection_failed`/
  `no_utterances`에서 교정을 조용히 노출하지 않기 위한 계약이 API 응답 shape까지
  그대로 이어진다(§5.5 "잠정 노출 금지").
* `drill`은 `corrections`와 **같은 규약**을 따른다 — `SessionResult.drill`이 `None`이면
  키 자체를 넣지 않는다. 그래서 `analyzing`/`connection_failed`/`no_utterances`에서는
  기대값이 이미 기록돼 있어도 빠지고, 계획 없이 시작한 세션에서도 빠진다(설계서 §2.3).
  ⚠️ 두 수(`exchanges_observed`/`exchanges_expected`)를 내려주지만 **화면은 그것을
  렌더하지 않는다** — 소비자는 서버·로그이고, 화면은 미달일 때 문장 하나만 그린다
  (캡틴 결정 10: `9 / 12`로 읽히면 점수처럼 보이고 미달의 주어는 학습자가 아니다).
  이 어긋나 보이는 계약은 의도된 것이며 정본은 `services/results.py`의 `DrillTurns`다.
* `pronunciation`은 **항상 있다**(비면 `[]`). 발음 시도는 R2 판정과 독립이며
  구조적으로 확정값이라 `corrections`의 키 생략 규약을 따르지 않는다 —
  근거는 `services/results.py` 모듈 docstring. 각 항목의 `spoken_form`은
  `None`이면 키를 지우지 않고 `null`로 싣는다: "들린 발음 없음"(대답 없이 끝난
  시도)과 "그 필드를 모른다"를 프론트가 구분해야 한다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response

from app.api.ws import FIXED_USER_ID
from app.config import get_settings
from app.services.recordings import RECORDING_MEDIA_TYPE, load_recording
from app.services.results import (
    Correction,
    DrillTurns,
    PronunciationAttempt,
    SessionResult,
    get_session_result,
)
from app.services.sessions import load_prepared_plan

router = APIRouter(prefix="/api/sessions", tags=["results"])


# 리터럴 경로를 `/{session_id}/results`보다 **먼저** 등록한다. 세그먼트 수가 달라 지금은
# 가려지지 않지만, 나중에 `/{something}` 한 세그먼트 경로가 생기면 등록 순서가 판정한다.
@router.get("/next-plan")
async def next_plan(request: Request) -> dict[str, str | None]:
    """다음 세션에 쓸 계획의 **추천 이유와 목표 수준만** 내려준다 (`docs/PRD.md:189` R11-3).

    계획이 없으면 404가 아니라 두 값이 `null`이다 — 계획 부재는 오류가 아니고, 화면은 그
    자리를 비우기만 한다(설계서 §9 Contract: 계획 부재가 실패로 번역되지 않는다). `null`이
    뜻하는 것은 "**세션이 쓸 계획이 없다**"이고, 빈 이유가 내려오는 경우는 아니다 —
    이유가 빈 계획은 저장 자체가 막힌다(`session_plans_reason_not_blank`, 007).

    초점 패턴·질문 목록을 내려주지 않는 이유: 캡틴 결정은 "간략하게 표시"였고, 질문을
    미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.

    **세션 시작과 같은 함수로 읽는다**(`load_prepared_plan`) — 조회 SQL을 여기서 다시
    쓰면 "다음 계획"의 정의가 둘로 갈라진다. 그래서 목표 수준도 지시문에서 꺼낸다:
    `session_plans.target_level`과 같은 값임을 저장 시점에 `PlanOutput`이 강제하고
    (`models/plan.py` `_target_level_matches_level_and_instruction`), 지시문을 읽을 수
    없어 세션이 그 계획을 **쓰지 못하는** 경우에는 화면도 함께 비워야 맞다 — 그때
    이유만 보여주면 화면은 오늘의 초점을 말하는데 대화 상대는 고정 지시문으로 말한다.

    조회 실패를 삼키지 않는다(`get_results`와 같은 규약) — 프론트가 실패를 이미 빈 화면으로
    번역하므로, 여기서 삼키면 화면 결과는 같은데 장애만 조용해진다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        prepared = await load_prepared_plan(conn, FIXED_USER_ID)
    if prepared is None:
        return {"reason": None, "target_level": None}
    return {"reason": prepared.reason, "target_level": prepared.instruction.target_level}


def _correction_payload(correction: Correction) -> dict[str, object]:
    return {
        "pattern_key": correction.pattern_key,
        "category": correction.category,
        "original_span": correction.original_span,
        "correction": correction.correction,
        "reason": correction.reason,
        "target_form": correction.target_form,
        "occurrences": correction.occurrences,
    }


def _pronunciation_payload(attempt: PronunciationAttempt) -> dict[str, object]:
    """기계 키(`target_sound`)는 여기에 없다 — 설계서 §10 미결 4 결정.

    계획서 `:1352`는 `{target_form, target_sound, outcome}`을 적었지만 그 `target_sound`는
    폐기됐다. 실물 왕복 0회라 키의 값역이 관측되지 않았고, 화면에 내보내면 학습자가
    `th_as_s`를 읽는다.
    """
    return {
        "target_form": attempt.target_form,
        "spoken_form": attempt.spoken_form,
        "outcome": attempt.outcome,
        "signal_source": attempt.signal_source,
    }


def _drill_payload(drill: DrillTurns) -> dict[str, object]:
    return {
        "exchanges_observed": drill.exchanges_observed,
        "exchanges_expected": drill.exchanges_expected,
    }


def _result_payload(result: SessionResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": result.status,
        "partial_failure": result.partial_failure,
        "pronunciation": [_pronunciation_payload(item) for item in result.pronunciation],
        # `TASK-79` — `pronunciation`과 같은 규약으로 **항상 싣는다**(아래 키 생략 규약을 따르지
        # 않는다). 화면이 상태마다 키 존재를 갈라 읽지 않게 하는 것이 목적이고, 뜻과 근거는
        # `services/results.SessionResult.awaiting_analysis`가 소유한다.
        "awaiting_analysis": result.awaiting_analysis,
    }
    if result.corrections is not None:
        payload["corrections"] = [_correction_payload(item) for item in result.corrections]
    # `corrections`와 **같은 모양**으로 뺀다 — 새 방식을 발명하지 않는다. 판정은 이미
    # `services/results.py`가 끝냈고(`drill=None`), 여기서는 그것을 키 유무로 옮기기만 한다.
    if result.drill is not None:
        payload["drill"] = _drill_payload(result.drill)
    return payload


@router.get("/{session_id}/results")
async def get_results(session_id: UUID, request: Request) -> dict[str, object]:
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        result = await get_session_result(conn, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="session not found")
    return _result_payload(result)


@router.get("/{session_id}/recordings/{utterance_id}")
async def get_recording(session_id: UUID, utterance_id: UUID, request: Request) -> Response:
    """학습자의 쉐도잉 낭독 하나를 raw PCM 으로 내보낸다 (`TASK-45` · 설계서 §4.4).

    **판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다** — 이 파일의 다른 라우터와 같은
    규약이다. `load_recording` 이 `None` 을 돌려주는 경우가 셋이고 **전부 404 다**: 발화가 없다 ·
    포인터가 아직 없다 · 포인터만 남고 파일이 없다. 뒤의 둘은 §4.5·§6 이 정상으로 인정하는 중간
    상태이므로 500 으로 터뜨리지 않는다.

    ⛔ **경로의 두 세그먼트가 둘 다 조회 조건이다** — `utterance_id` 만 보면 세션을 바꿔 넣은
    요청이 남의 녹음을 받아 간다. 두 값이 `UUID` 로 선언된 것이 경로 탈출도 함께 막는다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        audio = await load_recording(
            conn, get_settings().shadowing_audio_root, session_id, utterance_id
        )
    if audio is None:
        raise HTTPException(status_code=404, detail="recording not found")
    return Response(content=audio, media_type=RECORDING_MEDIA_TYPE)
