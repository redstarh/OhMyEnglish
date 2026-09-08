---
id: TASK-37
title: '실행: 테스트 하네스 5차수 — 미실행 Nova N6~N13 + 회귀 + tests/** 정리'
status: In Progress
assignee: []
created_date: '2026-09-07 17:50'
updated_date: '2026-09-08 23:42'
labels: []
dependencies:
  - TASK-44
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md D절(테스트 하네스 차수 원장)에서 이관. 원장은 tests/harness/runs/ROUNDS.md. 4/10 차수 사용, 미해결 앱 결함 0건. 5차수가 반드시 포함해야 하는 관측 3건: A-3(실물 tool 스키마 대조) · A-4(agent_reprompt 미충족 구간의 크기) · B-2(발음 개입 없는 일반 대화 1턴이 3차수 N5와 같은가, 대조군). 일부러 빼는 것: N9(세션 롤오버, 8분 이상 실음성 필요) · N10(무응답형 자격증명 실패, .env 편집 금지 제약).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 미실행 Nova N6·N7·N8·N11·N12·N13 시나리오를 실행한다
- [x] #2 B1~B4를 재확인하고 라이트·다크 5상태를 확인한다
- [x] #3 회귀 A1·A2·E4·E5·E6·D1·D2 + 프론트 npx tsc --noEmit 을 돌린다
- [x] #4 P8 + p2 쌍 + P7 재캡처를 수행한다
- [x] #5 신규 P9~P12(발음 복습 주기 시나리오)를 실행한다
- [x] #6 tests/** ruff 6건·format 4건을 정리한다(H-L 기준선 대조)
- [x] #7 스파이크 nova 스키마와 앱 상수를 대조해 A-3 tool 스키마 확인을 닫는다
- [ ] #8 A-4(agent_reprompt 미구현 구간)와 B-2(대조군) 관측 결과를 기록한다
- [x] #9 O-1(LOW) — agent 전사문에 선행 개행이 붙는 것을 5차수에서 다시 관측한다: Nova 가 '\nWhat time do you…' 를 보내고 save_final_transcript 가 그대로 저장한다. 4차수에서 두 세션(p1k·u1)에 재현됐고 agent 발화라 분석 job 이 없어 무해하다 — 재현하면 기록만 남기고, 사라졌으면 사라졌다고 적는다 (TASKS.md E절에서 이관, 소유자가 5차수였다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 착수 — 캡틴 결정 38 로 실물 Nova·마이크 세션 1회를 승인받았음(결정 20 이 유보한 것). 실행 순서를 실물 요구 여부로 갈랐음: ① 실물 0회 — AC#6(tests/** ruff·format) · AC#7(스파이크 스키마 대조) ② stub 스택 — AC#2(B1~B4 · 라이트/다크 5상태) · AC#3 의 A1·A2·D1·D2 + 프론트 tsc ③ 실물 1회 — AC#1 의 N6·N7·N8·N13 · AC#4 · AC#8 · AC#9 · AC#3 의 E4~E6(워커) 와 TASK-13·24·36 관측을 같은 세션에 실음 ④ AC#5 는 P9~P12 시나리오가 아직 없어 신설이 선행임. 근거: browser_leg.md §9 가 C1·C2·C5 를 stub·실물 0회로 명시함.

진행 (2026-09-09) — AC#6 ✅(게이트 밖 ruff·format 기준선 6·4 → 0·0. 커밋 51fdd72) · AC#5 작성 ✅ 실행 미완(P9~P12 를 scenarios-P §4.1 에 신설. 커밋 a82aa21) · AC#7 절반(스파이크가 앱 상수를 그대로 보내게 바꿨고 정적 대조 완료. 실물 왕복 미실행) · 실물 세션 1회의 순서를 착수 전에 못박음(커밋 d766efb). 곁가지 함정 3건 등록: H-AR(ruff format 의 N files 가 .md 를 함께 셈) · H-AO 번호 충돌 정리 → H-AQ · H-AS(문서 기동 명령이 워커를 켬 — 기본값 True 이고 .env 에 키가 없음. 하네스 문서 3곳 수정. 커밋 a5c62af). 브라우저 다리(AC#2 + AC#3 의 A1)는 frontend-verifier 에 위임해 진행 중임 — 등록부 §1 이 그 지시를 손으로 대체한 것을 실패로 기록했으므로 방식을 지켰음.

진행 2 (2026-09-09) — AC#2 ✅(라이트·다크 5상태. 5차 회차 cb2f4e19. 커밋 0b138ec) · AC#6 ✅ · AC#7 ✅(A-3 가 실물로 닫힘. Nova 가 앱 4필드 스키마를 받아들이고 pending 을 실제로 사용. parse_tool_payload 까지 확인. 커밋 9c3ea0d). 브라우저 다리는 5회차로 나눠 돌렸음 — 어댑터 모드 하나만 판정한다는 규약을 그 과정에서 만들었음. A1 여덟 건 PASS · A1-7 만 BLOCKED(표본 구성 — 스텁 세션이 32ms 프레임 하나가 만들어지기 전에 끝남) · A2 팀리드 직접 PASS(정크 5종이 각각 다른 이름 붙은 경로로 버려진 것을 로그로 확인) · C2·C3·C4 PASS · C5 PASS(대조 ①은 오염 — TASK-49 로 분리). 함정 3건 신설(H-AR·H-AS·H-AQ 번호 정리) + 계측 결함 1건 수정(startedSessionId) + 절차 결함 2건 수정(P5 실패 시 주체 · 로그 레벨) + 캐시 무력화 규약. 지금 nova 모드 실물 세션 1건 진행 중 — N7·TASK-36·O-1·TASK-13·TASK-24 다섯을 그 하나에서 얻음. 그 세션의 teardown 은 호출자가 소유함(구간 B 의 N8 이 그 job 을 씀).

AC#9 (O-1) 판정 2026-09-09 — 재현되나 문자가 다름. 선행 개행(\n)은 0건이고 DB 전사문의 선행 공백도 0건임. 대신 partial 프레임에 선행 공백(1~2자)이 있고 final 이 그 조각 병합으로 이중 공백을 가짐(팀리드가 DB 에서 'yesterday?  Try to say' 를 직접 봤음). 통제 대조 B 팔(앱 프롬프트)에서도 '  \n\nFor example…' 로 선행 공백 2개 + 개행 2개가 재현됐음. agent final 3건 중 하나에는 이중 공백이 없어 조각 경계에 달렸음이 드러났음. agent 발화라 분석 job 이 없어 무해함 — AC 문구대로 기록만 남기고 고치지 않았음. 4차수가 적은 「선행 개행」과 문자가 다르다는 것이 이 차수가 더한 것임.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행 TASK-44 를 건다. 근거는 이 태스크의 AC#5 자신이다 — 「신규 P9~P12(발음 복습 주기 시나리오)를 실행한다」. 발음 복습 주기는 TASK-9 가 설계만 했고 구현 소유자가 TASK-44(오늘 신설)다. 구현 전에 그 시나리오를 돌릴 수 없다. ⚠️ 이 태스크가 리포의 관측 병목이다 — TASK-13·24·30·36 네 건이 전부 이 차수의 관측을 소비하므로 선행으로 걸었다. AC#6(tests/** ruff 6건·format 4건 정리)도 이 태스크 소유다 — 팀리드가 이 턴에 직접 측정해 6건·4건이 그대로임을 확인했다.
---
<!-- COMMENTS:END -->
