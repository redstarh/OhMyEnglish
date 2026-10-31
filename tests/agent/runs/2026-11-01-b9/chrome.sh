#!/bin/sh
# 회차 b9 — 헤드리스 Chrome. 사용: chrome.sh <라벨> [nofake]  — nofake 면 가짜 장치·가짜 권한 UI 를 빼고 띄움(마이크 거부 시나리오용)
R=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b9
P=/private/tmp/_b9-chrome-$1; rm -rf "$P"
PORT=9335; FAKE="--use-fake-device-for-media-stream --use-fake-ui-for-media-stream"
[ "$2" = nofake ] && { PORT=9336; FAKE=""; }
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=$PORT --user-data-dir="$P" \
  --no-first-run --disable-features=AudioServiceSandbox $FAKE --autoplay-policy=no-user-gesture-required \
  --window-size=1400,1000 about:blank 2> "$R/evidence/chrome-stderr-$1.log"
