"""쉐도잉 낭독 오디오의 파일 수명과 DB 포인터 (`TASK-45` AC#3 · 설계서 §4.3~§4.5).

**R10-7(오디오를 저장하지 않는다)의 유일한 예외가 이 모듈이다.** 캡틴이 연 예외는 학습자의
쉐도잉 낭독 하나이고, 그 경계는 주석이 아니라 **011 의 CHECK 가 가둔다**
(`utterances_audio_only_for_shadowing`) — docstring 은 이 파일을 읽을 이유가 없는 사람을
구속하지 못하지만 스키마는 한다.

⛔ **이 모듈은 프레임을 받지 않는다.** 「낭독 턴을 언제 열고 닫는가」는 설계서 §12 요구 4 이고
WS 표면이라 `TASK-10` 의 설계 몫이다(결정 34 가 「최소한만 만든다」로 제약했다). 여기 있는 것은
턴이 닫힌 뒤의 두 걸음(§4.5 의 3·4)과 그 산출물을 읽는 길뿐이다.

**형식을 정하지 않고 이미 있는 것을 쓴다** (§4.4): 프론트가 `AudioWorklet` 으로 만드는 raw
LPCM 16kHz·16bit·mono 를 그대로 파일에 흘린다. 확장자가 `.pcm` 인 이유는 **헤더가 없기**
때문이고(`app/frontend/lib/audio.ts` 가 그 사실을 실측으로 적어 두었다), 그래서 표본율·채널을
`RECORDING_MEDIA_TYPE` 이 말해야 한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import asyncpg

logger = logging.getLogger(__name__)

# 헤더가 없으므로 파라미터를 Content-Type 이 싣는다 (§4.4). 프론트는 `<audio src>` 가 아니라
# `fetch()` 로 바이트를 받아 이미 가진 재생 큐(`VoiceIo`)에 넣는다 — 헤더 없는 PCM 은
# `new Audio()` 로 디코드되지 않는다.
RECORDING_MEDIA_TYPE = "audio/L16; rate=16000; channels=1"

# 한 유휴 사이클이 지우는 상한. ⚠️ **발명값이다** — 설계서 §6.2 는 "사이클당 상한. 루프를
# 굶기지 않는다"만 요구하고 수를 정하지 않았다. 근거는 하나뿐이다: 유휴 사이클이 파일 삭제로
# 오래 붙잡히지 않을 크기. **남은 것은 다음 사이클이 이어간다**(스윕이 멱등이라 그것이 안전하다).
PURGE_LIMIT_PER_CYCLE = 100

_SET_AUDIO_URL_SQL = """
update utterances
   set audio_url = $2
 where id = $1
"""

# 녹음이 남아 있는 사용자와 그 타임존. **사용자별로 경계를 따로 계산하기 위한 목록이다**
# (§5.2 의 이유 1 — 잘못된 tz 값이 한 사람만 막게 한다).
_SELECT_PURGE_USERS_SQL = """
select distinct usr.id as user_id, usr.timezone
  from utterances u
  join learning_sessions s on s.id = u.session_id
  join users usr on usr.id = s.user_id
 where u.audio_url is not null
   and u.utterance_type = 'shadowing_recording'
   and s.status <> 'active'
 order by usr.id
"""

# `created_at < $2` 가 011 의 부분 인덱스(`utterances_stored_audio_idx`)를 탄다 — 그것이 경계를
# SQL 의 `AT TIME ZONE` 으로 구하지 않은 둘째 이유다(§5.2).
_SELECT_EXPIRED_RECORDINGS_SQL = """
select u.id, u.session_id
  from utterances u
  join learning_sessions s on s.id = u.session_id
 where u.audio_url is not null
   and u.utterance_type = 'shadowing_recording'
   and s.user_id = $1
   and s.status <> 'active'
   and u.created_at < $2
 order by u.created_at, u.id
 limit $3
"""

_CLEAR_AUDIO_URL_SQL = """
update utterances
   set audio_url = null
 where id = any($1::uuid[])
"""

# 세션이 고른 클립. **join 0행이 「클립 없음」의 유일한 표현이다** — 세션 부재·`shadowing_item_id`
# null·클립 행 부재가 전부 여기로 수렴한다(`load_session_scenario` 와 같은 규약).
_SELECT_SESSION_CLIP_SQL = """
select i.id, i.source_title, i.transcript, i.clip_start_sec, i.clip_end_sec
  from learning_sessions s
  join shadowing_items i on i.id = s.shadowing_item_id
 where s.id = $1
