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
from pathlib import Path
from uuid import UUID

import asyncpg

from app.audio_gateway.port import Transcriber
from app.services.recordings import load_recording

MATCH = "match"
MISSING = "missing"
DIFFERENT = "different"


@dataclass(frozen=True)
class ReadbackJudgment:
    """낭독 하나에 대한 판정. `words` 가 비면 **전사를 얻지 못했다**는 뜻이다(설계서 §4)."""

    clip_transcript: str
    readback_transcript: str
    words: list[WordVerdict]


_READBACK_ROW_SQL = """
select transcript, readback_transcript
  from utterances
 where id = $1 and session_id = $2 and utterance_type = 'shadowing_recording'
"""


async def judge_readback(
    pool: asyncpg.Pool,
    root: Path,
    session_id: UUID,
    utterance_id: UUID,
    *,
    transcribe: Transcriber,
) -> ReadbackJudgment | None:
    """낭독 하나를 클립의 글과 견준다. 접근할 수 없으면 `None` — 호출자가 404 로 옮긴다.

    ⛔ **아는 음성 계약이 `Transcriber` 하나다** (`TASK-214` · 결정 131). 「PCM 을 주면 읽은 글이
    온다」 밖의 것 — 어댑터를 어떻게 열고 침묵을 얼마나 붙이는지 — 은 `audio_gateway/transcribe.py`
    가 소유한다. 배치 STT 로 옮길 때 이 함수가 그대로 남는 것이 결정 131 이 약속한 경계다.

    ⛔ **요청할 때 계산하고 한 번만 계산한다** (결정 131). 전사가 이미 있으면 전사기를 아예 부르지
    않으므로 두 번째 조회에 비용이 0 이다.
    ⛔ **세션과 발화 종류가 «둘 다» 조회 조건이다.** 세션은 개인정보 경계이고
    (`api/shadowing.py` 머리말) 종류는 「견줄 원본이 있는가」다 — 일반 발화의 `transcript` 는
    클립의 글이 아니라 학습자의 말이라 견주면 뜻이 없는 판정이 나온다.
    ⚠️ 종류 필터는 **둘째 겹**이다 — `utterances_audio_only_for_shadowing` 이 낭독이 아닌 발화에
    포인터 자체를 못 붙이게 한다.
    ⛔ **빈 전사를 저장하지 않는다** — 저장하면 다시 눌러도 영원히 빈 판정이 돌아온다. 저장하지
    않으면 학습자가 다시 눌러 볼 수 있고, 그때 비용은 실패한 회수만큼만 난다.

    ⛔ **연결이 아니라 풀을 받는다** (`TASK-212`) — 전사는 최대 `_TIMEOUT_S` 초이고 그 안에서
    사용량 기록이 풀에서 연결을 또 잡는다. 연결을 잡은 채 그 구간을 타면 한 판정이 풀의 두 자리를
    30초 넘게 묶는다. 그래서 **읽기 → 반납 → 전사 → 다시 잡아 쓰기**로 나눈다.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_READBACK_ROW_SQL, utterance_id, session_id)
        if row is None:
            return None
        clip_transcript: str = row["transcript"]
        readback: str | None = row["readback_transcript"]
        pcm = (
            None
            if readback is not None
            else await load_recording(conn, root, session_id, utterance_id)
        )
    if readback is None:
        if pcm is None:
            return None
        readback = await transcribe(pcm)
        if not readback:
            return ReadbackJudgment(
                clip_transcript=clip_transcript, readback_transcript="", words=[]
            )
        async with pool.acquire() as conn:
            await conn.execute(
                "update utterances set readback_transcript = $2 where id = $1",
                utterance_id,
                readback,
            )
    return ReadbackJudgment(
        clip_transcript=clip_transcript,
        readback_transcript=readback,
        words=compare_readback(clip_transcript, readback),
    )


# 견줄 때만 쓰는 형태 — 대소문자와 문장부호 차이를 오류로 세지 않기 위해 지운다.
# ⚠️ 홑따옴표도 지운다: `Don't` 와 `dont` 는 같은 낱말을 읽은 것이고 전사기가 어느 쪽으로 낼지
#    우리가 정하지 못한다.
_NOT_WORD = re.compile(r"[^0-9a-z]+")


@dataclass(frozen=True)
class WordVerdict:
    """기대한 낱말 하나에 대한 판정. `word` 는 원본의 «원래 모양»이다(화면이 그것을 보인다)."""

    word: str
    verdict: str


def _words(text: str) -> list[tuple[str, str]]:
    """`(원래 모양, 견줄 형태)` 짝의 목록.

    부호만 있는 토큰(줄표·홑따옴표 따위)은 견줄 형태가 비므로 버린다 — 판정할 낱말이 아니다.
    ⚠️ **짝으로 돌려주는 것이 계약이다** — 두 리스트를 나란히 돌려주면 길이가 어긋날 자리가 생긴다.
    """
    pairs = ((token, _NOT_WORD.sub("", token.lower())) for token in text.split())
    return [(token, key) for token, key in pairs if key]


def compare_readback(expected: str, spoken: str) -> list[WordVerdict]:
    """클립의 글 `expected` 를 낭독 전사문 `spoken` 과 견주어 낱말마다 판정한다."""
    pairs = _words(expected)
    want = [key for _, key in pairs]
    got = [key for _, key in _words(spoken)]
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
        WordVerdict(word=token, verdict=verdict)
        for (token, _), verdict in zip(pairs, verdicts, strict=True)
    ]
