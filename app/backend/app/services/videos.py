"""담아 둔 YouTube 영상과 그 영상에서 담은 문장 (`TASK-164`).

설계: `docs/design/2026-09-18-video-learning-design.md` §4.

⛔ **영상과 문장을 갈라 두는 이유는 수명이 다른 것이다.** 제목·채널은 YouTube 에서 온 값이라
Developer Policies III.E.4 가 보관을 30일로 제한하고, 문장은 사용자가 만든 학습 자산이라 그 제한
밖이다. 한 표에 섞으면 「30일 지난 것을 지워야 하는데 학습 자산이 함께 지워진다」가 된다.

⛔ **문장은 새 표가 아니라 `shadowing_items` 에 들어간다.** 그 표가 이미 `source_url`·`transcript`·
`clip_start_sec`·`clip_end_sec` 를 가지므로 「영상 구간 + 문장」이 그대로 담기고, 담은 문장이 **기존
쉐도잉·발음 판정·복습 경로를 그대로 탄다.** 새 표를 만들면 그 경로를 다시 배선해야 한다.

⚠️ **부재를 예외로 만들지 않는다** — `None`·`False` 로 돌려주고 라우터가 404 로 옮긴다.
`services/clip_audio.load_clip_audio` 가 세운 규약과 같다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import asyncpg

# YouTube Developer Policies III.E.4.c·d 가 「Authorized 아닌 데이터」의 보관을 30일로 제한한다.
# ⛔ 이 값을 프런트에 두지 않는다 — 시각 판정이 두 곳에 있으면 갈라진다(설계서 §3).
METADATA_MAX_AGE_DAYS = 30

# 구간 시각의 정밀도. 기존 시드 행이 `0.00`~`17.36` 으로 둘째 자리이므로 **선례를 따른다**
# (설계서 §1 질문 4). ⛔ 반올림을 프런트에서 하지 않는다 — 값역은 서버의 것이다.
_CLIP_PRECISION = Decimal("0.01")

# ⚠️ **`source_url` 을 한 형태로 정규화해 저장한다.** 사용자가 `youtu.be` 로 넣어도 저장은 이
# 형태다 — 그래야 나중에 문자열로 비교할 수 있다.
# ⛔ 그리고 이 값이 채워지는 것이 **오디오 저장 금지**로 이어진다: 027 의
# `shadowing_items_video_requires_source_url` 위에 기존
# `shadowing_items_audio_only_for_synthetic` 이 선다(정책 III.E.1).
_WATCH_URL_PREFIX = "https://www.youtube.com/watch?v="

# ⚠️ **`count(i.youtube_video_id)` 이지 `count(i.id)` 가 아니다.** 조인 조건이 그 열의 non-null 을
# 보장하므로 계산값은 같은데, 그 열은 027 의 부분 인덱스에 들어 있어 **Index Only Scan** 이 된다.
# 실측(영상 40건 · 매인 문장 400건): `count(i.id)` 는 버퍼 **191**·0.160 ms,
# 이쪽은 버퍼 **3**·0.086 ms. 목록은 화면 진입·담기·지우기마다 다시 부르므로 그 차이가 배수가 된다.
# ⚠️ `group by` 에 `v.id` 하나만 적는다 — 기본 키의 함수 종속으로 같은 표의 나머지 열이 허용된다.
# 여섯 칸을 적으면 「`select` 에 열을 더할 때마다 여기도 더해야 한다」로 잘못 읽힌다(실제로는 아님).
_LIST_VIDEOS_SQL = """
select v.id,
       v.youtube_id,
       v.title,
       v.channel_name,
       count(i.youtube_video_id) as phrase_count,
       (v.metadata_fetched_at < now() - make_interval(days => $1)) as metadata_stale
  from youtube_videos v
  left join shadowing_items i on i.youtube_video_id = v.id
 group by v.id
 order by v.created_at desc, v.id
"""

# ⚠️ **`xmax = 0` 이 「새로 만들었는가」를 준다.** upsert 에서 삽입과 갱신을 가르는 표준 수법이고,
# 그 값이 화면 문구(「담았어요」 vs 「이미 담아 둔 영상이에요」)를 가른다.
# ⛔ **`metadata_fetched_at` 을 갱신 쪽에서만 `now()` 로 적는다** — 삽입은 컬럼 기본값이 이미
# 그 값이다.
_UPSERT_VIDEO_SQL = """
insert into youtube_videos (youtube_id, title, channel_name)
values ($1, $2, $3)
on conflict (youtube_id) do update
   set title = excluded.title,
       channel_name = excluded.channel_name,
       metadata_fetched_at = now()
