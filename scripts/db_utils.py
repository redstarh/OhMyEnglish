"""DB DSN 계산 + drop/create 재생성 — 테스트·스모크·마이그레이션 스크립트가 공유하는
독립 ops 유틸리티.

앱 패키지(`app.*`)를 import하지 않는다 — `tests/conftest.py`, `scripts/smoke_analysis.py`,
`scripts/migrate.py`가 각각 `asyncpg`만 있으면 돌 수 있어야 하고(앱 가상환경이
없어도), 이 셋이 DSN 계산과 "drop/create + 마이그레이션 적용" 패턴을 따로 복붙해
갈라지는 것을 막는다.

`recreate_database`는 대상 DB를 매 실행마다 통째로 지우고 새로 만드는 **파괴적**
연산이다 — 테스트/스모크 전용 DB에만 쓴다. dev DB에 적용하는 `scripts/migrate.py`의
`apply_migrations`는 이것과 의도적으로 다른 함수다: drop 없이 파일별로
`schema_migrations`에 기록해 멱등하게 누적 적용한다(이유는 그 함수의 docstring 참조).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

# :5432는 homebrew `postgresql@17` (launchd로 부팅 시 자동 기동)이다. 2026-08-31에
# podman `ohmy-pg`(:5433)에서 이리로 옮겼다 — podman 가상머신이 내려가면 게이트가
# 155 errors로 무너지던 의존을 없애기 위해서다(함정 H-T). :5433 컨테이너는 폴백으로 남아 있다.
# ⚠️ 이 인스턴스는 StockAgent와 **공유**한다(`stockagent`·`stocknews*` DB). 인스턴스 단위
#    조작(재시작·ALTER SYSTEM)은 남의 서비스를 건드린다 — DB 단위로만 다룬다.
# ⚠️ 인스턴스 기본 TimeZone은 `Asia/Seoul`이지만 역할 `ohmy`에 UTC를 고정해 두었다
#    (`alter role ohmy set TimeZone='UTC'`). 그래야 함정 H-S가 계속 보인다.
DEFAULT_DEV_DSN = "postgresql://ohmy:ohmy@localhost:5432/ohmyenglish"


def base_dsn() -> str:
    """`DATABASE_URL` 환경변수, 없으면 로컬 dev DB DSN."""
    return os.environ.get("DATABASE_URL", DEFAULT_DEV_DSN)


def dsn_for(db_name: str) -> str:
    """`base_dsn()`과 같은 서버·인증정보를 쓰되 DB명만 바꾼 DSN."""
    parts = urlsplit(base_dsn())
    return urlunsplit((parts.scheme, parts.netloc, f"/{db_name}", parts.query, parts.fragment))


async def recreate_database(db_name: str, migrations_dir: Path) -> str:
    """`db_name`을 drop/create하고 `migrations_dir/*.sql`을 순서대로 적용한다.

    테스트·스모크 전용 DB를 매 실행마다 깨끗한 상태로 되돌리기 위한 파괴적
    연산이다 — dev DB에는 절대 쓰지 않는다(그건 `migrate.py`의 `apply_migrations`
    몫이다). 적용된 DB의 DSN을 돌려준다.
    """
    admin_conn = await asyncpg.connect(dsn=dsn_for("postgres"))
    try:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin_conn.close()

    dsn = dsn_for(db_name)
    conn = await asyncpg.connect(dsn=dsn)
    try:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            await conn.execute(sql_file.read_text())
    finally:
        await conn.close()
    return dsn
