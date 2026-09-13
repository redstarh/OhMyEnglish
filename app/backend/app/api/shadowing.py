"""쉐도잉 자원의 HTTP 표면 (`TASK-66`).

설계: `docs/design/2026-09-14-shadowing-clip-audio-design.md` §5.

⛔ **`/api/sessions` 아래에 넣지 않는다** — 클립은 세션에 매인 것이 아니라 여러 세션이 공유하는
제품 자산이다. 낭독(`api/results.py:get_recording`)이 세션 경로 아래 있는 것은 그것이 학습자
개인의 것이고 **세션 경계가 개인정보 경계**이기 때문이다(그 docstring 이 근거를 가진다).
클립을 그 아래에 두면 없는 경계를 있는 것처럼 보이게 하고, 세션마다 같은 자산을 다른 URL 로
부르게 된다.

⛔ **`StaticFiles` 로 마운트하지 않는다** — `recording_url` 의 주석이 *"파일 경로가 아니라 API
경로다"* 로 그 방향을 이미 정했고, 이 리포에 `StaticFiles` 마운트는 0곳이다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response

from app.config import get_settings
from app.services.clip_audio import CLIP_AUDIO_MEDIA_TYPE, load_clip_audio

router = APIRouter(prefix="/api/shadowing", tags=["shadowing"])


@router.get("/clips/{item_id}/audio")
async def get_clip_audio(item_id: UUID, request: Request) -> Response:
    """합성한 클립 오디오 하나를 WAV 로 내보낸다.

    **판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다** — `get_recording` 과 같은 규약이다.
    `load_clip_audio` 가 `None` 을 주는 세 경우가 **전부 404** 다: 클립 행이 없다 · 포인터가 아직
    없다(오디오를 만들지 않은 클립) · 포인터만 있고 파일이 없다(배포에서 자산이 빠졌다).
    뒤의 둘은 정상적인 중간 상태이므로 500 으로 터뜨리지 않는다.

    ⚠️ **`item_id` 가 `UUID` 로 선언된 것이 경로 탈출을 라우팅에서 막는다** — 022 의 CHECK(값역)와
    `clip_audio_path` 의 서명(조립)에 이은 셋째 겹이다.
    """
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        audio = await load_clip_audio(conn, get_settings().shadowing_clip_audio_root, item_id)
    if audio is None:
        raise HTTPException(status_code=404, detail="clip audio not found")
    return Response(content=audio, media_type=CLIP_AUDIO_MEDIA_TYPE)
