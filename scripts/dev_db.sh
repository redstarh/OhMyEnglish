#!/usr/bin/env bash
# 로컬 dev PostgreSQL 헬퍼 — homebrew postgresql@17 (:5432).
#
# 2026-08-31 에 dev DB 를 podman 컨테이너(ohmy-pg · :5433 · postgres:16-alpine)에서 이리로 옮겼다
# (함정 H-T — podman 가상머신이 내려가면 게이트가 155 errors 로 무너졌다). 2026-09-17(TASK-149)에
# 그 폴백 경로를 이 스크립트에서 지웠다: podman 소켓이 이 호스트에서 붙지 않고(실측: 가상머신
# 마지막 기동이 2개월 전), 컨테이너 데이터는 이관 시점의 사본이라 되살리면 「앱이 보지 않는 DB 를
# 고치고 통과라고 보고하는」 거짓 신호가 된다.
#
# ⛔ 이 서버는 다른 앱과 공유된다 — StockAgent(stockagent · stocknews) · En-Coach(ohmyenglish 안의
#    en_coach 스키마 · en_coach_harness_test). 그래서 stop·reset 을 이 스크립트가 갖지 않는다.
#
# Usage: scripts/dev_db.sh {start|status}

set -euo pipefail

FORMULA="postgresql@17"
DSN="postgresql://ohmy:ohmy@localhost:5432/ohmyenglish"

usage() {
  cat >&2 <<EOF
Usage: $0 {start|status}

  start   ${FORMULA} 를 띄운다 (이미 떠 있으면 그대로 두고 status 를 낸다)
  status  어느 서버에 붙는지 · 버전 · 마이그레이션이 적용됐는지

  stop·reset 은 없다 — 이 서버를 StockAgent·En-Coach 와 공유하기 때문이다.
  이유와 대안은 docs/ops/shared-database-guide.md §4.5 를 본다.
EOF
  exit 1
}

# homebrew 의 postgresql@17 은 keg-only 라 psql 이 PATH 에 없다
# (tests/harness/psql_cli.py 가 같은 사정을 같은 순서로 해결한다).
psql_bin() {
  local found candidates last
  found="$(command -v psql || true)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return 0
  fi
  candidates=(/opt/homebrew/opt/postgresql@*/bin/psql)
  last="${candidates[${#candidates[@]} - 1]}"
  if [[ -x "$last" ]]; then
    echo "$last"
    return 0
  fi
  echo "psql 을 찾을 수 없다 — brew install ${FORMULA} 를 하거나 PATH 에 psql 을 넣어라." >&2
  return 1
}

service_started() {
  brew services list 2>/dev/null |
    awk -v f="$FORMULA" '$1 == f && $2 == "started" { found = 1 } END { exit found ? 0 : 1 }'
}

status() {
  local psql_exe out
  psql_exe="$(psql_bin)"

  echo "psql         : ${psql_exe}"
  echo "DSN          : ${DSN}"
  printf 'brew service : '
  brew services list 2>/dev/null |
    awk -v f="$FORMULA" '$1 == f { print $2; found = 1 } END { if (!found) print "(항목 없음)" }'

  if ! out="$("$psql_exe" "$DSN" -tAqc \
    "select current_database() || ' / server_version ' || current_setting('server_version')" 2>&1)"; then
    echo "접속         : 실패 — ${out}" >&2
    echo "→ 서버가 내려가 있으면 $0 start" >&2
    return 1
  fi
  echo "접속         : ${out}"
  # 기대값은 17.x 다. 16.x 가 나오면 지운 podman 폴백에 붙은 것이다 — inet_server_port() 는
  # 두 서버 모두 5432 를 돌려주므로 버전이 유일한 판별값이다(함정 H-V).

  if ! out="$("$psql_exe" "$DSN" -tAqc "select count(*) from schema_migrations" 2>&1)"; then
    echo "마이그레이션 : schema_migrations 표가 없다 — scripts/migrate.py 를 돌린다"
    return 0
  fi
  echo "마이그레이션 : ${out}건 적용됨"
}

start() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "brew 를 찾을 수 없다 — 이 헬퍼는 homebrew ${FORMULA} 를 전제한다." >&2
    return 1
  fi
  if service_started; then
    echo "${FORMULA} 은 이미 떠 있다."
  else
    brew services start "$FORMULA"
  fi

  # 기동 직후에는 소켓이 아직 안 열려 있을 수 있다 — 붙을 때까지 최대 10초 기다린다.
  local psql_exe i
  psql_exe="$(psql_bin)"
  for i in $(seq 1 20); do
    if "$psql_exe" "$DSN" -tAqc "select 1" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done

  status
}

refuse() {
  cat >&2 <<EOF
${1} 은 이 스크립트가 갖지 않는다 — :5432 는 StockAgent(stockagent · stocknews)와
En-Coach(ohmyenglish 안의 en_coach 스키마)가 함께 쓰는 서버다.

 · 서버를 세우면 그 두 앱도 함께 멈춘다. 정말 필요하면 brew services stop ${FORMULA} 를 직접 돌린다.
 · dev DB 를 drop/create 하면 en_coach 스키마와 그 데이터까지 사라진다
   (docs/ops/shared-database-guide.md §4.5). 마이그레이션은 scripts/migrate.py 가 drop 없이
   누적 적용하므로 재생성이 필요하지 않다.
EOF
  exit 2
}

case "${1:-}" in
  start) start ;;
  status) status ;;
  stop) refuse "stop" ;;
  reset) refuse "reset" ;;
  *) usage ;;
esac
