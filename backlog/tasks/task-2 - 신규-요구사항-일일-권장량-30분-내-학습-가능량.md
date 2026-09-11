---
id: TASK-2
title: '신규 요구사항: 일일 권장량 = 30분 내 학습 가능량'
status: Done
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-11 01:29'
labels:
  - caps-req
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 5. 임의의 학습 시나리오는 사전에 생성하고, 이를 기반으로 사용자가 학습을 종료할지, 이어 갈지를 결정.
하나의 학습 시나리오를 마치면 이를 그날 학습을 완료한 것으로 봄 현재 판정 미완료
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 학습 시나리오를 마치면 이를 그날 학습을 완료한 것으로 봄
- [x] #2 학습 시나리오 하나라도 마치면 일일 학습량을 마친것으로 봄
- [x] #3 요구사항 상세화 + 설계 반영 + 저장 위치 지정
<!-- AC:END -->

## 착수 전 확인 (TASK-11 조사, 2026-09-06 — 팀리드 직접 확인)

⚠️ **`daily_goal_minutes` 결정이 착지하지 않았다.** `001_initial_schema.sql` 머리말이 그 컬럼을
"앱 상수로 대체했다"고 적었는데 **그 상수가 코드에 없다**(히트 0건). 결정만 기록되고 구현이 0줄이다 —
이 태스크는 "없는 것을 새로 만든다"가 아니라 **"기록된 결정을 착지시킨다"**로 시작한다.

⚠️ **`learning_sessions.learning_source`가 이미 `('recommended','additional','user_requested')`
값역을 갖는데 앱이 쓰지 않는다**(INSERT가 `user_id·scenario_id·mode` 셋뿐). 권장량 초과 후의
추가 학습을 구분할 때 **새 컬럼이 필요 없다** — TASK-10과 이 컬럼을 공유한다.

근거: `docs/design/2026-09-06-gap-investigation.md` §3 항목 14.

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 구현 완료 (세션 `ohmyenglish-7f`). 요구사항은 `docs/PRD.md` §14(v1.3 신설)가 갖고
설계·근거는 `docs/design/2026-09-11-daily-completion-design.md` 가 가짐.

⛔ **새 표를 만들지 않았음** — `TASK-1` 과 다른 판정이고 근거를 코드로 확인했음. `learning_sessions`
가 `scenario_id`·`status`·`ended_at` 을 이미 갖고, 종료 UPDATE 가 `where … and status = 'active'`
로 막혀 있어(캡틴 결정 2026-09-03) **한 번 끝난 세션의 그 값들을 다시 쓸 수 없음.** `scenario_id`
를 고치는 코드도 없음(UPDATE 네 곳을 전부 읽었음). 즉 조회 시 계산이 영구히 같은 답을 냄.

판정의 정의: 「시나리오가 붙은 세션이 `status='completed'` 로 끝났다」. 앵커는 `ended_at` 이고 날짜
경계는 `users.timezone` 임(`current_date` 금지).
⛔ 드릴 교대 수를 조건에 넣지 않았음 — 미달의 주어가 학습자가 아니라 대화 모델이므로(캡틴 결정 10)
넣으면 학습자가 손쓸 수 없는 수로 완료가 취소됨. 대가(30초 세션도 완료로 셈)를 설계서 §3.1 에 적었음.

실측 증거:
- 게이트 — pytest **926 passed**(16.4s · 신규 9건) · `ruff`(app·tests·scripts) 통과 ·
  `ruff format --check` 통과 · `ty` 통과 · 프론트 `tsc`·`eslint` exit 0.
- 판별력 — 변이 셋으로 확인했음: `status` 조건 무력화 → 1건 FAIL · 앵커를 `started_at` 으로 →
  3건 FAIL · `scenario_id is not null` 제거 → 1건 FAIL.
  ⛔ **첫 시도에서 변이 둘이 잡히지 않았음** — 하나는 내가 주석을 바꿨고(SQL 이 아니었음), 하나는
  픽스처가 `started_at` 을 기본값(now)으로 둬서 두 날짜가 같아 앵커를 구별하지 못했음. 픽스처를
  `ended_at - 3일` 로 고쳐 판별력을 만들었음.
- 화면 — 검증 전용 DB·포트(:8012·:3001)로 띄워 **직접 봤음**. 완료 세션에서 「오늘 학습을 마쳤어요」
  1건 · 그 세션을 `failed` 로 바꾸면 **0건**(AC14-5).
  ⛔ **화면을 보고 결함 하나를 잡았음**: 하루 값을 `TERMINAL_STATUSES` 뒤에만 읽어서 분석이
  `analyzing` 인 동안 완료 문구가 **아예 뜨지 않았음.** 완료 여부는 분석과 독립이므로 첫 판독부터
  읽게 고쳤음 — 코드 주석이 그 경위를 가짐.
- 공유 dev DB 무변경 확인(세션 17 · 계획 3 · 요약 0).

⚠️ 원장 제목(「일일 권장량 = 30분 내 학습 가능량」)은 낡았음 — 다른 문서가 ID 로 가리키므로 제목을
바꾸지 않고 PRD §14 와 설계서가 정본임을 명시했음.
⚠️ 미결 셋은 설계서 §6 이 가짐 — 최소 길이 요건 없음 · 시작 화면 표시는 범위 밖 · 「어느 시나리오를
마쳤는가」는 `TASK-102` 소유.
<!-- SECTION:NOTES:END -->
