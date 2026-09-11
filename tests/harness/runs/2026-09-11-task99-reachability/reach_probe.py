#!/usr/bin/env python3
"""TASK-99 AC#1 — `pronunciation_` 접두 `pattern_key` 의 **도달성**을 실물 분석 회차로 관측한다.

⛔ **이 스크립트는 DB 를 쓰지 않는다.** 읽는 것은 `error_patterns` 두 벌(제품 필터 적용·미적용)과
전후 스냅샷뿐이고, 모델 응답을 저장 단계에 넘기지 않는다 — `resolve_pattern_keys` 까지만 부르고
`save_analysis` 는 부르지 않는다. 관측 대상이 「모델이 무엇을 내는가」이므로 저장은 필요하지 않고,
공유 dev DB 를 오염시키지 않는 것이 더 중요하다.

⚠️ **`app/backend` cwd 에서만 import 가 풀린다**(`H-AV`).

**두 팔을 두는 이유 — 판별력.** 제품 팔만 돌려 0 이 나오면 「모델이 안 낸다」와 「내 검출기가
못 본다」를 가를 수 없다. 그래서 억제를 무력화한 팔을 같은 회차에서 함께 쟀다.

- 팔 A(제품): `load_existing_patterns` 를 그대로 부른다 → 발음 행이 프롬프트에서 **빠진다**(G-8).
- 팔 B(양성 대조): 같은 조회에서 **카테고리 필터만 뺀다** → 발음 행이 프롬프트에 **실린다.**
  ⛔ 이 팔은 제품 경로가 아니다. G-8 필터가 실제로 무엇을 막는지를 재는 대조군이다.

관측하는 것 넷 (판정은 회차 기록이 갖는다):

1. `category == 'pronunciation_intonation'` 을 낸 응답 수 — 프롬프트가 「쓰지 마라」로
   금지한 값이다.
2. `pattern_key` 가 `pronunciation_` 로 시작한 응답 수.
3. `resolve_pattern_keys` 의 판정 — 통과인지, `AnalysisValidationError` 로 그 발화의 분석 전체를
   실패시키는지. **후자는 `frequency` 덮어쓰기가 아니라 다른 결함이다.**
4. 팔 B 에서 발음 키를 **재사용**했는지 — 재사용은 형식 검사를 받지 않으므로 upsert 까지
   그대로 간다.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg

from app.config import Settings
from app.models.analysis import AnalysisValidationError
from app.services.analysis import (
    PatternRow,
    build_prompt,
    load_existing_patterns,
    parse_analysis,
    resolve_pattern_keys,
)
from app.workers.claude_client import BedrockClaudeClient

RUN_DIR = Path(__file__).resolve().parent
USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# 발음 카테고리를 «유발하려고» 고른 전사문. 마지막 하나는 순수 문법 대조군이다.
#
# ⚠️ 유발을 노린 이유: 제품 프롬프트는 발음 카테고리를 명시적으로 금지하므로, 아무 전사문이나
# 주고 0 이 나오는 것은 정보가 없다. 발음을 말로 꺼내거나(「내 발음이 나쁘다」) 음소 혼동이
# 전사문에 흔적을 남긴 것(`sink`/`think` · `rice`/`lice`)을 골라 **가장 불리한 조건**을 만들었다.
TRANSCRIPTS: tuple[tuple[str, str], ...] = (
    ("t1_sink_and_says_pronunciation_is_bad", "I sink so, but my pronunciation is very bad."),
    ("t2_rice_heard_as_lice", "Yesterday I go to the office and I say rice but they hear lice."),
    ("t3_r_and_l_sound_problem", "I have a same problem with r and l sound."),
    ("t4_accent_is_strong", "My teacher say my accent is strong so people no understand me."),
    ("t5_how_to_pronounce_world", "I want to improve my pronounce of the word world."),
    ("t6_sink_in_a_work_update", "I sink the meeting was good and I explain the status."),
    (
        "t7_skips_a_word_he_cannot_say",
        "I am not sure how to say this word correctly so I just skip it.",
    ),
    # 팔 B 에서 `pronunciation_an_as_a` 재사용을 유발하려고 넣었다 — `an` 자리에 `a` 가 왔다.
    ("t8_an_as_a", "It was a amazing experience and I learn a lot."),
    # 대조군: 발음과 무관한 순수 문법 오류. 여기서 발음 카테고리가 나오면 유발과 무관하다는 뜻이다.
    ("t9_grammar_control", "He live in Seoul and he work at a big company."),
)

_PRONUNCIATION_KEY = re.compile(r"^pronunciation_")
_UNFILTERED_SQL = """
select category, pattern_key, target_form
  from error_patterns
 where user_id = $1
 order by pattern_key