"""

# 2다리가 「살려 둘 파일」을 정하는 유일한 조회. **포인터가 정본이므로** 이 집합에 없는 바이트는
# 접근 불가이고 걷어도 잃을 것이 없다.
_SELECT_LIVE_RECORDING_IDS_SQL = """
select id
  from utterances
 where session_id = $1
   and audio_url is not null
"""

# ⛔ **세션과 발화를 함께 조건에 넣는다.** `utterance_id` 만 보면 세션을 바꿔 넣은 요청이
# 통과해 남의 녹음이 새어 나간다 — 녹음은 학습자 음성이므로 이 경계가 개인정보 경계다.
#
# 함께 읽는 셋은 **만료 판정에 필요한 전부**다 (§6.4): `created_at`(경계와 비교할 시각) ·
# `status`(§5.4 의 진행 중 예외) · `timezone`(경계의 정본 — 호스트 시간이 아니다).
_SELECT_RECORDING_SQL = """
select u.audio_url,
       u.created_at,
       s.status,
       usr.timezone
  from utterances u
  join learning_sessions s on s.id = u.session_id
  join users usr on usr.id = s.user_id
 where u.session_id = $1
   and u.id = $2
"""


@dataclass(frozen=True, slots=True)
class ShadowingClip:
    """세션이 고른 클립에서 **화면이 쓰는 것만** 담는다 (설계서 §12 요구 5).

    ⛔ `level` 을 담지 않는다 — 그것은 **선택의 키**이고 선택은 이미 끝났다. 화면에 실어 보내면
    「학습자에게 수준을 표시한다」는 결정을 이 자리가 발명하는 셈이 된다(PRD 에 그 요구가 없다).

    ⚠️ **문장으로 쪼개지 않는다.** PRD §7 의 「문장 단위로 제공한다」는 화면의 몫이고 쪼개는
    규칙은 `TASK-10` 이 정한다 — 여기서 정하면 두 곳이 갈라진다(설계서 §3.2 유도 2 가 색인을
    저장하지 않은 것과 같은 이유다).
    """

    id: UUID
    source_title: str
    transcript: str
    clip_start_sec: Decimal
    clip_end_sec: Decimal


@dataclass(frozen=True, slots=True)
class ShadowingTurns:
    """낭독 턴이 쓰는 재료 묶음 — 세션 시작이 만들어 러너에 넘긴다 (캡틴 결정 35).

    ⛔ **러너가 이 값을 스스로 조회하지 않는다.** 클립도 설정값도 세션 시작(`api/ws.py`)이 읽어
    넘긴다 — 게이트웨이가 `services` 를 더 깊이 알게 하면 의존 방향이 뒤집힌다(`factory`·`nova` 가
    `app.models` 만 아는 것과 같은 규약).

    ⚠️ **이 묶음이 있으면 쉐도잉 세션이다.** `None` 이면 낭독 턴 신호를 받아도 무시한다 — 모드를
    러너가 다시 판정하지 않는 것이 두 곳에서 갈라지지 않는 방법이다.
    """

    clip: ShadowingClip
    audio_root: Path
    playback_rate: float
    repeat_count: int

    def as_event_payload(self) -> dict[str, object]:
        """`session_started` 에 실어 보낼 형태 (요구 5 — 화면은 **전달만** 받는다).

        ⚠️ `Decimal` 을 `float` 로 바꾼다 — `json` 이 `Decimal` 을 직렬화하지 못한다. 초 단위
        시간 창이라 배정밀도로 잃을 정밀도가 없다(스키마가 `numeric(6,2)` 다).
        """
        return {
            "item_id": str(self.clip.id),
            "source_title": self.clip.source_title,
            "transcript": self.clip.transcript,
            "clip_start_sec": float(self.clip.clip_start_sec),
            "clip_end_sec": float(self.clip.clip_end_sec),
            "playback_rate": self.playback_rate,
            "repeat_count": self.repeat_count,
        }


async def load_session_clip(conn: asyncpg.Connection, session_id: UUID) -> ShadowingClip | None:
    """이 세션이 고른 쉐도잉 클립 — 없으면 `None`.

    **사후조건: 세션 부재 · `shadowing_item_id` null · 클립 행 부재 → 전부 `None`.** 셋이 한
    경로로 수렴하는 것은 `load_session_scenario` 가 세운 규약과 같다(그 docstring 이 근거를
    가진다). 클립이 0행이어도 세션을 여는 것이 `start_shadowing_session` 의 계약이므로 이
    `None` 은 정상 상태다 — 호출자는 클립 없이 진행한다.

    ⛔ **DB 오류는 던진다.** 흡수는 `api/ws.py` 의 래퍼가 한다(`_load_known_sounds_or_empty` 와
    같은 분업) — 여기서 삼키면 「조회가 깨졌다」와 「클립이 없다」가 구분되지 않는다.
    """
    row = await conn.fetchrow(_SELECT_SESSION_CLIP_SQL, session_id)
    if row is None:
        return None
    return ShadowingClip(
        id=row["id"],
        source_title=row["source_title"],
        transcript=row["transcript"],
        clip_start_sec=row["clip_start_sec"],
        clip_end_sec=row["clip_end_sec"],
    )


def day_start_for(tz_name: str, *, now: datetime) -> datetime:
    """학습자의 「오늘」이 시작한 절대 시각. **이 값보다 이전 녹음이 삭제 대상이다** (§5.2).

    ⛔ **`current_date` 를 쓰지 않는다.** 설계 세션이 공유 DB 에서 직접 관측한 값이 근거다:
    `current_date` 가 **2026-09-07** 인데 `(now() at time zone 'Asia/Seoul')` 는 **2026-09-08**
    이었다(`SHOW TimeZone` = UTC). 그 값으로 판정하면 학습자가 아직 비교하지 못한 녹음이 하루
    일찍 사라지고 **되돌릴 수 없다.** 타임존의 정본은 `users.timezone` 컬럼이고 호스트 시간도
    세션 기본값도 아니다.

    **SQL 의 `AT TIME ZONE` 이 아니라 Python 에서 구하는 이유 셋** (§5.2 — 전역 규약은 둘 다
    허용한다): ① 잘못된 타임존 값이 **한 사람만** 막는다(집합 UPDATE 안에서 터지면 한 사람의
    값이 전체 삭제를 막는다 · `users.timezone` 에 CHECK 가 없다) ② `created_at < $1` 이 011 의
    부분 인덱스를 탄다(`(created_at at time zone …)::date` 는 못 탄다) ③ 되돌릴 수 없는 삭제의
    경계라 DB 없이 경계값을 값싸게 재야 한다.

    ⚠️ **`replace(hour=0, …)` 를 쓰지 않는다.** 2026-09-09 리뷰가 이 서술의 이전 판을 정정했다 —
    위험은 「존재하지 않는 자정」이 아니라 **자정이 두 번 오는 날**이다(자정에 DST 가 끝나는 지역).
    `replace` 는 입력 시각의 `fold` 를 물려받아 **두 번째** 자정을 고르고, 그러면 경계가 한 시간
    늦어져 그 사이 녹음이 「어제」로 분류돼 하루 일찍 삭제된다. 날짜와 tzinfo 로 다시 조립하면
    `fold=0`, 즉 **첫 번째** 자정이 되고 그것이 「오늘이 시작한 시각」이다.
    실측(`America/Havana`, `2026-11-01 05:30Z`): 조립 → `04:00Z` · `replace` → `05:00Z`.
    ⚠️ **`America/New_York` 로는 이 차이가 드러나지 않는다** — 그 지역은 자정이 아니라 02:00 에
    바뀌어 두 방식이 같은 값을 낸다.

    ⚠️ **여기 있는 이유는 지금 소비자가 녹음뿐이기 때문이다.** 복습 주기·일일 계획이 같은 경계를
    밟으면(`H-S` 가 그것을 예고한다) 공용 자리로 옮긴다 — 그때까지 두 곳에서 계산하지 않는 것이
    이 함수의 목적이다(§6.4: 스윕과 서빙이 **같은 함수 하나**를 부른다).
    """
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware (naive datetime is not allowed)")
    zone = ZoneInfo(tz_name)
    today_local = now.astimezone(zone).date()
    return datetime.combine(today_local, time.min, tzinfo=zone).astimezone(UTC)


def recording_dir(root: Path, session_id: UUID) -> Path:
    """세션 하나의 녹음이 모이는 디렉터리. 삭제 스윕(§6)이 이 단위로 걷는다."""
    return root / str(session_id)


def recording_path(root: Path, session_id: UUID, utterance_id: UUID) -> Path:
    """완성된 녹음의 자리. **위치가 두 id 에서 결정론적으로 유도된다** (§4.4).

    그래서 뿌리를 옮겨도 저장된 행이 무효가 되지 않는다 — 뿌리는 설정이고 데이터가 아니다.
    """
    return recording_dir(root, session_id) / f"{utterance_id}.pcm"


def pending_recording_path(root: Path, session_id: UUID, turn_id: UUID) -> Path:
    """아직 `utterance_id` 를 모르는 동안의 자리 (§4.5 의 1단계).

    바이트가 전사문 확정보다 **먼저** 도착하기 때문에 이름이 두 번 필요하다 — `utterances` 행은
    Nova 가 문장을 닫을 때 생긴다. `.part` 가 「미완성」을 파일시스템에 적어 두어 고아 파일
    정리가 그것을 구분한다.
    """
    return recording_dir(root, session_id) / f"{turn_id}.pcm.part"


def recording_url(session_id: UUID, utterance_id: UUID) -> str:
    """`audio_url` 에 담는 값. ⛔ **파일 경로가 아니라 API 경로다** (§4.4).

    컬럼 이름과 `docs/database-schema.md` 의 계약(*"접근 불가 처리"*)이 이때만 성립한다.
    """
    return f"/api/sessions/{session_id}/recordings/{utterance_id}"


async def finalize_recording(
    conn: asyncpg.Connection,
    root: Path,
    *,
    session_id: UUID,
    turn_id: UUID,
    utterance_id: UUID,
) -> str:
    """§4.5 의 3·4 — 파일을 옮기고 **그 다음에** DB 포인터를 쓴다.

    ⛔ **순서를 뒤집지 마라.** 포인터를 먼저 쓰면 그 사이에 죽었을 때 「DB 는 접근 가능하다고
    말하는데 파일이 없는」 상태가 남고, 학습자에게 깨진 재생으로 보인다. 이 순서로 죽으면 파일만
    남아 **접근 불가**이고 §6 의 고아 파일 정리가 걷는다 — **DB 가 접근 가능성의 정본이다.**

    rename 은 같은 디렉터리 안이라 원자적이다. 파일이 없으면 여기서 `FileNotFoundError` 로
    멈추고 **UPDATE 에 도달하지 않는다** — 그것이 위 불변식을 지키는 방식이다.
    """
    pending = pending_recording_path(root, session_id, turn_id)
    pending.rename(recording_path(root, session_id, utterance_id))
    audio_url = recording_url(session_id, utterance_id)
    await conn.execute(_SET_AUDIO_URL_SQL, utterance_id, audio_url)
    return audio_url


async def load_recording(
    conn: asyncpg.Connection,
    root: Path,
    session_id: UUID,
    utterance_id: UUID,
    *,
    now: datetime | None = None,
) -> bytes | None:
    """녹음 바이트. 접근 불가면 `None` — 예외를 던지지 않는다.

    **접근 불가가 네 형태로 실재한다**: ① 포인터가 아직 없다(§4.5 의 3·4 사이에서 죽었다)
    ② 포인터만 남고 파일이 없다(§6 의 스윕이 파일과 포인터를 따로 걷는 사이다) ③ **학습자의
    당일이 지났다**(§6.4) ④ **경계를 계산할 수 없다**(아래). 전부 정상적인 상태이므로 여기서
    터뜨리면 학습자가 서버 오류를 본다.

    ⛔ **③ 이 워커에 개인정보를 걸지 않기 위한 장치다** (§6.4). `WORKER_ENABLED=false` 로 며칠을
    돌리면 스윕이 한 번도 돌지 않는데, 그동안 접근이 열려 있으면 「당일이 지나면 삭제」가 **워커
    기동 여부에 걸린 약속**이 된다. 그래서 조회가 **스윕과 같은 함수**(`day_start_for`)를 다시
    계산해 스스로 닫는다 — 두 곳에서 각자 계산하면 갈라진다.

    ⚠️ **§5.4 의 예외를 여기서 함께 적용한다**: 세션이 `active` 면 만료를 재지 않는다. 자정을
    넘기며 진행되는 세션의 녹음을 막으면 학습자가 **지금 비교하려는 것**이 사라진다.

    ⛔ **④ 는 닫는 쪽으로 넘어진다.** `users.timezone` 에 CHECK 가 없어 잘못된 값이 실재할 수
    있고, 그때 바이트를 내주면 삭제 약속이 설정값 하나로 무력화된다. **삭제 스윕은 반대로 그
    사용자만 건너뛴다**(§6.3) — 스윕은 열어 두고 넘어가면 되지만 조회는 그럴 수 없다.

    ⚠️ **읽기가 동기 I/O 인 것은 의도다.** 30초 클립이 약 1MB(16kHz·16bit·mono)라 스레드로
    넘기는 비용이 읽는 비용을 넘는다. 클립 상한이 PRD §7 의 90초이므로 이 크기가 요구사항으로
    묶여 있다 — 상한이 올라가면 그때 다시 잰다.
    """
    row = await conn.fetchrow(_SELECT_RECORDING_SQL, session_id, utterance_id)
    if row is None or row["audio_url"] is None:
        return None
    if row["status"] != "active" and _has_expired(row, now=now):
        return None
    path = recording_path(root, session_id, utterance_id)
    if not path.is_file():
        return None
    return path.read_bytes()


def _resolve_now(now: datetime | None) -> datetime:
    """`now` 를 확정하고 **aware 를 보장한다.**

    ⛔ 이 검사를 `day_start_for` 에만 맡기지 않는 이유: 아래 두 호출자가 타임존 값 문제를
    `except` 로 삼키는데, naive `now` 도 같은 `ValueError` 라 **호출자의 버그가 「타임존이
    이상하다」로 위장된다.** 여기서 미리 터뜨리면 그 `except` 가 타임존 값 문제로만 좁혀진다.

    ⚠️ 앱 시계를 쓰는 것이 판단이다 — 경계 계산이 Python 이므로(§5.2) 시계도 같은 쪽에 둔다.
    DB 시계(`clock_timestamp()`)를 쓰려면 왕복이 한 번 더 늘고, 두 시계는 같은 호스트다.
    """
    resolved = now if now is not None else datetime.now(UTC)
    if resolved.tzinfo is None:
        raise ValueError("`now` must be timezone-aware (naive datetime is not allowed)")
    return resolved


def _has_expired(row: asyncpg.Record, *, now: datetime | None) -> bool:
    """이 녹음의 학습자 당일이 지났는가. **계산할 수 없으면 만료로 본다**(닫는 쪽).

    ⛔ **`_resolve_now` 를 `try` 밖에서 부른다 — 안에 두면 그 함수의 목적이 무너진다.**
    2026-09-09 리뷰가 런타임으로 잡았다: 안에 뒀을 때 naive `now`(호출자의 버그)가
    `ValueError` 로 아래 `except` 에 걸려 **멀쩡한 `Asia/Seoul` 을 지목하는 경고**가 났고,
    조사하는 사람이 `users.timezone` 을 먼저 의심하게 됐다. `purge_expired_recordings` 는
    처음부터 밖에서 불렀으므로 **두 호출자가 갈라져 있었다.**
    """
    resolved_now = _resolve_now(now)
    try:
        cutoff = day_start_for(row["timezone"], now=resolved_now)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "학습자 타임존을 쓸 수 없어 녹음 접근을 닫는다 — timezone=%r", row["timezone"]
        )
        return True
    created_at: datetime = row["created_at"]
    return created_at < cutoff


async def purge_expired_recordings(
    conn: asyncpg.Connection,
    root: Path,
    *,
    now: datetime | None = None,
    limit: int = PURGE_LIMIT_PER_CYCLE,
) -> list[UUID]:
    """당일이 지난 녹음을 접근 불가로 만들고 바이트를 지운다 — §6.2 의 **1다리**.

    ⛔ **순서가 (a) 포인터 → (b) 파일인 것이 계약이다.** `docs/database-schema.md` 가 요구하는
    것은 「즉시 접근 불가」이므로 실패 시 **닫히는 쪽**으로 넘어져야 한다. 뒤집으면(파일 먼저)
    크래시 후 DB 는 "있다"고 하고 파일은 없어 **학습자에게 깨진 재생**이 남는다.

    ⛔ **사용자마다 경계를 따로 계산한다** (§5.2 의 이유 1). 집합 UPDATE 안에서
    `AT TIME ZONE` 을 쓰면 **한 사람의 잘못된 `users.timezone` 이 모든 사람의 삭제를 막는다** —
    설계 세션이 직접 확인했다(`select now() at time zone 'Not/AZone'` → `ERROR`). 여기서는 그
    사용자만 건너뛰고 `WARNING` 을 남긴다: 값을 고치면 다음 사이클에 낫는다(§6.3).

    ⚠️ **§5.4 의 예외**: `status = 'active'` 세션은 대상이 아니다. 크래시로 `active` 에 남은
    세션은 기존 고아 리퍼가 `failed` 로 닫고 그 다음 주기에 대상이 된다 — 새 장치가 필요없다.

    **재시도 장치를 두지 않는다** (§6.3). 이 스윕은 멱등이고(같은 조건을 다시 계산한다) 영구
    실패해도 데이터가 어긋나지 않는다(접근은 이미 막혀 있다). `(b)` 의 실패는 **1다리로 재시도되지
    않으므로**(조건이 `audio_url is not null` 이라 더 이상 선택되지 않는다) 고아 파일 정리
    2다리가 그것을 소유한다 — 그 다리는 **선택이 아니라 필수**다.
    """
    resolved_now = _resolve_now(now)
    purged: list[UUID] = []
    remaining = limit
    for user in await conn.fetch(_SELECT_PURGE_USERS_SQL):
        if remaining <= 0:
            break
        try:
            cutoff = day_start_for(user["timezone"], now=resolved_now)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning(
                "학습자 타임존을 쓸 수 없어 이 사용자의 삭제를 건너뛴다 — user=%s timezone=%r",
                user["user_id"],
                user["timezone"],
            )
            continue
        rows = await conn.fetch(_SELECT_EXPIRED_RECORDINGS_SQL, user["user_id"], cutoff, remaining)
        if not rows:
            continue
        expired = [row["id"] for row in rows]
        # (a) 먼저, 그리고 **자기 트랜잭션으로** 커밋한다 — 여기서 접근 불가가 확정된다.
        async with conn.transaction():
            await conn.execute(_CLEAR_AUDIO_URL_SQL, expired)
        # (b) 그 다음 바이트. 실패해도 (a) 는 이미 섰고 2다리가 같은 파일을 다시 고른다.
        for row in rows:
            _unlink_recording(root, row["session_id"], row["id"])
        purged.extend(expired)
        remaining -= len(expired)
    if purged:
        # **INFO 다** — 문서가 지정한 실행 명령은 root 로거에 핸들러를 두지 않아 `WARNING`
        # 이상만 흐른다(§6.3). 즉 이 줄은 개발 중에만 보이고 실패는 위 `WARNING` 으로 보인다.
        logger.info("만료된 쉐도잉 녹음 %d건을 접근 불가로 만들고 파일을 지웠다", len(purged))
    return purged


async def sweep_orphan_recording_files(
    conn: asyncpg.Connection, root: Path, *, limit: int = PURGE_LIMIT_PER_CYCLE
) -> int:
    """포인터가 없는 바이트를 걷는다 — §6.2 의 **2다리**. 지운 파일 수를 돌려준다.

    ⛔ **이 다리는 선택이 아니라 필수다.** 1다리의 `(b)` 실패는 1다리로 재시도되지 않는다 —
    조건이 `audio_url is not null` 이라 `(a)` 가 이미 선 행은 **다시 선택되지 않는다.** 파일
    쪽에서 걷는 다리가 없으면 바이트가 영구히 남는다.

    **잡는 것 셋**: ① 1다리의 unlink 실패 ② §4.5 의 중단된 쓰기(`.part`) ③ **FK cascade 로
    사라진 포인터** — `utterances` 는 `learning_sessions` 에 `on delete cascade` 이므로 세션을
    지우면 포인터는 사라지고 파일은 남는다. ③ 은 1다리가 원리적으로 볼 수 없는 경로다.

    ⚠️ **진행 중 세션 디렉터리는 건드리지 않는다** — §4.5 의 1단계가 지금 그 안의 `.part` 에
    프레임을 흘리고 있을 수 있다. §5.4 가 삭제에서 진행 중 세션을 뺀 것과 같은 판단이다.

    ⛔ **이름 규칙에 맞지 않는 파일은 지우지 않고 남긴다.** 설계서 §6.2 는 *"그 집합에 없는
    파일"* 을 지우라고 적었지만 알 수 없는 파일을 조용히 지우면 되돌릴 수 없다 — **이 절충은 내가
    정한 것이다.** ⚠️ **경고가 아니라 `debug` 로 적는다**: 2026-09-09 리뷰가 잡았듯 그 파일 하나가
    영구히 남으므로 유휴 사이클(기본 1초)마다 경고가 나 **하루 8만 줄이 넘고**, 그 홍수가 진짜
    실패(unlink 실패)의 `WARNING` 창구를 막는다(§6.3 이 지정한 실행 명령은 `WARNING` 이상만 흘린다).
    우리가 만드는 이름은 `.pcm`·`.pcm.part` 둘뿐이라 그 밖의 파일은 애초에 우리 것이 아니다 —
    남기는 것이 정책이고, 조사가 필요하면 **디렉터리가 지워지지 않고 남는 것**이 그 신호다.

    ⚠️ **사이클 상한을 1다리와 같은 상수로 묶는다.** 파일시스템을 걷는 쪽만 무제한이면 유휴 사이클이
    삭제로 오래 붙잡힌다. 남은 것은 다음 사이클이 이어간다(멱등).

    뿌리가 없으면 0을 돌려준다: 저장한 적이 없다는 뜻이라 오류가 아니다(§6.3).
    """
    if not root.is_dir():
        return 0
    removed = 0
    for session_dir in sorted(root.iterdir()):
        if removed >= limit:
            break
        if not session_dir.is_dir():
            continue
        try:
            session_id = UUID(session_dir.name)
        except ValueError:
            # 우리가 만든 디렉터리가 아니다 — 뿌리를 남과 공유할 수 있으므로 건드리지 않는다.
            continue
        status = await conn.fetchval(
            "select status from learning_sessions where id = $1", session_id
        )
        if status == "active":
            continue
        live = {row["id"] for row in await conn.fetch(_SELECT_LIVE_RECORDING_IDS_SQL, session_id)}
        removed += _remove_orphans_in(session_dir, live, limit=limit - removed)
        _remove_dir_if_empty(session_dir)
    if removed:
        logger.info("포인터 없는 쉐도잉 녹음 파일 %d건을 지웠다 (2다리)", removed)
    return removed


def _remove_orphans_in(session_dir: Path, live: set[UUID], *, limit: int) -> int:
    """한 세션 디렉터리에서 고아를 지운다. `.part` 는 언제나 고아다(미완성 쓰기)."""
    removed = 0
    for path in sorted(session_dir.iterdir()):
        if removed >= limit:
            break
        if not path.is_file():
            continue
        if path.name.endswith(".pcm.part"):
            pass  # 미완성 — 살아있는 포인터를 가질 수 없다
        elif path.suffix == ".pcm":
            try:
                if UUID(path.stem) in live:
                    continue
            except ValueError:
                logger.debug("이름을 해석할 수 없는 녹음 파일을 남긴다: %s", path)
                continue
        else:
            logger.debug("녹음 이름 규칙에 맞지 않는 파일을 남긴다: %s", path)
            continue
        try:
            path.unlink()
        except OSError:
            # ⚠️ 이쪽은 `WARNING` 을 유지한다 — **우리 파일이고 조치가 필요하다.** 위의
            # `debug` 와 갈라지는 근거가 그것이다: 남기는 것이 정책인 파일과, 지워야 하는데
            # 못 지운 파일은 다르다.
            logger.warning("고아 녹음 파일을 지우지 못했다 — 다음 사이클에 다시 건다: %s", path)
            continue
        removed += 1
    return removed


def _remove_dir_if_empty(session_dir: Path) -> None:
    """빈 세션 디렉터리를 걷는다. 비어 있지 않으면 그대로 둔다 — 실패를 올리지 않는다."""
    try:
        session_dir.rmdir()
    except OSError:
        return


def _unlink_recording(root: Path, session_id: UUID, utterance_id: UUID) -> None:
    """바이트를 지운다. **실패를 예외로 올리지 않는다** — (a) 를 되돌리지 않기 위해서다.

    파일이 이미 없는 것은 흔한 상태다(2다리가 먼저 걷었거나 사람이 지웠다) — `missing_ok` 로
    받는다. 권한·EBUSY 같은 실패는 `WARNING` 으로 남기고 2다리에 넘긴다.
    """
    path = recording_path(root, session_id, utterance_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("녹음 파일을 지우지 못했다 — 고아 파일 정리가 다시 걷는다: %s", path)
