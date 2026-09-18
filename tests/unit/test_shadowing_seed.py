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

import subprocess
import wave
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
from migrate import SEED_SHADOWING_ITEMS, USER_ID, ShadowingSeedClip, seed

from app.config import get_settings

# 설정의 뿌리는 백엔드 cwd 기준 상대경로다 — 이 파일이 어디서 불리든 같은 자리를 보게 한다.
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "app" / "backend"
REPO_ROOT = Path(__file__).resolve().parents[2]

# PRD §7 「30~90초의 짧은 오디오·영상 클립」. **범위는 요구사항이다** — 011 의
# `shadowing_items_span_within_limit` 가 상한만 가두므로 하한은 이 테스트가 지킨다.
PRD_CLIP_MIN_SEC = 30
PRD_CLIP_MAX_SEC = 90

# ⛔ **하한을 깨는 시드를 «알려진 격차»로 기록한다** (사용자 결정 88 · 2026-09-13 ·
# `docs/ops/captain-instruction-register.md`). ⚠️ **이 파일은 그 전까지 반대를 적어 뒀다** —
# *"TTS 실측이 30초 미만을 내면 값을 내리는 것이 아니라 전사문을 늘리는 것이 옳은 대응이다"*.
# 사용자가 그것을 뒤집었다: 시드 값은 **실측**으로 정직해지고 하한 미달은 고치는 것이 아니라
# **기록**한다. 늘리는 쪽은 결정 25(*"분량은 늘리지 않는다"*)와 부딪히기 때문이다.
#
# ⚠️ **면제를 «규칙»으로 열지 않고 «id»로 준다.** 하한 단정을 지우면 앞으로 넣는 클립이 조용히
# 짧아지고 아무 것도 실패하지 않는다 — 그것이 이 파일이 애초에 막던 실패다. 아래 두 단정이
# 양방향으로 물려 있다: 목록에 없는 짧은 클립은 실패하고, 목록에 남은 긴 클립도 실패한다.
KNOWN_SUB_MIN_CLIP_IDS = frozenset({UUID("00000000-0000-0000-0000-000000000201")})


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
def test_seeded_clip_window_stays_under_the_prd_upper_bound(clip: ShadowingSeedClip) -> None:
    """클립 길이가 PRD §7 의 상한 90초를 넘지 않고 창이 양수다.

    ⚠️ 011 의 CHECK 둘(`span_within_limit`·`span_ordered`)이 같은 축을 DB 에서 가두지만 **시드
    상수를 DB 없이 읽는 소비자가 있다** — 이 파일이 그렇고, 그래서 상수 자체에도 단정을 둔다.
    """
    span_sec = clip.clip_end_sec - clip.clip_start_sec
    assert 0 < span_sec <= PRD_CLIP_MAX_SEC


@pytest.mark.parametrize("clip", SEED_SHADOWING_ITEMS, ids=lambda clip: clip.source_title)
def test_only_a_recorded_clip_falls_short_of_the_prd_lower_bound(clip: ShadowingSeedClip) -> None:
    """하한 미달은 `KNOWN_SUB_MIN_CLIP_IDS` 에 **있는** 클립만 허용한다 (결정 88).

    ⛔ 새로 넣는 클립이 30초를 못 채우면 그것은 기록된 격차가 아니라 **새 요구 위반**이다.
    """
    span_sec = clip.clip_end_sec - clip.clip_start_sec

    if span_sec < PRD_CLIP_MIN_SEC:
        assert clip.id in KNOWN_SUB_MIN_CLIP_IDS, (
            f"{clip.source_title} 이 PRD 하한 {PRD_CLIP_MIN_SEC}초에 {span_sec}초로 미달인데 "
            "알려진 격차로 기록되지 않았다 — 전사문을 늘리거나 결정을 받아 목록에 넣는다"
        )


def test_the_recorded_gap_does_not_outlive_the_shortfall() -> None:
    """면제가 낡지 않는다 — 목록에 있는데 실제로는 하한을 채우거나 시드에 없으면 실패한다.

    ⛔ **이 단정이 없으면 면제가 영구 통행권이 된다.** 전사문을 늘려 30초를 넘긴 뒤에도 목록에
    남아 있으면 다음 사람은 그 클립이 아직 미달이라고 읽는다 — 기록이 조용히 거짓이 되는 자리다.
    """
    spans_by_id = {
        clip.id: clip.clip_end_sec - clip.clip_start_sec for clip in SEED_SHADOWING_ITEMS
    }

    stale = {
        clip_id
        for clip_id in KNOWN_SUB_MIN_CLIP_IDS
        if clip_id not in spans_by_id or spans_by_id[clip_id] >= PRD_CLIP_MIN_SEC
    }

    assert stale == frozenset(), f"면제가 낡았다 — `KNOWN_SUB_MIN_CLIP_IDS` 에서 지운다: {stale}"