returning id, youtube_id, title, channel_name, (xmax = 0) as created
"""

_LOAD_VIDEO_SQL = """
select id,
       youtube_id,
       title,
       channel_name,
       (metadata_fetched_at < now() - make_interval(days => $2)) as metadata_stale
  from youtube_videos
 where id = $1
"""

_LOAD_PHRASES_SQL = """
select id, transcript, clip_start_sec, clip_end_sec
  from shadowing_items
 where youtube_video_id = $1
 order by clip_start_sec, id
"""

_DELETE_VIDEO_SQL = """
delete from youtube_videos where id = $1 returning id
"""

# ⛔ **`youtube_video_id` 를 조건에 함께 넣는 것이 이 문장의 값이다** — 그 영상에 속하지 않는 문장
# id 를 주면 0행이 되어 「다른 영상의 문장을 지우는 요청」이 성립하지 않는다(설계서 §3).
_DELETE_PHRASE_SQL = """
delete from shadowing_items
 where id = $2 and youtube_video_id = $1
returning id
"""

# ⚠️ **`insert ... select` 로 영상 행을 함께 읽는다.** 영상이 없으면 0행이 삽입되어 `None` 이 되므로
# 「존재 확인 → 삽입」의 두 왕복이 필요 없고, 그 사이에 영상이 지워지는 창도 없다.
# ⛔ `level` 도 같은 문장에서 읽는다 — 사용자가 없으면 null 이 되어 NOT NULL 위반으로 실패한다.
#    조용히 기본값을 만들지 않는 것이 의도다(설계서 §4).
_ADD_PHRASE_SQL = """
insert into shadowing_items
       (source_title, source_url, transcript, clip_start_sec, clip_end_sec, level,
        youtube_video_id)
select v.title,
       $6 || v.youtube_id,
       $2,
       $3,
       $4,
       (select u.current_level from users u where u.id = $5),
       v.id
  from youtube_videos v
 where v.id = $1
