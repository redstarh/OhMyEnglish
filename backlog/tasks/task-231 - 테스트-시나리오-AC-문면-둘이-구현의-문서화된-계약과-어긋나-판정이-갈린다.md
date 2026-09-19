---
id: TASK-231
title: 테스트 시나리오 AC 문면 둘이 구현의 문서화된 계약과 어긋나 판정이 갈린다
status: Done
assignee: []
created_date: '2026-09-19 06:01'
updated_date: '2026-09-19 08:51'
labels: []
dependencies: []
ordinal: 295000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치 B3 회차(2026-09-19 · HEAD ced8df0)가 두 자리에서 AC 문면과 구현 계약의 갈림을 만났음. 둘 다 제품이 기대와 다르게 동작한 것이 아니고, 어느 쪽이 정본인지 사람이 정해야 하는 자리임. 그래서 시나리오 AC 를 체크하지 않고 이 태스크로 넘김.

## 갈림 ① — TS-23 AC#2 와 GET /api/sessions/next-plan

- 재현: curl -sS http://localhost:8002/api/sessions/next-plan
- 기대(AC 문면): 「계획이 있으면 초점 패턴 1~2개·질문 3~5개·난이도·추천 이유를 함께 줌」
- 실제: {"reason": "...", "target_level": "A2"} — 초점 패턴과 질문이 없음
- 저장된 계획 쪽은 네 요소를 전부 갖고 있음(6건 전수: 초점 2개 · 질문 5개 · target_level A2 · reason 74~100자). 값역은 DB CHECK 넷이 못박고 있음(session_plans_focus_len · session_plans_questions_len · session_plans_target_level_check · session_plans_reason_not_blank).
- 내리지 않는 것이 의도된 계약임 — app/backend/app/api/results.py 의 next_plan docstring 이 근거를 적어 둠: 「질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다」(캡틴 결정).
- PRD 는 엔드포인트가 질문을 노출할 것을 요구하지 않음 — docs/PRD.md R11-2 는 계획의 «내용» 요구이고 R11-3 은 추천 이유만 화면에 요구함.

## 갈림 ② — TS-25 AC#3 과 화면 /history

- 재현: 브라우저로 http://localhost:3000/history 를 열고 빈 목록 안내 문구를 찾음
- 기대(AC 문면): 「기록 0건일 때 화면이 빈 목록 안내를 냄」
- 실제: 그런 문구가 없음. /api/history 의 days 는 generate_series 로 항상 30줄을 내므로 목록이 빌 수 없음.
- 없는 것이 의도임 — PRD R15-5 가 「학습이 없던 날도 보여야 함」을 요구하고, app/frontend/app/history/page.tsx 의 주석이 그 근거를 적어 둠(그 날이 보이지 않으면 연속이 어디서 끊겼는지 알 수 없음).
- 하이드레이션 판정에 쓸 클라이언트 전용 문구는 따로 있고 관측됐음: 「3일 연속 학습 중이에요」 · 「최장 연속 3일」 · 날짜줄의 「분석 기록 없음」·「오류 없음」.

## 증거

tests/agent/runs/2026-09-19-b3/result.md §5-2 · §6-2 와 그 회차의 evidence/17-history-screen-snapshot.json · evidence/11-nextplan-unreadable.txt

HEAD: ced8df0
시나리오: TS-23 (AC#2) · TS-25 (AC#3) — 테스트 원장(tests/agent) 의 ID 임

## 제안 (직접 고치지 않았음)

⛔ 코드를 고치는 쪽이 아니라 AC 문면을 구현 계약에 맞추는 쪽이 옳아 보임. 근거: 두 계약 모두 PRD 와 어긋나지 않고 각자 캡틴 결정·요구사항을 근거로 적어 두었음.
- TS-23 AC#2 → 「계획이 저장될 때 초점 패턴 1~2개·질문 3~5개·난이도·추천 이유를 전부 갖는다. 그 가운데 화면에 나가는 것은 추천 이유와 목표 수준 둘이다(R11-3)」 로 고치는 안.
- TS-25 AC#3 → 「기록 0건」 전제를 버리고 「화면이 클라이언트 전용 문구를 렌더한다(연속일 문구·날짜줄의 사실 서술)」 로 고치는 안. 빈 목록 안내가 실제로 있는 화면은 /history/weekly 이고 그것은 TS-26 AC#3 이 이미 덮고 있음.
⚠️ 반대로 엔드포인트에 질문을 실으라고 판단한다면 그것은 캡틴 결정을 뒤집는 일이므로 결정 기록이 먼저 있어야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TS-23 AC#2 와 TS-25 AC#3 의 문면이 구현 계약과 일치하도록 고쳐졌거나, 구현을 바꾸기로 한 결정이 docs/design 에 기록되었다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
해소됐음 (2026-09-19 · 커밋 754a69a). TS-23 과 TS-25 의 AC 문면을 구현의 문서화된 계약에 맞춰 고쳤음 — 구현을 바꾸지 않았음. 근거는 각 시나리오 노트가 가짐: next-plan 이 질문을 내리지 «않는» 것은 results.py 의 docstring 이 캡틴 결정으로 적어 둔 의도이고(질문을 미리 보여주면 즉흥 발화 연습이 무의미해짐), /history 가 빈 목록 상태를 갖지 않는 것은 PRD R15-5 의 요구임(학습이 없던 날도 보여야 함). 회차 B3 이 고쳐진 문면을 그 회차의 기존 증거로 대조해 덮이는 것을 확인한 뒤 AC 를 체크했고 새로 재지 않았음.
<!-- SECTION:NOTES:END -->
