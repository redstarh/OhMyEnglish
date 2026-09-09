---
id: TS-3
title: J3 · 존재하지 않는 세션 uuid 로 결과를 조회하면 사용자가 무엇을 보는가
status: In Progress
assignee: []
created_date: '2026-09-09 08:20'
updated_date: '2026-09-09 08:31'
labels: []
dependencies: []
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
근거: app/backend/app/api/results.py:137 404 session not found · app/frontend/lib/api.ts:94-96 throw · app/frontend/app/results/[sessionId]/page.tsx:114-119 catch 후 재폴링 · :149-153 문구 렌더. 절차: 1) 실재하지 않는 uuid 로 GET results 2) HTTP 상태·본문 기록 3) 프론트가 그 응답을 무엇으로 번역하는지 소스로 확정 4) 형식이 uuid 가 아닌 경우도 함께 관측. 판정 수단: HTTP 상태 코드 + 본문 + 프론트 소스 파일:줄. 위험도: 중간(오류 경로). 회차: tests/agent/runs/2026-09-09-1722
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 실재하지 않는 uuid 조회의 HTTP 상태와 본문을 기록함
- [x] #2 프론트가 그 응답을 무엇으로 번역하는지 소스로 확정함
- [x] #3 사용자가 실제로 보는 화면 문구를 적음
- [x] #4 uuid 형식이 아닌 입력의 상태·본문도 함께 기록함
- [ ] #5 사용자가 학습자 언어의 안내를 봄 — HTTP 상태 코드·API 라는 낱말이 화면에 노출되지 않음 (D1)
- [ ] #6 영구 오류(4xx)에서 폴링이 멈춤 — 2초 간격 무한 재시도가 사라짐 (D2)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: FAIL. API 는 옳음 — 404 + {"detail":"session not found"}, 랜덤 uuid 3/3 재현. uuid 형식 아니면 422 + FastAPI 기계 오류 배열. 화면이 문제임: 사용자가 '결과 API가 404을 반환했습니다' 를 danger 색으로 보고(lib/api.ts:95 -> results page:151), 2초마다 영구 재시도함(:118 — TERMINAL_STATUSES 가 성공 상태만 담음). 결함 D1(HIGH 상태코드 노출)·D2(MEDIUM 무한 재시도)·D3(LOW 조사 오류)·D4(LOW 문체 혼용) 를 runs/2026-09-09-1722/result.md 5절에 기록함 — 이 회차는 작업 원장 수정이 금지돼 대상 backlog/ 에 등록하지 못했고 등록 주체는 호출 세션임. AC 4/4 체크됐으나 결함이 열려 있어 Done 으로 올리지 않음.

게이트 지적 반영 (2026-09-09 17:2x): 원래 AC 4건이 전부 관측 과제('기록함·확정함·적음')여서 다 체크되면 끝난 것처럼 보였으나 판정은 FAIL 이었음 — 통과 조건 AC 가 빠진 것이 내 AC 설계 결함임. D1·D2 가 참이 되는 조건을 AC#5·#6 으로 추가함. 기대값을 낮춘 것이 아니라 올린 것임. 이 둘이 체크될 때 TS-3 이 Done 이 됨.
<!-- SECTION:NOTES:END -->
