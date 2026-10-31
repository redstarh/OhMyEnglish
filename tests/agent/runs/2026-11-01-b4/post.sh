#!/bin/sh
# 회차 b4 — 앱 API 로 진도를 놓는다. 사용: post.sh <day> <json>
curl -sS -X POST -H 'Content-Type: application/json' -d "$2" -w ' %{http_code}\n' http://localhost:8002/api/course/days/$1/progress
echo "$(date -u +%FT%TZ) day=$1 $2" >> /Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b4/evidence/api-writes.log
