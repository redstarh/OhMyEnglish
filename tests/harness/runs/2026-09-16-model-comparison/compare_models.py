#!/usr/bin/env python3
"""TASK-141 — 학습 추천(다음 세션 계획) 모델 후보를 같은 입력으로 재고 기계 판정한다.

⛔ **입력은 실물이다.** 개발 DB 의 진짜 사용자 재료를 `load_plan_input` 으로 읽고
`build_plan_prompt` 로 조립한다 — 프롬프트를 이 파일에서 만들지 않는다. DB 는 SELECT 만 한다.

⛔ **판정은 제품의 검증 함수가 한다.** `parse_plan` 이 스키마·초점 출처·가장 깊은 재발·CEFR
한 단계 규칙을 전부 소유하므로 눈대중 점수를 만들지 않는다. 그 위에 얹는 관찰값 넷
(한국어 `reason` · 질문 수 · 초점 수 · 질문 상황의 중복)은 **거부 사유가 아니라 서술**이다.

**호출 경로가 둘인 이유**: openai 계열은 앱의 현재 본문(`anthropic_version`)을
`unknown_parameter` 로 거부한다(`probe_body_format.json`). 네 모델이 모두 받는 유일한 모양이
Converse 이므로 **비교는 Converse 로 통일**하고, 앱의 실제 경로(InvokeModel + Anthropic 본문)는
`us.anthropic.claude-opus-5` 한 팔로 따로 재서 Converse 가 기준선을 왜곡하지 않는지 본다.

**자격증명**: 앱의 SigV4 IAM 사용자는 `us.anthropic.claude-opus-5` 에만 권한이 있어 후보 셋이
`AccessDeniedException` 이다(실측). 그래서 측정은 bearer 경로로 붙는다 — 값은 남기지 않는다.

**차수 배치**: 팔을 한 번에 5회 몰지 않고 회차마다 팔을 돌린다. 몰면 그 팔의 지연에 시각대
변동이 통째로 실린다. 예열 1회는 회차에 넣지 않고 따로 적는다.
"""

import asyncio
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/app/backend")

import boto3  # noqa: E402

from app.config import bedrock_boto_config, get_settings  # noqa: E402
from app.db import close_pool, pool  # noqa: E402
from app.models.plan import parse_plan  # noqa: E402
from app.services.chronic import deepest_recurrence  # noqa: E402
from app.services.plan import build_plan_prompt  # noqa: E402
from app.services.plan_input import load_plan_input  # noqa: E402
from app.workers.claude_client import MAX_TOKENS, build_invoke_body, extract_text  # noqa: E402

HERE = Path(__file__).parent
RAW = HERE / "raw"
# AC#3 의 하한. 늘리지 않는다 — Opus 호출은 돈이 나간다. `ROUNDS=1` 은 배선 확인용이고
# 그 실행의 수치는 보고서에 쓰지 않는다.
ROUNDS = int(os.environ.get("ROUNDS", "5"))

# (팔 이름, 모델 ID, 호출 경로)
ARMS = [
    ("opus5-converse", "us.anthropic.claude-opus-5", "converse"),
    ("sonnet5-converse", "us.anthropic.claude-sonnet-5", "converse"),
    ("luna-converse", "us.openai.gpt-5.6-luna", "converse"),
    ("terra-converse", "us.openai.gpt-5.6-terra", "converse"),
    # 앱이 지금 실제로 쓰는 경로. 기준선이 Converse 때문에 움직이지 않는지 대조한다.
    ("opus5-app-invoke", "us.anthropic.claude-opus-5", "invoke_anthropic"),
]

_HANGUL = re.compile(r"[가-힣]")


def measuring_client(region: str):
    """bearer 토큰만으로 붙는 `bedrock-runtime` 클라이언트 (`probe_body_format.py` 와 같은 이유)."""
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        os.environ.pop(key, None)
    if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        raise SystemExit("AWS_BEARER_TOKEN_BEDROCK 이 셸 환경에 없다 — 측정 경로가 붙지 않는다")
    return boto3.client("bedrock-runtime", region_name=region, config=bedrock_boto_config())


