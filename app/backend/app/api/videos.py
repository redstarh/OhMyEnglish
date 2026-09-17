"""영상 학습 자원의 HTTP 표면 (`TASK-165`).

설계: `docs/design/2026-09-18-video-learning-design.md` §3·§7.

⛔ **이 리포의 첫 쓰기 REST 라우터다.** 기존 일곱은 전부 `GET` 이고 쓰기는 WebSocket 으로만
일어났다. 그래서 `create_app()` 의 CORS `allow_methods` 를 **함께 넓혀야 한다** — 그 값을 그대로
두면 이 파일의 테스트는 전부 통과하는데(ASGI 는 preflight 를 거치지 않는다) **브라우저에서만
담기·지우기가 막힌다.** `tests/integration/test_videos_api.py` 의
`test_the_browser_is_allowed_to_send_the_write_methods` 가 그 구멍을 겨눈다.

⛔ **판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다** — `api/shadowing.py`·`api/daily.py` 와
같은 규약이다. 그래서 이 파일에 SQL 도 30일 계산도 반올림도 없다.

⚠️ **`video_id`·`item_id` 를 `UUID` 로 선언하는 것이 경로 탈출을 라우팅에서 막는 겹이다** —
`api/shadowing.py:get_clip_audio` 가 같은 근거로 그 형을 쓴다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response

from app.models.user import FIXED_USER_ID
from app.models.video import CLIP_MAX_SPAN_SECONDS, PhraseCreateRequest, VideoCreateRequest
from app.services.video_url import parse_youtube_id
from app.services.videos import (
    UpsertedVideo,
    VideoDetail,
    VideoPhrase,
    VideoSummary,
    add_phrase,
    delete_phrase,
    delete_video,
    list_videos,
    load_video_with_phrases,
    upsert_video,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _video_core(video: VideoSummary | VideoDetail | UpsertedVideo) -> dict[str, object]:
    """세 응답이 공통으로 싣는 넷. ⛔ 썸네일 URL 은 없다 — 화면이 `youtube_id` 로 조립한다(§2)."""
    return {
        "id": str(video.id),
        "youtube_id": video.youtube_id,
        "title": video.title,
        "channel_name": video.channel_name,
    }


def _summary_payload(video: VideoSummary) -> dict[str, object]:
    return {
        **_video_core(video),
        "phrase_count": video.phrase_count,
        "metadata_stale": video.metadata_stale,
    }


def _phrase_payload(phrase: VideoPhrase) -> dict[str, object]:
    """⚠️ `Decimal` 을 `float` 로 바꾼다 — `json` 이 `Decimal` 을 직렬화하지 못한다.

    초 단위 시간 창이라 배정밀도로 잃을 정밀도가 없다. `ShadowingTurns.as_event_payload` 가 같은
    변환을 같은 근거로 한다 — **이름도 그쪽과 맞춘다**(`clip_start_sec`·`clip_end_sec`).
    """
    return {
        "id": str(phrase.id),
        "transcript": phrase.transcript,
        "clip_start_sec": float(phrase.clip_start_sec),
        "clip_end_sec": float(phrase.clip_end_sec),
    }


def _detail_payload(detail: VideoDetail) -> dict[str, object]:
    """⚠️ **구간 상한을 함께 내려보낸다.**

    이 값은 스키마의 `shadowing_items_span_within_limit` 이 정본이고 `CLIP_MAX_SPAN_SECONDS` 가 그
    사본이다(그 둘은 `tests/unit/test_schema.py` 가 대조한다). ⛔ 화면이 **자기 사본을 두지 않게**
    여기서 실어 준다 — 세 번째 사본만 대조 장치가 없어 조용히 갈라질 자리였다.
    """
    return {
        **_video_core(detail),
        "metadata_stale": detail.metadata_stale,
        "clip_max_span_sec": float(CLIP_MAX_SPAN_SECONDS),
        "phrases": [_phrase_payload(phrase) for phrase in detail.phrases],
    }


def _upserted_payload(video: UpsertedVideo) -> dict[str, object]:
    return {**_video_core(video), "created": video.created}


@router.get("")
async def get_videos(request: Request) -> dict[str, object]:
    """담아 둔 영상 전부. 없으면 빈 배열이고 404 가 아니다.

    ⚠️ 배열을 최상위로 내리지 않고 `videos` 키로 감싼다 — `api/daily.py` 가 같은 모양이고, 나중에
    곁가지(개수·페이지)를 더할 때 응답 형태가 바뀌지 않는다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        videos = await list_videos(conn)
    return {"videos": [_summary_payload(video) for video in videos]}


