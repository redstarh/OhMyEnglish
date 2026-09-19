#!/usr/bin/env python
"""`TASK-259` 탐침 — 무대가 없는 전사문에서 실물 모델이 `category` 를 정말 `null` 로 내는가.

⛔ **고치기 전에 도달 가능성을 먼저 잰다.** 프롬프트는 「축 1(무대)이 전사문에 없으면 `category` 를
`null` 로 내라」고 지시하고 파서는 그 답을 거부한다. 그 모순의 대가(유료 호출 4건 낭비)는 스텁으로
이미 셌지만, **모델이 실제로 그 답을 내지 않으면 그 경로는 도달 불가**이고 고칠 이유가 약해진다.

⛔ DB 를 쓰지 않는다 — `build_scenario_prompt` → 실물 모델 → `parse_scenario` 만 지나간다. 사용량은
격리 DB 의 `llm_calls` 에만 남는다(`H-CK` 의 배선 규칙).

    cd app/backend
    env -u AWS_BEARER_TOKEN_BEDROCK .venv/bin/python ../../tests/harness/scenario_null_probe.py \
        --repeats 8 --out ../../tests/harness/runs/<회차>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from db_utils import dsn_for  # noqa: E402

WORKER_DB_NAME = "ohmyenglish_worker"

# 무대를 한 번도 말하지 않은 5회 대화. ⛔ **다른 넷(상대·목표·초점·어조)도 비우지 않는다** — 축 1만
# 비는 조건을 만들어야 「무대가 없으면」 갈래를 재는 것이 된다. 넷까지 비우면 응답이 왜 null 인지
# 가려진다.
STAGELESS_TRANSCRIPT = """agent: Where will you need English soon?
user: Hmm, I am not sure yet. I don't have a specific plan.
agent: Who will you talk to?
user: Maybe anyone. I just want to speak more naturally.
agent: What do you want to achieve?
user: I want to feel less nervous when I speak English.
agent: Which part feels hardest?
user: Listening is hard for me, and I forget words.
agent: Do you prefer a formal or relaxed tone?
user: Relaxed is better for me."""


async def main(*, repeats: int, out_dir: Path, concurrency: int) -> int:
    os.environ["DATABASE_URL"] = dsn_for(WORKER_DB_NAME)

    from app.config import Settings, get_settings, prepare_bedrock_credentials
    from app.db import close_pool
    from app.db import pool as get_db_pool
    from app.models.scenario_draft import ScenarioValidationError, parse_scenario
    from app.services.scenario_generator import build_scenario_prompt
    from app.services.usage import pool_usage_sink
    from app.workers.claude_client import BedrockClaudeClient

    prepare_bedrock_credentials(Settings())  # ty: ignore[missing-argument]
    settings = get_settings()

    pool = await get_db_pool()
    try:
        # 값역은 시드에 실재하는 계열이다 — 격리 DB 의 시드에서 그대로 읽는다(제품과 같은 질의).
        async with pool.acquire() as conn:
            categories = tuple(
                row["category"]
                for row in await conn.fetch(
                    "select distinct category from learning_scenarios where source = 'seed'"
                    " order by 1"
                )
            )
        print(f"허용 계열 {len(categories)}개: {list(categories)}")
        prompt = build_scenario_prompt(
            transcript=STAGELESS_TRANSCRIPT, allowed_categories=categories
        )
        claude = BedrockClaudeClient(settings, usage_sink=pool_usage_sink(pool))

        semaphore = asyncio.Semaphore(concurrency)

        async def one(index: int) -> dict[str, object]:
            async with semaphore:
                raw = await claude.analyze(prompt, purpose="generate_scenario")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {}
            category = body.get("category") if isinstance(body, dict) else "<json 아님>"
            verdict = "parse_ok"
            try:
                parse_scenario(
                    raw, allowed_categories=frozenset(categories), existing_titles=frozenset()
                )
            except ScenarioValidationError as exc:
                verdict = f"거부: {str(exc)[:80]}"
            print(f"  {index}: category={category!r} · {verdict}")
            return {"index": index, "category": category, "verdict": verdict, "raw": raw}

        records = await asyncio.gather(*(one(index) for index in range(1, repeats + 1)))
        counts = Counter(
            "null" if record["category"] is None else str(record["category"]) for record in records
        )
        rejected = sum(1 for record in records if record["verdict"] != "parse_ok")
        summary = {
            "repeats": repeats,
            "category_counts": dict(counts),
            "rejected_by_parser": rejected,
        }
        (out_dir / "scenario-null-probe.json").write_text(
            json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2)
            + "\n"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        await close_pool()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.exit(
        asyncio.run(main(repeats=args.repeats, out_dir=args.out, concurrency=args.concurrency))
    )
