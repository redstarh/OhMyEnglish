#!/bin/sh
# 회차 b14 — macOS say 로 조각을 만들고 16kHz mono wav 로 바꿈
A=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b14/audio
mk(){ say -v "$1" -o /private/tmp/_b14-$2.aiff "$3" && afconvert -f WAVE -d LEI16@16000 -c 1 /private/tmp/_b14-$2.aiff $A/raw-$2.wav && rm /private/tmp/_b14-$2.aiff && echo "ok $2"; }
mk Samantha e1 "Yesterday I go to the office and I meet my manager."
mk Samantha e2 "I am work at IT company. I am software tester."
mk Samantha e3 "My manager say the project is late, so we has a meeting."
mk Samantha e4 "Last week I finish the test report and I send it to my team."
mk Samantha cmdend "Hey, end the lesson."
mk Samantha yes "Yes."
mk Samantha cmdpause "Hey, pause the lesson."
mk Samantha cmdresume "Hey, continue the lesson."
mk Yuna koend "헤이, 학습 종료."
mk Yuna koyes "네."
mk Yuna kopause "헤이, 일시 정지."
mk Yuna koresume "헤이, 학습 계속."
