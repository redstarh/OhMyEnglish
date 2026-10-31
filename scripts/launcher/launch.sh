#!/bin/zsh
# OhMyEnglish 실행 아이콘의 본체 (`TASK-291`).
#
# 하는 일: ① SSO 세션(kjihoon-bedrock)을 확인해 없거나 곧 끝나면 `aws sso login` 창을 띄움
# ② SSO 임시 자격증명으로 백엔드(:8002 · VOICE_ADAPTER=nova · dev DB)를 새로 띄움
# ③ 프런트(:3000)가 없으면 띄움 ④ 브라우저로 화면을 띄움.
#
# ⛔ Bedrock API 키(bearer)는 쓰지 않음 — Nova 양방향 스트림이 API 키를 거부함(2026-11-01 실측).
# ⛔ 앱의 Nova SDK 는 SSO 프로필을 읽지 않음 — 그래서 임시 키를 환경 변수로 넘김(TASK-288).
# ⚠️ 임시 키가 만료되면 따라 하기 판정이 「쓸 수 없어요」가 됨 — 아이콘을 다시 누르면 다시 로그인함.

set -u

REPO="${0:A:h:h:h}"
PROFILE="${OMY_SSO_PROFILE:-kjihoon-bedrock}"  # 바꿔 끼우는 것은 시험용임
MIN_VALID_SECONDS=1800  # 이보다 짧게 남은 세션은 미리 다시 로그인함
LOG_DIR="$HOME/Library/Logs/OhMyEnglish"
AWS_CLI="/opt/homebrew/bin/aws"
APP_URL="http://localhost:3000"

mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/launcher.log" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 실행"

export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# 셸 설정에서 물려받을 수 있는 자격증명을 비움 — 앱이 엉뚱한 키를 쓰지 않게.
unset AWS_BEARER_TOKEN_BEDROCK AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN \
  AWS_CREDENTIAL_EXPIRATION AWS_PROFILE DATABASE_URL VOICE_ADAPTER

notify() {
  osascript -e "display notification \"$1\" with title \"OhMyEnglish\"" >/dev/null 2>&1
}

fail() {
  echo "실패: $1"
  osascript -e "display dialog \"$1\n\n기록: $LOG_DIR/launcher.log\" with title \"OhMyEnglish\" buttons {\"확인\"} default button 1 with icon stop giving up after 60" >/dev/null 2>&1
  exit 1
}

owned_by() {  # $1 = pid · $2 = 기대하는 작업 폴더 — 그 폴더에서 뜬 프로세스인가
  [[ "$(lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')" == "$2" ]]
}

wait_http() {  # $1 = URL · $2 = 초
  local i
  for i in $(seq 1 "$2"); do
    [[ "$(curl -s -o /dev/null -w '%{http_code}' "$1")" == "200" ]] && return 0
    sleep 1
  done
  return 1
}

# ── ① SSO 세션 ───────────────────────────────────────────────────────────────
seconds_left() {
  local exp
  exp=$("$AWS_CLI" configure export-credentials --profile "$PROFILE" --format env 2>/dev/null \
    | sed -n 's/^export AWS_CREDENTIAL_EXPIRATION=//p')
  [[ -z "$exp" ]] && { echo 0; return; }
  echo $(( $(date -j -u -f "%Y-%m-%dT%H:%M:%S" "${exp%%+*}" +%s 2>/dev/null || echo 0) - $(date -u +%s) ))
}

left=$(seconds_left)
if (( left < MIN_VALID_SECONDS )); then
  echo "SSO 세션 없음 또는 곧 만료(${left}초) — 로그인 창을 띄움"
  notify "AWS SSO 로그인 창을 띄웁니다. 브라우저에서 승인해 주세요."
  "$AWS_CLI" sso login --profile "$PROFILE" || fail "AWS SSO 로그인에 실패했습니다."
  left=$(seconds_left)
  (( left > 0 )) || fail "SSO 로그인 뒤에도 자격증명을 받지 못했습니다."
else
  echo "SSO 세션 유효(${left}초 남음)"
fi

eval "$("$AWS_CLI" configure export-credentials --profile "$PROFILE" --format env)" \
  || fail "SSO 임시 자격증명을 꺼내지 못했습니다."
[[ -n "${AWS_SESSION_TOKEN:-}" ]] || fail "SSO 임시 자격증명이 비어 있습니다."

# ── ② 백엔드 — 새 자격증명을 싣도록 늘 다시 띄움 ─────────────────────────────
old=$(lsof -nP -iTCP:8002 -sTCP:LISTEN -t 2>/dev/null)
if [[ -n "$old" ]]; then
  # ⛔ 이 리포의 백엔드만 내림 — 다른 작업 트리의 같은 앱을 내리지 않게(codex 리뷰).
  if owned_by "$old" "$REPO/app/backend"; then
    echo "기존 백엔드(pid $old)를 내림"
    kill "$old"
    for i in $(seq 1 10); do lsof -nP -iTCP:8002 -sTCP:LISTEN -t >/dev/null 2>&1 || break; sleep 1; done
  else
    fail "포트 8002 를 이 리포 밖의 프로그램이 쓰고 있습니다."
  fi
fi
(
  cd "$REPO/app/backend" || exit 1
  VOICE_ADAPTER=nova nohup .venv/bin/uvicorn app.api.main:app --port 8002 >>"$LOG_DIR/backend.log" 2>&1 &
)
wait_http "http://localhost:8002/api/course" 30 || fail "백엔드가 30초 안에 응답하지 않았습니다."
echo "백엔드 응답함 (nova · dev DB)"

# ── ③ 프런트 — 떠 있으면 그대로 씀 ──────────────────────────────────────────
front=$(lsof -nP -iTCP:3000 -sTCP:LISTEN -t 2>/dev/null | head -1)
if [[ -n "$front" ]] && ! owned_by "$front" "$REPO/app/frontend"; then
  fail "포트 3000 을 이 리포 밖의 프로그램이 쓰고 있습니다."
fi
if [[ -z "$front" ]]; then
  echo "프런트를 띄움"
  # nvm.sh 는 정의되지 않은 변수를 읽으므로 그 구간만 `set -u` 를 끔.
  set +u
  source "$HOME/.nvm/nvm.sh" && nvm use default >/dev/null
  nvm_ok=$?
  set -u
  (( nvm_ok == 0 )) || fail "Node(nvm)를 찾지 못했습니다."
  (
    cd "$REPO/app/frontend" || exit 1
    nohup npm run dev >>"$LOG_DIR/frontend.log" 2>&1 &
  )
fi
wait_http "$APP_URL" 90 || fail "화면 서버가 90초 안에 응답하지 않았습니다."
echo "프런트 응답함"

# ── ④ 화면 ──────────────────────────────────────────────────────────────────
open "$APP_URL"
notify "준비됐습니다. 실제 Nova 판정은 약 $(( left / 3600 ))시간 동안 쓸 수 있어요."
echo "완료"