def call(client, model_id: str, route: str, prompt: str) -> dict:
    """1회 호출. 벽시계 지연·Bedrock 보고 지연·토큰·종료사유·본문을 함께 돌려준다."""
    started = time.perf_counter()
    if route == "converse":
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": MAX_TOKENS},
        )
        wall_ms = (time.perf_counter() - started) * 1000
        blocks = response["output"]["message"].get("content") or []
        text = "".join(b.get("text", "") for b in blocks if "text" in b)
        usage = response.get("usage") or {}
        return {
            "wall_ms": round(wall_ms, 1),
            "bedrock_latency_ms": (response.get("metrics") or {}).get("latencyMs"),
            "input_tokens": usage.get("inputTokens"),
            "output_tokens": usage.get("outputTokens"),
            "usage_raw": usage,
            "stop_reason": response.get("stopReason"),
            "text": text,
        }
    if route == "invoke_anthropic":
        response = client.invoke_model(modelId=model_id, body=build_invoke_body(prompt))
        payload = json.loads(response["body"].read())
        wall_ms = (time.perf_counter() - started) * 1000
        usage = payload.get("usage") or {}
        # ⛔ `extract_text` 를 쓴다 — 앱이 실제로 쓰는 추출기다. 여기서 따로 만들면 앱이
        # 버리는 응답을 통과로 셀 수 있다.
        return {
            "wall_ms": round(wall_ms, 1),
            "bedrock_latency_ms": None,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "usage_raw": usage,
            "stop_reason": payload.get("stop_reason"),
            "text": extract_text(payload),
        }
    raise ValueError(route)


