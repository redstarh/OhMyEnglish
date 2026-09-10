---
id: TASK-97
title: '결함 후보: 발음 tool 의 내용이 쓸 수 없다 — target_form 에 무너진 전사, target_sound 에 오류가 아닌 키'
status: To Do
assignee: []
created_date: '2026-09-10 17:54'
labels: []
dependencies: []
ordinal: 100000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-93·TASK-95 회차가 관측했음. 정본은 tests/harness/runs/2026-09-11-task93-d50-tool-rate.md §4.3 · §8.2 임.

⛔ 왜 등록하는가: 결정 50 의 ③(우회로 제거)이 「tool 이 잘 오면 걷어낸다」로 정해져 있는데, tool 이 «와도» 내용이 쓸 수 없음. 즉 ③이 두 겹으로 막혀 있고, 그것을 등록하지 않으면 ③이 열리는 시점에 아무도 기억하지 않음.

관측 (기반 프롬프트 팔 8회에서 tool 8/8 도착):
- 첫 tool 의 target_form 이 «무너진 전사 그대로»임 — 'I finished the la porte en chaille de lesseps with my team.' 즉 「이렇게 말하세요」의 목표 문장이 학습자의 오발음임. 되말하게 하면 틀린 발음을 목표로 줌.
- target_sound 가 'r as r' 임 — 「r 을 r 로」, 오류가 아닌 것을 소리 키로 만듦. 그 키로 패턴을 묶으면 복습 시계가 엉뚱한 소리에 걸림.
- p2k 회차에서는 'th_as_t' 로 그럴듯했으나 실린 것이 1/4 이고 나머지 셋은 None 임.

⚠️ 이것은 «기반 프롬프트» 팔의 관측이고 제품 경로가 아님 — 제품 경로(AS4·계획 실린 판)에서는 tool 이 오지 않음. 그래서 지금 당장의 결함이 아니고 ③의 «선행 조건»임.

⚠️ 세션 ohmyenglish-40 의 P7 발견과 같은 부류임 — 교정 카드 문면이 「들려요」로 청취를 가리키면서 처방이 어휘였음(TASK-84·TASK-88). 청취/발음 축을 가리키면서 산출물이 다른 축임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 결정 50 의 ③ 판정 기준에 「내용의 질」을 넣을지 판정한다 — tool 도착률만으로 우회로를 걷어내면 기록은 생기고 그 기록이 틀린 구간이 생긴다
- [ ] #2 target_form 에 무너진 전사가 들어가는 것이 프롬프트로 고쳐지는지 확인한다 — 규칙 10 이 target_form 의 내용을 지시하지 않는다
- [ ] #3 target_sound 가 오류가 아닌 키로 오는 것을 막을 수 있는지 확인한다 — services/pronunciation.py 의 SQL 이 빈 값만 거르고 내용은 검사하지 않는다
- [ ] #4 ⛔ 이 태스크가 닫히기 전에 결정 50 의 ③(우회로 제거)을 실행하지 않는다
<!-- AC:END -->
