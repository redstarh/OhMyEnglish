"""`api/videos.py` — 영상 학습의 HTTP 표면 (`TASK-165`).

설계: `docs/design/2026-09-18-video-learning-design.md` §3·§7.

⛔ **이 파일이 지키는 것 가운데 하나는 테스트로만 잡히지 않는다** — CORS 다. `api_client` 는 ASGI 로
앱에 직접 붙어 **미들웨어의 preflight 를 거치지 않으므로**, `create_app()` 의
`allow_methods=["GET"]` 를 넓히지 않아도 이 파일의 다른 단정은 전부 통과한다. 그러면 게이트는
초록인데 **브라우저에서만 담기·지우기가 막힌다.**
⇒ 그래서 `test_the_browser_is_allowed_to_send_the_write_methods` 가 그 구멍을 겨눈다.

⚠️ **`api_client` 는 커밋된 행만 본다**(그 픽스처의 docstring). 라우터가 여는 커넥션이 테스트와
별개이므로 롤백되는 `db_conn` 을 쓸 수 없고, **정리 책임이 이 파일에 있다.**
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest
import pytest_asyncio

from app.api.main import FRONTEND_ORIGIN, create_app
from app.models.user import FIXED_USER_ID
from app.models.video import CLIP_MAX_SPAN_SECONDS, CLIP_PRECISION, TRANSCRIPT_MAX_LENGTH

_ID = "dQw4w9WgXcQ"
_OTHER_ID = "jNQXAC9IVRw"
_URL = f"https://www.youtube.com/watch?v={_ID}"


@pytest_asyncio.fixture
async def clean_videos(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자를 세우고, 이 파일이 만든 것을 지운다.

    ⛔ **고정 사용자가 필요한 이유가 설계 그대로 드러났다** — `add_phrase` 는 `level` 을
    `users.current_level` 에서 읽고 **사용자가 없으면 NOT NULL 위반으로 실패한다**(조용히 기본값을
    만들지 않는다). 처음에 이 픽스처가 사용자를 세우지 않아 그 실패를 실제로 봤다.

    ⛔ **내가 만든 경우에만 지운다.** 이 라우터는 `FIXED_USER_ID` 를 쓰는데 그 행은 시드가 넣는
    것일 수도 있다 — 무조건 지우면 `users` cascade 로 **남의 테스트 데이터를 걷는다.**

    ⛔ **`source_url is not null` 로 좁히는 것이 중요하다** — 시드가 넣은 합성 클립은 `source_url`
    이 없으므로 그 조건이 그것을 보호한다. 영상을 지우면 문장의 링크만 null 이 되어 남으므로(설계
    계약) 문장을 **먼저** 지운다.
    """
    async with db_pool.acquire() as conn:
        inserted = await conn.fetchval(
            "insert into users (id, display_name, timezone) "
            "values ($1, 'Video API Test', 'Asia/Seoul') "
            "on conflict (id) do nothing returning id",
            FIXED_USER_ID,
        )
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("delete from shadowing_items where source_url is not null")
        await conn.execute("delete from youtube_videos")
        if inserted is not None:
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)


