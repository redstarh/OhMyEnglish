---
id: TASK-222
title: '정리 회차: 백엔드 앱 소스 전체 (codebase-cleanup)'
status: In Progress
assignee: []
created_date: '2026-09-19 00:18'
updated_date: '2026-09-19 00:56'
labels: []
dependencies: []
ordinal: 283000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 2026-09-19 — 범위는 app/backend/app 전체(63파일 15,629줄). 프런트는 테스트 러너가 0건이라 회귀 게이트가 없어 제외했고, 러너 도입은 별 작업으로 둔다. 기준선(이 턴 실측): HEAD 07e81ef · 수집 1400 · 통과 1400(skip 0 이라 두 수가 같음) · ruff exit 0 · ruff format 305 files · ty exit 0 · tsc 0 · eslint 0 · next build 0. 규칙군 전수: 0건 다섯(C4 LOG PIE TID RSE) · PERF 1 RET 1 FURB 2 ISC 2 SIM 3 ARG 4 · ANN 10 RUF 18 PL 23 TRY 59 EM 59. ARG 넷은 포트 구현의 미사용 인자이고 ISC 둘은 의도한 줄바꿈 f-string 이라 둘 다 켜지 않는다. noqa 표식은 BLE001 한 건뿐이고 살아 있다(직전 회차 TASK-144.1 이 그 축을 이미 수확함). ⛔ 문면 정본 검사가 SYSTEM_PROMPT 부분 문자열 12건 포함으로 많다 — 그 문면을 건드리면 FAIL 하고, 그때 검사를 고치지 않고 내 변경을 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 리뷰 여섯 갈래를 읽기 전용으로 돌려 지적을 수집하고 신뢰도로 통합한다
- [ ] #2 동작변경=예 인 지적은 갈라내 별 태스크로 등록한다
- [ ] #3 적용 뒤 수집 개수가 1400 이상이고 게이트 여덟이 통과한다
- [x] #4 위반 0건 규칙군을 켜서 안전망을 늘린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 리뷰 여섯 갈래 — 2026-09-19 미도착 상태로 마감

착수: `cb-reuse` · `cb-simplify` · `cb-efficiency` · `cb-altitude` · `cb-stale`(도구 낡음 · 범위가
tests·scripts 까지) · `cb-codex`(외부 모델 · 회귀 위험). 여섯 다 읽기 전용 제약과 건수 상한을 걸어
띄웠음.

경과: 6분에 전부 `running` → 17분에 전부 `idle` → 27분에 직접 제출 요청(`SendMessage` 여섯) →
36분에도 **결과 0건이고 상태 변화도 없었음.**

⚠️ **직전 회차(`TASK-220`)와 다른 모양임** — 그쪽은 같은 지점에서 직접 요청을 보내자 다시 `running`
이 됐고 약 20분에 결과가 왔음. 이번에는 요청 뒤에도 `idle` 그대로였음.
⛔ **원인을 지목하지 않음.** 직전에 표본 다섯으로 「전달 경로 고장」을 단정했다가 틀렸으므로, 지금
말할 수 있는 것은 **「36분과 직접 요청 한 번으로는 도착하지 않았다」** 뿐임.

⇒ **후계 세션이 리뷰를 다시 띄워야 함.** 이 노트의 프롬프트 설계(각도 하나씩 · 읽기 전용 ·
건수 상한 · `동작변경` 표기 · 죽은 코드 주장에는 명령 출력 첨부)는 그대로 재사용하면 됨.

## 이 회차에서 실제로 끝난 것

규칙군 다섯(`C4`·`LOG`·`PIE`·`TID`·`RSE`)을 켰음(`232fda1`) — AC4 충족. 세 트리 전부 0건이라
per-file-ignores 가 필요 없었고, 켜지 않기로 한 것(`ARG` 4건은 포트 구현 · `ISC` 2건은 의도적
줄바꿈 · `TRY`·`EM`·`PL`·`RUF`·`ANN` 은 건수 초과)의 근거를 `pyproject.toml` 에 적었음.

기준선 대조: 수집 **1400 유지** · 통과 **1400** · `ruff` 0 · `format` 305 · `ty` 0 · 프런트 셋 0.
⇒ **회귀 0.** AC1~3 은 리뷰가 와야 닫히므로 미충족으로 남김.
<!-- SECTION:NOTES:END -->
