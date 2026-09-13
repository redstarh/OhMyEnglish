---
id: TASK-66.9
title: '운영: dev DB 에 022 를 적용한다 — 승인 사안'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 23:16'
labels: []
dependencies:
  - TASK-66.8
parent_task_id: TASK-66
ordinal: 157000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 9. ⛔ 사용자 승인 없이 착수하지 않는다. dev DB 는 019 까지 적용돼 있고 020(발음 축)·021(내 것)이 미적용이라 순서와 소유가 함께 걸린다 — 발음 축과의 조율이 선행된다. 011 의 적용 5단계를 따른다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 승인을 받고 020·021 과의 순서를 정한다
- [x] #2 적용 전후 조회 출력을 원장에 남긴다 — migrate.py 는 조용한 성공이라 출력만으로 판정하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4) — 사용자 승인을 이 세션에서 직접 받았음.

⛔ 동료 세션(ohmyenglish-d9)의 「사용자 승인을 받았음」을 근거로 쓰지 않았음 — 세션 사이의 전달이 승인을 옮기지 못함. 그쪽도 그 판단이 옳다고 정정해 왔음. 그쪽에서 받은 것은 «사실»뿐임: dev DB 에 pronunciation_attempts.sound_check 가 없고 origin 코드가 9곳에서 그것을 읽으며 그 SQL 이 세션 종료 트랜잭션(try 없음)에 있음. ⚠️ 예외가 실제로 나는지는 미실증임(그쪽도 단정하지 않았음).

011 의 5단계를 따랐음.
① 백업: /tmp/dbbackup/ohmyenglish-2026-09-14-pre022.sql (116KB · CREATE TABLE 16). ⚠️ 첫 시도가 실패했음 — pg_dump -n public 이 harness_pattern_baseline 에서 permission denied 를 냈음(그 표 둘의 소유자가 redstar 임). -T 'harness_*' 로 빼고 성공했음. 즉 H-? 의 「-n public 이면 된다」는 서술이 이 리포에서는 부족함.
② 적용 전: schema_migrations 17(max 019) · users 1 · learning_sessions 17 · utterances 128 · error_patterns 9 · pronunciation_attempts 7 · shadowing_items 1 · analysis_jobs 57 · llm_calls 4.
③ 적용: migrate.py exit 0(출력 없음 — 조용한 성공이라 조회로 확인함).
④ 적용 후: schema_migrations 20(max 022_shadowing_clip_audio.sql) · 나머지 행 수 전부 동일 ⇒ 데이터 변경 0.
   020·021·022 가 같은 초에 적용됐음(2026-09-13 23:15:57 UTC).
   반영 확인: 시드가 0.00~17.36 + audio_filename · pronunciation_attempts.sound_check 컬럼 있음(nullable) · llm_calls_purpose_check 값역 6개(generate_scenario·summarize_session 포함) · shadowing_items 의 제약 둘.
⑤ 어긋남 0건이라 멈추지 않았음.

⚠️ 남은 확인 하나 — 발음 경로가 020 적용 뒤 실제로 도는지는 발음 축이 통합 테스트로 볼 몫임(그쪽 역할이 그것으로 정리됐음).
<!-- SECTION:NOTES:END -->
