#!/usr/bin/env python3
"""TS-4 드라이버 — R2 규칙 4 와 「규칙 1 대 3 우선순위」를 **앱 경로(HTTP)** 로 관측한다.

⛔ **앱 코드를 고치지 않는다.** 이 파일은 회차 디렉터리에만 있고 DB 에 행을 심은 뒤
`GET /api/sessions/<id>/results` 를 두드릴 뿐이다.

**왜 행을 직접 심는가.** 워커를 켜면 미등록 발화 스윕이 job 을 새로 등록해 유료 호출이 남는다
(함정 `H-CD`). 이 회차는 job 상태의 «조합»만 필요하므로 행을 심는 것이 옳다.

**격리 사용자를 쓴다.** 고정 사용자(00000000-…-0001)의 기존 27개 세션을 건드리지 않기 위해서다.
회차 끝에 이 사용자와 딸린 행을 전부 지운다(`--cleanup`).

**심는 세션 셋 — 셋째가 판별력이다.**

| 이름 | 세션 status | job 구성 | 기대 |
|---|---|---|---|
| `D-rule4` | `completed` | done 1 + failed 1 | `partial_failure` · corrections ≥ 1 |
| `E-rule1-vs-3` | `failed` | pending 1 + done 1 | `connection_failed` · corrections 키 부재 |
| `F-control-rule3` | `completed` | pending 1 + done 1 | `analyzing` |

⛔ `F` 없이 `E` 만 재면 「내 seed 가 애초에 non-terminal job 을 못 만들었다」와
「우선순위가 지켜졌다」를 가를 수 없다. `F` 는 `E` 와 **세션 status 한 글자만** 다르므로,
`F` 가 `analyzing` 이면 그 job 구성이 규칙 3 에 실제로 닿는다는 증명이다(§7-7 · §7-9).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tests" / "harness"))

from psql_cli import psql  # noqa: E402

API = "http://localhost:8002/api/sessions"
EVIDENCE = HERE / "evidence"
# 격리 사용자 — 고정 UUID 로 두어 cleanup 이 시각창을 쓰지 않게 한다.
USER_ID = "b8000000-0000-0000-0000-0000000000b8"
USER_NAME = "ts4-b8-isolated"


def q(sql: str) -> str:
    return psql(sql)


def seed_user() -> None:
    q(
        f"insert into users (id, display_name, timezone, current_level) "
        f"values ('{USER_ID}', '{USER_NAME}', 'Asia/Seoul', 'A2')"
    )
    # 교정에 쓸 패턴 1종. severity 는 occurrence 쪽 컬럼이라 여기에는 없다.
    q(
        f"insert into error_patterns (user_id, category, pattern_key, target_form, frequency) "
        f"values ('{USER_ID}', 'article', 'b8_article_missing', 'a/an + 단수 명사', 2)"
    )


def pattern_id() -> str:
    return q(f"select id from error_patterns where user_id='{USER_ID}'")


def seed_session(*, status: str, jobs: list[str], with_occurrence: bool, pid: str) -> str:
    """세션 1건 + 발화 n건 + job n건(+ 교정 1건)을 심고 세션 id 를 돌려준다.

    `jobs` 의 각 원소가 발화 1건과 job 1건을 만든다 — job 상태를 발화마다 갈라 두면
    `_JOB_COUNTS_SQL` 의 세 수(total·non_terminal·failed)를 그대로 조립할 수 있다.
    """
    sid = q(
        f"insert into learning_sessions (user_id, mode, learning_source, status, ended_at) "
        f"values ('{USER_ID}', 'speaking', 'recommended', '{status}', now()) returning id"
    )
    # 코치 발화를 먼저 두어 exchange 전이가 성립하게 한다 — 드릴 관측이 0 으로만 남지 않게 한다.
    q(
        f"insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
        f"values ('{sid}', 'agent', 'learning', 'What did you do yesterday?', 1)"
    )
    first_utterance = ""
    for index, job_status in enumerate(jobs, start=2):
        uid = q(
            f"insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
            f"values ('{sid}', 'user', 'learning', 'I go to gym yesterday.', {index}) returning id"
        )
        if not first_utterance:
            first_utterance = uid
        q(
            f"insert into analysis_jobs (job_type, utterance_id, status) "
            f"values ('analyze_utterance', '{uid}', '{job_status}')"
        )
    if with_occurrence:
        q(
            "insert into error_occurrences "
            "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
            f"values ('{first_utterance}', '{pid}', 'go to gym', 'went to the gym', "
            "'어제 일이므로 과거형과 the 가 필요하다.', 'high', 0.9)"
        )
    return sid


def fetch(sid: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(f"{API}/{sid}/results", timeout=20) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:  # 본문도 증거다
        return error.code, json.loads(error.read().decode() or "{}")


def job_counts(sid: str) -> str:
    return q(
        "select count(*) as total, "
        "count(*) filter (where j.status in ('pending','running')) as non_terminal, "
        "count(*) filter (where j.status='failed') as failed "
        "from analysis_jobs j join utterances u on u.id = j.utterance_id "
        f"where u.session_id='{sid}' and j.job_type='analyze_utterance'"
    )


def run() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    seed_user()
    pid = pattern_id()
    plan = [
        ("D-rule4", "completed", ["done", "failed"], True, "partial_failure"),
        ("E-rule1-vs-3", "failed", ["done", "pending"], True, "connection_failed"),
        ("F-control-rule3", "completed", ["done", "pending"], True, "analyzing"),
    ]
    lines: list[str] = []
    ids: dict[str, str] = {}
    verdicts: list[tuple[str, bool, str]] = []
    for name, status, jobs, occ, expected in plan:
        sid = seed_session(status=status, jobs=jobs, with_occurrence=occ, pid=pid)
        ids[name] = sid
        code, body = fetch(sid)
        counts = job_counts(sid)
        corrections = body.get("corrections", "<KEY ABSENT>")
        got = body.get("status")
        ok = got == expected
        lines.append(f"=== {name}  세션 {sid}  HTTP {code} ===")
        lines.append(f"  세션 status(DB)  : {status}")
        lines.append(f"  job total|non_terminal|failed : {counts}")
        lines.append(f"  기대 status      : {expected}")
        lines.append(f"  실제 status      : {got}   -> {'일치' if ok else '어긋남'}")
        if corrections == "<KEY ABSENT>":
            lines.append("  corrections      : <KEY ABSENT>")
        else:
            lines.append(f"  corrections 건수 : {len(corrections)}")
            for item in corrections:
                lines.append(
                    f"    - pattern_key={item['pattern_key']} "
                    f"원문={item['original_span']!r} 교정={item['correction']!r}"
                )
        lines.append(f"  drill            : {body.get('drill', '<KEY ABSENT>')}")
        lines.append(f"  응답 키 전체     : {sorted(body.keys())}")
        lines.append("")
        verdicts.append((name, ok, f"{got} (기대 {expected})"))
        (EVIDENCE / f"TS-4-{name}-body.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (HERE / ".seeded_session_ids.json").write_text(json.dumps(ids, indent=2), encoding="utf-8")
    text = "\n".join(lines)
    (EVIDENCE / "TS-4-r2-rules-observed.txt").write_text(text, encoding="utf-8")
    print(text)
    print("판정 요약:")
    for name, ok, detail in verdicts:
        print(f"  {name}: {'PASS' if ok else 'FAIL'} — {detail}")
    return 0 if all(ok for _, ok, _ in verdicts) else 1


def cleanup() -> int:
    """이 회차가 심은 것만 지운다 — 격리 사용자에 매달린 행 전부."""
    before = q(f"select count(*) from learning_sessions where user_id='{USER_ID}'")
    q(
        "delete from analysis_jobs where utterance_id in "
        "(select u.id from utterances u join learning_sessions ls on ls.id=u.session_id "
        f"where ls.user_id='{USER_ID}')"
    )
    q(
        "delete from error_occurrences where utterance_id in "
        "(select u.id from utterances u join learning_sessions ls on ls.id=u.session_id "
        f"where ls.user_id='{USER_ID}')"
    )
    q(
        "delete from utterances where session_id in "
        f"(select id from learning_sessions where user_id='{USER_ID}')"
    )
    q(f"delete from learning_sessions where user_id='{USER_ID}'")
    q(f"delete from error_patterns where user_id='{USER_ID}'")
    q(f"delete from users where id='{USER_ID}'")
    # ⛔ 삭제 «명령의 성공»을 복원 근거로 쓰지 않는다 — 다시 읽어 0 인 것을 본다.
    report = [
        f"지우기 전 세션 수: {before}",
        f"users 잔여        : {q(f'select count(*) from users where id=' + chr(39) + USER_ID + chr(39))}",
        f"sessions 잔여     : {q(f'select count(*) from learning_sessions where user_id=' + chr(39) + USER_ID + chr(39))}",
        f"error_patterns 잔여: {q(f'select count(*) from error_patterns where user_id=' + chr(39) + USER_ID + chr(39))}",
        f"전체 users 수     : {q('select count(*) from users')}",
        f"전체 sessions 수  : {q('select count(*) from learning_sessions')}",
    ]
    text = "\n".join(report)
    (EVIDENCE / "TS-4-cleanup-verified.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    sys.exit(cleanup() if args.cleanup else run())
