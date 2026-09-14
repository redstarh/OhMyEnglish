---
id: TASK-88.1
title: >-
  결함 후보: 분석 기원 발음 기록의 내용이 학습자에게 보일 모양이 아니다 — target_form 이 한국어 주석 붙은 틀이고 화면이
  spoken_form 을 그리지 않는다
status: To Do
assignee: []
created_date: '2026-09-14 16:35'
labels: []
dependencies: []
parent_task_id: TASK-88
ordinal: 172000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-88 AC#4 회차(2026-09-15)가 관측했다. 정본은 tests/harness/runs/2026-09-15-task88-p2m-end-to-end/README.md §2 다. 실린 값: target_form = 'I finished the + 업무 산출물 명사 (report / presentation / draft)' · spoken_form = 'the la porte en chaille de lesseps'. ⇒ target_form 이 문장이 아니라 빈칸 채우기 틀이고 한국어 주석이 붙었다. 그리고 결과 화면은 signal_source 가 nova_tool 이 아닌 행을 「관찰된 신호」 갈래로 렌더하며 그 갈래는 spoken_form 을 그리지 않는다 — 학습자가 자기 발화를 못 보고 틀만 본다. ⚠️ 이 판정은 코드를 읽어 얻은 것이고 화면으로 관측하지 않았다(그 회차는 분석 경로만 세웠다). ⛔ TASK-97 과 다른 경로다 — 그쪽은 Nova tool 이 만드는 내용이고 이쪽은 분석기가 만든다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 화면으로 재현한다 — transcript_analysis 행이 결과 화면에서 실제로 어떻게 보이는지 브라우저 레그로 관측한다
- [ ] #2 분석 프롬프트가 그 필드에 무엇을 요구하는지 읽고 틀이 나오는 이유를 특정한다 — 문장을 요구하는데 틀이 오는지, 애초에 틀을 허용하는지 가른다
- [ ] #3 화면 갈래를 셋으로 가를지 정한다 — 지금 둘(nova_tool 대 그 밖)이라 새 신호가 korean_transcript 와 같은 취급을 받는다. ⛔ 학습자에게 보이는 문구가 바뀌면 사용자 승인 대상이다
- [ ] #4 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다
<!-- AC:END -->
