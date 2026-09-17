"""붙여넣은 YouTube 링크에서 영상 식별자를 뽑는다 (`TASK-163`).

설계: `docs/design/2026-09-18-video-learning-design.md` §4.

⛔ **`conn` 을 받지 않는 유일한 서비스 모듈이다.** `services/videos.py` 에 섞지 않는 이유는 그
파일의 테스트가 「DB 를 쓰는 것」과 「안 쓰는 것」을 함께 담게 되기 때문이다 — 배치 관례가
`tests/unit/test_<모듈>.py` 1:1 이라 모듈을 갈라 두면 짝이 맞는다.

⛔ **파싱을 프런트에 두지 않는 이유**: 프런트에는 테스트 러너가 없다(`TASK-159` 6항). 그리고 규칙이
두 곳에 있으면 갈라진다 — 프런트는 URL 을 **그대로** 넘기고 뽑지 않는다.

⚠️ **11자 검사가 여기와 027 의 `youtube_videos_youtube_id_shape` 양쪽에 있는 것은 중복이 아니다.**
이 값이 URL 조립에 쓰이므로(`i.ytimg.com/vi/<id>/hqdefault.jpg` · `watch?v=<id>`) 임의 문자열이
들어오면 화면이 만드는 URL 이 우리 통제 밖으로 나간다. 값역이 한 겹, 이 함수가 다른 겹이다 —
`services/clip_audio.clip_audio_path` 가 경로 조립에서 같은 판단을 적어 두었다.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

# ⛔ **호스트를 정확히 일치로 검사한다.** 부분 문자열로 보면 `youtube.com.attacker.test` 가
# 통과하고, 그 순간 이 함수가 「아무 URL 에서 11자 조각을 뽑는 함수」가 된다.
_ALLOWED_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})

# YouTube 영상 식별자는 11자이고 알파벳은 URL-safe base64 다.
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{11}$")

# `/shorts/<id>` · `/embed/<id>` 처럼 **경로의 둘째 조각**이 식별자인 형태.
_PATH_PREFIXES = frozenset({"shorts", "embed"})


def parse_youtube_id(url: str) -> str | None:
    """링크에서 영상 식별자를 뽑는다. 뽑지 못하면 `None` — 예외를 던지지 않는다.

    받는 형태 넷: `watch?v=` · `youtu.be/` · `shorts/` · `embed/`. 질의 문자열이 더 붙어도(`&t=42s`)
    영향받지 않는다 — 사용자가 「현재 시각부터」로 복사하면 그것이 붙는다.

    ⚠️ **스킴이 없어도 받는다.** 손으로 옮겨 적으면 `www.youtube.com/watch?v=...` 가 되는데, 그것을
    거부하면 사용자가 이유를 알 수 없다. 스킴을 붙여 파싱하되 **호스트 검사는 그대로 거친다.**

    ⛔ **맨 식별자만 준 것은 거부한다**(`dQw4w9WgXcQ`). 관대하게 받으면 「검색어를 붙여넣었다」와
    구분되지 않는다 — 이 함수의 계약은 「링크에서 뽑는 것」이다.
    """
    text = url.strip()
    if not text:
        return None

    # `//` 가 없으면 스킴이 없는 것으로 본다. `urlparse` 는 스킴 없는 문자열의 호스트를 경로로 읽어
    # `hostname` 이 `None` 이 되므로, 붙여 주지 않으면 호스트 검사가 통과할 길이 아예 없다.
    if "//" not in text:
        text = f"https://{text}"

    parsed = urlparse(text)
    if parsed.hostname is None or parsed.hostname not in _ALLOWED_HOSTS:
        return None

    segments = [segment for segment in parsed.path.split("/") if segment]

    if parsed.hostname == "youtu.be":
        candidate = segments[0] if segments else None
    elif segments and segments[0] in _PATH_PREFIXES:
        candidate = segments[1] if len(segments) > 1 else None
    else:
        # `watch?v=` 형태. ⚠️ `parse_qs` 는 값이 여러 개일 수 있어 리스트를 준다 — 첫 값을 쓴다.
        values = parse_qs(parsed.query).get("v", [])
        candidate = values[0] if values else None

    if candidate is None or not _IDENTIFIER.match(candidate):
        return None
    return candidate
