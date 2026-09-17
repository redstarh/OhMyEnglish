#!/usr/bin/env python3
"""하네스 도구가 dev DB에 psql로 질의할 때 쓰는 공용 헬퍼.

이전에는 `inject_errors.py`와 `ws_session.py`가 `podman exec -i ohmy-pg psql …`을 각자
하드코딩했다. 2026-08-31에 dev DB가 homebrew `postgresql@17`(:5432)로 옮겨지면서 그 경로는
**폴백 컨테이너에 남은 사본**을 건드리게 됐다 — 주입은 성공하는데 앱이 보는 DB에는 없는
상태가 되어 하네스가 조용히 잘못된 판정을 낸다(함정 H-T).

지금은 `DATABASE_URL`을 그대로 psql에 넘기므로 설정이 가리키는 DB를 따라간다. 그 폴백 컨테이너는
2026-09-17에 도구에서 지웠다(`TASK-149`) — dev DB 는 homebrew :5432 하나다.

⚠️ `DATABASE_URL`은 **환경변수**로 읽는다(`db_utils.base_dsn`). `app/backend/.env`만 고치면
이 헬퍼에는 반영되지 않는다 — 다른 DB를 겨눌 때는 `export DATABASE_URL=...`로 넘긴다.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from glob import glob
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from db_utils import base_dsn  # noqa: E402

# homebrew의 postgresql@17은 keg-only라 psql이 PATH에 없다 (2026-08-31 실측).
_BREW_PSQL_GLOB = "/opt/homebrew/opt/postgresql@*/bin/psql"


def psql_binary() -> str:
    """psql 실행 파일 경로. PATH → homebrew keg 순으로 찾는다."""
    found = shutil.which("psql")
    if found:
        return found
    candidates = sorted(glob(_BREW_PSQL_GLOB), reverse=True)
    if candidates:
        return candidates[0]
    raise RuntimeError(
        "psql을 찾을 수 없다. `brew install postgresql@17`을 하거나 PATH에 psql을 넣어라. "
        f"찾아본 곳: PATH, {_BREW_PSQL_GLOB}"
    )


def psql(sql: str) -> str:
    """`DATABASE_URL`이 가리키는 DB에 SQL 한 줄을 던지고 stdout(strip)을 돌려준다.

    ⛔ **`-q` 가 없으면 `insert … returning` 의 반환값 뒤에 명령 태그가 붙는다.** 2026-09-17 실측:
    `.harness/run_id.txt` 가 `<uuid>\\nINSERT 0 1` **47바이트**로 적혔다(36바이트여야 한다).
    `strip()` 은 앞뒤 «공백»만 걷으므로 그 태그를 걷지 못한다 — 그 파일을 SQL 에 그대로 넣는
    `ws_session.py`·`inject_errors.py` 가 1회차에서 실제로 그 오염(`INSERT01`)에 걸렸고
    `tests/harness/README.md` 가 경고로 남겨 두었다.
    ⚠️ **`select` 로만 확인하면 이 결함이 드러나지 않는다** — `select` 에는 태그가 없다. 그래서 이
    함수를 고칠 때는 반드시 **`insert … returning` 으로** 재현해 본다.
    """
    out = subprocess.run(
        [psql_binary(), base_dsn(), "-q", "-tAc", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()
