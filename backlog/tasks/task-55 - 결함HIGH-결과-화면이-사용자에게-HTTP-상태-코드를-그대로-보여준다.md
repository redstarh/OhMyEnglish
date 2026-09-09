---
id: TASK-55
title: '결함(HIGH): 결과 화면이 사용자에게 HTTP 상태 코드를 그대로 보여준다'
status: To Do
assignee: []
created_date: '2026-09-09 08:33'
labels: []
dependencies: []
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차(TS-3)에서 관측. app/frontend/lib/api.ts:95 가 결과 API가 ${response.status}을 반환했습니다 를 던지고, app/frontend/app/results/[sessionId]/page.tsx:116 이 그것을 fetchError 로 세우며 :149-153 이 danger 색으로 그대로 그린다. 없는 세션 uuid 로 결과 화면을 열면 학습자가 결과 API가 404을 반환했습니다 를 본다. 메인이 그 네 줄을 직접 열어 확인했다. 결과 화면에는 홈으로 가는 인앱 링크가 없어(app/frontend/app/page.tsx:233 이 그 사실을 명시) 학습자가 브라우저 조작 없이 빠져나갈 수단이 없다. 곁가지로 그 문장의 조사가 틀린다 — 404(사백사)·422(사백이십이)는 를 이고 을 이 맞는 것은 500 류다. D1 을 고치면 그 문장이 사라지므로 함께 처리한다. 재현: 백엔드를 띄우고 /results/00000000-0000-4000-8000-000000000000 을 연다. API 자체는 404 로 옳게 응답하고 본문은 detail: session not found 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 상태 코드를 화면 문구로 쓰지 않는다 — API·404 같은 기계 낱말이 학습자 화면에 노출되지 않는다
- [ ] #2 404 는 그 학습 결과를 찾을 수 없습니다 류의 학습자 언어로 안내된다
- [ ] #3 조사 오류가 사라진다 — 문장을 없애거나 상태 코드를 문구에서 뺀다
- [ ] #4 고친 뒤 없는 uuid 로 결과 화면을 열어 문구를 직접 확인한다
<!-- AC:END -->
