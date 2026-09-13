"""합성한 쉐도잉 클립 오디오를 읽는 길 (`TASK-66`).

설계: `docs/design/2026-09-14-shadowing-clip-audio-design.md` §5.

⛔ **학습자 낭독(`services/recordings.py`)과 합치지 않는다 — 수명주기가 반대다.** 낭독은 학습자의
당일이 지나면 지워지는 개인정보이고(그 모듈의 만료·스윕), 클립 오디오는 리포와 함께 배포되는
**제품 자산**이라 지우는 경로가 없다. 한 모듈에 두면 만료 판정이 제품 자산으로 번질 자리가 생긴다.

**R10-7 예외의 경계는 이 docstring 이 아니라 022 의 CHECK 둘이 가둔다**
(`shadowing_items_audio_filename_matches_id` · `shadowing_items_audio_only_for_synthetic`) —
011 이 세운 방식이고 그 이유는 *"docstring 은 그 함수를 읽을 이유가 없는 사람을 구속하지 못한다 —
스키마는 한다"* 다. 캡틴이 연 예외 범위는 「합성한 쉐도잉 클립 오디오」 하나다(결정 47).
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import asyncpg

# WAV 는 RIFF 헤더가 표본율·채널을 싣는다 — 그래서 프런트가 `new Audio()` 로 그대로 디코드한다.
# ⚠️ 낭독의 `RECORDING_MEDIA_TYPE`(`audio/L16; rate=16000; channels=1`)과 **다른 이유가 이것이다**:
# 그쪽은 헤더가 없어 파라미터를 Content-Type 이 말해야 하고 `fetch()` + `VoiceIo` 로만 재생된다.
# 두 값을 섞으면 재생 경로가 조용히 틀어진다(설계서 §6 이 그 차이에 기대어 화면을 정했다).
CLIP_AUDIO_MEDIA_TYPE = "audio/wav"

_SELECT_CLIP_AUDIO_FILENAME_SQL = """
select audio_filename
  from shadowing_items
 where id = $1
"""


def clip_audio_path(root: Path, item_id: UUID) -> Path:
    """클립 오디오 파일의 자리. **파일명을 DB 에서 받지 않고 id 로 조립한다.**

    022 의 CHECK 가 `audio_filename = id::text || '.wav'` 를 강제하므로 두 값은 같다. 그래도
    조립을 id 로 하는 것은 방어를 겹으로 두는 것이다 — 한 겹이 뚫려도 다른 겹이 막아야 한다.
    ⛔ **이 함수에 파일명 인자를 더하지 마라.** 그 순간 DB 문자열이 경로에 닿는 길이 열린다.
    """
    return root / f"{item_id}.wav"


async def load_clip_audio(conn: asyncpg.Connection, root: Path, item_id: UUID) -> bytes | None:
    """클립 오디오 바이트. 접근 불가면 `None` — 예외를 던지지 않는다.

    **접근 불가가 세 형태로 실재한다**: ① 클립 행이 없다 ② `audio_filename` 이 null 이다(오디오를
    아직 만들지 않은 클립) ③ 포인터는 있고 파일이 없다(배포에서 자산이 빠졌다). 전부 404 로
    옮긴다 — `load_recording` 이 세운 규약과 같다.
    ⚠️ ①과 ②는 `fetchval` 이 둘 다 `None` 을 주어 **한 갈래로 수렴한다.**

    ⛔ **만료를 재지 않는다.** 제품 자산이라 「학습자의 당일이 지났다」가 없다 — `load_recording`
    과 갈라지는 자리이고, 여기에 만료를 더하면 배포된 자산이 시간에 따라 사라진다.

    ⚠️ **읽기가 동기 I/O 인 것은 의도다** — `load_recording` 이 같은 판단을 적어 두었다: 이 크기의
    파일(546KB · 17.36초)은 스레드로 넘기는 비용이 읽는 비용을 넘는다.
    """
    filename = await conn.fetchval(_SELECT_CLIP_AUDIO_FILENAME_SQL, item_id)
    if filename is None:
        return None
    path = clip_audio_path(root, item_id)
    if not path.is_file():
        return None
    return path.read_bytes()
