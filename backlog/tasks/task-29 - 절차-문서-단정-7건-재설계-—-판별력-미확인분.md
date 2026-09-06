---
id: TASK-29
title: 절차 문서 단정 7건 재설계 — 판별력 미확인분
status: Done
assignee: []
created_date: '2026-09-06 01:41'
updated_date: '2026-09-06 02:44'
labels:
  - caps-req
dependencies: []
priority: high
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
독립 리뷰(codex, 2026-09-06)가 tests/harness/browser_leg.md 의 남은 단정 17건 중 7건에서 거짓 통과 경로를 찾았다: A1-4·A1-5·A1-7·A3-1·A4-1·A4-2·A5-1. 상세와 공통 형태 3개는 docs/design/2026-09-06-review-outcomes.md §4가 소유한다. ⚠️ 문서가 '단정 18건·음성 대조 빈칸 0건'을 품질 근거로 내세운 것이 오판이었다 — 대조가 있다는 지표이고 판별력이 있다는 지표가 아니다. 재설계 전에는 이 7건을 PASS로 보고하지 않는다(문서에 경고를 박았다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 7건 각각을 재설계한다 — 계수 지점을 효과 지점으로 옮기거나, 내용까지 재거나, 기대값이 0이 될 수 없게 한다
- [x] #2 A4-1은 corrections가 비지 않은 세션을 primary로 쓴다(0 == 0 통과를 막는다)
- [x] #3 재설계 후 문서의 경고 블록을 갱신한다 — 남은 미확인 건수를 정확히 적는다
- [x] #4 재설계 후에도 판별력이 미확인으로 남는 건을 문서와 원장에 명시하고 관측을 별도 태스크로 넘긴다 (관측은 브라우저 회차에서만 가능해 이 태스크 안에서 순환한다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
재설계 완료 — tests/harness/browser_leg.md. 수단 4가지로 고쳤다: ① 계수 지점을 효과 지점으로 (A1-4 createBufferSource→AudioBufferSourceNode.prototype.start · A1-7 sendAudio→WebSocket.prototype.send) ② 전역 검색을 요소 지목+등호로 (A3-1 main 첫 직계 p · A4-2 카드 div 안 셋째 p · A5-1 p[aria-live=polite] 개수 1 + 등호) ③ 개수에 내용을 더함 (A1-5 textContent 6개 축자 · A4-1 카드당 p 3개) ④ 기대값 0 배제 (A4-1 N>=1, 0 이면 BLOCKED).

근거로 직접 읽어 확인한 것 4개: lib/audio.ts:enqueueAudio 가 createBufferSource 와 source.start 를 별개 줄에서 부른다 / ws.ts:SessionSocket.send 가 readyState!==OPEN 이면 조용히 버린다 / stub.py 가 FIXTURE_TURNS 문장을 축자로 흘린다 / aria-live 가 프론트 전체에 1건이다.

파생 변경 3건: §4-3 후킹 대상이 2개→3개로 늘었다(send 신설, createBufferSource→start 교체) · §4-4 window.__omy 계약에 sent·started·finalLines 키를 명시했다(T2 가 채운다) · §11 에 미결 9·10 을 열었다(대조를 강하게 만들면 표본 요구가 올라간다 — 교정 2건 이상 세션이 필요해졌다).

⚠️ AC#2 를 옮겼다(조용히 덮지 않는다). 원문은 '각 단정의 대조가 무력화에서 실제로 FAIL 을 내는지 확인한다'였고 그것은 브라우저 회차에서만 관측되는데 회차(TASK-19)가 이 재설계를 전제해 순환한다. 관측은 TASK-30 이 소유하고 TASK-19·21·22 를 선행으로 건다. 재설계는 판별력을 설계했을 뿐 관측하지 않았다 — 문서 상자에 그 사실을 박았다.
<!-- SECTION:NOTES:END -->
