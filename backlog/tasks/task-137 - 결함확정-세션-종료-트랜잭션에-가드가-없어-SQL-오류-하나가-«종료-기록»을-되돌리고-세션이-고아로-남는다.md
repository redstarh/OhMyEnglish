---
id: TASK-137
title: '결함(확정): 세션 종료 트랜잭션에 가드가 없어 SQL 오류 하나가 «종료 기록»을 되돌리고 세션이 고아로 남는다'
status: To Do
assignee: []
created_date: '2026-09-13 23:29'
labels: []
dependencies: []
ordinal: 159000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
발음 축(ohmyenglish-d9)이 두 팔로 갈라 재서 확정한 관측임(2026-09-14 · 검증 전용 DB ohmyenglish_v020 + :8014 + stub). 팔 A: sound_check 컬럼이 있으면 세션이 completed 로 닫히고 ended_at 이 서며 예외 0건. 팔 B: 그 컬럼을 drop 해 019 상태를 재현하면 UndefinedColumnError 가 나고 ⛔ 세션이 active · ended_at null 로 남음. 기전: check_recorded_sounds 가 end_session·resolve_dangling 과 «같은 트랜잭션»에 있고 그 블록에 try 가 없어 예외가 종료 기록까지 되돌림. ⚠️ dev 피해는 0건임 — 그 창에 mode='pronunciation' 세션이 0건이었고 지금 active 도 0건임. ⚠️ I-4 리퍼가 그 고아를 닫는지는 «재지 않았음»(발음 축이 추측으로 적지 않았음). ⛔ 판단은 개발 세션 몫이라고 넘겨 왔음 — 즉 이 태스크는 「종료 기록을 무엇으로부터 보호하는가」를 정하는 것임. 020 이 적용됐으므로 그 컬럼의 직접 위험은 해소됐고 남은 것은 구조적 취약성임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 종료 기록이 «부가 조회» 실패로 되돌아가지 않는 것을 단정으로 못박는다 — 무력화(그 조회를 일부러 실패시킴)로 red 를 먼저 본다
- [ ] #2 부가 조회 셋 가운데 어느 것이 종료 기록과 같은 트랜잭션에 있어야 하는지 가른다 — 전부 감싸면 「기록은 됐는데 판정이 없다」가 조용해질 수 있으므로 근거를 적는다
- [ ] #3 I-4 리퍼가 그 고아를 실제로 닫는지 확인한다 — 발음 축이 재지 않은 자리이고 추측으로 닫지 않는다
<!-- AC:END -->
