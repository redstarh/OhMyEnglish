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
때문이다(`app/frontend/lib/audio.ts` 가 그 사실을 실측으로 적어 두었다).

⛔ **저장은 헤더 없는 PCM 이고 변환은 「읽을 때만」 한다** (결정 128). `models/recording.py` 의
`wav_from_pcm` 이 내보내는 길에서만 RIFF 헤더를 얹는다 — 저장 쪽에 헤더를 넣으면 §6 의 스윕·고아
파일 판정이 바이트 길이를 다시 계산해야 하고, 이미 쌓인 파일이 모두 낡은 형식이 된다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfoNotFoundError

import asyncpg

from app.models.learner_time import day_start_for, resolve_now
from app.services.sessions import LIVE_SESSION_STATUSES, LIVE_SESSION_STATUSES_SQL

logger = logging.getLogger(__name__)

# 디스크에 쌓이는 raw LPCM 의 규격 (§4.4) — **정본은 `models/recording.py` 로 옮겼다**(`TASK-221`).
# ⛔ 옮긴 이유는 어댑터 층이 그 값을 읽어야 하는데 서비스에 두면 의존 방향이 뒤집히는 것이다. 그
# 모듈의 머리말이 근거와 계측값을 갖는다. ⛔ **`nova.SAMPLE_RATE_HZ` 와 합치지 않는다**(같은 자리).
# ⚠️ **여기서 재수출하지 않는다** — 이 파일 밖에서 이 상수를 쓰는 곳은 정본에서 바로 가져간다.

# ⚠️ **앞 판은 `audio/L16; rate=16000; channels=1` 이었다** (결정 128 이 바꿨다). 그 파라미터를 읽어
# 재생하는 브라우저 API 가 없어 프론트가 `fetch()` + `VoiceIo` 로만 재생할 수 있었는데, 그 큐는
# **코치 발화의 것**이라 낭독이 발화와 섞이고 barge-in 이 낭독을 끊는다. RIFF 헤더가 표본율·채널을
# 실으면 `new Audio()` 가 그대로 디코드한다 — `services/clip_audio.py` 가 이미 그 길을 쓴다.
RECORDING_MEDIA_TYPE = "audio/wav"


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
#
# ⛔ **「끝난 세션」을 `<> 'active'` 로 재지 않는다** (`TASK-140`). 025(결정 117)가 `paused` 를
# 더해 살아 있는 상태가 둘이 됐고, 정지는 §5.4 의 예외가 지키려던 바로 그 상황이다 —
# 학습자가 자리를 비웠다 돌아와 이어 한다. `<> 'active'` 로 두었을 때 자정을 넘겨 정지 중인
# 세션의 녹음이 `completed` 와 똑같이 지워지는 것을 실물로 관측했다
# (`runs/2026-09-16-task140-paused-recording-purge`). 값역의 정본은 `services/sessions.py` 다.
_SELECT_PURGE_USERS_SQL = f"""
select distinct usr.id as user_id, usr.timezone
  from utterances u
  join learning_sessions s on s.id = u.session_id
  join users usr on usr.id = s.user_id
 where u.audio_url is not null
   and u.utterance_type = 'shadowing_recording'
   and s.status not in {LIVE_SESSION_STATUSES_SQL}
 order by usr.id
"""

# `created_at < $2` 가 011 의 부분 인덱스(`utterances_stored_audio_idx`)를 탄다 — 그것이 경계를
# SQL 의 `AT TIME ZONE` 으로 구하지 않은 둘째 이유다(§5.2).
#
# ⛔ **살아 있는 상태를 위 목록과 «각자» 판정한다** — 그래서 여기도 같은 정본을 읽어야 한다.
# 끝난 세션 하나가 학습자를 목록에 올리면 그 학습자의 **정지 세션 녹음까지** 이 조회가 고른다
# (`TASK-140` · 진행 중 세션에 같은 형태의 단정이 이미 있었다).
_SELECT_EXPIRED_RECORDINGS_SQL = f"""
select u.id, u.session_id
  from utterances u
  join learning_sessions s on s.id = u.session_id
 where u.audio_url is not null
   and u.utterance_type = 'shadowing_recording'
   and s.user_id = $1
   and s.status not in {LIVE_SESSION_STATUSES_SQL}
   and u.created_at < $2
 order by u.created_at, u.id
 limit $3
"""

_CLEAR_AUDIO_URL_SQL = """
update utterances
   set audio_url = null
 where id = any($1::uuid[])
"""

