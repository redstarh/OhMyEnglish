"""튜터 발화의 한국어 번역 (`TASK-275` · 말풍선 [번역] 버튼).

⚠️ **`vocab` 과 달리 저장한다.** 낱말 조회는 결정 130 이 캐시를 뺐지만 그 근거는 「담는 단위가 늘면
목록·동기화가 따라온다」였다. 번역은 **이미 있는 발화 행 한 칸**에 매이므로 새 단위가 생기지 않고,
같은 말풍선을 여러 번 눌러도 모델은 한 번만 부른다(032 머리말).

⚠️ **모델을 목적으로 가르지 않았다** — `vocab` 과 같은 판단이다(`model_for_purpose` 가 유일한 자리).
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.models.usage import PURPOSE_TRANSLATION
from app.workers.claude_client import ClaudeClient

_TRANSLATION_PROMPT = """다음은 영어 말하기 코치가 한국인 학습자에게 한 말임.
자연스러운 한국어로 옮겨 줘.

문장: {sentence}

규칙:
- 번역문만 돌려줌. 설명·원문·따옴표를 붙이지 않음.
- 코치의 말투는 친절한 존댓말로 옮김."""

_SELECT_UTTERANCE_SQL = """
select transcript, translation_ko
  from utterances
 where session_id = $1 and sequence_no = $2 and speaker = 'agent'
"""

_SET_TRANSLATION_SQL = """
update utterances
   set translation_ko = $3
 where session_id = $1 and sequence_no = $2
"""


class UtteranceNotFoundError(LookupError):
    """그 세션에 그 순번의 «튜터» 발화가 없다.

    ⛔ 학습자 발화는 없는 것으로 친다 — 프롬프트가 「코치가 한 말」이라고 말하므로 학습자 문장을
    넣으면 뜻이 틀어지고, 화면에 버튼이 없는 요청으로 모델 비용이 나간다(`TASK-275` 리뷰).
    """


def build_translation_prompt(sentence: str) -> str:
    return _TRANSLATION_PROMPT.format(sentence=sentence)


async def translate_to_korean(claude: ClaudeClient, sentence: str) -> str | None:
    """영어 한 문장의 한국어 번역. 모델이 아무것도 주지 않으면 `None`.

    ⛔ **빈 문장으로 모델을 부르지 않는다** — 돈을 쓰면서 빈 답을 받는다(`ValueError`).
    ⚠️ 여러 줄이 와도 한 줄로 접는다 — 화면은 말풍선 안에 한 단락을 그린다.
    """
    if not sentence.strip():
        raise ValueError("번역할 문장이 비어 있다")
    raw = await claude.analyze(build_translation_prompt(sentence), purpose=PURPOSE_TRANSLATION)
    translation = " ".join(raw.split())
    return translation or None


async def translate_utterance(
    pool: asyncpg.Pool, claude: ClaudeClient, *, session_id: UUID, sequence_no: int
) -> str | None:
    """발화 하나의 번역. 저장된 것이 있으면 그것을, 없으면 만들어 저장한 뒤 돌려준다.

    ⛔ **모델 호출 동안 커넥션을 잡지 않는다** — 호출이 수 초 걸리고 풀은 음성 세션과 공유한다.
    ⚠️ 두 요청이 동시에 오면 둘 다 모델을 부를 수 있다 — 결과는 같은 칸에 덮이고 비용이 한 번 더
    나갈 뿐이라 잠금을 두지 않았다.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_SELECT_UTTERANCE_SQL, session_id, sequence_no)
    if row is None:
        raise UtteranceNotFoundError(f"{session_id}#{sequence_no}")
    if row["translation_ko"] is not None:
        return row["translation_ko"]
    translation = await translate_to_korean(claude, row["transcript"])
    if translation is None:
        return None
    async with pool.acquire() as conn:
        await conn.execute(_SET_TRANSLATION_SQL, session_id, sequence_no, translation)
    return translation
