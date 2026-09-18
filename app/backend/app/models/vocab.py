"""낱말 뜻 조회의 들어오는 값 (`TASK-194` · 캡틴 결정 130).

⚠️ **`models/video.py` 와 같은 자리에 두는 이유**: 그 파일이 *"이 파일은 **들어오는 값**만 다룬다"*
로 규약을 세웠고 `VideoCreateRequest`·`PhraseCreateRequest` 가 여기 산다. 라우터 안에 두면 요청
모델의 자리가 두 곳으로 갈린다.

⛔ **응답 모델을 만들지 않는다** — 이 리포의 라우터는 `dict[str, object]` 를 돌려주고
(`api/videos.py` 의 `_..._payload` 들), `response_model=` 을 쓰는 자리가 0곳이다. 한 필드 응답에
클래스를 만들면 그 관행에서 혼자 갈라진다.
"""

from __future__ import annotations

import pydantic


class VocabLookupRequest(pydantic.BaseModel):
    """조회할 낱말과 그 낱말이 있던 문장.

    ⚠️ **문장이 필수인 것이 이 기능의 계약이다** — 낱말만으로는 다의어를 가릴 수 없다
    (`services/vocab.py` 가 근거를 가진다).
    ⚠️ 길이 상한은 **모델 호출 비용의 상한**이다 — 문장 하나를 넘는 입력을 받지 않는다.
    """

    word: str = pydantic.Field(min_length=1, max_length=80)
    sentence: str = pydantic.Field(min_length=1, max_length=600)
