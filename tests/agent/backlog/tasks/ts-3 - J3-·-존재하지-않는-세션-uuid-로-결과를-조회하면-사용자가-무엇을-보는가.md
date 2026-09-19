---
id: TS-3
title: J3 · 존재하지 않는 세션 uuid 로 결과를 조회하면 사용자가 무엇을 보는가
status: Done
assignee: []
created_date: '2026-09-09 08:20'
updated_date: '2026-09-19 14:41'
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
- [x] #5 사용자가 학습자 언어의 안내를 봄 — HTTP 상태 코드·API 라는 낱말이 화면에 노출되지 않음 (D1)
- [x] #6 영구 오류(4xx)에서 폴링이 멈춤 — 2초 간격 무한 재시도가 사라짐 (D2)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: FAIL. API 는 옳음 — 404 + {"detail":"session not found"}, 랜덤 uuid 3/3 재현. uuid 형식 아니면 422 + FastAPI 기계 오류 배열. 화면이 문제임: 사용자가 '결과 API가 404을 반환했습니다' 를 danger 색으로 보고(lib/api.ts:95 -> results page:151), 2초마다 영구 재시도함(:118 — TERMINAL_STATUSES 가 성공 상태만 담음). 결함 D1(HIGH 상태코드 노출)·D2(MEDIUM 무한 재시도)·D3(LOW 조사 오류)·D4(LOW 문체 혼용) 를 runs/2026-09-09-1722/result.md 5절에 기록함 — 이 회차는 작업 원장 수정이 금지돼 대상 backlog/ 에 등록하지 못했고 등록 주체는 호출 세션임. AC 4/4 체크됐으나 결함이 열려 있어 Done 으로 올리지 않음.

게이트 지적 반영 (2026-09-09 17:2x): 원래 AC 4건이 전부 관측 과제('기록함·확정함·적음')여서 다 체크되면 끝난 것처럼 보였으나 판정은 FAIL 이었음 — 통과 조건 AC 가 빠진 것이 내 AC 설계 결함임. D1·D2 가 참이 되는 조건을 AC#5·#6 으로 추가함. 기대값을 낮춘 것이 아니라 올린 것임. 이 둘이 체크될 때 TS-3 이 Done 이 됨.

회차 B10 (2026-09-19 · 측정 대상 코드 5ee0fa8 = 8403094, 그 사이 app/ 변경 0건). AC#5·AC#6 둘 다 성립함 — TS-3 을 Done 으로 올렸음. 두 갈래를 모두 쟀음.

수정은 이 회차가 한 것이 아님. TASK-55(D1)·TASK-56(D2)이 2026-09-09 에 이미 Done 이고 AC 전건 체크임 — 코드는 그때 고쳐졌고 시나리오 쪽 AC 만 다시 재지지 않은 채 남아 있었음. 이 회차가 한 일은 그 확인임. 새 결함 0건.

API (evidence/ts3-api-two-branches.txt): 실재하지 않는 uuid 2304d2e1-3721-481e-947b-fdcb2c428272 는 404 + {"detail":"session not found"} · not-a-uuid 는 422 + uuid_parsing 배열이고 그 본문에 영어 기계 문구 'Input should be a valid UUID, invalid character: found n at 1' 이 들어 있음. 즉 화면이 그 본문을 그대로 그리면 AC#5 가 깨지는 상태라 화면 관측이 필수였음.

AC#5 — 화면 문구 (evidence/ts3-screen-readings.txt). 진입은 중립 주소로 탭을 만들고 orca goto 로 이동했음(함정 H-CI 회피) · 주소는 localhost:3000(H-CA). 404 갈래의 본문 전체는 '학습 결과 / 그 학습 결과를 찾을 수 없습니다. / ← 학습 시작 화면으로 / 학습 히스토리 보기 →' 이고 422 갈래는 둘째 줄만 '그 학습 결과를 열 수 없습니다.' 로 갈림. 두 갈래 모두 학습자 언어이고 상태 코드·API 라는 낱말·영어 예외가 없음.

관측력 증명 (evidence/ts3-token-scan.json) — 「없음」을 재기 전에 둘을 보였음. 첫째, 금지 낱말 열하나를 보이는 본문에서 세어 전건 0 을 얻으면서 같은 주사기의 양성 대조가 맞았음: '학습 결과' 2건 · 갈래별 문구가 해당 갈래에서만 1건(404 에서 '찾을 수 없' 1건·'열 수 없' 0건, 422 에서 그 반대) — 주사기가 화면의 실제 내용을 따라가며 두 갈래를 옳게 가름. 둘째, 같은 정규식이 같은 낱말을 다른 건초더미에서 실제로 찾아냈음: '404' 가 보이는 본문에서 0건인데 DOM 전체에서는 2건이고, 그 2건을 열어 보니 Next.js 프레임워크의 기본 not-found 판본이 script 안에 직렬화된 것('404: This page could not be found.')이라 렌더되지 않음 — document.body.innerText.includes('404') 는 false 임. 즉 주사기는 404 를 잡을 능력이 있으면서 보이는 본문에서 0 을 냈으므로 그 0 은 진짜 부재임. 접근성 트리 채널도 같은 화면에서 영어 문구 'Open Next.js Dev Tools' 를 읽어 냈으므로 영어에 눈이 멀지 않았음.

AC#6 — 폴링 정지. POLL_INTERVAL_MS 는 2000(results/[sessionId]/page.tsx:17). 404 갈래는 페이지 경과 19,518ms 시점에 결과 조회 호출이 62·63ms 의 2건뿐이고, 422 갈래는 19,546ms 시점에 80·81ms 의 2건뿐임 — 폴링이 살아 있었다면 각각 약 10건이었을 시간임. 같은 순간의 2건은 재시도가 아니라 개발 모드의 이펙트 이중 실행이고, TASK-56 의 노트가 번들 문서를 직접 확인해 같은 판정을 적어 뒀으며 그 회차의 기록 [0.0, 0.01] 과 이번 값이 같은 모양임.

스크린샷은 창이 보이지 않아(Page.captureScreenshot 타임아웃) 얻지 못했음. 판정은 접근성 트리와 렌더된 본문으로 했으므로 영향 없음. 이 회차는 세션을 만들지 않았음(TS-3 은 조회 경로임). 증거: tests/agent/runs/2026-09-19-b10/ (result.md 3절).
<!-- SECTION:NOTES:END -->
