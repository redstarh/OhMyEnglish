#!/usr/bin/env python3
"""TS-36 AC#3 전제 — 결과 화면의 패턴 카드가 뜰 조건을 만든다.

그 절은 `dailyPatterns.length > 0` 일 때만 렌더되고, `dailyPatterns` 는
`GET /api/daily-summary` 의 **오늘(사용자 타임존)** 행에서 온다. 회차 시작 시 그 행은 없었다
(가장 최근 행이 2026-09-06). ⇒ 오늘 행 1건을 심는다.

**고른 패턴**: `verb_tense_past_simple_for_past_events`.
⛔ 준비된 계획의 초점(`pronunciation_an_as_a` · `article_missing_before_noun`)과 **겹치지 않는 것**을
고른 것이 이 선택의 전부다 — 겹치면 「초점이 고른 패턴으로 바뀌었다」와 「계획의 초점이 그대로다」를
가를 수 없다.

⛔ **기준선**: `2026-09-19` 행은 **없었다.** 그러므로 복원은 그 행의 삭제이고, 삭제 뒤 다시 읽어
없음을 확인한다(`--restore`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tests" / "harness"))

from psql_cli import psql  # noqa: E402

USER = "00000000-0000-0000-0000-000000000001"
PATTERN_KEY = "verb_tense_past_simple_for_past_events"
PATTERNS = [
    {
        "pattern_key": PATTERN_KEY,
        "category": "verb_tense",
        "target_form": "Yesterday + 주어 + 동사 과거형",
        "occurrences": 2,
        "example": {
            "original_span": "Yesterday I go to the office",
            "correction": "Yesterday I went to the office",
            "reason": "어제 일이므로 과거형 went 를 사용합니다.",
        },
    }
]


def today() -> str:
    return psql("select (now() at time zone 'Asia/Seoul')::date")


def show() -> str:
    return psql(
        "select summary_date || ' | pattern_count=' || pattern_count || ' | computed_at=' || "
        f"coalesce(computed_at::text,'NULL') from daily_error_summary where user_id='{USER}' "
        f"and summary_date='{today()}'"
    )


def seed() -> int:
    day = today()
    before = show()
    print(f"오늘(KST) = {day}")
    print(f"기준선(심기 전) 오늘 행: {before!r}  <- 빈 문자열이면 «행 없음»")
    payload = json.dumps(PATTERNS, ensure_ascii=False).replace("'", "''")
    psql(
        "insert into daily_error_summary "
        "(user_id, summary_date, timezone, occurrence_count, pattern_count, patterns, computed_at) "
        f"values ('{USER}', '{day}', 'Asia/Seoul', 2, 1, '{payload}'::jsonb, now())"
    )
    print(f"심은 뒤 오늘 행: {show()!r}")
    (HERE / ".daily_seed_baseline.txt").write_text(
        f"today={day}\nbefore={before!r}\n", encoding="utf-8"
    )
    return 0


def restore() -> int:
    day = today()
    psql(f"delete from daily_error_summary where user_id='{USER}' and summary_date='{day}'")
    # 삭제 명령의 성공을 복원 근거로 쓰지 않는다 — 다시 읽는다.
    after = show()
    rows = psql(f"select count(*) from daily_error_summary where user_id='{USER}'")
    text = f"복원 뒤 오늘({day}) 행: {after!r}  <- 빈 문자열이면 기준선과 같다\n전체 행 수: {rows}"
    print(text)
    (HERE / "evidence" / "TS-36-daily-seed-restored.txt").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    sys.exit(restore() if args.restore else seed())
