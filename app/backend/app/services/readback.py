"""낭독 전사문을 클립의 글과 견준다 — 낭독 판정의 계산 (`TASK-207`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4.

⛔ **모델을 부르지 않는다.** 「원본대로 읽었는가」는 낱말 일치로 답이 정해지므로 모델 판단이 필요
없고, 순수 함수라 같은 입력에 같은 답이 난다 — 화면 안내가 그 성질에 걸린다.

⚠️ **판정은 「기대한」 낱말마다 난다.** 학습자가 없는 낱말을 «더» 말한 경우(`insert`)는 판정할 기대
낱말이 없어 세지 않는다 — 값역이 셋(맞음·빠짐·다름)이고 넷째 갈래를 넣으려면 값역부터 넓힌다.

⚠️ **알려진 한계 — 되풀이가 심한 글에서는 정렬이 모호하다.** 같은 문장을 서른 번 이어 붙인
270낱말 입력에서 낱말 하나를 빼면 `difflib` 이 «똑같이 긴 다른 정렬»을 골라 99낱말을 빠짐으로
낸다(2026-09-18 직접 관측). 쉐도잉 클립은 한 문장이므로 이 형태가 실제로 오지 않아 받아들였다 —
긴 글을 판정 대상으로 넓히려면 정렬을 문장 단위로 먼저 자르는 것이 선행한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

MATCH = "match"
MISSING = "missing"
DIFFERENT = "different"

# 견줄 때만 쓰는 형태 — 대소문자와 문장부호 차이를 오류로 세지 않기 위해 지운다.
# ⚠️ 홑따옴표도 지운다: `Don't` 와 `dont` 는 같은 낱말을 읽은 것이고 전사기가 어느 쪽으로 낼지
#    우리가 정하지 못한다.
_NOT_WORD = re.compile(r"[^0-9a-z]+")


@dataclass(frozen=True)
class WordVerdict:
    """기대한 낱말 하나에 대한 판정. `word` 는 원본의 «원래 모양»이다(화면이 그것을 보인다)."""

    word: str
    verdict: str


def _words(text: str) -> tuple[list[str], list[str]]:
    """원래 모양과 견줄 형태를 같은 순서로 짝지어 돌려준다.

    부호만 있는 토큰(줄표·홑따옴표 따위)은 견줄 형태가 비므로 버린다 — 판정할 낱말이 아니다.
    """
    originals: list[str] = []
    normalized: list[str] = []
    for token in text.split():
        key = _NOT_WORD.sub("", token.lower())
        if not key:
            continue
        originals.append(token)
        normalized.append(key)
    return originals, normalized


def compare_readback(expected: str, spoken: str) -> list[WordVerdict]:
    """클립의 글 `expected` 를 낭독 전사문 `spoken` 과 견주어 낱말마다 판정한다."""
    originals, want = _words(expected)
    _, got = _words(spoken)
    # 기본값이 「빠짐」이다 — `delete` 갈래와 낭독이 아예 빈 경우가 그대로 여기에 남는다.
    verdicts = [MISSING] * len(want)
    # ⛔ `autojunk=False` 를 명시한다 — 기본값은 b 가 200 항목을 넘으면 «자주 나오는 항목»을
    #    자동으로 버려서 긴 전사문에서 판정이 길이에 따라 달라진다(같은 입력에 같은 답이라는
    #    성질이 깨진다).
    matcher = SequenceMatcher(a=want, b=got, autojunk=False)
    for tag, start, stop, _b_start, _b_stop in matcher.get_opcodes():
        if tag == "equal":
            fill = MATCH
        elif tag == "replace":
            fill = DIFFERENT
        else:
            continue
        for index in range(start, stop):
            verdicts[index] = fill
    return [
        WordVerdict(word=word, verdict=verdict)
        for word, verdict in zip(originals, verdicts, strict=True)
    ]
