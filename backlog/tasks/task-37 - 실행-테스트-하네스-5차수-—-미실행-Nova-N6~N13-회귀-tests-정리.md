---
id: TASK-37
title: '실행: 테스트 하네스 5차수 — 미실행 Nova N6~N13 + 회귀 + tests/** 정리'
status: To Do
assignee: []
created_date: '2026-09-07 17:50'
labels: []
dependencies: []
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md D절(테스트 하네스 차수 원장)에서 이관. 원장은 tests/harness/runs/ROUNDS.md. 4/10 차수 사용, 미해결 앱 결함 0건. 5차수가 반드시 포함해야 하는 관측 3건: A-3(실물 tool 스키마 대조) · A-4(agent_reprompt 미충족 구간의 크기) · B-2(발음 개입 없는 일반 대화 1턴이 3차수 N5와 같은가, 대조군). 일부러 빼는 것: N9(세션 롤오버, 8분 이상 실음성 필요) · N10(무응답형 자격증명 실패, .env 편집 금지 제약).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 미실행 Nova N6·N7·N8·N11·N12·N13 시나리오를 실행한다
- [ ] #2 B1~B4를 재확인하고 라이트·다크 5상태를 확인한다
- [ ] #3 회귀 A1·A2·E4·E5·E6·D1·D2 + 프론트 npx tsc --noEmit 을 돌린다
- [ ] #4 P8 + p2 쌍 + P7 재캡처를 수행한다
- [ ] #5 신규 P9~P12(발음 복습 주기 시나리오)를 실행한다
- [ ] #6 tests/** ruff 6건·format 4건을 정리한다(H-L 기준선 대조)
- [ ] #7 스파이크 nova 스키마와 앱 상수를 대조해 A-3 tool 스키마 확인을 닫는다
- [ ] #8 A-4(agent_reprompt 미구현 구간)와 B-2(대조군) 관측 결과를 기록한다
<!-- AC:END -->
