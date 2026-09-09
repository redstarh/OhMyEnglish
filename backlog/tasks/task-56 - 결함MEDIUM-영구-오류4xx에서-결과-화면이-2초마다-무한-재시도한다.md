---
id: TASK-56
title: '결함(MEDIUM): 영구 오류(4xx)에서 결과 화면이 2초마다 무한 재시도한다'
status: Done
assignee: []
created_date: '2026-09-09 08:33'
updated_date: '2026-09-09 13:46'
labels: []
dependencies: []
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차(TS-3)에서 관측. app/frontend/app/results/[sessionId]/page.tsx:15-20 의 TERMINAL_STATUSES 는 종료 상태 4종(final·partial_failure·connection_failed·no_utterances)만 담고, catch 분기(:117-118)가 모든 예외에 2초 재시도를 건다. 그 자리 주석은 네트워크 오류는 terminal 이 아니다 를 전제하지만 404·422 는 네트워크 오류가 아니다. 그래서 없는 세션을 연 화면이 끝없이 폴링한다. 메인이 그 줄을 직접 열어 확인했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 4xx 응답을 terminal 로 분류해 폴링을 멈춘다
- [x] #2 주석이 전제한 네트워크 오류와 응답이 4xx 인 경우를 코드에서 갈라 쓴다
- [x] #3 고친 뒤 없는 uuid 화면에서 요청이 반복되지 않는 것을 직접 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 4xx 를 terminal 로 갈라 폴링을 멈춤.

무엇을 고쳤는가: results/[sessionId]/page.tsx 의 catch 분기가 모든 예외에 2초 재시도를 걸던 것을 `isPermanentFailure(err)` 로 갈랐음. 4xx(=`SessionResultsError` 의 status 가 400~499)면 타이머를 걸지 않고, 5xx·네트워크 실패(`fetch` 자체가 reject)면 계속 폴링함. AC2 가 요구한 「주석이 전제한 네트워크 오류와 4xx 를 코드에서 갈라 쓴다」는 그 함수가 담음 — TASK-55 가 만든 `SessionResultsError.status` 가 그 분류의 입력임.

AC3 증거 — 직접 재서 얻은 출력임. ⛔ 개수만 재면 「멈췄다」와 「폴링이 애초에 죽었다」가 같은 값으로 보이므로 비종료 상태(analyzing) 화면을 같은 계측으로 함께 재는 음성 대조를 넣었음. 계측은 CDP `Page.addScriptToEvaluateOnNewDocument` 로 `fetch` 를 감싸 세는 것이라 백엔드 로그에 의존하지 않음.

  missing(404)   결과 API 호출 2건 · 관측창 10.0s · 첫~끝 0.0s  · 첫 주기 뒤 0건
  analyzing      결과 API 호출 6건 · 관측창 10.0s · 첫~끝 8.02s · 첫 주기 뒤 3건
  PASS  4xx 는 첫 주기 뒤 0건이고 analyzing 은 3건 이어졌다 — 두 경로가 갈렸다

호출 시각(첫 호출 기준 초): missing = [0.0, 0.01] · analyzing = [0.0, 0.0, 2.01, 4.01, 6.02, 8.02].

⚠️ t≈0 의 2건은 재시도가 아니라 개발 모드의 이펙트 이중 실행임 — App Router 는 Strict Mode 가 기본 `true` 이고 개발 모드 한정 기능임(번들 문서에서 직접 확인함: node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/reactStrictMode.md). 두 화면에 똑같이 나타나므로 판정 기준에서 뺐음. 처음에 「1건이어야 한다」로 재서 FAIL 을 봤고 그 FAIL 이 앱 결함이 아니라 내 기준의 결함이었음 — 그 사실을 남김.

⚠️ 이 관측은 회차 기록이 소유함(tests/harness/runs/2026-09-09-task55-56-57-results-screen-fix.md). 계측 스크립트는 /tmp 에 뒀고 tests/ 아래에 넣지 않았음 — 그 아래 새 .py 는 `ty` 게이트 대상인데 `pytest` 가 수집하지 않아 틈이 생김(H-AV).
<!-- SECTION:NOTES:END -->
