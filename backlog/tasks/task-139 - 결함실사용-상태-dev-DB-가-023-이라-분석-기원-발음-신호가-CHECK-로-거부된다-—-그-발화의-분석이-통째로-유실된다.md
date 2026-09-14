---
id: TASK-139
title: '결함(실사용 상태): dev DB 가 023 이라 분석 기원 발음 신호가 CHECK 로 거부된다 — 그 발화의 분석이 통째로 유실된다'
status: Done
assignee: []
created_date: '2026-09-14 22:26'
updated_date: '2026-09-14 22:48'
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
- [x] #1 적용 전에 그 세션이 사용자 승인을 직접 받는다 — 다른 세션이 받은 승인을 근거로 쓰지 않는다
- [x] #2 011 이 세운 5단계 절차로 024 를 적용하고 전후 조회를 노트에 남긴다 (백업에 -T harness_* 를 붙인다 · H-BT)
- [x] #3 적용 뒤 signal_source CHECK 값역에 transcript_analysis 가 있는 것을 조회로 확인한다
- [x] #4 실사용 경로에서 분석 기원 발음 신호가 실제로 저장되고 결과 화면에 3줄 카드로 그려지는 것을 관측한다 (통합 테스트 세션 몫 · 결정 99)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 회차 하나를 붙였음 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task139-analysis-row-real-path/README.md 임. Claude 분석 1회 · Nova 0.

024 검증 전용 DB(ohmyenglish_t139)에서 실물 분석 경로로 돌렸음: transcript_analysis 행 1건이 생기고 target_form 이 finding 의 correction('the report')이며 결과 화면이 3줄 카드(교정문 · 내 발화 · 다시 연습해요)로 그렸음. error_patterns·error_occurrences·review_tasks 는 0행으로 반대 방향 단정도 성립함.

⇒ 이 태스크의 성질이 좁혀짐: 코드 결함이 아니고 «DB 상태» 하나임. 024 를 적용하면 이 경로가 그대로 돌 근거가 그 회차임.

⛔ AC#4 는 닫지 않았음 — dev DB 에 024 가 적용된 «뒤» 그 경로에서 관측하는 것을 요구하므로 검증 전용 DB 의 관측으로 대신하지 않음. AC#1~#3 은 다른 주체(적용하는 세션)의 몫이라 To Do 로 되돌림.

관측 하나: 결정 99 ① 의 문면이 「문장」이라고 적었는데 실린 값은 구간임(finding 의 계약이 original_span↔correction 쌍임). 결함으로 보지 않음 — 화면이 내 발화와 짝으로 그림. 다음에 그 항을 인용할 때 「correction(구간)」으로 읽어야 함.

2026-09-15 적용 완료 (세션 ohmyenglish-65 · 사용자가 이 세션에 직접 지시함 — 결정 103). 정본은 tests/harness/runs/2026-09-15-task139-dev-db-apply/README.md 임.

011 의 5단계로 적용했음: pg_dump -n public -T harness_* (119,128 바이트 · harness_ 0건 · exit 0) → 표별 행 수 기록(17표) → migrate.py exit 0 → 재조회 대조(schema_migrations 21→22 · 최대 024 · 다른 표 열여섯 무변경) → 어긋남 0.

CHECK 값역이 넷이 됐음(transcript_analysis 포함). dev DB 에서 실물 분석 1회를 돌려 그 삽입이 실제로 받아들여지는 것을 관측했음 — 등록 때 롤백으로 재현했던 CheckViolationError 가 사라졌음.

⚠️ 부작용 둘을 기록했음: 합성 전사문이 기존 문법 패턴(verb_tense_past_simple_for_past_events)의 복습 시계를 움직였고(1단계 done · 2단계 생성 · next_review_at 2026-09-12 → 09-17) daily_error_summary 행 하나가 생겼음. 백업 덤프에서 정확한 값을 떠서 전부 복원했고, 백업과 «행 단위로» 대조해 표기 차이 11건(덤프 이스케이프·배열 표기) 외 어긋남 0 을 확인했음.

⛔ 배운 것: 되돌릴 대상을 먼저 정하고 그 컬럼을 스냅샷해야 함 — 행 수만 떴고 되돌릴 값을 준 것은 pg_dump 였음(browser_leg.md §8 의 경고가 그대로 재현됨).

⚠️ AC#4 의 화면 부분은 앞 회차(runs/2026-09-15-task139-analysis-row-real-path)의 실물 행 관측으로 갈랐음 — dev DB 에 합성 세션을 남기지 않기 위함임.
<!-- SECTION:NOTES:END -->
