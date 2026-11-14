"""문법 코스 565문장의 한국어 번역을 한 번 만들어 콘텐츠 옆 파일에 둔다 (`TASK-328`).

사용: (app/backend 에서) .venv/bin/python ../../scripts/translate_grammar_course.py
결과: app/backend/app/content/grammar_basic_ko.json — {문장 키: 번역}.
이미 있는 키는 다시 만들지 않는다.

⛔ 열 때마다 번역하지 않는다(2026-11-14 사용자 결정) — 미리 만들어 검수하고 파일로 둔다.
⛔ 분석 워커와 같은 Claude 경로(`BedrockClaudeClient`)를 쓴다.
   자격증명·모델 판정을 둘로 만들지 않는다.
⚠️ 번역 규칙은 학습자 프로필(h-doc)에 맞춘 것이고 해요체 통일은 이 스크립트가 정한 값이다.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from app.config import get_settings
from app.models.analysis import AnalysisValidationError
from app.models.course import load_course, sentence_key
from app.workers.claude_client import BedrockClaudeClient

OUT = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "backend"
    / "app"
    / "content"
    / "grammar_basic_ko.json"
)
HANGUL = re.compile(r"[가-힣]")
RETRIES = 2

# ⚠️ 2026-11-14 실측: Day 단위 · 기술 낱말 예시를 넣은 프롬프트에서
#    평범한 단원도 refusal(cyber)로 거절됐음. 단원 단위로 나누고 기술 예시를 뺐음.
#    원인은 추정이고, 남는 거절은 모델을 바꿔 다시 만듦(CLAUDE_MODEL_ID).
PROMPT = """These are everyday speaking-practice sentences from a grammar course in an
English-learning app. Translate them into Korean so a Korean adult learner (beginner to
lower-intermediate) can see what each sentence means while practicing.

Rules:
- Translate each sentence into natural, short Korean that keeps the meaning close to the
  English, so the learner can match the words.
- Do not add explanations, notes, romanization or alternatives.
- Use polite informal Korean (해요체) consistently, e.g. "저는 소프트웨어 테스터예요."
- Write place and person names in Korean (서울, 부산, 한강, 미나).
  Keep brand and product names in English.
- Use the loanwords Korean offices actually say instead of forced native words.
- Keep the tense and question/negative form of the English.

Return only a JSON object mapping each key to its Korean translation, with exactly these keys.

Sentences:
{items}
"""


def parse_json_object(text: str) -> dict[str, str]:
    """응답에서 JSON 객체 하나를 꺼낸다 — 코드 울타리를 두르고 와도 받는다."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in response")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("response is not an object")
    return {str(key): str(value).strip() for key, value in data.items()}


def problems(batch: dict[str, str], got: dict[str, str]) -> list[str]:
    """받은 번역의 결함 — 빠진 키 · 남는 키 · 한글이 없는 값."""
    out = [f"missing {key}" for key in batch if key not in got]
    out += [f"extra {key}" for key in got if key not in batch]
    out += [
        f"no hangul {key}"
        for key, value in got.items()
        if key in batch and not HANGUL.search(value)
    ]
    return out


async def translate_batch(client: BedrockClaudeClient, batch: dict[str, str]) -> dict[str, str]:
    items = "\n".join(f"{key}: {text}" for key, text in batch.items())
    last: list[str] = []
    for attempt in range(1 + RETRIES):
        try:
            got = parse_json_object(await client.analyze(PROMPT.format(items=items)))
        except (AnalysisValidationError, ValueError) as exc:
            # ⛔ JSON 이 아닌 응답(`ValueError`)도 다시 묻는다(`TASK-331` codex 리뷰 ③).
            #    예전에는 한 번에 생성기 전체가 멈췄다. `AnalysisValidationError` 는
            #    `ValueError` 의 하위지만 뜻을 보이려 둘 다 적는다.
            # ⚠️ 2026-11-14 실측: Day 하나(약 95문장)를 한 번에 보내자
            #    `refusal(cyber)` 로 거절됐음 — 분류기 오판으로 봄(추정).
            #    그래서 단원 단위로 보내고 거절은 다시 묻는다.
            last = [f"{type(exc).__name__}: {exc}"]
            print(f"  다시 요청 {attempt + 1}: {last}", file=sys.stderr)
            continue
        last = problems(batch, got)
        if not last:
            return {key: got[key] for key in batch}
        print(f"  다시 요청 {attempt + 1}: {last[:5]}", file=sys.stderr)
    raise RuntimeError(f"번역 결함이 남음: {last[:10]}")


async def main() -> None:
    course = load_course()
    done: dict[str, str] = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    client = BedrockClaudeClient(get_settings())
    skipped: list[int] = []
    for unit in (item for day in course.days for item in day.units):
        batch = {
            sentence_key(unit.unit, index): text
            for index, text in enumerate(unit.sentences)
            if sentence_key(unit.unit, index) not in done
        }
        if not batch:
            continue
        try:
            done.update(await translate_batch(client, batch))
        except RuntimeError as exc:
            # 끝내 못 만든 단원은 건너뛰고 남긴다 — 다시 실행하면 그 단원만 다시 만든다.
            print(f"Unit {unit.unit} 건너뜀: {exc}", file=sys.stderr)
            skipped.append(unit.unit)
            continue
        # 단원마다 적는다 — 중간에 끊겨도 다음 실행이 남은 단원만 만든다.
        ordered = {key: done[key] for key in sorted(done)}
        OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"모두 {len(done)} 문장 → {OUT} · 건너뛴 단원 {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
