---
id: TS-25
title: A7 · 연속 학습일과 학습 히스토리 — history
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:07'
labels: []
dependencies: []
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A7. 대상: GET /api/history · 화면 /history. 근거: PRD §15. 실물 외부 호출 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 연속 학습일 계산이 사용자 타임존 기준으로 성립함
- [x] #2 화면 /history 가 세션 목록을 사람이 읽을 수 있게 냄
- [x] #3 학습이 없던 날도 목록에 보임 — 빈 목록 상태가 성립하지 않는 것이 의도임(PRD R15-5). 하이드레이션 판정은 클라이언트 전용 문구(연속 학습일 표시)로 함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#1·#2 통과. AC#1 은 ended_at 의 UTC 날짜(2026-09-16)와 KST 날짜(2026-09-17)가 갈리는 세션을 직접 심어 가렸음 — 2026-09-17 줄에 들어가고 09-16 은 learned=false 로 남았으며 연속일이 2→3 으로 움직였음. AC#3 은 차단됨 — /api/history 의 days 가 항상 30줄이라 목록이 빌 수 없음(R15-5 가 요구한 것). 전제를 세우려면 회차가 만들지 않은 완료 세션을 지워야 해서 하지 않았음. AC 문면 문제는 결함 TASK-231 (작업 원장) 이 가짐. 상세는 result.md §5-5·§5-6·§6-2.

⚠️ AC 문면을 고쳤음 (2026-09-19 · 호출 세션). 원래 AC#3 은 「기록 0건일 때 화면이 빈 목록 안내를 냄」이었으나 그런 상태가 성립하지 않음 — /api/history 의 days 가 generate_series 로 항상 30줄을 내고, 그것이 PRD R15-5(「학습이 없던 날도 보여야 함」)의 요구임. history/page.tsx 주석이 같은 근거를 적어 두었음(그 날이 안 보이면 연속이 어디서 끊겼는지 알 수 없음). ⇒ 구현이 아니라 내 AC 를 고쳤고 번호가 밀렸음. 하이드레이션 판정에 쓸 문구는 「3일 연속 학습 중이에요」 류임. 발견은 TASK-231 이 가짐.

고쳐진 AC#3 을 이 회차의 증거로 대조해 체크했음. 근거: evidence/17-history-screen-snapshot.json 이 날짜 30줄을 담고 그 가운데 2026-09-16·09-15·09-14·09-13·09-12·09-11·09-08·09-07·09-05 등이 「· 학습함」 없이 날짜만으로 렌더됨 — 학습이 없던 날이 목록에 보임(R15-5). 하이드레이션은 클라이언트 전용 문구 「3일 연속 학습 중이에요」·「최장 연속 3일」 로 판정했고 성립했음. ⚠️ AC 문면 수정은 호출 세션의 것이라 이 체크도 미커밋으로 남김.
<!-- SECTION:NOTES:END -->