# 이 세션에서 지금까지 읽은 낭독 회차 (`TASK-186` · 결정 129 ③).
#
# ⛔ **`audio_url` 을 조건에 넣지 않는다.** 그것은 「접근 가능한가」이고 회차는 「몇 번 읽었나」다.
# 만료 스윕이 포인터를 지우면 읽은 사실까지 사라져 진행도가 **되돌아간다.**
_COUNT_RECORDING_TURNS_SQL = """
select count(*)
  from utterances
 where session_id = $1
   and utterance_type = 'shadowing_recording'
"""

# 세션이 고른 클립. **join 0행이 「클립 없음」의 유일한 표현이다** — 세션 부재·`shadowing_item_id`
# null·클립 행 부재가 전부 여기로 수렴한다(`load_session_scenario` 와 같은 규약).
_SELECT_SESSION_CLIP_SQL = """
select i.id, i.source_title, i.transcript, i.clip_start_sec, i.clip_end_sec, i.audio_filename
  from learning_sessions s
  join shadowing_items i on i.id = s.shadowing_item_id
 where s.id = $1
"""

# 2다리가 「살려 둘 파일」을 정하는 유일한 조회. **포인터가 정본이므로** 이 집합에 없는 바이트는
# 접근 불가이고 걷어도 잃을 것이 없다.
#
# ⛔ **세션 목록을 한 번에 받는다** (`TASK-227`). 디렉터리마다 부르면 유휴 사이클(1Hz)이 왕복 2N
# 건을 낸다 — 실측: 디렉터리 10개에서 **20건**. 지금은 두 문장으로 접혀 **2건**이다.
_SELECT_LIVE_RECORDING_IDS_SQL = """
select session_id, id
  from utterances
 where session_id = any($1::uuid[])
   and audio_url is not null
"""

