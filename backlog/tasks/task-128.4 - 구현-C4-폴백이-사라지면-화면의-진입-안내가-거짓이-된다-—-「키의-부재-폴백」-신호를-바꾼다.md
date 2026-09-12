---
id: TASK-128.4
title: '구현 C4: 폴백이 사라지면 화면의 진입 안내가 거짓이 된다 — 「키의 부재 = 폴백」 신호를 바꾼다'
status: To Do
assignee: []
created_date: '2026-09-12 13:47'
labels: []
dependencies:
  - TASK-128.2
parent_task_id: TASK-128
ordinal: 141000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 72 가 «소리를 못 골라도 전용 모드로 간다» 로 바꾸므로, page.tsx 가 pronunciation_focus 의 «부재» 를 「말하기로 떨어졌다」 로 읽는 것이 거짓이 된다. 지금 dev DB 는 발음 기록 0건이라(nova.py:464) 후보가 빈 것이 «기본» 상태이고, 그때 화면이 «일반 대화로 시작했어요» 를 띄운다 — 실제로는 전용 세션이다. 자리: app/frontend/app/page.tsx:70-75(문구 둘)·147-153(분기) · app/frontend/lib/ws.ts:56-63(그 키의 계약 주석). ⚠️ 이 문구에는 테스트가 없음(grep 0건).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 화면 문구가 «전용 세션인데 후보가 없다» 를 참으로 말한다 — 폴백이라 말하지 않는다
- [ ] #2 ws.ts 의 pronunciation_focus 계약 주석에서 「부재 = 폴백」 서술을 걷는다
- [ ] #3 학습자에게 보이는 한국어 문구는 사용자 승인 대상이라 올려서 받는다 — 내가 정하지 않는다
<!-- AC:END -->
