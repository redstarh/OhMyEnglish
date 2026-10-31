#!/bin/sh
# 회차 b8 — 헤드리스 Chrome. 사용: chrome.sh <wav 이름(audio/ 아래)> <라벨> [default]  (default 면 자동 재생 기본 정책)
R=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b8
A=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b6/audio
F="$A/$1"; case "$1" in /*) F="$1";; esac
P=/private/tmp/_b8-chrome-$2; rm -rf "$P"
AP="--autoplay-policy=no-user-gesture-required"; [ "$3" = default ] && AP=""
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=9334 --user-data-dir="$P" \
  --no-first-run --disable-features=AudioServiceSandbox --use-fake-device-for-media-stream --use-fake-ui-for-media-stream \
  --use-file-for-fake-audio-capture="$F" $AP --window-size=1200,1400 about:blank 2> "$R/evidence/chrome-stderr-$2.log"
