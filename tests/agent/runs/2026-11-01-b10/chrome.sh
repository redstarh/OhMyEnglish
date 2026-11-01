#!/bin/sh
# 회차 b10 — 헤드리스 Chrome + 가짜 마이크(파일 반복 재생). 사용: chrome.sh <audio/ 아래 wav> <라벨>
R=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b10
P=/private/tmp/_b10-chrome-$2; rm -rf "$P"
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=9337 --user-data-dir="$P" \
  --no-first-run --disable-features=AudioServiceSandbox --use-fake-device-for-media-stream --use-fake-ui-for-media-stream \
  --use-file-for-fake-audio-capture="$R/audio/$1" --autoplay-policy=no-user-gesture-required \
  --window-size=1400,1000 about:blank 2> "$R/evidence/chrome-stderr-$2.log"