@router.post("", status_code=201)
async def post_video(
    body: VideoCreateRequest, request: Request, response: Response
) -> dict[str, object]:
    """영상을 담거나, 이미 담은 것이면 **메타데이터를 갱신한다.**

    ⛔ **중복이 오류가 아니다**(설계서 §1 질문 2). 갱신이면 `200` 과 `created=false` 를 주고
    화면이 「이미 담아 둔 영상이에요」를 보인다 — 별도 갱신 엔드포인트를 만들지 않는 것이 이 판단의
    값이다.

    ⚠️ **URL 파싱 실패가 `422` 다.** `parse_youtube_id` 는 「YouTube 링크가 아니다」와 「영상이
    없다」를 가르지 않는다(가를 수 없다 — 우리는 조회하지 않는다). 화면이 한 문구로 옮긴다(§7).
    """
    youtube_id = parse_youtube_id(body.url)
    if youtube_id is None:
        raise HTTPException(status_code=422, detail="no youtube video in that link")

    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        stored = await upsert_video(
            conn, youtube_id=youtube_id, title=body.title, channel_name=body.channel_name
        )
    if not stored.created:
        response.status_code = 200
    return _upserted_payload(stored)


@router.get("/{video_id}")
async def get_video(video_id: UUID, request: Request) -> dict[str, object]:
    """영상 하나와 담은 문장 전부 — **한 번의 왕복**이다(설계서 §3)."""
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        detail = await load_video_with_phrases(conn, video_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="video not found")
    return _detail_payload(detail)


@router.delete("/{video_id}", status_code=204)
async def remove_video(video_id: UUID, request: Request) -> Response:
    """영상만 지운다. **담은 문장은 남는다** — FK 가 `on delete set null` 이다(설계서 §1 질문 1)."""
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        removed = await delete_video(conn, video_id)
    if not removed:
        raise HTTPException(status_code=404, detail="video not found")
    return Response(status_code=204)


@router.post("/{video_id}/phrases", status_code=201)
async def post_phrase(
    video_id: UUID, body: PhraseCreateRequest, request: Request
) -> dict[str, object]:
    """구간과 그 구간에서 들은 문장을 담는다.

    ⚠️ 구간의 순서·길이는 `PhraseCreateRequest` 가 이미 `422` 로 막았다 — 여기 도달한 값은 값역
    안이다. `None` 이 오는 경우는 **영상이 없는 것 하나**다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        phrase = await add_phrase(
            conn,
            video_id,
            user_id=FIXED_USER_ID,
            transcript=body.transcript,
            start_sec=body.clip_start_sec,
            end_sec=body.clip_end_sec,
        )
    if phrase is None:
        raise HTTPException(status_code=404, detail="video not found")
    return _phrase_payload(phrase)


@router.delete("/{video_id}/phrases/{item_id}", status_code=204)
async def remove_phrase(video_id: UUID, item_id: UUID, request: Request) -> Response:
    """그 영상에 속한 문장만 지운다.

    ⛔ **속하지 않으면 404 다** — 「다른 영상의 문장을 지우는 요청」이 성립하지 않게 하는 것이
    경로에 `video_id` 를 요구한 이유다(설계서 §3).
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        removed = await delete_phrase(conn, video_id, item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="phrase not found")
    return Response(status_code=204)
