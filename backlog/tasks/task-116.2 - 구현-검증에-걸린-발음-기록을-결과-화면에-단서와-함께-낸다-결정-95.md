---
id: TASK-116.2
title: '구현: 검증에 걸린 발음 기록을 결과 화면에 단서와 함께 낸다 (결정 95)'
status: Done
assignee: []
created_date: '2026-09-14 14:26'
updated_date: '2026-09-14 16:31'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 168000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 95 를 이행함. 정본은 docs/ops/captain-instruction-register.md 의 결정 95 임. 승인된 것은 「표시함」과 「복습 제외를 말함」 둘뿐이고 최종 문구는 구현이 정함. 설계 배경은 docs/design/2026-09-13-decision82-record-path-verification.md §7 이고 복습 큐 제외 자체는 결정 82 · TASK-116.1 이 이미 이행했음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 지금 결과 화면의 발음 카드가 검증에 걸린 시도를 표시하는지 코드로 먼저 확인한다 — 표시 여부를 가정하지 않는다
- [x] #2 카드에 「기록만 함 · 복습에는 쓰지 않음」에 해당하는 표시를 낸다 — 문구는 구현이 정하고 결정 95 는 두 사실만 정했다
- [x] #3 검증에 걸리지 않은 시도에는 그 표시가 나지 않는 것을 반대 방향 단정으로 확인한다
- [x] #4 브라우저 레그에서 그 카드를 실제로 본 증거를 남긴다 — 단위 테스트만으로 닫지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현·검증 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task116-2-review-excluded-card/README.md 임.

AC#1: 결과 API 가 sound_check 를 아예 내보내지 않는 것을 코드로 확인했음(조회에도 페이로드에도 없었음).
AC#2: review_excluded 를 계약에 더하고 카드에 문구를 붙였음. 문구는 사용자가 승인한 「기록만 했어요 · 복습에는 쓰지 않아요」임. ⛔ 판정값 자체는 화면에 내보내지 않음.
AC#3: 정상 시도에는 그 줄이 없는 것을 단위 테스트와 화면에서 각각 확인했음.
AC#4: 브라우저 레그에서 카드 줄을 읽고 스크린샷을 남겼으며 내가 직접 열어 봤음.

TDD 로 진행해 KeyError 실패를 먼저 봤고, 계약을 못박은 기존 테스트가 키 추가로 깨진 것도 갱신했음. 게이트 넷 다 exit 0(pytest 1198 passed) · 프론트 tsc·eslint 도 깨끗함. 실물 모델 사용 0.
<!-- SECTION:NOTES:END -->
