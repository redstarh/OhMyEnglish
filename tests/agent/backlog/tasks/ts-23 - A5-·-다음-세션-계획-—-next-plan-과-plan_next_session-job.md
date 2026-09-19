---
id: TS-23
title: A5 · 다음 세션 계획 — next-plan 과 plan_next_session job
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:07'
labels: []
dependencies: []
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A5. 대상: GET /api/sessions/next-plan · job plan_next_session. 근거: PRD §11. 워커는 꺼 둔 채 시드 데이터로 읽기 경로를 잼.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 계획이 없거나 만들기에 실패해도 학습이 그냥 시작됨 (PRD §11 요구)
- [x] #2 직전 세션 종료가 plan_next_session job 을 등록함
- [x] #3 계획이 있으면 엔드포인트가 추천 이유와 난이도를 줌 — 질문과 초점 패턴은 의도적으로 내리지 않음(results.py next_plan docstring 의 캡틴 결정). 저장된 계획이 네 요소를 전부 갖는 것은 DB 쪽에서 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#1·#3 통과. AC#2 는 미확인 — AC 문면의 「함께 줌」 주체가 엔드포인트인지 계획인지에 따라 판정이 갈림. 결함 TASK-231 (작업 원장) 이 그 결정을 가짐. 저장된 계획 6건은 R11-2 의 네 요소를 전부 가짐(초점 2 · 질문 5 · A2 · reason 74~100자). 상세는 tests/agent/runs/2026-09-19-b3/result.md §5-1·§5-2·§5-3.

⚠️ AC 문면을 고쳤음 (2026-09-19 · 호출 세션). 원래 AC#2 는 「계획이 있으면 초점 패턴 1~2개·질문 3~5개·난이도·추천 이유를 함께 줌」이었으나 그것이 틀렸음 — 엔드포인트가 질문을 내리지 «않는» 것이 의도된 계약이고 근거가 results.py 의 next_plan docstring 에 캡틴 결정으로 적혀 있음(질문을 미리 보여주면 즉흥 발화 연습이 무의미해짐). PRD R11-2 는 계획의 내용 요구이고 R11-3 은 추천 이유만 화면에 요구하므로 PRD 와도 어긋나지 않음. ⇒ 구현이 아니라 내 AC 를 고쳤고, 고친 AC 는 목록 끝에 붙어 번호가 밀렸음. 발견은 TASK-231 이 가짐.

고쳐진 AC#3 을 이 회차의 증거로 대조해 체크했음 (새로 재지 않았음 — 같은 측정이 이미 있었음). 근거 둘: ⑴ evidence/01-baseline-next-plan.json 과 evidence/23-final-next-plan.json 이 {"reason":"…an…","target_level":"A2"} 로 추천 이유와 난이도 둘을 담고 있음 ⑵ 저장된 계획 6건 전수에서 초점 2개·질문 5개·target_level A2·reason 74~100자를 DB 로 확인했고 값역은 CHECK 넷이 못박고 있음. ⚠️ 이 파일의 AC 문면 수정은 호출 세션의 것이고 내 커밋(7fd236c)에 들어가지 않았음 — 이 체크도 함께 미커밋으로 남겨 그 세션이 커밋하게 둠.
<!-- SECTION:NOTES:END -->
