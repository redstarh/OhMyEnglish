#!/bin/sh
# 회차 b5 — D5 준비: Day 1~5 를 앱 API 로 완료하고 Day 6 을 마지막 문장(Unit 113 · 문장 5)에 둔다. 사용: d5setup.sh <완료 횟수 cc>
D=$(dirname "$0"); CC=$1
for pair in 1:1 2:22 3:42 4:63 5:83; do day=${pair%%:*}; unit=${pair##*:}
  sh "$D/post.sh" $day "{\"position_sec\":0,\"unit\":$unit,\"sentence_index\":0,\"completed\":true,\"completed_count\":$CC}"; done
sh "$D/post.sh" 6 "{\"position_sec\":0,\"unit\":113,\"sentence_index\":4,\"completed\":false,\"completed_count\":$CC}"
curl -s localhost:8002/api/course | python3 -c 'import json,sys;j=json.load(sys.stdin);print("cycle",j["cycle"],"current_day",j["current_day"],[(d["day"],d["progress"] and (d["progress"]["unit"],d["progress"]["sentence_index"],d["progress"]["position_sec"],d["progress"]["completed_count"])) for d in j["days"]])'
