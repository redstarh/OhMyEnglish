"""쉐도잉 클립 시드의 계약 (`TASK-45` AC#8 · 캡틴 결정 25).

⚠️ **재는 것은 「행이 있다」가 아니라 「그 행이 진입점에 걸린다」다.** 표를 만들어도 0행이면
쉐도잉이 동작하지 않는다는 것이 설계서 약점 2 이고, 결정 25 가 그것을 시드로 닫았다. 그런데
행을 아무 값으로나 넣으면 **`start_shadowing_session` 의 수준 일치 절이 폴백으로 떨어진다** —
`SEED_SCENARIOS` 의 ⛔ 주석이 시나리오에서 같은 함정을 이미 적었다. 그래서 아래는
**시드 사용자의 `current_level` 과 시드 클립의 `level` 이 같다**를 계약으로 못 박는다.

⛔ 진입점과의 결합(`start_shadowing_session` 이 실제로 클립을 고른다)은 여기서 재지 않는다 —
그것은 `tests/unit/test_sessions.py` 가 `seed_shadowing_clips` 픽스처로 이미 소유한다. 그 픽스처는
**자기가 만든 행 밖의 클립이 있으면 실패**하므로, 시드 행을 커밋하는 테스트를 여기에 두면
그쪽이 조용히 깨진다. 이 파일은 `db_conn`(롤백 트랜잭션)만 쓴다.
"""

from __future__ import annotations

import asyncpg
import pytest
from migrate import SEED_SHADOWING_ITEMS, USER_ID, ShadowingSeedClip, seed

# PRD §7 「30~90초의 짧은 오디오·영상 클립」. **발명값이 아니라 요구사항이다** — 011 의
# `shadowing_items_span_within_limit` 가 상한만 가두므로 하한은 이 테스트가 지킨다.
PRD_CLIP_MIN_SEC = 30
PRD_CLIP_MAX_SEC = 90


def test_seed_has_at_least_one_clip() -> None:
    """0행이 아니다 — 결정 25 가 닫은 실패(설계서 약점 2)가 이 단정에 걸린다."""
    assert SEED_SHADOWING_ITEMS


def test_every_seeded_clip_omits_an_external_source_url() -> None:
    """⛔ 외부 콘텐츠를 긁지 않는다 (결정 25 · PRD §5 가 자동 수집을 비범위로 둔다).

    `source_url` 이 null 인 것이 「내장·직접 입력 자료」의 표시다(011 의 그 컬럼 주석). 링크가
    하나라도 들어오면 그것은 시드가 아니라 학습자 입력이고, 그 경로는 `TASK-10` 이 소유한다.
    """
    assert [clip for clip in SEED_SHADOWING_ITEMS if clip.source_url is not None] == []


@pytest.mark.parametrize("clip", SEED_SHADOWING_ITEMS, ids=lambda clip: clip.source_title)
def test_seeded_clip_window_stays_inside_the_prd_range(clip: ShadowingSeedClip) -> None:
    """클립 길이가 PRD §7 의 30~90초 안이다. 상한은 스키마가, 하한은 이 단정이 지킨다."""
    span_sec = clip.clip_end_sec - clip.clip_start_sec
    assert PRD_CLIP_MIN_SEC <= span_sec <= PRD_CLIP_MAX_SEC


@pytest.mark.asyncio
async def test_seed_inserts_clips_that_satisfy_the_schema(db_conn: asyncpg.Connection) -> None:
    """시드가 011 의 CHECK 넷을 전부 만족한다 — insert 가 통과하는 것이 그 증거다.

    ⚠️ 값을 다시 세지 않고 **상수와 대조한다**: 개수를 적으면 시드를 늘린 턴에 낡는다.
    """
    await seed(db_conn)

    assert await db_conn.fetchval("select count(*) from shadowing_items") == len(
        SEED_SHADOWING_ITEMS
    )


@pytest.mark.asyncio
async def test_seeding_twice_does_not_duplicate_clips(db_conn: asyncpg.Connection) -> None:
    """멱등이다 — `SEED_SCENARIOS` 와 같은 규약(고정 id + upsert)을 쓴다."""
    await seed(db_conn)
    await seed(db_conn)

    assert await db_conn.fetchval("select count(*) from shadowing_items") == len(
        SEED_SHADOWING_ITEMS
    )


@pytest.mark.asyncio
async def test_reseeding_restores_an_edited_transcript(db_conn: asyncpg.Connection) -> None:
    """`do nothing` 이 아니라 **`do update`** 다 (결정 14 가 시나리오에서 정한 이유와 같다).

    id 가 고정이므로 `do nothing` 이면 **상수를 고쳐도 이미 시드된 행이 영원히 낡은 값으로
    남는다** — 2026-09-07 에 시나리오 3행에서 실제로 그랬다.
    """
    await seed(db_conn)
    clip = SEED_SHADOWING_ITEMS[0]
    await db_conn.execute(
        "update shadowing_items set transcript = 'hand-edited' where id = $1", clip.id
    )

    await seed(db_conn)

    assert (
        await db_conn.fetchval("select transcript from shadowing_items where id = $1", clip.id)
        == clip.transcript
    )


@pytest.mark.asyncio
async def test_seeded_clip_level_matches_the_seeded_learner(db_conn: asyncpg.Connection) -> None:
    """⛔ **이것이 이 파일의 핵심 단정이다.**

    `_ATTACH_SHADOWING_CLIP_SQL` 은 `users.current_level` 로 클립을 좁힌 뒤 없으면 **가장 이른
    행으로 폴백한다.** 즉 수준이 어긋나도 세션은 열리므로 **어긋남이 조용하다** — 시드 클립의
    `level` 이 시드 학습자의 수준과 다르면 「수준에 맞는 클립을 고른다」는 계약이 시드에서만
    무의미해지고 아무 테스트도 실패하지 않는다. 그 침묵을 여기서 깬다.
    """
    await seed(db_conn)
    learner_level = await db_conn.fetchval("select current_level from users where id = $1", USER_ID)

    matching = await db_conn.fetchval(
        "select count(*) from shadowing_items where level = $1", learner_level
    )

    assert matching > 0, f"시드 클립에 {learner_level} 수준이 없다 — 선택이 폴백으로 떨어진다"
