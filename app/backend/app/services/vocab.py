"""낱말 뜻 조회 (`TASK-194` · 캡틴 결정 130).

**스토리보드 §6 이 뺐던 것을 되살린 갈래다.** 그 근거는 *"외부 의존이 하나 더 늘고, 이 앱의 학습
목표는 말하기임"* 이었는데 「무엇에 의존하는가」를 적지 않았다 — 사전 API 를 전제한 것으로 읽히지만
**이 앱은 이미 Bedrock Claude 를 부르므로**(분석·계획·주간 요약) 그 경로로 얻으면 **새 외부 의존이
0건**이다. 남은 절반은 사전을 학습의 *주*로 삼지 말라는 뜻으로 읽었고, 보조는 막지 않는다.

⛔ **저장하지 않는다 — 표도 캐시도 만들지 않는다** (결정 130). 담는 단위를 늘리면 목록·동기화가
함께 늘어나고, 그것이 §6 이 「재생목록 담기」를 뺀 근거와 같다. 같은 낱말을 두 번 물으면 두 번
부른다 — 그 비용이 캐시의 복잡도보다 싸다(호출당 토큰이 작다).

⚠️ **모델을 목적으로 가르지 않았다** — `model_for_purpose` 가 `plan` 만 다른 모델을 쓰고 나머지는
`claude_model_id` 다. 낱말 한 줄에 그 모델이 과하지만, 값을 하나 더 두면 노브가 늘고 「누가 그 값을
정했나」가 다시 생긴다. 비용이 문제가 되면 그때 가른다(그 함수가 유일하게 고칠 자리다).
"""

from __future__ import annotations

from app.models.usage import PURPOSE_VOCAB
from app.workers.claude_client import ClaudeClient

# ⚠️ **문맥 문장을 함께 넣는 것이 이 프롬프트의 핵심이다** — 낱말만 주면 다의어에서 엉뚱한 뜻이
# 온다(`book` 이 「책」인지 「예약하다」인지는 문장이 정한다).
# ⛔ **한 문장을 요구하되 그것에 기대지 않는다** — 지키지 않을 수 있으므로 `lookup_word` 가 접는다.
_VOCAB_PROMPT = """다음 문장에 쓰인 낱말의 뜻을 한국어로 알려 줘.

문장: {sentence}
낱말: {word}

규칙:
- 이 문장에서 쓰인 뜻 하나만 말함. 다른 뜻은 적지 않음.
- 한 문장으로 20자 안팎으로 짧게 함.
- 사전 표제어 형식(품사 표시·발음기호·번호)을 쓰지 않음.
- 뜻을 알 수 없으면 빈 답을 돌려줌."""


def build_vocab_prompt(*, word: str, sentence: str) -> str:
    """낱말과 그 낱말이 있던 문장을 담은 프롬프트."""
    return _VOCAB_PROMPT.format(sentence=sentence, word=word)


async def lookup_word(claude: ClaudeClient, *, word: str, sentence: str) -> str | None:
    """낱말 뜻 한 줄. 모델이 아무것도 주지 않으면 `None`.

    ⛔ **빈 낱말로 모델을 부르지 않는다** — 돈을 쓰면서 뜻 없는 답을 받는다. 그래서 `ValueError` 를
    던진다(호출자가 400 으로 옮긴다).

    ⚠️ **여러 줄이 와도 한 줄로 접는다.** 프롬프트가 한 문장을 요구하지만 모델이 지킨다는 보장이
    없고, 화면은 한 줄을 그린다. 빈 응답을 빈 문자열로 내보내지 않는 것도 같은 이유다 — 화면이
    「뜻이 왔다」로 읽고 빈 줄을 그린다.
    """
    if not word.strip():
        raise ValueError("낱말이 비어 있다")
    prompt = build_vocab_prompt(word=word, sentence=sentence)
    raw = await claude.analyze(prompt, purpose=PURPOSE_VOCAB)
    meaning = " ".join(raw.split())
    return meaning or None
