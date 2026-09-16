#!/usr/bin/env python3
"""`TASK-143` — analysis 프롬프트를 두 모델로 재는 **그림자 평가**. 제품을 바꾸지 않는다.

⛔ 문턱은 이 스크립트를 돌리기 «전에» 태스크에 적혔다(결정 50 1항의 교훈).
프롬프트는 제품의 `build_prompt` 가 만들고 판정은 제품의 `parse_analysis` 가 한다 —
평가자가 자기 기준을 발명하지 않는 것이 이 회차의 규율이다.

    cd app/backend && ./.venv/bin/python \
      ../../tests/harness/runs/2026-09-16-task143-analysis-shadow/p_analysis_shadow.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/app/backend")

from app.config import bedrock_client, get_settings  # noqa: E402
from app.models.analysis import AnalysisValidationError, parse_analysis  # noqa: E402
from app.services.analysis import build_prompt  # noqa: E402
from app.workers.claude_client import (  # noqa: E402
    body_for,
    extract_text,
    extract_usage,
    invoke_openai_model,
    is_openai_model,
)

OPUS = "us.anthropic.claude-opus-5"
TERRA = "us.openai.gpt-5.6-terra"

# 입력 정본은 `tests/harness/inject_errors.py` 의 세 묶음이다 — 그 파일이 카테고리를 노려 만든
# 문장이고, 같은 파일이 ⚠️ **어느 카테고리가 나올지는 비결정적**이라고 적어 두었다. 그래서
# 「카테고리가 정답과 같은가」를 재지 않고 **검출 여부와 오탐**을 잰다.
ERROR_SENTENCES = [
    "Yesterday I go to the client meeting and present the project status.",
    "I will discuss about the deployment risk with my manager on next week.",
    "I know not why the migration failed during the last release.",
    "The team have finish the integration test already.",
    "I usually go to gym before the daily standup meeting.",
    "I go to office by subway every morning.",
    "She go to gym after work on Tuesday.",
    "We go to airport by taxi tomorrow.",
]
CLEAN_SENTENCES = [
    "I went to the gym after work yesterday.",
    "She usually takes the subway to the office.",
    "We need to finish the migration before the release.",
]


def _call(model_id: str, prompt: str, settings) -> tuple[dict, str]:  # noqa: ANN001
    body = body_for(model_id, prompt)
    started = time.monotonic()
    if is_openai_model(model_id):
        payload = invoke_openai_model(
            model_id,
            body,
            region=settings.aws_region,
            token=settings.aws_bearer_token_bedrock,
        )
    else:
        response = bedrock_client().invoke_model(modelId=model_id, body=body)
        payload = json.loads(response["body"].read())
    elapsed_ms = int((time.monotonic() - started) * 1000)
    usage = extract_usage(payload)
    row: dict = {"elapsed_ms": elapsed_ms}
    if usage is not None:
        row["input_tokens"] = usage.input_tokens
        row["output_tokens"] = usage.output_tokens
    try:
        raw = extract_text(payload)
    except AnalysisValidationError as exc:
        row.update(schema_ok=False, reason=f"extract: {exc}", findings=None)
        return row, ""
    try:
        result = parse_analysis(raw)
    except AnalysisValidationError as exc:
        row.update(schema_ok=False, reason=f"parse: {exc}", findings=None)
        return row, raw
    row.update(
        schema_ok=True,
        reason=None,
        findings=len(result.findings),
        categories=sorted({f.category for f in result.findings}),
    )
    return row, raw


def main() -> None:
    settings = get_settings()
    out_dir = Path(__file__).parent
    (out_dir / "raw").mkdir(exist_ok=True)
    rows: list[dict] = []

    for kind, sentences in (("error", ERROR_SENTENCES), ("clean", CLEAN_SENTENCES)):
        for index, sentence in enumerate(sentences, start=1):
            prompt = build_prompt(sentence, [])
            for model_id in (OPUS, TERRA):
                arm = "opus5" if model_id == OPUS else "terra"
                row, raw = _call(model_id, prompt, settings)
                row.update(kind=kind, arm=arm, sentence=sentence)
                rows.append(row)
                (out_dir / "raw" / f"{arm}-{kind}{index}.txt").write_text(raw, encoding="utf-8")
                print(
                    f"{arm:<6} {kind}{index} schema_ok={row['schema_ok']} "
                    f"findings={row.get('findings')} {row['elapsed_ms']}ms"
                )

    summary = {}
    for arm in ("opus5", "terra"):
        mine = [r for r in rows if r["arm"] == arm]
        errors = [r for r in mine if r["kind"] == "error"]
        cleans = [r for r in mine if r["kind"] == "clean"]
        passed = [r for r in mine if r["schema_ok"]]
        summary[arm] = {
            "calls": len(mine),
            "schema_pass": len(passed),
            "schema_pass_pct": round(100 * len(passed) / len(mine), 1),
            "detected_on_error_sentences": sum(1 for r in errors if (r.get("findings") or 0) >= 1),
            "false_positive_on_clean": sum(1 for r in cleans if (r.get("findings") or 0) >= 1),
            "median_ms": sorted(r["elapsed_ms"] for r in mine)[len(mine) // 2],
            "input_tokens_total": sum(r.get("input_tokens", 0) for r in mine),
            "output_tokens_total": sum(r.get("output_tokens", 0) for r in mine),
        }

    (out_dir / "results.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