@pytest.mark.asyncio
async def test_seeding_twice_does_not_duplicate_clips(db_conn: asyncpg.Connection) -> None:
    """멱등이다 — `SEED_SCENARIOS` 와 같은 규약(고정 id + upsert)을 쓴다.

    ⚠️ **첫 `seed()` 호출이 011 의 CHECK 넷 통과도 함께 증명한다** — 위반이면 그 줄에서 이미
    `asyncpg` 예외로 걸린다. 그래서 그것만 따로 재던 단정을 지웠다(2026-09-09 정리 검토): 이름이
    「스키마를 만족한다」였는데 실제로 재는 것은 **행 수**였고, CHECK 자체는
    `tests/unit/test_schema.py` 의 011 절이 임의 값으로 이미 소유한다. **이름과 내용이 어긋난 것**이
    지적의 핵심이었다.

    ⚠️ 값을 다시 세지 않고 **상수와 대조한다**: 개수를 적으면 시드를 늘린 턴에 낡는다.
    """
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


def test_every_seeded_clip_names_its_audio_by_the_id_convention() -> None:
    """시드가 파일명을 규약대로 갖는다 — 022 의 CHECK 와 같은 규약을 상수에서도 지킨다.

    ⚠️ DB 를 거치지 않고 상수를 직접 읽는 소비자가 있으므로(이 파일이 그렇다) 상수에도 단정을 둔다.
    """
    named = [clip for clip in SEED_SHADOWING_ITEMS if clip.audio_filename is not None]

    assert named, "시드에 오디오를 가진 클립이 0건이다 — 화면에 들려줄 소리가 없다"
    for clip in named:
        assert clip.audio_filename == f"{clip.id}.wav"


def test_seeded_clip_audio_files_exist_in_the_repository() -> None:
    """⛔ **이것이 「제품 자산이 배포되는가」를 재는 유일한 단정이다** (설계서 §7).

    파일이 있는 것과 **추적되는 것**은 다르므로 둘을 함께 잰다 — `.gitignore` 된 자리에 두면
    clone 한 환경에서 소리가 사라지고, 그 실패는 배포 뒤에야 드러난다.
    """
    root = (BACKEND_ROOT / get_settings().shadowing_clip_audio_root).resolve()

    for clip in SEED_SHADOWING_ITEMS:
        if clip.audio_filename is None:
            continue
        path = root / clip.audio_filename
        assert path.is_file(), f"{path} 가 없다 — 생성 절차는 2026-09-09 선행 검토 §7.1 이 소유한다"
        # `check-ignore` 는 무시되면 0, 무시되지 않으면 1 이다 — 여기서 원하는 것은 1 이다.
        # ⛔ **먼저 git 이 «돌았는지» 를 가른다** — 0·1 이 아닌 코드는 판정이 아니라 git 자체의
        #    실패다. 가르지 않으면 그 코드가 「무시되고 있다」로 보고되어 문면이 원인을 잘못
        #    지목한다: 2026-09-19 에 Xcode 라이선스 미동의로 `/usr/bin/git` 셰임이 **exit 69** 를
        #    내자 추적되고 있는 파일이 「`.gitignore` 에 걸려 있다」로 실패했다(`H-CH`).
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert ignored.returncode in (0, 1), (
            f"git check-ignore 가 돌지 않았다 (exit {ignored.returncode}) — 이 단정은 "
            f"추적 여부를 재지 못했다: {ignored.stderr.strip()}"
        )
        assert ignored.returncode == 1, f"{path} 가 .gitignore 에 걸려 있다 — 배포되지 않는다"


def test_the_seeded_window_matches_the_committed_audio_length() -> None:
    """⛔ **시간 창이 커밋된 오디오의 «실제» 길이다** (결정 88 · 설계서 §3).

    합성음에서는 시간 창이 곧 오디오 전체이므로 둘이 어긋나면 화면이 없는 구간을 가리킨다.
    ⚠️ **TTS 는 회차마다 같은 길이를 내지 않는다** — 2026-09-09 회차는 16.64초였고 2026-09-14
    회차는 17.36초였다(같은 전사문·같은 화자). 그래서 값을 기억으로 적을 수 없고, **커밋된
    파일에서 다시 읽어** 대조하는 것이 유일하게 낡지 않는 방법이다.
    """
    root = (BACKEND_ROOT / get_settings().shadowing_clip_audio_root).resolve()

    for clip in SEED_SHADOWING_ITEMS:
        if clip.audio_filename is None:
            continue
        with wave.open(str(root / clip.audio_filename)) as handle:
            measured_sec = Decimal(handle.getnframes()) / Decimal(handle.getframerate())
        # 스키마가 `numeric(6,2)` 이므로 같은 자리수로 내려 비교한다.
        assert clip.clip_end_sec == measured_sec.quantize(Decimal("0.01")), (
            f"{clip.source_title} 의 시간 창 {clip.clip_end_sec} 가 실측 {measured_sec} 와 다르다"
        )
        assert clip.clip_start_sec == Decimal("0.00"), "합성음의 창은 0 에서 시작한다"
