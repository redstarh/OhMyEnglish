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

from pathlib import Path
from uuid import UUID

import asyncpg

# 헤더가 없으므로 파라미터를 Content-Type 이 싣는다 (§4.4). 프론트는 `<audio src>` 가 아니라
# `fetch()` 로 바이트를 받아 이미 가진 재생 큐(`VoiceIo`)에 넣는다 — 헤더 없는 PCM 은
# `new Audio()` 로 디코드되지 않는다.
RECORDING_MEDIA_TYPE = "audio/L16; rate=16000; channels=1"

_SET_AUDIO_URL_SQL = """
update utterances
   set audio_url = $2
 where id = $1
"""

# ⛔ **세션과 발화를 함께 조건에 넣는다.** `utterance_id` 만 보면 세션을 바꿔 넣은 요청이
# 통과해 남의 녹음이 새어 나간다 — 녹음은 학습자 음성이므로 이 경계가 개인정보 경계다.
_SELECT_AUDIO_URL_SQL = """
select audio_url
  from utterances
 where session_id = $1
   and id = $2
"""


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
    conn: asyncpg.Connection, root: Path, session_id: UUID, utterance_id: UUID
) -> bytes | None:
    """녹음 바이트. 접근 불가면 `None` — 예외를 던지지 않는다.

    **접근 불가가 두 형태로 실재한다**: ① 포인터가 아직 없다(§4.5 의 3·4 사이에서 죽었다)
    ② 포인터만 남고 파일이 없다(§6 의 스윕이 파일과 포인터를 따로 걷는 사이다). 둘 다 정상적인
    중간 상태이므로 여기서 터뜨리면 학습자가 서버 오류를 본다.

    ⚠️ **읽기가 동기 I/O 인 것은 의도다.** 30초 클립이 약 1MB(16kHz·16bit·mono)라 스레드로
    넘기는 비용이 읽는 비용을 넘는다. 클립 상한이 PRD §7 의 90초이므로 이 크기가 요구사항으로
    묶여 있다 — 상한이 올라가면 그때 다시 잰다.
    """
    audio_url = await conn.fetchval(_SELECT_AUDIO_URL_SQL, session_id, utterance_id)
    if audio_url is None:
        return None
    path = recording_path(root, session_id, utterance_id)
    if not path.is_file():
        return None
    return path.read_bytes()
