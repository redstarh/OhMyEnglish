#!/bin/zsh
# TS-24 AC#1 축 A — daily_error_summary 읽기 경로의 「오늘」이 users.timezone 컬럼에서 오는가.
# 승인 조건 넷을 순서로 박아 둠: ① 원값 먼저 읽어 남김 ② 복원을 «읽어» 확인 ③ ALTER 계열 금지
# (행 값 UPDATE 만) ④ timestamptz 를 변환해 UPDATE 하지 않음(텍스트 컬럼 하나만 건드림).
set -u
cd /Users/redstar/MyProject/OhMyEnglish
P=app/backend/.venv/bin/python
Q=/tmp/b3_q.py
E=tests/agent/runs/2026-09-19-b3/evidence/32-axisA-timezone-discrimination.txt
UID_=00000000-0000-0000-0000-000000000001

exec > >(tee "$E") 2>&1

echo "### ① 원값을 먼저 읽어 남김 (되돌릴 근거)"
ORIG=$($P $Q "select timezone from users where id='$UID_'" | tail -1)
echo "users.timezone (원값) = [$ORIG]"
echo "측정 시각: $($P $Q "select now(), current_date" | tail -1)"
if [[ "$ORIG" != "Asia/Seoul" ]]; then
  echo "⛔ 원값이 예상과 다름 — 다른 세션이 이미 바꿨을 수 있어 중단함"
  exit 1
fi

echo
echo "### ② 판별용 요약 행 둘을 심음 (같은 사용자 · 두 날짜 · 개수가 다름)"
$P $Q "insert into daily_error_summary (id,user_id,summary_date,timezone,occurrence_count,pattern_count,patterns,computed_at) values
 ('b3000000-0000-0000-0000-0000000000e1','$UID_','2026-09-19','Asia/Seoul',91,1,'[{\"pattern_key\":\"b3_utc_side\",\"category\":\"grammar\",\"target_form\":\"UTC 날짜 쪽\",\"occurrences\":91,\"example\":{\"original_span\":\"a\",\"correction\":\"b\",\"reason\":\"c\"}}]'::jsonb,'2026-09-19 06:00:00+00'),
 ('b3000000-0000-0000-0000-0000000000e2','$UID_','2026-09-18','Asia/Seoul',82,1,'[{\"pattern_key\":\"b3_midway_side\",\"category\":\"grammar\",\"target_form\":\"Midway 날짜 쪽\",\"occurrences\":82,\"example\":{\"original_span\":\"a\",\"correction\":\"b\",\"reason\":\"c\"}}]'::jsonb,'2026-09-18 06:00:00+00')
 returning summary_date" | tail -2

echo
echo "### ③ 원값(Asia/Seoul)으로 읽음 — current_date(UTC) 와 같은 날짜라 판별력이 없는 상태"
curl -sS http://localhost:8002/api/daily-summary | $P -c 'import json,sys;d=json.load(sys.stdin);print("summary_date=",d["summary_date"],"occurrence_count=",d["occurrence_count"])'

echo
echo "### ④ 행 값만 UPDATE — Pacific/Midway (UTC-11). ⛔ ALTER DATABASE/SYSTEM 을 쓰지 않음"
FLIP_AT=$($P $Q "update users set timezone='Pacific/Midway' where id='$UID_' returning timezone" | tail -1)
echo "바꾼 값 = [$FLIP_AT] · 바꾼 시각 = $($P $Q "select now()" | tail -1)"

echo
echo "### ⑤ 같은 엔드포인트를 다시 읽음 — 여기가 판정 지점임"
echo "   기대: 컬럼을 읽으면 2026-09-18 / 82 · current_date(UTC) 를 읽으면 2026-09-19 / 91"
curl -sS http://localhost:8002/api/daily-summary | $P -c 'import json,sys;d=json.load(sys.stdin);print("summary_date=",d["summary_date"],"occurrence_count=",d["occurrence_count"],"patterns[0].target_form=",d["patterns"][0]["target_form"] if d["patterns"] else None)'
echo "   /api/history 의 첫 줄도 함께 봄 (같은 「오늘」을 쓰는지)"
curl -sS http://localhost:8002/api/history | $P -c 'import json,sys;d=json.load(sys.stdin);print("days[0].day=",d["days"][0]["day"],"| streak=",d["streak"])'

echo
echo "### ⑥ 복원하고 «읽어» 확인 — 명령 성공을 복원 근거로 쓰지 않음"
$P $Q "update users set timezone='$ORIG' where id='$UID_'" >/dev/null 2>&1
BACK=$($P $Q "select timezone from users where id='$UID_'" | tail -1)
echo "복원 뒤 읽은 값 = [$BACK] · 복원 시각 = $($P $Q "select now()" | tail -1)"
if [[ "$BACK" == "$ORIG" ]]; then echo "복원 확인됨 (원값과 같음)"; else echo "⛔ 복원 실패 — 값이 [$BACK] 임"; fi

echo
echo "### ⑦ 복원 뒤 엔드포인트가 원래 날짜로 돌아왔는지"
curl -sS http://localhost:8002/api/daily-summary | $P -c 'import json,sys;d=json.load(sys.stdin);print("summary_date=",d["summary_date"],"occurrence_count=",d["occurrence_count"])'
