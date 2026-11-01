#!/bin/sh
# 회차 b14 — 세션 하나의 학습자 발화·분석 job 조회 (읽기 전용). 사용: q.sh <세션 id> <라벨>
PY=/Users/redstar/MyProject/OhMyEnglish/app/backend/.venv/bin/python; D=/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b14
cd $D && $PY db.py paid sql "select u.sequence_no, u.speaker, u.utterance_type, left(u.transcript,60) t, u.created_at, j.job_type, j.status, j.attempts, left(j.last_error,120) err, j.created_at job_at from utterances u left join analysis_jobs j on j.utterance_id=u.id where u.session_id='$1' order by u.sequence_no, j.created_at" > evidence/db-$2-utterances.json
$PY db.py paid sql "select job_type, status, attempts, utterance_id is null as no_utt, left(last_error,160) err, created_at, available_at from analysis_jobs where session_id='$1' and utterance_id is null" > evidence/db-$2-session-jobs.json
$PY db.py paid sql "select id, status, started_at, ended_at, paused from learning_sessions where id='$1'" > evidence/db-$2-session.json 2>&1 || $PY db.py paid sql "select * from learning_sessions where id='$1'" > evidence/db-$2-session.json
python3 -c '
import json,sys
for r in json.load(open(sys.argv[1])):
    if r["speaker"]!="user" and r["job_type"] is None: continue
    print(r["sequence_no"], r["speaker"], r["utterance_type"], repr(r["t"]), "|", r["job_type"], r["status"], r["attempts"], r["err"] or "")' evidence/db-$2-utterances.json
echo "-- session jobs"; cat evidence/db-$2-session-jobs.json | python3 -c 'import json,sys; [print(r["job_type"],r["status"],r["attempts"],r["err"],r["created_at"]) for r in json.load(sys.stdin)]'
echo "-- session"; head -c 600 evidence/db-$2-session.json
