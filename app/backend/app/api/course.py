"""문법 코스 엔드포인트 (`TASK-286`).

설계: `docs/design/2026-10-26-grammar-course-design.md` §6.
판정은 `services.course` 가 하고 여기서는 HTTP 로 옮기기만 한다.
이 리포의 다른 라우터와 같은 규약이다.

⚠️ **진도 저장이 `PUT` 이 아니라 `POST` 인 이유**: CORS 허용 메서드가 `GET`·`POST`·`DELETE` 이고
(`api/main.py`), 메서드 하나를 위해 그 표면을 넓히지 않았다.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from app.audio_gateway.factory import create_transcriber, transcriber_available
from app.config import get_settings
from app.models.course import (
    MAX_ATTEMPT_PCM_BYTES,
    Course,
    ProgressUpdate,
    load_course,
    sentence_key,
)
from app.models.user import FIXED_USER_ID
from app.services.course import (
    DayProgress,
    day_sentence_keys,
    load_overview,
    load_progress,
    load_sentence_counts,
    record_attempt,
    save_progress,
)
from app.services.daily_summary import timezone_of
from app.services.usage import pool_usage_sink

router = APIRouter(prefix="/api/course", tags=["course"])


def _progress_payload(progress: DayProgress | None) -> dict[str, object] | None:
    if progress is None:
        return None
    return {
        "position_sec": float(progress.position_sec),
        "unit": progress.unit,
        "sentence_index": progress.sentence_index,
        "completed_count": progress.completed_count,
        "last_completed_at": progress.last_completed_at,
        "last_completed_date": (
            progress.last_completed_date.isoformat() if progress.last_completed_date else None
        ),
        "updated_at": progress.updated_at,
    }


@router.get("")
async def get_course(request: Request) -> dict[str, object]:
    """목록 화면 — Day 목록 · 회차 · 날짜별 히트맵 · 최근 날짜 표."""
    course: Course = load_course()
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        timezone = await timezone_of(conn, FIXED_USER_ID)
        overview = await load_overview(conn, course, FIXED_USER_ID, timezone=timezone)
    return {
        "cycle": overview.cycle,
        "current_day": overview.current_day,
        "days": [
            {
                "day": item.day,
                "first_unit": item.units[0].unit,
                "last_unit": item.units[-1].unit,
                "duration_sec": item.duration_sec,
                "progress": _progress_payload(overview.progress.get(item.day)),
            }
            for item in course.days
        ],
        "heatmap": [
            {"date": local_date.isoformat(), "attempts": attempts}
            for local_date, attempts in overview.heatmap
        ],
        "recent": [
            {
                "date": row.local_date.isoformat(),
                "days": row.days,
                "first_unit": row.first_unit,
                "last_unit": row.last_unit,
                "sentences": row.sentences,
                "attempts": row.attempts,
            }
            for row in overview.recent
        ],
    }


@router.get("/days/{day}")
async def get_course_day(day: int, request: Request) -> dict[str, object]:
    """학습 화면 — Day 의 단원·문장과 저장된 진도, 문장별 누적 따라 하기 횟수."""
    course: Course = load_course()
    found = course.day(day)
    if found is None:
        raise HTTPException(status_code=404, detail="day not found")
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        timezone = await timezone_of(conn, FIXED_USER_ID)
        progress = (await load_progress(conn, FIXED_USER_ID, timezone=timezone)).get(day)
        counts = await load_sentence_counts(conn, FIXED_USER_ID, day_sentence_keys(course, day))
    return {
        "day": found.day,
        "youtube_id": found.youtube_id,
        "duration_sec": found.duration_sec,
        "progress": _progress_payload(progress),
        "units": [
            {
                "unit": unit.unit,
                "topic": unit.topic,
                "start_sec": unit.start_sec,
                "end_sec": unit.end_sec,
                "sentences": [
                    {"key": key, "text": text, "attempts": counts.get(key, 0)}
                    for key, text in (
                        (sentence_key(unit.unit, index), text)
                        for index, text in enumerate(unit.sentences)
                    )
                ],
            }
            for unit in found.units
        ],
    }


@router.post("/days/{day}/progress", status_code=204)
async def post_course_progress(day: int, update: ProgressUpdate, request: Request) -> None:
    """재생 위치·연습 단원·문장 번호를 저장한다.

    `completed` 면 그 Day 를 끝낸 것으로 적고 처음으로 되감는다.
    """
    course: Course = load_course()
    if course.day(day) is None:
        raise HTTPException(status_code=404, detail="day not found")
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        saved = await save_progress(conn, course, FIXED_USER_ID, day, update)
    if not saved:
        raise HTTPException(status_code=422, detail="unit is not in that day")


@router.post("/sentences/{key}/attempts")
async def post_course_attempt(key: str, request: Request) -> dict[str, object]:
    """따라 하기 한 번 — 본문은 원시 PCM(16kHz·16bit·mono). 전사해 원문과 낱말 단위로 견준다.

    ⛔ **전사기가 없으면 503 이다** (`api/results.py` 의 낭독 판정과 같은 판단 · `TASK-213`).
    가드가 전사 «앞» 이므로 픽스처 어댑터가 발명한 문장이 기록되지 않는다.
    ⚠️ `words` 가 빈 200 은 「전사를 얻지 못했다」다 — 그래도 따라 한 횟수에는 든다.
    """
    course: Course = load_course()
    if course.sentence(key) is None:
        raise HTTPException(status_code=404, detail="sentence not found")
    # 본문을 읽기 «전에» 선언된 길이로 먼저 거른다(codex 리뷰 MEDIUM).
    # 상한 넘는 본문을 다 받아 메모리에 올린 뒤 413 을 내면 상한이 프로세스를 지키지 못한다.
    # 선언이 없거나 거짓이면 아래의 실제 길이 검사가 잰다.
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_ATTEMPT_PCM_BYTES:
        raise HTTPException(status_code=413, detail="recording is too long")
    pcm = await request.body()
    if not pcm or len(pcm) % 2:
        raise HTTPException(status_code=422, detail="body must be 16-bit PCM")
    if len(pcm) > MAX_ATTEMPT_PCM_BYTES:
        raise HTTPException(status_code=413, detail="recording is too long")
    settings = get_settings()
    if not transcriber_available(settings):
        raise HTTPException(status_code=503, detail="따라 하기 판정을 쓸 수 없다")
    pool: asyncpg.Pool = request.app.state.db_pool
    result = await record_attempt(
        pool,
        course,
        FIXED_USER_ID,
        key,
        pcm,
        transcribe=create_transcriber(settings, usage_sink=pool_usage_sink(pool)),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="sentence not found")
    return {
        "transcript": result.transcript,
        "words": [{"word": item.word, "verdict": item.verdict} for item in result.words],
        "attempts": result.attempts,
    }
