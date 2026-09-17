"""`services/videos` — 담아 둔 영상과 그 영상에서 담은 문장 (`TASK-164`).

설계: `docs/design/2026-09-18-video-learning-design.md` §4.

⛔ **이 파일이 지키는 계약 둘**이 다른 것보다 값이 크다.

1. **영상을 지워도 담은 문장은 남는다**(설계서 §1 질문 1). 문장은 사용자가 만든 학습 자산이고
   `review_tasks`·`error_patterns`·`utterances` 가 그것에 매여 있다 — 영상 하나를 지우는 동작이
   복습 이력을 지우면 그 동작이 되돌릴 수 없어진다.
2. **같은 영상을 다시 담는 것은 오류가 아니라 갱신이다.** YouTube Developer Policies III.E.4 가
   메타데이터 보관을 30일로 제한하므로 **갱신 경로가 있어야 하고**, 그 경로를 새 엔드포인트가 아니라
   담기와 같은 호출이 겸한다.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.videos import (
    METADATA_MAX_AGE_DAYS,
    add_phrase,
    delete_phrase,
    delete_video,
    list_videos,
    load_video_with_phrases,
    upsert_video,
)

_ID = "dQw4w9WgXcQ"
_OTHER_ID = "jNQXAC9IVRw"


async def _a_user(conn: asyncpg.Connection, level: str = "A2") -> UUID:
    user_id = await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('Video Test', 'Asia/Seoul', $1) returning id",
        level,
    )
    assert user_id is not None
    return user_id


async def _a_video(conn: asyncpg.Connection, youtube_id: str = _ID):
    return await upsert_video(
        conn, youtube_id=youtube_id, title="A title", channel_name="A channel"
    )


@pytest.mark.asyncio
async def test_a_stored_video_shows_up_in_the_list(db_conn: asyncpg.Connection):
    stored = await _a_video(db_conn)

    videos = await list_videos(db_conn)

    assert stored.created is True
    assert [video.youtube_id for video in videos] == [_ID]
    assert videos[0].title == "A title"
    assert videos[0].channel_name == "A channel"
    assert videos[0].phrase_count == 0
    assert videos[0].metadata_stale is False


@pytest.mark.asyncio
async def test_storing_the_same_video_again_refreshes_it_instead_of_duplicating(
    db_conn: asyncpg.Connection,
):
    """⛔ 계약 2 — 중복은 오류가 아니라 갱신이다(설계서 §1 질문 2)."""
    first = await _a_video(db_conn)

    second = await upsert_video(
        db_conn, youtube_id=_ID, title="A newer title", channel_name="A newer channel"
    )

    assert second.created is False, "두 번째 담기가 삽입으로 보고됐다"
    assert second.id == first.id, "같은 영상이 두 행이 됐다"

    videos = await list_videos(db_conn)
    assert len(videos) == 1
    assert videos[0].title == "A newer title"
    assert videos[0].channel_name == "A newer channel"


@pytest.mark.asyncio
async def test_refreshing_a_video_moves_its_metadata_clock_forward(db_conn: asyncpg.Connection):
    """⚠️ 30일 경계에서 갈리는지를 잰다 — 갱신이 그 시계를 되돌려야 한다."""
    stored = await _a_video(db_conn)
    await db_conn.execute(
        "update youtube_videos set metadata_fetched_at = now() - make_interval(days => $2) "
        "where id = $1",
        stored.id,
        METADATA_MAX_AGE_DAYS + 1,
    )

    stale = await list_videos(db_conn)
    assert stale[0].metadata_stale is True, "31일 지난 메타데이터가 신선하다고 보고됐다"

    await upsert_video(db_conn, youtube_id=_ID, title="A title", channel_name="A channel")

    refreshed = await list_videos(db_conn)
    assert refreshed[0].metadata_stale is False, "갱신했는데 시계가 그대로다"


@pytest.mark.asyncio
async def test_a_phrase_takes_the_level_from_the_user(db_conn: asyncpg.Connection):
    """설계서 §1 질문 3 — 사용자에게 묻지 않고 `users.current_level` 을 읽는다."""
    user_id = await _a_user(db_conn, level="B1")
    video = await _a_video(db_conn)

    phrase = await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Hello there",
        start_sec=Decimal("1.5"),
        end_sec=Decimal("4.25"),
    )

    assert phrase is not None
    level = await db_conn.fetchval("select level from shadowing_items where id = $1", phrase.id)
    assert level == "B1"


@pytest.mark.asyncio
async def test_a_phrase_stores_a_normalised_watch_url_and_the_video_link(
    db_conn: asyncpg.Connection,
):
    """⛔ `source_url` 을 한 형태로 저장한다 — 그래야 나중에 문자열로 비교할 수 있다.

    ⚠️ 그리고 `source_url` 이 채워지는 것이 **오디오 저장 금지**로 이어진다: 027 의
    `shadowing_items_video_requires_source_url` 위에 기존
    `shadowing_items_audio_only_for_synthetic` 이 선다.
    """
    user_id = await _a_user(db_conn)
    video = await _a_video(db_conn)

    phrase = await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Hello there",
        start_sec=Decimal("0"),
        end_sec=Decimal("3"),
    )

    assert phrase is not None
    row = await db_conn.fetchrow(
        "select source_title, source_url, youtube_video_id, audio_filename "
        "from shadowing_items where id = $1",
        phrase.id,
    )
    assert row is not None
    assert row["source_url"] == f"https://www.youtube.com/watch?v={_ID}"
    assert row["source_title"] == "A title"
    assert row["youtube_video_id"] == video.id
    assert row["audio_filename"] is None


@pytest.mark.asyncio
async def test_stored_phrases_come_back_with_the_video(db_conn: asyncpg.Connection):
    user_id = await _a_user(db_conn)
    video = await _a_video(db_conn)
    await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="First one",
        start_sec=Decimal("0"),
        end_sec=Decimal("3"),
    )
    await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Second one",
        start_sec=Decimal("10.5"),
        end_sec=Decimal("14"),
    )

    detail = await load_video_with_phrases(db_conn, video.id)

    assert detail is not None
    assert detail.youtube_id == _ID
    assert [phrase.transcript for phrase in detail.phrases] == ["First one", "Second one"]
    assert detail.phrases[1].clip_start_sec == Decimal("10.50")

    videos = await list_videos(db_conn)
    assert videos[0].phrase_count == 2


@pytest.mark.asyncio
async def test_deleting_a_video_keeps_its_phrases(db_conn: asyncpg.Connection):
    """⛔ 계약 1 — 이 단정이 뒤집히면 사용자의 복습 이력이 지워진다."""
    user_id = await _a_user(db_conn)
    video = await _a_video(db_conn)
    phrase = await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Hello there",
        start_sec=Decimal("0"),
        end_sec=Decimal("3"),
    )
    assert phrase is not None

    assert await delete_video(db_conn, video.id) is True

    assert await list_videos(db_conn) == ()
    row = await db_conn.fetchrow(
        "select transcript, source_url, youtube_video_id from shadowing_items where id = $1",
        phrase.id,
    )
    assert row is not None, "영상을 지웠는데 문장이 함께 사라졌다"
    assert row["transcript"] == "Hello there"
    assert row["youtube_video_id"] is None


@pytest.mark.asyncio
async def test_a_phrase_can_only_be_deleted_through_its_own_video(db_conn: asyncpg.Connection):
    """⛔ 다른 영상의 문장을 지우는 요청이 성립하지 않는다(설계서 §3 의 하위 자원 규약)."""
    user_id = await _a_user(db_conn)
    video = await _a_video(db_conn)
    other = await _a_video(db_conn, _OTHER_ID)
    phrase = await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Hello there",
        start_sec=Decimal("0"),
        end_sec=Decimal("3"),
    )
    assert phrase is not None

    assert await delete_phrase(db_conn, other.id, phrase.id) is False
    assert (
        await db_conn.fetchval("select count(*) from shadowing_items where id = $1", phrase.id) == 1
    )

    assert await delete_phrase(db_conn, video.id, phrase.id) is True
    assert (
        await db_conn.fetchval("select count(*) from shadowing_items where id = $1", phrase.id) == 0
    )


@pytest.mark.asyncio
async def test_missing_rows_come_back_as_absence_not_as_an_error(db_conn: asyncpg.Connection):
    """⚠️ 부재를 예외로 만들지 않는다 — 라우터가 그것을 404 로 옮긴다(`clip_audio` 와 같은 규약)."""
    user_id = await _a_user(db_conn)
    unknown = uuid4()

    assert await load_video_with_phrases(db_conn, unknown) is None
    assert await delete_video(db_conn, unknown) is False
    assert await delete_phrase(db_conn, unknown, uuid4()) is False
    assert (
        await add_phrase(
            db_conn,
            unknown,
            user_id=user_id,
            transcript="Hello there",
            start_sec=Decimal("0"),
            end_sec=Decimal("3"),
        )
        is None
    )


@pytest.mark.asyncio
async def test_clip_seconds_are_rounded_to_two_places(db_conn: asyncpg.Connection):
    """설계서 §1 질문 4 — 플레이어가 주는 부동소수를 **서버가** 둘째 자리로 접는다."""
    user_id = await _a_user(db_conn)
    video = await _a_video(db_conn)

    phrase = await add_phrase(
        db_conn,
        video.id,
        user_id=user_id,
        transcript="Hello there",
        start_sec=Decimal("1.238"),
        end_sec=Decimal("4.001"),
    )

    assert phrase is not None
    assert phrase.clip_start_sec == Decimal("1.24")
    assert phrase.clip_end_sec == Decimal("4.00")
