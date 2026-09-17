"""영상 학습의 요청 몸통 값역 (`TASK-165`).

설계: `docs/design/2026-09-18-video-learning-design.md` §3.

⛔ **이 리포의 첫 쓰기 REST 표면이다.** 기존 엔드포인트 일곱은 전부 `GET` 이고 쓰기는 WebSocket
으로만 일어났다(2026-09-18 실측). 그래서 「요청 몸통을 어떻게 검증하나」의 선례가 없고,
`models/plan.py` 가 **모델이 준 JSON** 을 `BaseModel` 로 가두는 방식을 그대로 가져온다 — 밖에서 온
값을 값역으로 막는 자리가 같기 때문이다.

⚠️ **조회 결과 DTO 는 여기 두지 않는다** — 그것은 `services/videos.py` 가 갖는다
(`services/recordings.py` 의 `ShadowingClip` 선례). 이 파일은 **들어오는 값**만 다룬다.
"""

from __future__ import annotations

from decimal import Decimal

import pydantic

# 표시용 문자열의 상한. 제목·채널명은 화면 카드 한 줄에 들어가는 값이다.
TEXT_MAX_LENGTH = 200

# 담는 문장의 상한. 구간이 90초까지이므로 한 사람이 그 안에 말할 수 있는 분량을 넉넉히 덮는다.
TRANSCRIPT_MAX_LENGTH = 1000

# ⛔ **정본은 스키마의 `shadowing_items_span_within_limit` 이다.** 여기 같은 값을 두는 이유는
# 사용자에게 **문구를 주기 위한 것**이고, 두 곳이 갈리면 사용자는 통과했다고 보는데 DB 가 거부한다.
# ⚠️ 그래서 `tests/unit/test_schema.py` 가 두 값을 **대조한다** — 갈라지면 red 가 된다.
CLIP_MAX_SPAN_SECONDS = Decimal(90)


class VideoCreateRequest(pydantic.BaseModel):
    """영상을 담거나 이미 담은 것의 메타데이터를 갱신하는 요청.

    ⛔ **`url` 을 그대로 받고 식별자를 프런트에서 받지 않는다** — 파싱은 서버의 일이고
    (`services/video_url.parse_youtube_id`) 규칙이 두 곳에 있으면 갈라진다.
    ⚠️ **제목·채널은 프런트가 oEmbed 에서 받아 넘긴다.** 백엔드가 그 값을 믿는 대가를 설계서 §0 이
    적었다 — 단일 사용자 앱이고 표시용 라벨이라 받아들이되, **길이와 공백은 여기서 가둔다.**
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = pydantic.Field(min_length=1)
    title: str = pydantic.Field(min_length=1, max_length=TEXT_MAX_LENGTH)
    channel_name: str = pydantic.Field(min_length=1, max_length=TEXT_MAX_LENGTH)


class PhraseCreateRequest(pydantic.BaseModel):
    """영상의 한 구간과 그 구간에서 들은 문장.

    ⚠️ **정밀도를 여기서 접지 않는다** — 반올림은 `services/videos.add_phrase` 가 한다. 이 자리는
    「받을 수 있는 값인가」만 판정하고, 저장 형태는 서비스가 정한다.

    ⚠️ **이름을 `clip_start_sec`·`clip_end_sec` 로 둔 것은 선례다** — 프런트가 쉐도잉에서 이미 그
    이름을 받고 있다(`ShadowingTurns.as_event_payload`). 요청과 응답에서 다른 이름을 쓰면 화면이
    같은 값을 두 이름으로 다루게 된다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    transcript: str = pydantic.Field(min_length=1, max_length=TRANSCRIPT_MAX_LENGTH)
    clip_start_sec: Decimal = pydantic.Field(ge=0)
    clip_end_sec: Decimal = pydantic.Field(ge=0)

    @pydantic.model_validator(mode="after")
    def _span_is_ordered_and_bounded(self) -> PhraseCreateRequest:
        """구간의 순서와 길이를 판정한다 — 스키마 CHECK 둘과 같은 판정을 사용자 쪽에서 먼저 한다.

        ⛔ **여기서 막는 이유는 문구다.** 스키마가 거부하면 사용자는 `500` 에 가까운 실패를 보고,
        여기서 막으면 「구간 끝이 시작보다 뒤여야 해요」를 본다(설계서 §7).
        """
        if self.clip_end_sec <= self.clip_start_sec:
            raise ValueError("clip_end_sec must be greater than clip_start_sec")
        if self.clip_end_sec - self.clip_start_sec > CLIP_MAX_SPAN_SECONDS:
            raise ValueError(f"clip span must not exceed {CLIP_MAX_SPAN_SECONDS} seconds")
        return self
