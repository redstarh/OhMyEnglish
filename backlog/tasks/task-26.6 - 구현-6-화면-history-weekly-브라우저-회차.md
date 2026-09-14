---
id: TASK-26.6
title: '구현 6: 화면 /history/weekly + 브라우저 회차'
status: Done
assignee: []
created_date: '2026-09-13 23:36'
updated_date: '2026-09-14 00:12'
labels: []
dependencies:
  - TASK-26.5
parent_task_id: TASK-26
ordinal: 165000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 6. 프런트 테스트 인프라가 0이라 브라우저 회차가 검증이다. ⛔ 오디오 주소처럼 상대 경로를 쓰지 않고 API_BASE 를 쓴다(TASK-66.7 회차가 그 결함을 잡았다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tsc·eslint 가 exit 0 이다
- [x] #2 history 화면에 닿는 링크를 둔다 — 화면이 있어도 길이 없으면 소비자 0곳과 같다
- [x] #3 검증 전용 스택에서 화면을 직접 열어 보고 회차를 기록한다 — ⛔ dev DB 를 쓰지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4) — 회차 기록은 tests/harness/runs/2026-09-14-task26-weekly.md 임.

게이트: tsc exit 0 · eslint exit 0.

브라우저 회차로 확인한 것 넷: API 가 실물 경로에서 사실과 판단을 함께 냄 · 화면이 주 범위(9월 7일 ~ 9월 13일 · 월~일)와 사실 셋·상위 오류 둘·판단 둘을 그림 · ⛔ 점수·등급·달성률이 화면에 0건임 · 「아직 없음」이 빈 표 대신 안내를 보임 · 히스토리에서 닿는 링크가 있음. 스크린샷과 본문을 직접 열어 봤음.

⚠️ 앞선 회차(TASK-66.7)가 잡은 상대 경로 결함을 반복하지 않았음 — 처음부터 API_BASE 를 썼음.

정리: :3000·:8013 이 000 · dropdb exit 0 · dev DB 는 마이그레이션 20건(최대 022) · 세션 17 · weekly_reports 표가 «없음». ⛔ 그 부재가 023 미적용의 증거임. ⚠️ 무오염 조회가 처음에 그 표를 세려다 relation does not exist 로 실패했고 그 실패 자체가 답이었음 — to_regclass 로 바꿔 사실로 적었음.

⚠️ 미결 셋을 회차 §4 에 남겼음 — 모델 출력의 품질(insights 를 손으로 심었음) · 여러 주가 쌓인 화면 · 좁은 화면 배치.
<!-- SECTION:NOTES:END -->
