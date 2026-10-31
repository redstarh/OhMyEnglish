---
id: TASK-298
title: '리디자인 T6: 하네스 갱신 · 통합 회차 · codex 리뷰'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:55'
labels: []
dependencies:
  - TASK-296
  - TASK-297
ordinal: 363000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §8. 회차는 격리 DB + VOICE_ADAPTER=stub.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 하네스(instrument.js · c1 · c3 · c5 · p_app_path)가 새 문구·testid 로 갱신되고 통과함
- [x] #2 app-test-agent 회차가 홈·세션·쉐도잉·문법 코스·영상·결과를 확인하고 기록을 남김
- [x] #3 codex 리뷰 findings 를 검증해 수용·반박을 기록함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01
- 하네스: 영어 문구·testid 로 갱신. C5 15/15(stub_unresponsive) · C2 56/56(light·dark, A2-3 을 「두 모드 토큰이 같다 = 밝은 테마 고정」으로 뒤집음 — 옛 기대는 두 모드가 달라야 했음) · 대비 5/5 · C1 A1-4·A1-5 통과(A1-7 은 stub 에서 원래 BLOCKED) · 게이트 테스트 112 passed. C3 는 격리 DB 에 확정 세션이 없어 일부 미평가. p_readback_leg 는 nova 필요로 미실행.
- codex 리뷰(리디자인 전체): MEDIUM 2 — ① 실패 화면이 사이드바를 가린 채 홈으로 갈 길이 없음 → 수용, session-failed-home 버튼 · ② 다음 계획·오늘 요약 실패가 빈 값으로 보임 → 반박: 오늘의 연습 칸의 기본 문장은 설계 §5 의 의도(계획이 시작을 막지 않음)이고, 패턴 칸은 오늘 요약이 비면 주간 상위 패턴으로 넘어감.
- 회차 b9(tests/agent/runs/2026-11-01-b9): 10 중 9 통과 · 새 결함 D1(실패 뒤 Try again 이 고른 학습을 버리고 추천으로 엶 — 리디자인 전부터) → 고침(lastEntryRef). 관찰(수동 모드 Next 뒤 앞 문장 안내가 남음) → 고침(goTo 에서 안내 지움).
- 회차 b9r(같은 폴더 r2/): 4항목 모두 통과 · 낡은 진입이 남지 않음까지 확인. codex 리뷰(이 수정분) 지적 0.
- 내가 직접: dev DB 기준선 그대로(sessions 18 · utterances 144 · progress 0 · attempts 0) · tsc 0 · lint 0 · build 0 · 백엔드 pytest 1484 passed · ruff 0 · ty 0.
- 남은 미결: TASK-299(백엔드가 만드는 한국어 문구) · 음성 명령 영어 문구의 실물 확인 · 결과 화면의 교정·요약 영어 표시는 분석이 끝난 세션이 없어 미관측.
<!-- SECTION:NOTES:END -->
