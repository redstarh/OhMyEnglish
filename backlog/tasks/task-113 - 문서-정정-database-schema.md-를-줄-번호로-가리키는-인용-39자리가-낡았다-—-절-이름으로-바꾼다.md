---
id: TASK-113
title: '문서 정정: database-schema.md 를 줄 번호로 가리키는 인용 39자리가 낡았다 — 절 이름으로 바꾼다'
status: To Do
assignee: []
created_date: '2026-09-11 15:48'
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
- [ ] #1 39자리를 전수 조사해 각 인용이 «지금» 무엇을 가리키는지와 주장하는 내용이 실제로 어디 있는지를 대조한다
- [ ] #2 줄 번호를 갱신하지 않고 «절 이름»으로 바꾼다 — 갱신하면 다음 삽입에서 다시 낡는다(H-H)
- [ ] #3 앱 코드·테스트의 인용 3자리를 함께 고친다 — 문서만 고치면 코드가 낡은 채 남는다
- [ ] #4 보관본(docs/backup/**)은 고치지 않는다 — 그 시점의 기록이므로 손대면 증거가 바뀐다
<!-- AC:END -->