async def _store_video(client: httpx.AsyncClient, youtube_id: str = _ID) -> dict:
    response = await client.post(
        "/api/videos",
        json={
            "url": _URL if youtube_id == _ID else f"https://www.youtube.com/watch?v={youtube_id}",
            "title": "A title",
            "channel_name": "A channel",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_storing_a_video_then_listing_it(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    stored = await _store_video(api_client)

    assert stored["youtube_id"] == _ID
    assert stored["created"] is True

    listed = await api_client.get("/api/videos")
    assert listed.status_code == 200
    videos = listed.json()["videos"]
    assert [video["youtube_id"] for video in videos] == [_ID]
    assert videos[0]["phrase_count"] == 0
    assert videos[0]["metadata_stale"] is False


@pytest.mark.asyncio
async def test_storing_the_same_video_again_reports_it_as_not_created(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⛔ 중복이 오류가 아니라 갱신이다 — 화면 문구가 `created` 에 걸린다(설계서 §7)."""
    first = await _store_video(api_client)

    again = await api_client.post(
        "/api/videos",
        json={"url": _URL, "title": "A newer title", "channel_name": "A newer channel"},
    )

    assert again.status_code == 200, "갱신이 201 로 보고됐다"
    assert again.json()["created"] is False
    assert again.json()["id"] == first["id"]


@pytest.mark.asyncio
async def test_a_link_without_a_video_is_refused(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    for bad in ("https://www.youtube.com/", "https://vimeo.com/watch?v=dQw4w9WgXcQ", "hello"):
        response = await api_client.post(
            "/api/videos",
            json={"url": bad, "title": "A title", "channel_name": "A channel"},
        )
        assert response.status_code == 422, f"{bad} 가 통과했다"


@pytest.mark.asyncio
async def test_a_blank_title_is_refused(api_client: httpx.AsyncClient, clean_videos: None) -> None:
    response = await api_client.post(
        "/api/videos", json={"url": _URL, "title": "   ", "channel_name": "A channel"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_phrase_is_stored_and_comes_back_with_the_video(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    stored = await _store_video(api_client)

    created = await api_client.post(
        f"/api/videos/{stored['id']}/phrases",
        json={"transcript": "Hello there", "clip_start_sec": 1.238, "clip_end_sec": 4.001},
    )
    assert created.status_code == 201, created.text
    phrase = created.json()
    # 설계서 §1 질문 4 — 서버가 소수 둘째 자리로 접는다.
    assert phrase["clip_start_sec"] == 1.24
    assert phrase["clip_end_sec"] == 4.0

    detail = await api_client.get(f"/api/videos/{stored['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["youtube_id"] == _ID
    assert [item["transcript"] for item in body["phrases"]] == ["Hello there"]


@pytest.mark.asyncio
async def test_a_span_that_is_too_long_or_backwards_is_refused(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """설계서 §7 — 사용자에게 문구를 주기 위해 서버가 먼저 막는다."""
    stored = await _store_video(api_client)
    too_long = float(CLIP_MAX_SPAN_SECONDS) + 1

    for body in (
        {"transcript": "Hello", "clip_start_sec": 0, "clip_end_sec": too_long},
        {"transcript": "Hello", "clip_start_sec": 10, "clip_end_sec": 10},
        {"transcript": "Hello", "clip_start_sec": 10, "clip_end_sec": 4},
        {"transcript": "Hello", "clip_start_sec": -1, "clip_end_sec": 4},
        {"transcript": "   ", "clip_start_sec": 0, "clip_end_sec": 4},
        {"transcript": "x" * (TRANSCRIPT_MAX_LENGTH + 1), "clip_start_sec": 0, "clip_end_sec": 4},
    ):
        response = await api_client.post(f"/api/videos/{stored['id']}/phrases", json=body)
        assert response.status_code == 422, f"{body} 가 통과했다"


@pytest.mark.asyncio
async def test_deleting_a_video_keeps_its_phrases(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, clean_videos: None
) -> None:
    """⛔ 설계 계약 — 영상을 지워도 학습 자산은 남는다(설계서 §1 질문 1)."""
    stored = await _store_video(api_client)
    created = await api_client.post(
        f"/api/videos/{stored['id']}/phrases",
        json={"transcript": "Hello there", "clip_start_sec": 0, "clip_end_sec": 3},
    )
    phrase_id = created.json()["id"]

    removed = await api_client.delete(f"/api/videos/{stored['id']}")
    assert removed.status_code == 204

    assert (await api_client.get("/api/videos")).json()["videos"] == []
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select transcript, youtube_video_id from shadowing_items where id = $1", phrase_id
        )
    assert row is not None, "영상을 지웠는데 문장이 함께 사라졌다"
    assert row["youtube_video_id"] is None


@pytest.mark.asyncio
async def test_a_phrase_cannot_be_deleted_through_another_video(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⛔ 문장은 자기 영상의 하위 자원이다(설계서 §3)."""
    stored = await _store_video(api_client)
    other = await _store_video(api_client, _OTHER_ID)
    created = await api_client.post(
        f"/api/videos/{stored['id']}/phrases",
        json={"transcript": "Hello there", "clip_start_sec": 0, "clip_end_sec": 3},
    )
    phrase_id = created.json()["id"]

    wrong = await api_client.delete(f"/api/videos/{other['id']}/phrases/{phrase_id}")
    assert wrong.status_code == 404

    right = await api_client.delete(f"/api/videos/{stored['id']}/phrases/{phrase_id}")
    assert right.status_code == 204


@pytest.mark.asyncio
async def test_unknown_ids_are_not_found_rather_than_errors(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    unknown = "00000000-0000-0000-0000-0000000009f9"

    assert (await api_client.get(f"/api/videos/{unknown}")).status_code == 404
    assert (await api_client.delete(f"/api/videos/{unknown}")).status_code == 404
    assert (await api_client.delete(f"/api/videos/{unknown}/phrases/{unknown}")).status_code == 404
    phrase = await api_client.post(
        f"/api/videos/{unknown}/phrases",
        json={"transcript": "Hello there", "clip_start_sec": 0, "clip_end_sec": 3},
    )
    assert phrase.status_code == 404


@pytest.mark.asyncio
async def test_a_malformed_id_is_refused_by_routing(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⚠️ 경로 형이 `UUID` 라 라우팅이 먼저 막는다 — `api/shadowing.py` 와 같은 겹이다."""
    assert (await api_client.get("/api/videos/../../etc/passwd")).status_code in (404, 422)
    assert (await api_client.delete("/api/videos/not-a-uuid")).status_code == 422


@pytest.mark.asyncio
async def test_the_browser_is_allowed_to_send_the_write_methods(
    api_client: httpx.AsyncClient,
) -> None:
    """⛔ 이 단정만이 「브라우저에서만 막히는 실패」를 잡는다.

    `create_app()` 의 CORS 미들웨어는 `allow_methods=["GET"]` 로 시작했다 — WebSocket 에는 CORS 가
    적용되지 않고 HTTP 는 조회뿐이었으므로 그때는 맞았다. 쓰기 표면이 생기면 그 값이 **틀린 값**이
    되는데, ASGI 로 붙는 다른 단정은 preflight 를 거치지 않아 **전부 통과한다.**
    ⇒ 그래서 여기서 preflight 를 직접 보낸다.
    """
    for method in ("POST", "DELETE"):
        response = await api_client.request(
            "OPTIONS",
            "/api/videos",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": method,
            },
        )
        allowed = response.headers.get("access-control-allow-methods", "")
        assert method in allowed, f"{method} 가 preflight 에서 허용되지 않았다: {allowed!r}"


@pytest.mark.asyncio
async def test_every_http_method_the_routers_use_survives_preflight(
    api_client: httpx.AsyncClient,
) -> None:
    """⛔ CORS 의 `allow_methods` 는 **라우터의 사본**이고 그 사본은 이미 한 번 갈라졌다.

    `TASK-165` 가 첫 쓰기 라우터를 넣을 때까지 그 값은 `["GET"]` 이었고, 그것을 잡은 것은 값역이
    아니라 위의 preflight 단정이었다. 다음 메서드(`PUT`·`PATCH`)에서 같은 실패가 같은 방식으로
    반복되므로, **메서드 목록을 라우터에서 뽑아** 전부 시험한다.

    ⚠️ 그래서 이 단정은 새 메서드를 쓰는 라우터가 생기면 **CORS 를 함께 넓히라고 red 로 말한다.**
    `OPTIONS`·`HEAD` 는 Starlette 가 스스로 붙이는 것이라 뺀다.
    """
    app = create_app()
    used: set[str] = set()
    for route in app.routes:
        for method in getattr(route, "methods", None) or ():
            used.add(method)
    used -= {"OPTIONS", "HEAD"}
    assert used, "라우터에서 메서드를 하나도 못 읽었다 — 이 단정이 아무것도 재지 않는다"

    for method in sorted(used):
        response = await api_client.request(
            "OPTIONS",
            "/api/videos",
            headers={"Origin": FRONTEND_ORIGIN, "Access-Control-Request-Method": method},
        )
        allowed = response.headers.get("access-control-allow-methods", "")
        assert method in allowed, f"라우터가 {method} 를 쓰는데 preflight 가 막는다: {allowed!r}"


@pytest.mark.asyncio
async def test_the_detail_response_carries_the_clip_span_limit(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⛔ 구간 상한이 **화면까지 닿는지** 잰다.

    이 값은 스키마가 정본이고 `CLIP_MAX_SPAN_SECONDS` 가 사본이며 그 둘은
    `tests/unit/test_schema.py` 가 대조한다. ⚠️ 그런데 **화면이 자기 사본을 두면 그것만 대조 장치가
    없다** — 첫 판이 그랬다(`MAX_SPAN_SECONDS = 90` 이 화면에 있었고 아무 것도 그것을 묶지 않았다).
    이 단정이 사라지면 화면이 다시 자기 값을 발명할 자리가 생긴다.
    """
    stored = await _store_video(api_client)

    detail = await api_client.get(f"/api/videos/{stored['id']}")

    assert detail.status_code == 200
    assert detail.json()["clip_max_span_sec"] == float(CLIP_MAX_SPAN_SECONDS)
    # ⛔ 정밀도도 함께 닿아야 한다 (`TASK-170`) — 화면이 구간 순서를 **접힌 값**으로 판정하려면
    #    이 값이 필요하고, 없으면 화면이 자기 상수를 두게 된다.
    assert detail.json()["clip_precision_sec"] == float(CLIP_PRECISION)


@pytest.mark.asyncio
async def test_a_span_that_collapses_when_rounded_is_refused_not_crashed(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⛔ `TASK-170` — 접으면 시작과 끝이 같아지는 구간이 `500` 이었다.

    기전: 값역 검증이 **원본 값**으로 순서를 보고 반올림은 그 뒤 서비스가 했다. 원본은 순서가 맞아도
    둘째 자리로 접으면 같은 값이 되어 스키마 CHECK(`shadowing_items_span_ordered`)가 잡고, 사용자는
    「구간 끝이 시작보다 뒤여야 해요」가 아니라 일반 실패 문구를 봤다.

    ⚠️ **이 단정의 값은 `422` 가 아니라 「`500` 이 아님」에 있다** — 검증이 저장될 값을 보지 않으면
    같은 부류의 구멍이 다시 생긴다.
    """
    stored = await _store_video(api_client)

    for start, end in ((5.0, 5.001), (0.001, 0.004), (1.001, 1.002), (12.3401, 12.3449)):
        response = await api_client.post(
            f"/api/videos/{stored['id']}/phrases",
            json={"transcript": "collapse probe", "clip_start_sec": start, "clip_end_sec": end},
        )
        assert response.status_code == 422, f"{start}..{end} 가 {response.status_code} 를 냈다"
        assert "clip_end_sec" in response.text, response.text


@pytest.mark.asyncio
async def test_a_normal_span_still_rounds_and_stores(
    api_client: httpx.AsyncClient, clean_videos: None
) -> None:
    """⚠️ 위 단정이 정상 구간을 함께 막지 않는지 잰다 — 막으면 기능이 죽는다."""
    stored = await _store_video(api_client)

    created = await api_client.post(
        f"/api/videos/{stored['id']}/phrases",
        json={"transcript": "Hello there", "clip_start_sec": 1.234, "clip_end_sec": 5.678},
    )

    assert created.status_code == 201, created.text
    assert created.json()["clip_start_sec"] == 1.23
    assert created.json()["clip_end_sec"] == 5.68
