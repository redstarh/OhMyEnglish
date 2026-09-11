---
id: TASK-113
title: '문서 정정: database-schema.md 를 줄 번호로 가리키는 인용 39자리가 낡았다 — 절 이름으로 바꾼다'
status: Done
assignee: []
created_date: '2026-09-11 15:48'
updated_date: '2026-09-11 15:59'
labels: []
dependencies: []
ordinal: 118000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-72(그 문서에 표 셋을 더한 태스크)가 부수로 발견했다. 실측 2026-09-12: 리포 안에서 database-schema.md 를 «줄 번호»로 인용하는 자리가 39곳이고(보관본 제외 · 12개 파일), 확인한 셋이 전부 다른 내용을 가리켰다 — :120 이 주장하는 target_form 정의는 실제로 196~197 행, :139-140 이 주장하는 last_seen_at 앵커는 183~184 행, :377 이 주장하는 1·3·7일은 530 행이다. 원인은 그 문서에 절이 삽입될 때마다 뒤 줄이 밀리는 것이고(011 shadowing_items · 012 daily_error_summary · 007 두 표) 함정 H-H 가 이미 「문서를 줄 번호로 인용하지 않는다」로 그것을 금지한다. ⛔ 이 결함이 위험한 이유는 조용하다는 것이다 — 인용이 «존재하는» 줄을 가리키므로 따라간 사람이 엉뚱한 문단을 근거로 읽는다. 가장 많은 곳은 docs/design/2026-09-08-pronunciation-review-cycle-design.md(16자리)이고 app 코드에도 2자리, 테스트에 1자리가 있다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 39자리를 전수 조사해 각 인용이 «지금» 무엇을 가리키는지와 주장하는 내용이 실제로 어디 있는지를 대조한다
- [x] #2 줄 번호를 갱신하지 않고 «절 이름»으로 바꾼다 — 갱신하면 다음 삽입에서 다시 낡는다(H-H)
- [x] #3 앱 코드·테스트의 인용 3자리를 함께 고친다 — 문서만 고치면 코드가 낡은 채 남는다
- [x] #4 보관본(docs/backup/**)은 고치지 않는다 — 그 시점의 기록이므로 손대면 증거가 바뀐다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 완료 — 인용 39자리를 전수 대조하고 살아 있는 문서 31자리를 절 이름으로 바꿨음. 남은 9자리는 «기록» 이라 손대지 않고 오독을 막는 주의를 넣었음.

⛔ AC#1 이 세운 「39자리」가 하한이었음. 파일명 없이 이어 붙은 인용(`:303-305` 처럼)은 grep 패턴 database-schema\.md:[0-9] 에 걸리지 않음 — 실제로 그런 것을 하나 찾아 함께 고쳤음. ⇒ 다음에 같은 조사를 할 때는 백틱 안의 맨 `:숫자` 도 함께 봐야 함.

대조 결과 — 인용이 «지금» 가리키는 것 대 주장이 실제로 있는 자리.

| 인용 | 주장 | 실제 위치 | 바꾼 절 |
|---|---|---|---|
| :120 · :152-166 · :162-166 | target_form 은 일반형이고 문장이 아니다 | 196~197 | error_patterns |
| :139-140 | 문법 last_seen_at 은 발화 시각 · 발음은 resolved_at | 183~184 | error_patterns |
| :145 · :147-150 | next_review_at·mastery_score 의 유일 writer · 상태 마커 | 189~191 | error_patterns |
| :137 · :137-138 · :111 | 발음 frequency 는 시도 수 · 워커는 산출하지 않는다 | 223 · 375 | error_patterns |
| :35 | 영문 카테고리 코드 verb_tense | 217 | error_patterns(카테고리 표) |
| :161 | review_tasks 도입 단계 | 256 | review_tasks |
| :230 · :232-235 · :212-246 | 유일 writer · 0행 또는 1행 규약 · 표 정의 | 256~318 | review_tasks |
| :226-227 · :240 | user_id 를 두지 않는 규약 · task_type 값역 | 277 · 262·305 | review_tasks |
| :339 | 판정할 수 없는 발화를 incorrect 로 강제하지 않는다 | 410 | pattern_attempts |
| :281 · :297 · :303-305 | utterance_id set null · 인덱스 2개 · 시도 수 | 352 · 368 · 375 | pronunciation_attempts |
| :72 · :73-74 · :76-78 | mode 값역 · learning_source·started_via · summary 소유자 | 75 · 76~77 · 81 | learning_sessions |
| :377 · :47 | 1·3·7일 · 우선순위 공식 | 530 · 528 | 복습 우선순위 |
| :59 | 녹음 「즉시 접근 불가」 | 547 | 개인정보 원칙 |
| :49 | 복습 간격 14일 | ⛔ 없음 — 그 판정대로 삭제됐음 | (기록으로 보존) |

고친 파일 — 앱 코드 2자리(services/pronunciation.py) · 테스트 1자리(tests/integration/test_pronunciation_service.py) · 문서 28자리(pronunciation-review-cycle-design 17 · scenario-and-drill-turns 4 · review-task-history 3 · immediate-drill-entry 2 · pronunciation-echo 1 · learning-coach-agent 1 · TASKS.md 1).

⛔ AC#4 의 근거를 확장해 적용했음. 그 AC 는 docs/backup/** 만 제외했는데 같은 이유가 걸리는 것이 셋 더 있었음 — 회차 기록(tests/harness/runs/**) · tasks-md-archive · 완료된 슬라이스 1 설계서의 리뷰 이력 표. 셋 다 «그 시점의 판정 근거» 를 담으므로 고치면 무엇을 보고 판정했는지가 바뀜. 판별 기준: 지금 정본으로 읽히는 문서인가, 그 회차·그 시점의 기록인가.

⇒ 대신 오독을 막았음. 슬라이스 1 설계서 머리에 ⛔ 주의를 넣어 다섯 자리가 실제로 무엇을 가리키는지 적었고(직접 조회한 값), 「살아 있는 문서에서 이 문서를 다시 인용할 때는 절 이름을 쓴다」를 명시했음. 남은 9자리는 그 5 + archive 3 + 회차 기록 1 임.

게이트 (app/backend cwd 에서 직접 돌림): pytest 957 passed(13.07s) · ruff check 안·밖 exit 0 · unformatted 0 · ty All checks passed.
<!-- SECTION:NOTES:END -->