"""
_SNAPSHOT_SQL = """
select category, pattern_key, frequency, last_seen_at, next_review_at
  from error_patterns
 where user_id = $1
 order by pattern_key
"""


@dataclass(frozen=True, slots=True)
class Observation:
    arm: str
    transcript_id: str
    raw: str
    parse_error: str | None
    findings: list[dict[str, str]]
    pronunciation_category_hits: list[str]
    pronunciation_prefix_hits: list[str]
    reused_existing_pronunciation_key: bool
    resolve_verdict: str


async def _snapshot(conn: asyncpg.Connection) -> list[dict[str, object]]:
    rows = await conn.fetch(_SNAPSHOT_SQL, USER_ID)
    return [
        {
            "category": row["category"],
            "pattern_key": row["pattern_key"],
            "frequency": row["frequency"],
            "last_seen_at": row["last_seen_at"].isoformat() if row["last_seen_at"] else None,
            "next_review_at": row["next_review_at"].isoformat() if row["next_review_at"] else None,
        }
        for row in rows
    ]


async def _unfiltered_patterns(conn: asyncpg.Connection) -> list[PatternRow]:
    records = await conn.fetch(_UNFILTERED_SQL, USER_ID)
    return [
        PatternRow(
            category=record["category"],
            pattern_key=record["pattern_key"],
            target_form=record["target_form"],
        )
        for record in records
    ]


def _observe(
    arm: str,
    transcript_id: str,
    raw: str,
    existing: list[PatternRow],
) -> Observation:
    existing_pronunciation_keys = {
        row.pattern_key for row in existing if _PRONUNCIATION_KEY.match(row.pattern_key)
    }
    try:
        result = parse_analysis(raw)
    except ValueError as exc:
        return Observation(
            arm=arm,
            transcript_id=transcript_id,
            raw=raw,
            parse_error=f"{type(exc).__name__}: {exc}",
            findings=[],
            pronunciation_category_hits=[],
            pronunciation_prefix_hits=[],
            reused_existing_pronunciation_key=False,
            resolve_verdict="not reached (parse failed)",
        )

    findings = [
        {"category": f.category, "pattern_key": f.pattern_key, "target_form": f.target_form}
        for f in result.findings
    ]
    category_hits = [
        f["pattern_key"] for f in findings if f["category"] == "pronunciation_intonation"
    ]
    prefix_hits = [f["pattern_key"] for f in findings if _PRONUNCIATION_KEY.match(f["pattern_key"])]
    reused = any(f["pattern_key"] in existing_pronunciation_keys for f in findings)

    try:
        resolve_pattern_keys(result, existing)
        verdict = "accepted"
    except AnalysisValidationError as exc:
        verdict = f"AnalysisValidationError: {exc}"
    except ValueError as exc:
        verdict = f"{type(exc).__name__}: {exc}"

    return Observation(
        arm=arm,
        transcript_id=transcript_id,
        raw=raw,
        parse_error=None,
        findings=findings,
        pronunciation_category_hits=category_hits,
        pronunciation_prefix_hits=prefix_hits,
        reused_existing_pronunciation_key=reused,
        resolve_verdict=verdict,
    )


def _fake_raw(category: str, pattern_key: str) -> str:
    """모델이 냈다고 «가정한» 응답 1건. Bedrock 을 부르지 않는다."""
    return json.dumps(
        {
            "findings": [
                {
                    "category": category,
                    "pattern_key": pattern_key,
                    "target_form": "an + 모음",
                    "original_span": "a amazing",
                    "correction": "an amazing",
                    "explanation": "모음 앞에서는 an 을 쓴다.",
                    "severity": "medium",
                    "confidence": 0.9,
                }
            ],
            "attempts": [],
        },
        ensure_ascii=False,
    )


def self_check() -> int:
    """⛔ 판별력 시험 — 검출기가 «볼 수 있는지»를 무력화 대조로 잰다. Bedrock·DB 를 쓰지 않는다.

    이것이 없으면 실물 팔의 0 을 읽을 수 없다. 2026-09-11 회차에서 **양성 대조로 둔 팔 B 까지
    0 이 나왔기 때문에** 이 시험이 필수가 됐다 — 발화한 적이 없는 검출기는 「모델이 안 냈다」의
    증거가 되지 못한다.

    네 사례의 기대값은 코드가 결정한다: 신규 키는 `is_valid_new_pattern_key` 가 `^{category}_`
    를 강제하고, 재사용 키는 그 검사를 받지 않는다.
    """
    existing_without = [
        PatternRow(category="article", pattern_key="article_missing_before_noun", target_form="a")
    ]
    existing_with = [
        *existing_without,
        PatternRow(
            category="pronunciation_intonation",
            pattern_key="pronunciation_an_as_a",
            target_form="an_as_a",
        ),
    ]
    cases = (
        # (사례 이름, category, pattern_key, existing, 기대 pron_category, 기대 prefix,
        #  기대 reused, resolve 가 거부인가)
        (
            "c1_forbidden_category_new_key",
            "pronunciation_intonation",
            "pronunciation_intonation_th_as_s",
            existing_without,
            1,
            1,
            False,
            False,
        ),
        (
            "c2_grammar_category_pron_prefix",
            "article",
            "pronunciation_th_as_s",
            existing_without,
            0,
            1,
            False,
            True,
        ),
        (
            "c3_reuses_existing_pron_key",
            "pronunciation_intonation",
            "pronunciation_an_as_a",
            existing_with,
            1,
            1,
            True,
            False,
        ),
        (
            "c4_negative_control_clean",
            "article",
            "article_missing_before_noun",
            existing_without,
            0,
            0,
            False,
            False,
        ),
    )
    failures = 0
    for (
        name,
        category,
        pattern_key,
        existing,
        want_cat,
        want_prefix,
        want_reused,
        want_reject,
    ) in cases:
        observation = _observe("self_check", name, _fake_raw(category, pattern_key), existing)
        rejected = observation.resolve_verdict.startswith("AnalysisValidationError")
        got = (
            len(observation.pronunciation_category_hits),
            len(observation.pronunciation_prefix_hits),
            observation.reused_existing_pronunciation_key,
            rejected,
        )
        want = (want_cat, want_prefix, want_reused, want_reject)
        ok = got == want
        failures += 0 if ok else 1
        print(
            f"{'PASS' if ok else 'FAIL'} {name:34s} got={got} want={want} "
            f"resolve={observation.resolve_verdict[:60]}"
        )
    print(f"self-check failures={failures}")
    return 1 if failures else 0


async def main() -> int:
    if "--self-check" in sys.argv:
        return self_check()

    settings = Settings()  # ty: ignore[missing-argument]
    claude = BedrockClaudeClient(settings)
    started = datetime.now(UTC)

    conn = await asyncpg.connect(settings.database_url)
    try:
        product_patterns = await load_existing_patterns(conn, USER_ID)
        unfiltered_patterns = await _unfiltered_patterns(conn)
        snapshot_before = await _snapshot(conn)
    finally:
        await conn.close()

    arms = {"A_product_filtered": product_patterns, "B_control_unfiltered": unfiltered_patterns}
    observations: list[Observation] = []
    for arm, existing in arms.items():
        for transcript_id, transcript in TRANSCRIPTS:
            prompt = build_prompt(transcript, existing)
            raw = await claude.analyze(prompt)
            observation = _observe(arm, transcript_id, raw, existing)
            observations.append(observation)
            print(
                f"{arm:22s} {transcript_id:38s} "
                f"pron_category={len(observation.pronunciation_category_hits)} "
                f"pron_prefix={len(observation.pronunciation_prefix_hits)} "
                f"reused={observation.reused_existing_pronunciation_key} "
                f"resolve={observation.resolve_verdict[:48]}",
                flush=True,
            )

    conn = await asyncpg.connect(settings.database_url)
    try:
        snapshot_after = await _snapshot(conn)
    finally:
        await conn.close()

    payload = {
        "task": "TASK-99 AC#1",
        "model_id": settings.claude_model_id,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "user_id": str(USER_ID),
        "arms": {
            arm: [{"pattern_key": row.pattern_key, "category": row.category} for row in existing]
            for arm, existing in arms.items()
        },
        "snapshot_before": snapshot_before,
        "snapshot_after": snapshot_after,
        "snapshot_unchanged": snapshot_before == snapshot_after,
        "observations": [
            {
                "arm": o.arm,
                "transcript_id": o.transcript_id,
                "parse_error": o.parse_error,
                "findings": o.findings,
                "pronunciation_category_hits": o.pronunciation_category_hits,
                "pronunciation_prefix_hits": o.pronunciation_prefix_hits,
                "reused_existing_pronunciation_key": o.reused_existing_pronunciation_key,
                "resolve_verdict": o.resolve_verdict,
                "raw": o.raw,
            }
            for o in observations
        ],
    }
    out = RUN_DIR / "observations.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    for arm in arms:
        arm_rows = [o for o in observations if o.arm == arm]
        print(
            f"{arm}: n={len(arm_rows)} "
            f"pron_category={sum(1 for o in arm_rows if o.pronunciation_category_hits)} "
            f"pron_prefix={sum(1 for o in arm_rows if o.pronunciation_prefix_hits)} "
            f"reused={sum(1 for o in arm_rows if o.reused_existing_pronunciation_key)} "
            f"rejected={sum(1 for o in arm_rows if o.resolve_verdict.startswith('Analysis'))}"
        )
    print(f"snapshot_unchanged={payload['snapshot_unchanged']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
