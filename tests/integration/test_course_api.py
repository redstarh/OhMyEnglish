"""문법 코스 엔드포인트 (`TASK-286`).

설계: `docs/design/2026-10-26-grammar-course-design.md` §6.

⚠️ 전사기의 구동(프레임 흘리기·침묵 판정)은 `tests/unit/test_readback_transcribe.py` 가 소유한다.
여기서는 **라우터와 서비스**를 재므로 전사기 자리에 고정 문장을 돌려주는 대역을 건다.
⛔ 대역은 설정이 `nova` 일 때만 쓰인다 — 기본 `stub` 의 503 갈래는 전용 테스트가 잰다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime

import asyncpg
import httpx
import pytest
import pytest_asyncio
from conftest import pin_settings_env

from app.api import course as course_module
from app.config import get_settings
from app.models.user import FIXED_USER_ID

PCM = b"\x10\x00" * 1600  # 0.1초


@pytest_asyncio.fixture(autouse=True)
async def committed_fixed_user(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자 1행을 커밋해두고 teardown 에서 지운다 — 코스 행은 cascade 로 함께 지워진다.

    `api_client` 는 커밋된 행만 본다. 값은 `test_daily_summary_api.py` 의 같은 이름 픽스처와 같다.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into users (id, display_name, timezone) values ($1, 'Learner', 'Asia/Seoul') "
            "on conflict (id) do nothing",
            FIXED_USER_ID,
        )
    try:
        yield
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch, test_database: str) -> Iterator[Callable[[str], None]]:
    def use(name: str) -> None:
        monkeypatch.setenv("DATABASE_URL", test_database)
        monkeypatch.setenv("VOICE_ADAPTER", name)
        pin_settings_env(monkeypatch, keep=("DATABASE_URL", "VOICE_ADAPTER"))
        get_settings.cache_clear()

    yield use
    get_settings.cache_clear()


@pytest.fixture
def heard(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """전사기 대역 — 학습자가 `text` 를 말한 것으로 둔다."""

    def say(text: str) -> None:
        async def transcribe(pcm: bytes) -> str:
            assert pcm == PCM
            return text

        monkeypatch.setattr(
            course_module, "create_transcriber", lambda *_args, **_kwargs: transcribe
        )

    return say


async def test_overview_starts_at_day_one_cycle_one(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/course")
    assert response.status_code == 200
    body = response.json()
    assert body["cycle"] == 1
    assert body["current_day"] == 1
    assert [day["first_unit"] for day in body["days"]] == [1, 22, 42, 63, 83, 101]
    assert all(day["progress"] is None for day in body["days"])
    assert len(body["heatmap"]) == 16 * 7
    assert all(cell["attempts"] == 0 for cell in body["heatmap"])
    assert body["recent"] == []


async def test_day_detail_lists_units_and_sentences(api_client: httpx.AsyncClient) -> None:
    body = (await api_client.get("/api/course/days/2")).json()
    assert body["youtube_id"] == "z881DusiriA"
    assert [unit["unit"] for unit in body["units"]] == list(range(22, 42))
    first = body["units"][0]["sentences"][0]
    assert first["key"] == "u022-s1"
    assert first["attempts"] == 0
    assert (await api_client.get("/api/course/days/7")).status_code == 404


async def test_progress_is_saved_and_resumed(api_client: httpx.AsyncClient) -> None:
    saved = await api_client.post(
        "/api/course/days/2/progress",
        json={"position_sec": 800.5, "unit": 27, "sentence_index": 1},
    )
    assert saved.status_code == 204
    detail = (await api_client.get("/api/course/days/2")).json()
    assert detail["progress"]["position_sec"] == 800.5
    assert detail["progress"]["unit"] == 27
    assert detail["progress"]["sentence_index"] == 1
    overview = (await api_client.get("/api/course")).json()
    assert overview["current_day"] == 2


async def test_progress_rejects_a_unit_from_another_day(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/course/days/2/progress", json={"position_sec": 0, "unit": 5, "sentence_index": 0}
    )
    assert response.status_code == 422
    bad_index = await api_client.post(
        "/api/course/days/2/progress", json={"position_sec": 0, "unit": 22, "sentence_index": 5}
    )
    assert bad_index.status_code == 422


async def test_completing_every_day_starts_cycle_two(api_client: httpx.AsyncClient) -> None:
    firsts = {1: 1, 2: 22, 3: 42, 4: 63, 5: 83, 6: 101}
    for day, unit in firsts.items():
        await api_client.post(
            f"/api/course/days/{day}/progress",
            json={"position_sec": 10, "unit": unit, "sentence_index": 0, "completed": True},
        )
    overview = (await api_client.get("/api/course")).json()
    assert overview["cycle"] == 2
    assert overview["current_day"] in firsts
    day_one = overview["days"][0]["progress"]
    assert day_one["completed_count"] == 1
    assert day_one["position_sec"] == 0  # 끝낸 Day 는 처음으로 되감긴다


async def test_attempt_is_judged_and_counted(
    api_client: httpx.AsyncClient, adapter: Callable[[str], None], heard: Callable[[str], None]
) -> None:
    adapter("nova")
    heard("I am a software tester")
    first = await api_client.post("/api/course/sentences/u001-s1/attempts", content=PCM)
    assert first.status_code == 200
    body = first.json()
    assert body["transcript"] == "I am a software tester"
    assert {word["verdict"] for word in body["words"]} == {"match"}
    assert body["attempts"] == 1

    heard("I a software")
    second = (await api_client.post("/api/course/sentences/u001-s1/attempts", content=PCM)).json()
    verdicts = {word["word"]: word["verdict"] for word in second["words"]}
    assert verdicts["am"] == "missing"
    assert verdicts["tester."] == "missing"
    assert second["attempts"] == 2

    detail = (await api_client.get("/api/course/days/1")).json()
    assert detail["units"][0]["sentences"][0]["attempts"] == 2
    overview = (await api_client.get("/api/course")).json()
    assert overview["heatmap"][-1]["attempts"] == 2
    assert overview["recent"][0]["attempts"] == 2
    assert overview["recent"][0]["days"] == [1]


async def test_empty_transcript_still_counts_as_an_attempt(
    api_client: httpx.AsyncClient, adapter: Callable[[str], None], heard: Callable[[str], None]
) -> None:
    adapter("nova")
    heard("   ")
    body = (await api_client.post("/api/course/sentences/u002-s3/attempts", content=PCM)).json()
    assert body == {"transcript": "", "words": [], "attempts": 1}


async def test_attempt_is_503_without_a_transcriber(
    api_client: httpx.AsyncClient, adapter: Callable[[str], None], db_pool: asyncpg.Pool
) -> None:
    adapter("stub")
    response = await api_client.post("/api/course/sentences/u001-s1/attempts", content=PCM)
    assert response.status_code == 503
    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            "select count(*) from course_attempts where user_id = $1", FIXED_USER_ID
        )
    assert count == 0  # 가드가 전사 앞이라 아무것도 기록되지 않는다


async def test_attempt_rejects_bad_key_and_bad_body(
    api_client: httpx.AsyncClient, adapter: Callable[[str], None]
) -> None:
    adapter("nova")
    assert (
        await api_client.post("/api/course/sentences/u999-s1/attempts", content=PCM)
    ).status_code == 404
    assert (
        await api_client.post("/api/course/sentences/u001-s1/attempts", content=b"")
    ).status_code == 422
    assert (
        await api_client.post("/api/course/sentences/u001-s1/attempts", content=b"\x00")
    ).status_code == 422
    too_long = b"\x00\x00" * (30 * 16_000 + 1)
    assert (
        await api_client.post("/api/course/sentences/u001-s1/attempts", content=too_long)
    ).status_code == 413


async def test_recent_dates_are_bucketed_in_the_learner_timezone(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool
) -> None:
    # 2026-10-25 23:30 UTC = 2026-10-26 08:30 KST — UTC 로 가르면 하루 앞 칸에 들어간다.
    instant = datetime(2026, 10, 25, 23, 30, tzinfo=UTC)
    async with db_pool.acquire() as conn:
        timezone = await conn.fetchval("select timezone from users where id = $1", FIXED_USER_ID)
        await conn.execute(
            "insert into course_attempts (user_id, sentence_key, transcript, created_at)"
            " values ($1, 'u030-s1', 'x', $2)",
            FIXED_USER_ID,
            instant,
        )
    assert timezone == "Asia/Seoul"
    recent = (await api_client.get("/api/course")).json()["recent"]
    assert recent[0]["date"] == "2026-10-26"
    assert recent[0]["days"] == [2]


async def test_completion_date_is_the_learner_local_date(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool
) -> None:
    """회차 2026-10-26-b1 D1 — KST 09시 전 완료가 UTC 전날로 보이던 결함."""
    await api_client.post(
        "/api/course/days/6/progress",
        json={"position_sec": 0, "unit": 101, "sentence_index": 0, "completed": True},
    )
    async with db_pool.acquire() as conn:
        await conn.execute(
            "update course_day_progress set last_completed_at = $2 where user_id = $1 and day = 6",
            FIXED_USER_ID,
            datetime(2026, 10, 25, 23, 41, tzinfo=UTC),  # = 2026-10-26 08:41 KST
        )
    day_six = (await api_client.get("/api/course")).json()["days"][5]["progress"]
    assert day_six["last_completed_date"] == "2026-10-26"
    detail = (await api_client.get("/api/course/days/6")).json()["progress"]
    assert detail["last_completed_date"] == "2026-10-26"


async def test_oversized_declared_length_is_refused_before_reading(
    api_client: httpx.AsyncClient, adapter: Callable[[str], None]
) -> None:
    """codex 리뷰 MEDIUM — 선언된 길이가 상한을 넘으면 본문을 읽기 전에 413 이다."""
    adapter("nova")
    response = await api_client.post(
        "/api/course/sentences/u001-s1/attempts",
        content=PCM,
        headers={"content-length": str(30 * 16_000 * 2 + 2)},
    )
    assert response.status_code == 413