returning id, transcript, clip_start_sec, clip_end_sec
"""


@dataclass(frozen=True, slots=True)
class VideoSummary:
    """목록 화면이 카드 하나에 쓰는 것만 담는다.

    ⛔ **썸네일 URL 을 담지 않는다** — 화면이 `youtube_id` 로 조립한다(설계서 §2). 담으면 30일 보관
    대상이 하나 늘고, 조립할 수 있는 값을 저장하는 셈이 된다.
    """

    id: UUID
    youtube_id: str
    title: str
    channel_name: str
    phrase_count: int
    metadata_stale: bool


@dataclass(frozen=True, slots=True)
class VideoPhrase:
    """담은 문장 하나. `level` 을 담지 않는 근거는 `ShadowingClip` 과 같다 — 화면이 쓰지 않는다."""

    id: UUID
    transcript: str
    clip_start_sec: Decimal
    clip_end_sec: Decimal


@dataclass(frozen=True, slots=True)
class VideoDetail:
    """학습 화면이 한 번의 왕복으로 받는 것 — 영상과 그 문장 전부(설계서 §3)."""

    id: UUID
    youtube_id: str
    title: str
    channel_name: str
    metadata_stale: bool
    phrases: tuple[VideoPhrase, ...]


@dataclass(frozen=True, slots=True)
class UpsertedVideo:
    """담기·갱신의 결과. `created` 가 화면 문구를 가른다."""

    id: UUID
    youtube_id: str
    title: str
    channel_name: str
    created: bool


def _round_seconds(value: Decimal) -> Decimal:
    return value.quantize(_CLIP_PRECISION, rounding=ROUND_HALF_UP)


async def list_videos(conn: asyncpg.Connection) -> tuple[VideoSummary, ...]:
    """담아 둔 영상 전부. 최근에 담은 것이 앞이다."""
    rows = await conn.fetch(_LIST_VIDEOS_SQL, METADATA_MAX_AGE_DAYS)
    return tuple(
        VideoSummary(
            id=row["id"],
            youtube_id=row["youtube_id"],
            title=row["title"],
            channel_name=row["channel_name"],
            phrase_count=row["phrase_count"],
            metadata_stale=row["metadata_stale"],
        )
        for row in rows
    )


async def upsert_video(
    conn: asyncpg.Connection, *, youtube_id: str, title: str, channel_name: str
) -> UpsertedVideo:
    """영상을 담거나, 이미 담은 것이면 **메타데이터를 갱신한다.**

    ⛔ **중복을 오류로 만들지 않는 것이 계약이다.** 정책이 메타데이터 보관을 30일로 제한하므로 갱신
    경로가 있어야 하고, 그 경로를 새 엔드포인트가 아니라 이 호출이 겸한다(설계서 §1 질문 2).
    """
    # ⚠️ `.strip()` 이 값역 층과 **의도적으로 겹친다** — 요청 모델이 `str_strip_whitespace=True` 로
    # 이미 다듬으므로 라우터를 거친 값에는 두 번째 수행이다. 서비스는 라우터 없이도 불릴 수 있고
    # (테스트·스크립트) 그때 공백이 그대로 저장되면 CHECK 가 잡지 못하는 앞뒤 공백이 남는다.
    row = await conn.fetchrow(_UPSERT_VIDEO_SQL, youtube_id, title.strip(), channel_name.strip())
    assert row is not None, "upsert ... returning produced no row"
    return UpsertedVideo(
        id=row["id"],
        youtube_id=row["youtube_id"],
        title=row["title"],
        channel_name=row["channel_name"],
        created=row["created"],
    )


async def delete_video(conn: asyncpg.Connection, video_id: UUID) -> bool:
    """영상만 지운다. **담은 문장은 남는다** — FK 가 `on delete set null` 이다.

    ⛔ 그것이 설계서 §1 질문 1 의 답이다: 문장에 복습 이력이 매여 있어 함께 지우면 되돌릴 수 없다.
    """
    return await conn.fetchval(_DELETE_VIDEO_SQL, video_id) is not None


async def load_video_with_phrases(conn: asyncpg.Connection, video_id: UUID) -> VideoDetail | None:
    """영상 하나와 그 영상에서 담은 문장 전부. 영상이 없으면 `None`."""
    row = await conn.fetchrow(_LOAD_VIDEO_SQL, video_id, METADATA_MAX_AGE_DAYS)
    if row is None:
        return None
    phrase_rows = await conn.fetch(_LOAD_PHRASES_SQL, video_id)
    return VideoDetail(
        id=row["id"],
        youtube_id=row["youtube_id"],
        title=row["title"],
        channel_name=row["channel_name"],
        metadata_stale=row["metadata_stale"],
        phrases=tuple(
            VideoPhrase(
                id=phrase["id"],
                transcript=phrase["transcript"],
                clip_start_sec=phrase["clip_start_sec"],
                clip_end_sec=phrase["clip_end_sec"],
            )
            for phrase in phrase_rows
        ),
    )


async def add_phrase(
    conn: asyncpg.Connection,
    video_id: UUID,
    *,
    user_id: UUID,
    transcript: str,
    start_sec: Decimal,
    end_sec: Decimal,
) -> VideoPhrase | None:
    """구간과 문장을 담는다. 영상이 없으면 `None`.

    ⚠️ **구간 상한(90초)과 순서를 여기서 재지 않는다** — 스키마 CHECK 둘이 이미 가두고
    (`shadowing_items_span_within_limit` · `shadowing_items_span_ordered`), 사용자에게 문구를 주는
    검사는 라우터가 한다(설계서 §7). 여기서 또 재면 상한이 세 곳에 흩어진다.
    """
    row = await conn.fetchrow(
        _ADD_PHRASE_SQL,
        video_id,
        transcript.strip(),
        _round_seconds(start_sec),
        _round_seconds(end_sec),
        user_id,
        _WATCH_URL_PREFIX,
    )
    if row is None:
        return None
    return VideoPhrase(
        id=row["id"],
        transcript=row["transcript"],
        clip_start_sec=row["clip_start_sec"],
        clip_end_sec=row["clip_end_sec"],
    )


async def delete_phrase(conn: asyncpg.Connection, video_id: UUID, item_id: UUID) -> bool:
    """그 영상에 속한 문장만 지운다. 속하지 않으면 `False` — 라우터가 404 로 옮긴다."""
    return await conn.fetchval(_DELETE_PHRASE_SQL, video_id, item_id) is not None
