#!/bin/sh
# 회차 b12r4 — 헤드리스 Chrome. 사용: chrome.sh <라벨> [nofake|fake] [포트]  — nofake 면 가짜 장치·가짜 권한 UI 를 빼고 띄움(마이크 거부 시나리오용)
R=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b12/r4
P=/private/tmp/_b12r4-chrome-$1; rm -rf "$P"
PORT=9345; FAKE="--use-fake-device-for-media-stream --use-fake-ui-for-media-stream"
[ "$2" = nofake ] && { PORT=9346; FAKE=""; }
[ -n "$3" ] && PORT=$3
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=$PORT --user-data-dir="$P" \
  --no-first-run --disable-features=AudioServiceSandbox $FAKE --autoplay-policy=no-user-gesture-required \
  --window-size=1400,1000 about:blank 2> "$R/evidence/chrome-stderr-$1.log"