# 그 목록 가운데 **살아 있는** 세션. 없는 세션(FK cascade 로 사라진 것)은 이 결과에 안 나오고,
# 그것이 곧 「걷어도 된다」다 — 이전 판이 `status is null` 로 같은 판정을 내렸다.
_SELECT_LIVE_SESSION_IDS_SQL = f"""
select id
  from learning_sessions
 where id = any($1::uuid[])
   and status in {LIVE_SESSION_STATUSES_SQL}
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
    # 이 클립에 합성 오디오가 있는가 (`TASK-66` · 결정 90). ⛔ **파일명이 아니라 불린이다** —
    # 경로는 서버의 것이고 화면이 알아야 하는 것은 「재생 버튼을 보일지」 하나다. `level` 을 담지
    # 않은 것과 같은 규율이다: 화면이 쓰지 않는 것을 싣지 않는다.
    # ⚠️ 파일의 존재가 아니라 **DB 포인터**를 뜻한다 — 접근 가능성의 정본이 DB 이고, 파일 부재는
    # `load_clip_audio` 가 404 로 닫는다(설계서 §5·§6).
    has_audio: bool


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
            # ⛔ 파일명을 싣지 않는다 — 화면은 `/api/shadowing/clips/{item_id}/audio` 를 부르고
            # 경로 조립은 서버가 한다(`TASK-66` · 설계서 §6).
            "has_audio": self.clip.has_audio,
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
        has_audio=row["audio_filename"] is not None,
    )


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

    ⚠️ **§5.4 의 예외를 여기서 함께 적용한다**: 세션이 **살아 있으면** 만료를 재지 않는다. 자정을
    넘기며 진행되는 세션의 녹음을 막으면 학습자가 **지금 비교하려는 것**이 사라진다.
    ⛔ **`active` 하나로 재지 않는다** (`TASK-140`) — 025 가 `paused` 를 더했고 정지는 「자리를
    비웠다 돌아온다」이므로 이 예외가 지키려는 상황 그 자체다. 값역의 정본은 `services/sessions.py`
    의 `LIVE_SESSION_STATUSES` 이고 **스윕 두 다리도 같은 이름을 읽는다**(1다리는 SQL 로, 2다리는
    `sweep_orphan_recording_files` 에서) — 각자 적으면 갈린다. ⚠️ **실제로 갈렸다**: `TASK-140` 이
    025 에 맞춰 세 자리를 고치며 2다리를 지나쳤고, 그 자리만 리터럴로 남아 정지 중 세션의 `.part`
    를 지웠다(`TASK-223`). 그래서 이 서술은 「읽어야 한다」가 아니라 **어디서 읽는지**를 적는다.

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
    if row["status"] not in LIVE_SESSION_STATUSES and _has_expired(row, now=now):
        return None
    path = recording_path(root, session_id, utterance_id)
    if not path.is_file():
        return None
    return path.read_bytes()


async def count_recording_turns(conn: asyncpg.Connection, session_id: UUID) -> int:
    """이 세션에서 지금까지 읽은 낭독 회차 (`TASK-186` · 결정 129 ③).

    **정본이 발화 수인 것이 이 함수의 값이다** — 화면이 세면 새로 고침·재접속에 잃지만 발화는 DB 에
    있으므로 어느 시점에 다시 물어도 같은 값이 나온다.

    ⚠️ **턴을 닫는 트랜잭션 «안에서» 부르면 방금 만든 발화가 포함된다** — 그래서 첫 턴이 `1` 이다.
    """
    return await conn.fetchval(_COUNT_RECORDING_TURNS_SQL, session_id)


def _has_expired(row: asyncpg.Record, *, now: datetime | None) -> bool:
    """이 녹음의 학습자 당일이 지났는가. **계산할 수 없으면 만료로 본다**(닫는 쪽).

    ⛔ **`resolve_now` 를 `try` 밖에서 부른다 — 안에 두면 그 함수의 목적이 무너진다.**
    2026-09-09 리뷰가 런타임으로 잡았다: 안에 뒀을 때 naive `now`(호출자의 버그)가
    `ValueError` 로 아래 `except` 에 걸려 **멀쩡한 `Asia/Seoul` 을 지목하는 경고**가 났고,
    조사하는 사람이 `users.timezone` 을 먼저 의심하게 됐다. `purge_expired_recordings` 는
    처음부터 밖에서 불렀으므로 **두 호출자가 갈라져 있었다.**
    """
    resolved_now = resolve_now(now)
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

    ⚠️ **§5.4 의 예외**: **살아 있는**(`LIVE_SESSION_STATUSES` — `active`·`paused`) 세션은 대상이
    아니다. 크래시로 `active` 에 남은 세션은 기존 고아 리퍼가 `failed` 로 닫고 그 다음 주기에
    대상이 된다 — 새 장치가 필요없다.

    **재시도 장치를 두지 않는다** (§6.3). 이 스윕은 멱등이고(같은 조건을 다시 계산한다) 영구
    실패해도 데이터가 어긋나지 않는다(접근은 이미 막혀 있다). `(b)` 의 실패는 **1다리로 재시도되지
    않으므로**(조건이 `audio_url is not null` 이라 더 이상 선택되지 않는다) 고아 파일 정리
    2다리가 그것을 소유한다 — 그 다리는 **선택이 아니라 필수**다.
    """
    resolved_now = resolve_now(now)
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

    ⚠️ **살아 있는 세션 디렉터리는 건드리지 않는다** — §4.5 의 1단계가 지금 그 안의 `.part` 에
    프레임을 흘리고 있을 수 있다. §5.4 가 삭제에서 살아 있는 세션을 뺀 것과 같은 판단이다.
    ⛔ **`active` 하나로 재지 않는다**(`TASK-223`) — 값역의 정본은 `sessions.LIVE_SESSION_STATUSES`
    이고 정지도 「자리를 비웠다 돌아온다」이므로 이 가드가 지키려는 상황 그 자체다.

    ⛔ **이름 규칙에 맞지 않는 파일은 지우지 않고 남긴다.** 설계서 §6.2 는 *"그 집합에 없는
    파일"* 을 지우라고 적었지만 알 수 없는 파일을 조용히 지우면 되돌릴 수 없다 — **이 절충은 내가
    정한 것이다.** ⚠️ **경고가 아니라 `debug` 로 적는다**: 2026-09-09 리뷰가 잡았듯 그 파일 하나가
    영구히 남으므로 유휴 사이클(기본 1초)마다 경고가 나 **하루 8만 줄이 넘고**, 그 홍수가 진짜
    실패(unlink 실패)의 `WARNING` 창구를 막는다(§6.3 이 지정한 실행 명령은 `WARNING` 이상만 흘린다).
    우리가 만드는 이름은 `.pcm`·`.pcm.part` 둘뿐이라 그 밖의 파일은 애초에 우리 것이 아니다 —
    남기는 것이 정책이고, 조사가 필요하면 **디렉터리가 지워지지 않고 남는 것**이 그 신호다.

    ⚠️ **사이클 상한을 1다리와 같은 상수로 묶는다.** 파일시스템을 걷는 쪽만 무제한이면 유휴 사이클이
    삭제로 오래 붙잡힌다. 남은 것은 다음 사이클이 이어간다(멱등).

    ⛔ **DB 를 두 문장으로만 본다 — 디렉터리마다 묻지 않는다** (`TASK-227`). 이전 판은 디렉터리당
    조회 2건이라 유휴 사이클(1Hz)이 왕복 2N 건을 냈다 — 실측: 디렉터리 10개에서 **20건**이었고
    지금은 **2건**이다.
    ⚠️ **스냅샷이 앞에서 한 번 찍히는 것을 알고 둔다**: 「살아 있는 세션」을 사이클 «시작»에 읽으므로
    그 뒤에 살아나는 세션은 이 사이클에 반영되지 않는다. ⛔ 그런데 그 창은 **닫혀 있다** —
    `end_session` 은 종단이고 `set_session_paused` 는 **살아 있는 상태에서만** 옮기므로
    (`services/sessions.py`) 끝난 세션이 다시 살아나는 경로가 없다. 새 세션은 사이클 시작 뒤에
    디렉터리를 만들므로 목록에 애초에 없다.

    뿌리가 없으면 0을 돌려준다: 저장한 적이 없다는 뜻이라 오류가 아니다(§6.3).
    """
    if not root.is_dir():
        return 0
    ours: list[tuple[Path, UUID]] = []
    for session_dir in sorted(root.iterdir()):
        if not session_dir.is_dir():
            continue
        try:
            ours.append((session_dir, UUID(session_dir.name)))
        except ValueError:
            # 우리가 만든 디렉터리가 아니다 — 뿌리를 남과 공유할 수 있으므로 건드리지 않는다.
            continue
    if not ours:
        return 0
    session_ids = [session_id for _, session_id in ours]
    live_sessions = {
        row["id"] for row in await conn.fetch(_SELECT_LIVE_SESSION_IDS_SQL, session_ids)
    }
    live_recordings: dict[UUID, set[UUID]] = {session_id: set() for session_id in session_ids}
    for row in await conn.fetch(_SELECT_LIVE_RECORDING_IDS_SQL, session_ids):
        live_recordings[row["session_id"]].add(row["id"])
    removed = 0
    for session_dir, session_id in ours:
        if removed >= limit:
            break
        if session_id in live_sessions:
            continue
        removed += remove_orphan_recordings_in(
            session_dir, live_recordings[session_id], limit=limit - removed
        )
        remove_recording_dir_if_empty(session_dir)
    if removed:
        logger.info("포인터 없는 쉐도잉 녹음 파일 %d건을 지웠다 (2다리)", removed)
    return removed


def remove_orphan_recordings_in(session_dir: Path, live: set[UUID], *, limit: int) -> int:
    """한 세션 디렉터리에서 고아를 지운다. `.part` 는 언제나 고아다(미완성 쓰기).

    ⛔ **삭제 규칙의 정본이 이 함수다** (`TASK-216`). 공개인 이유는 **세션 하나만** 걷는 호출자가
    있기 때문이다 — 회차 teardown(`tests/harness/teardown_session.py`)이 그렇다. 위
    `sweep_orphan_recording_files` 는 뿌리 전체를 순회하므로 세션 단위 개수를 잃는다.
    ⚠️ **그 호출자가 규칙을 다시 구현하고 있었고 정책이 갈라져 있었다** — 하네스는 디렉터리의
    **모든** 파일을 지웠고, 그래서 이름 규칙 밖의 파일도 조용히 사라졌다(되돌릴 수 없다).
    ⇒ 규칙을 고칠 자리를 하나로 두는 것이 이 함수가 공개인 값이다.
    """
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


def remove_recording_dir_if_empty(session_dir: Path) -> None:
    """빈 세션 디렉터리를 걷는다. 비어 있지 않으면 그대로 둔다 — 실패를 올리지 않는다.

    ⚠️ **남는 디렉터리가 조사의 신호다** — 이름 규칙 밖의 파일이 있으면 지워지지 않고 남으므로,
    「비어 있지 않아 남았다」가 곧 「우리 것이 아닌 파일이 거기 있다」다
    (`sweep_orphan_recording_files` 의 docstring 이 그 절충의 근거를 가진다).
    """
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