def observe(raw: str) -> dict:
    """거부 사유가 아닌 서술값. 통과한 응답끼리 견주는 데 쓴다."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    questions = payload.get("questions") or []
    contexts = [q.get("context") for q in questions if isinstance(q, dict)]
    reason = payload.get("reason") or ""
    return {
        "focus_n": len(payload.get("focus") or []),
        "questions_n": len(questions),
        "distinct_contexts": len({c for c in contexts if c}),
        "notes_n": len(payload.get("notes") or []),
        "reason_korean": bool(_HANGUL.search(reason)),
        "reason_chars": len(reason),
        "level_action": (payload.get("level") or {}).get("action"),
        "instruction_contexts_n": len((payload.get("instruction") or {}).get("contexts") or []),
    }


def classify(verdict: str) -> str:
    if verdict == "통과":
        return "통과"
    if "Extra inputs are not permitted" in verdict:
        return "여분키"
    if "is not valid JSON" in verdict or "not JSON" in verdict:
        return "JSON아님"
    if "failed validation" in verdict:
        return "스키마"
    return "그외"


async def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    conn_pool = await pool()
    async with conn_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "select ls.user_id from session_plans sp "
            "join learning_sessions ls on ls.id = sp.session_id "
            "order by sp.created_at desc limit 1"
        )
        if user_id is None:
            raise SystemExit("계획이 붙은 세션이 없다 — 이 비교는 제품 재료 위에 선다")
        data = await load_plan_input(conn, user_id)
    await close_pool()

    deepest = deepest_recurrence(data.chronic)
    prompt = build_plan_prompt(data)
    allowed = {r.pattern_id for r in data.due_reviews} | {m.pattern_id for m in data.chronic}
    (HERE / "prompt_plan.txt").write_text(prompt, encoding="utf-8")
    print(
        f"=== 재료 user={user_id} 복습예정={len(data.due_reviews)} 만성={len(data.chronic)} "
        f"발화={len(data.recent)} 프롬프트={len(prompt)}자 허용id={len(allowed)} "
        f"현재레벨={data.current_level} "
        f"최다재발={'없음' if deepest is None else deepest.pattern_key}"
    )
    print(f"=== 앱 설정 모델 ID = {settings.claude_model_id} · region={settings.aws_region}")

    client = measuring_client(settings.aws_region)
    rows: list[dict] = []

    def one(arm: str, model_id: str, route: str, label: str) -> dict:
        row: dict = {"arm": arm, "model_id": model_id, "route": route, "round": label}
        try:
            got = call(client, model_id, route, prompt)
        except Exception as exc:  # noqa: BLE001 — 호출 실패도 결과다
            row["error"] = f"{type(exc).__name__}: {exc}"[:400]
            row["kind"] = "호출실패"
            print(f"  {arm} {label} 호출실패 {row['error'][:120]}")
            return row
        text = got.pop("text")
        row.update(got)
        row["text_chars"] = len(text)
        (RAW / f"{arm}_{label}.txt").write_text(text, encoding="utf-8")
        verdict = "통과"
        try:
            parse_plan(
                text,
                current_level=data.current_level,
                allowed_pattern_ids=allowed,
                deepest_pattern_id=None if deepest is None else deepest.pattern_id,
            )
        except Exception as exc:  # noqa: BLE001
            verdict = f"{type(exc).__name__}: {exc}"
        row["verdict"] = verdict
        row["kind"] = classify(verdict)
        row["observed"] = observe(text)
        print(
            f"  {arm} {label} {row['kind']} wall={row['wall_ms']}ms "
            f"out_tok={row['output_tokens']} {'' if verdict == '통과' else verdict[:110]}"
        )
        return row

    print("=== 예열 (회차에 넣지 않는다)")
    for arm, model_id, route in ARMS:
        rows.append(one(arm, model_id, route, "warmup"))

    for number in range(1, ROUNDS + 1):
        print(f"=== 회차 {number}/{ROUNDS}")
        for arm, model_id, route in ARMS:
            rows.append(one(arm, model_id, route, f"r{number}"))

    summary: dict[str, dict] = {}
    for arm, model_id, route in ARMS:
        measured = [r for r in rows if r["arm"] == arm and r["round"] != "warmup"]
        warm = next(r for r in rows if r["arm"] == arm and r["round"] == "warmup")
        latencies = [r["wall_ms"] for r in measured if r.get("wall_ms") is not None]
        out_tokens = [r["output_tokens"] for r in measured if r.get("output_tokens") is not None]
        passed = [r for r in measured if r.get("kind") == "통과"]
        kinds: dict[str, int] = {}
        for r in measured:
            kinds[r.get("kind", "?")] = kinds.get(r.get("kind", "?"), 0) + 1
        summary[arm] = {
            "model_id": model_id,
            "route": route,
            "n": len(measured),
            "warmup_wall_ms": warm.get("wall_ms"),
            "wall_ms_median": None if not latencies else round(statistics.median(latencies), 1),
            "wall_ms_min": None if not latencies else min(latencies),
            "wall_ms_max": None if not latencies else max(latencies),
            "output_tokens_median": None
            if not out_tokens
            else round(statistics.median(out_tokens), 1),
            "output_tokens_max": None if not out_tokens else max(out_tokens),
            "input_tokens": next(
                (r["input_tokens"] for r in measured if r.get("input_tokens")), None
            ),
            "pass_n": len(passed),
            "kinds": kinds,
        }

    (HERE / "results.json").write_text(
        json.dumps(
            {
                "user_id": str(user_id),
                "prompt_chars": len(prompt),
                "current_level": data.current_level,
                "allowed_pattern_ids": len(allowed),
                "app_model_id": settings.claude_model_id,
                "region": settings.aws_region,
                "max_tokens": MAX_TOKENS,
                "rounds": ROUNDS,
                "summary": summary,
                "calls": rows,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print("=== 집계")
    for arm, value in summary.items():
        print(
            f"  {arm:20s} 통과 {value['pass_n']}/{value['n']} "
            f"지연중앙 {value['wall_ms_median']}ms 최대 {value['wall_ms_max']}ms "
            f"출력토큰중앙 {value['output_tokens_median']} {value['kinds']}"
        )
    print(f"-> {HERE / 'results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
