---
id: TASK-139
title: '결함(실사용 상태): dev DB 가 023 이라 분석 기원 발음 신호가 CHECK 로 거부된다 — 그 발화의 분석이 통째로 유실된다'
status: To Do
assignee: []
created_date: '2026-09-14 22:26'
labels: []
dependencies: []
ordinal: 178000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-15 세션 ohmyenglish-65 이 통합 관측 중에 찾았음. 코드는 마이그레이션 024 를 전제하는데 공유 dev DB 는 023 임(직접 조회: schema_migrations 최대가 023_weekly_reports.sql · signal_source CHECK 가 nova_tool·korean_transcript·agent_reprompt 셋뿐).

재현(2026-09-15 · 공유 dev DB · 트랜잭션을 열고 롤백해 커밋 0): pronunciation_attempts 에 signal_source='transcript_analysis' 행을 넣으면 CheckViolationError(pronunciation_attempts_signal_source_check)로 거부됨. 회차 전후 표 건수 7 로 같음.

영향: analysis.py:524 의 record_transcript_analysis_signal 이 발음 기원 finding 을 그 값으로 넣고, 그 호출이 나머지 finding 저장과 «같은 트랜잭션» 안에 있음(analysis.py:531·535). 즉 발음 기원 오류가 하나라도 나오면 그 발화의 분석 전체가 롤백되고, jobs.py 의 재시도 5회를 소진한 뒤 terminal failed 가 됨 ⇒ 문법 교정까지 함께 유실됨.

⛔ 코드 결함이 아니라 «운영 상태» 결함임 — 024 파일은 리포에 있고 커밋됐음(TASK-88). 결정 93 이 024 발급을 승인했고 그 시점에는 아직 파일이 없어 「024 는 아직 쓰지 않았다」로 적혀 있음. 즉 적용 승인을 받은 적이 없음.

⛔ 이 태스크의 주체는 개발 세션이거나 사용자임 — 마이그레이션을 dev DB 에 적용하는 것은 사전 승인 밖이고, 승인은 세션을 넘어 이동하지 않으므로 «적용하는 세션»이 자기 세션에서 직접 받아야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 적용 전에 그 세션이 사용자 승인을 직접 받는다 — 다른 세션이 받은 승인을 근거로 쓰지 않는다
- [ ] #2 011 이 세운 5단계 절차로 024 를 적용하고 전후 조회를 노트에 남긴다 (백업에 -T harness_* 를 붙인다 · H-BT)
- [ ] #3 적용 뒤 signal_source CHECK 값역에 transcript_analysis 가 있는 것을 조회로 확인한다
- [ ] #4 실사용 경로에서 분석 기원 발음 신호가 실제로 저장되고 결과 화면에 3줄 카드로 그려지는 것을 관측한다 (통합 테스트 세션 몫 · 결정 99)
<!-- AC:END -->
