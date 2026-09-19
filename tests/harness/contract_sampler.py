#!/usr/bin/env python
"""`TASK-258` 계약 표본기 — 실물 응답이 파서 계약을 지키는 비율을 프롬프트 A/B 로 센다.

`TASK-257` 이 프롬프트를 고쳤지만 수정 후 표본이 `findings` 항목 12개뿐이어서 「위반 빈도가
낮아졌다」를 증명하지 못한 채 닫혔다. 이 표본기가 그 공백을 메운다.

⛔ **DB 의 학습 데이터를 한 행도 쓰지 않는다.** 지나가는 것은 `build_prompt` → 실물 Claude →
`parse_analysis` 뿐이고 저장 경로(`process_analysis`)를 부르지 않는다. 격리 DB 에 남는 것은
`llm_calls`(비용 표) 하나다 — `usage_sink` 를 빼면 유료 호출이 표에 0행으로 남기 때문에(`H-CK`)
실물 배선을 그대로 베낀다.

⛔ **계약을 손으로 베끼지 않는다** — 허용 키와 필수 키를 `ErrorFinding.model_fields` 에서 읽는다.
베끼면 모델이 바뀔 때 표본기만 낡고, 그 낡음이 「위반 0건」으로 보인다.

두 갈래:

* `treated` — 지금 프롬프트 그대로.
* `control` — 그 프롬프트에서 `TASK-257` 이 더한 한 줄만 뺀 것. ⛔ 파일을 고치지 않고 문자열에서
  뺀다(회차가 소스를 바꾸면 그 사이 다른 실행이 오염된다). 그 줄이 없으면 즉시 실패한다 — 프롬프트가
  바뀌었다는 뜻이고, 그때 조용히 같은 두 갈래를 비교하면 A/B 가 거짓이 된다.

    cd app/backend
    .venv/bin/python ../../tests/harness/contract_sampler.py --repeats 5 --concurrency 4 \
        --out ../../tests/harness/runs/<회차>

cwd 는 `app/backend` 다(`H-A` — 설정과 `.env` 가 거기 있다).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from db_utils import dsn_for  # noqa: E402

WORKER_DB_NAME = "ohmyenglish_worker"


# ⛔ 값역을 손으로 적지 않는다 — 제품의 `Outcome` 리터럴에서 읽는다(`ErrorFinding.model_fields` 를
# 읽는 것과 같은 이유다).
def _attempt_outcome_range() -> frozenset[str]:
    from typing import get_args

    from app.models.analysis import PatternAttempt

    return frozenset(get_args(PatternAttempt.model_fields["outcome"].annotation))


# `TASK-257` 이 `_OUTPUT_RULES` 에 더한 줄. ⛔ 문면을 여기 적는 것이 A/B 의 전제다 — 프롬프트에서
# 사라지면 `control` 갈래가 `treated` 와 같아지고 비교가 조용히 무의미해진다. 그래서 단정으로
# 막는다.
TREATED_LINE = (
    "- findings 의 **모든** 항목이 아래 키 이름을 글자 그대로 쓴다. 항목마다 키를 다시 짓지 마라.\n"
)

# 오류를 셋 이상 담은 전사문. ⛔ **여러 항목을 «반드시» 만들어야 한다** — 관측하려는 흔들림이
# `findings[1]` 부터 나타나므로, 항목이 하나만 나오는 문장은 판별력이 0이다.
TRANSCRIPTS: list[str] = [
    "Yesterday I go to office by subway and I meet my new manager for first time.",
    "I am afraid on speaking in meeting because I forget many word when they ask me question.",
    "Last week our team finish the release but customer complain about performance issue.",
    "I need explain our roadmap to partner team next month but I don't know how start.",
    "My director join the call sometimes and he always ask me about status of project.",
]


# ⛔ **위반이 실제로 난 조건은 「기존 패턴 목록이 있는」 프롬프트였다** (`TASK-256` 회차의 call 1 ·
# 그때 씨앗 패턴이 2건이었다). 그 목록 절은 `pattern_key | category | target_form` 표를 보여 주므로,
# 관측된 `pattern_form` 은 두 열 이름이 섞인 모양일 수 있다 — 그 가설을 재는 갈래가
# `--existing` 이다.
# ⚠️ 값은 회차의 씨앗과 같게 둔다. 다른 값을 쓰면 「같은 조건을 다시 만들었다」가 성립하지 않는다.
EXISTING_SEED: list[tuple[str, str, str]] = [
    ("verb_tense", "verb_tense_past_simple", "went / explained"),
    ("article", "article_missing_plural", "many words"),
]


def _point_settings_at_worker_db() -> str:
    """`get_settings()` 가 처음 불리기 «전에» DSN 을 격리 DB 로 바꾼다.

    `w_worker_round.py` 의 같은 이름 함수와 같은 이유다 — `lru_cache` 라 한 번 불린 뒤에는
    되돌릴 수 없다.
    """
    dsn = dsn_for(WORKER_DB_NAME)
    os.environ["DATABASE_URL"] = dsn
    return dsn


def _classify(
    raw: str, *, allowed: set[str], required: set[str], existing_keys: frozenset[str]
) -> dict[str, Any]:
    """응답 하나를 계약 관점으로 가른다 — **파서 판정과 항목 단위 관측을 따로** 낸다.

    ⛔ 파서가 거부한 응답도 항목을 센다. 파서는 첫 위반에서 멈추므로 그 판정만 쓰면 「한 응답에 몇
    항목이 어긋났는가」를 알 수 없고, 그 수가 이 회차가 세려는 값이다.
    """
    # ⚠️ **사설 `_json_candidates` 를 일부러 쓴다** — 항목을 세려면 파서가 «실제로 본» 후보와 같은
    # 문자열을 봐야 한다. 여기서 코드펜스 처리를 다시 구현하면 표본기와 제품이 다른 것을 세게 된다.
    from app.models.analysis import (
        AnalysisValidationError,
        _json_candidates,
        is_valid_new_pattern_key,
        parse_analysis,
    )

    outcome_range = _attempt_outcome_range()
    verdict: dict[str, Any] = {"parse_ok": False, "parse_error": None}
    try:
        parse_analysis(raw)
        verdict["parse_ok"] = True
    except AnalysisValidationError as exc:
        # 문면 전체를 남기지 않는다 — 종류를 가르는 앞부분만 쓴다(원문은 따로 저장한다).
        verdict["parse_error"] = str(exc)[:160]

    body: object = None
    for candidate in _json_candidates(raw):
        try:
            body = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        break
    if not isinstance(body, dict):
        verdict |= {"json_ok": False, "items": 0}
        return verdict

    findings = body.get("findings")
    findings = findings if isinstance(findings, list) else []
    attempts = body.get("attempts")
    attempts = attempts if isinstance(attempts, list) else []

    extra_keys: Counter[str] = Counter()
    missing_keys: Counter[str] = Counter()
    bad_key_format = 0
    items = 0
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        items += 1
        present = {str(name) for name in finding}
        extra_keys.update(present - allowed)
        missing_keys.update(required - present)
        key = finding.get("pattern_key")
        category = finding.get("category")
        # ⚠️ 이 회차의 기존 패턴 목록은 **비어 있다** — 그래서 모든 key 가 「새 key」이고 형식 규칙이
        # (`^{category}_[a-z0-9_]+$`) 그대로 적용된다. 목록이 있으면 재사용 key 가 형식 밖일 수 있어
        # 이 계수가 뜻을 잃는다.
        # ⛔ 기존 key 재사용은 형식 규칙 밖이다(`is_valid_new_pattern_key` 의 docstring) — 그것을
        # 위반으로 세면 `--existing` 갈래에서만 계수가 부풀어 두 갈래를 비교할 수 없다.
        if (
            isinstance(key, str)
            and isinstance(category, str)
            and key not in existing_keys
            and not is_valid_new_pattern_key(category, key)
        ):
            bad_key_format += 1

    # ⛔ **`attempts` 가 비어 있지 않은 것 자체는 위반이 아니다 — 첫 판의 계수가 그것을 위반으로
    # 셌고 실측에서 거짓 신호를 냈다**(2026-09-20: 기존 패턴을 넣은 갈래에서 두 갈래 각각 32건이
    # 잡혔는데, 전건이 목록 안의 key 에 `outcome=incorrect` 였다 — 프롬프트가 요구한 그대로다).
    # 계약은 셋이다: key 가 **목록 안**이고 · `outcome` 이 값역 안이고 · 다른 키가 없다.
    bad_attempts = 0
    for attempt in attempts:
        if not isinstance(attempt, dict):
            bad_attempts += 1
            continue
        if (
            attempt.get("pattern_key") not in existing_keys
            or attempt.get("outcome") not in outcome_range
            or set(attempt) - {"pattern_key", "outcome"}
        ):
            bad_attempts += 1

    verdict |= {
        "json_ok": True,
        "items": items,
        "extra_keys": dict(extra_keys),
        "missing_keys": dict(missing_keys),
        "bad_pattern_key_format": bad_key_format,
        "attempts": len(attempts),
        "bad_attempts": bad_attempts,
    }
    return verdict


async def _one_call(
    claude: Any,
    prompt: str,
    *,
    arm: str,
    transcript_no: int,
    repeat: int,
    allowed: set[str],
    required: set[str],
    existing_keys: frozenset[str],
    semaphore: asyncio.Semaphore,
    log_path: Path,
    lock: asyncio.Lock,
) -> dict[str, Any]:
    from app.models.usage import PURPOSE_ANALYSIS

    async with semaphore:
        try:
            raw = await claude.analyze(prompt, purpose=PURPOSE_ANALYSIS)
        except Exception as exc:  # 호출 자체의 실패 — 계약 위반과 갈라 센다
            record = {
                "arm": arm,
                "transcript_no": transcript_no,
                "repeat": repeat,
                "call_failed": f"{type(exc).__name__}: {exc}"[:160],
            }
            raw = ""
        else:
            record = {
                "arm": arm,
                "transcript_no": transcript_no,
                "repeat": repeat,
                "call_failed": None,
            } | _classify(raw, allowed=allowed, required=required, existing_keys=existing_keys)
    async with lock:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({**record, "raw": raw}, ensure_ascii=False) + "\n")
    print(
        f"  {arm} t{transcript_no} r{repeat}: "
        + ("호출 실패" if record["call_failed"] else f"parse_ok={record['parse_ok']}")
    )
    return record


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    extra: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    for record in records:
        extra.update(record.get("extra_keys") or {})
        missing.update(record.get("missing_keys") or {})
    items = sum(record.get("items", 0) for record in records)
    bad_items = sum(extra.values()) + sum(missing.values())
    return {
        "calls": len(records),
        "call_failures": sum(1 for record in records if record["call_failed"]),
        "parse_ok": sum(1 for record in records if record.get("parse_ok")),
        "parse_failed": sum(
            1 for record in records if not record.get("parse_ok") and not record["call_failed"]
        ),
        "items": items,
        "items_with_key_violation": bad_items,
        "extra_keys": dict(extra),
        "missing_keys": dict(missing),
        "bad_pattern_key_format": sum(
            record.get("bad_pattern_key_format", 0) for record in records
        ),
        "attempts": sum(record.get("attempts", 0) for record in records),
        "bad_attempts": sum(record.get("bad_attempts", 0) for record in records),
    }


def rescan(out_dir: Path, *, existing: bool) -> int:
    """저장된 `samples.jsonl` 을 **다시 세어** `summary-rescan.json` 을 낸다 — 호출을 내지 않는다.

    ⛔ **계수의 뜻이 바뀌면 옛 판정을 다시 내려야 한다.** 첫 판의 `unexpected_attempts` 가 정상
    동작을 위반으로 셌고(그 상수 위 주석), 그때 원문을 남겨 둔 덕분에 유료 호출 없이 다시 셀 수
    있었다. ⚠️ **원본 `summary.json` 을 덮지 않는다** — 그 파일이 「그때 그렇게 판정했다」는
    기록이다.
    """
    from app.models.analysis import ErrorFinding

    allowed = set(ErrorFinding.model_fields)
    required = {name for name, field in ErrorFinding.model_fields.items() if field.is_required()}
    existing_keys = frozenset(key for _, key, _ in EXISTING_SEED) if existing else frozenset()

    rows = [
        json.loads(line)
        for line in (out_dir / "samples.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records: list[dict[str, Any]] = []
    for row in rows:
        record = {key: row[key] for key in ("arm", "transcript_no", "repeat", "call_failed")}
        if not record["call_failed"]:
            record |= _classify(
                row["raw"], allowed=allowed, required=required, existing_keys=existing_keys
            )
        records.append(record)
    arms = sorted({record["arm"] for record in records})
    summary = {
        "rescanned": True,
        "existing_patterns": sorted(existing_keys),
        "arms": {arm: _summarize([r for r in records if r["arm"] == arm]) for arm in arms},
    }
    (out_dir / "summary-rescan.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
    )
    print(json.dumps(summary["arms"], ensure_ascii=False, indent=2))
    return 0


async def main(
    *, repeats: int, concurrency: int, out_dir: Path, arms: list[str], existing: bool
) -> int:
    _point_settings_at_worker_db()

    from app.config import Settings, get_settings, prepare_bedrock_credentials
    from app.db import close_pool
    from app.db import pool as get_db_pool
    from app.models.analysis import ErrorFinding
    from app.services.analysis import PatternRow, build_prompt
    from app.services.usage import pool_usage_sink
    from app.workers.claude_client import BedrockClaudeClient

    prepare_bedrock_credentials(Settings())  # ty: ignore[missing-argument]
    settings = get_settings()

    allowed = set(ErrorFinding.model_fields)
    required = {name for name, field in ErrorFinding.model_fields.items() if field.is_required()}
    print(f"계약: 허용 키 {len(allowed)}개 · 필수 키 {sorted(required)}")

    existing_patterns = (
        [
            PatternRow(category=category, pattern_key=key, target_form=form)
            for category, key, form in EXISTING_SEED
        ]
        if existing
        else []
    )
    existing_keys = frozenset(row.pattern_key for row in existing_patterns)
    print(f"기존 패턴 목록: {sorted(existing_keys) if existing_keys else '비어 있음'}")

    pool = await get_db_pool()
    try:
        # ⛔ 학습 데이터가 바뀌지 않았음을 «수치로» 보이기 위해 앞뒤로 같은 질의를 돌린다.
        async with pool.acquire() as conn:
            before = dict(
                await conn.fetchrow(
                    "select (select count(*) from error_patterns) as error_patterns,"
                    "       (select count(*) from error_occurrences) as error_occurrences,"
                    "       (select count(*) from utterances) as utterances,"
                    "       (select count(*) from llm_calls) as llm_calls"
                )
                or {}
            )
        claude = BedrockClaudeClient(settings, usage_sink=pool_usage_sink(pool))

        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        log_path = out_dir / "samples.jsonl"
        tasks = []
        for arm in arms:
            for transcript_no, transcript in enumerate(TRANSCRIPTS, start=1):
                prompt = build_prompt(transcript, existing_patterns)
                if TREATED_LINE not in prompt:
                    raise RuntimeError(
                        "프롬프트에서 `TASK-257` 의 줄을 찾지 못했다 — 문면이 바뀌었으므로 "
                        "A/B 가 성립하지 않는다. `TREATED_LINE` 을 먼저 맞춘다."
                    )
                if arm == "control":
                    prompt = prompt.replace(TREATED_LINE, "")
                for repeat in range(1, repeats + 1):
                    tasks.append(
                        _one_call(
                            claude,
                            prompt,
                            arm=arm,
                            transcript_no=transcript_no,
                            repeat=repeat,
                            allowed=allowed,
                            required=required,
                            existing_keys=existing_keys,
                            semaphore=semaphore,
                            log_path=log_path,
                            lock=lock,
                        )
                    )
        print(f"호출 {len(tasks)}건 시작 (동시성 {concurrency})")
        records = await asyncio.gather(*tasks)

        async with pool.acquire() as conn:
            after = dict(
                await conn.fetchrow(
                    "select (select count(*) from error_patterns) as error_patterns,"
                    "       (select count(*) from error_occurrences) as error_occurrences,"
                    "       (select count(*) from utterances) as utterances,"
                    "       (select count(*) from llm_calls) as llm_calls,"
                    "       (select coalesce(sum(input_tokens), 0) from llm_calls) as in_tokens,"
                    "       (select coalesce(sum(output_tokens), 0) from llm_calls) as out_tokens"
                )
                or {}
            )
        summary = {
            "repeats_per_transcript": repeats,
            "existing_patterns": sorted(existing_keys),
            "transcripts": len(TRANSCRIPTS),
            "arms": {arm: _summarize([r for r in records if r["arm"] == arm]) for arm in arms},
            "learning_rows_before": before,
            "learning_rows_after": after,
        }
        (out_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        print(json.dumps(summary["arms"], ensure_ascii=False, indent=2))
        print(f"학습 데이터 앞: {before}")
        print(f"학습 데이터 뒤: {after}")
    finally:
        await close_pool()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--repeats", type=int, default=5, help="전사문 하나당 반복 호출 수")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--arms",
        default="control,treated",
        help="쉼표로 구분 — 기본은 두 갈래 모두",
    )
    parser.add_argument(
        "--existing",
        action="store_true",
        help="기존 패턴 목록을 넣은 프롬프트로 센다 (위반이 난 조건)",
    )
    parser.add_argument(
        "--rescan",
        action="store_true",
        help="저장된 samples.jsonl 을 다시 세기만 한다 (호출 0건)",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.rescan:
        sys.exit(rescan(args.out, existing=args.existing))
    sys.exit(
        asyncio.run(
            main(
                repeats=args.repeats,
                concurrency=args.concurrency,
                out_dir=args.out,
                arms=[arm.strip() for arm in args.arms.split(",") if arm.strip()],
                existing=args.existing,
            )
        )
    )
