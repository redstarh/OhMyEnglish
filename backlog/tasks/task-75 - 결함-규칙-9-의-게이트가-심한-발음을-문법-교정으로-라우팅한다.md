---
id: TASK-75
title: '결함: 규칙 9 의 게이트가 심한 발음을 문법 교정으로 라우팅한다'
status: To Do
assignee: []
created_date: '2026-09-09 16:11'
labels: []
dependencies: []
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-67 조사에서 양성 대조 기준 단일 변수로 확정했음(n=2). 근거는 tests/harness/runs/2026-09-09-task67-tool-call-investigation.md §2 C1 임.

작동하는 프롬프트에 규칙 9 의 게이트 문장만(+198자) 더하니 발화가 「Let's make sure the grammar is correct. The sentence should be ...」로 바뀌었음. 두 회차의 발화 문구가 동일해 간헐이 아님. 쓴 픽스처는 p1k.wav 로 ASR 이 한글로 전사할 만큼 심한 발음임 — 규칙 9 자신이 「take it up」 하라고 지정한 구간인데 모델이 문법으로 라우팅함.

⛔ 이것은 tool 호출과 별개 문제임. 결정 49 가 tool 강제를 버렸으므로 tool 은 이 태스크의 관심이 아님. 관심은 학습자가 듣는 것임 — 심하게 잘못 발음했는데 문법 교정을 받음.

⚠️ 확률적임. 기준선·H1·H3 회차는 코칭을 발화했고 H4 두 회차는 문법으로 갔음. 즉 게이트가 라우팅을 「항상」 뒤집는 것이 아니라 뒤집을 수 있음.

⛔ 게이트를 그냥 느슨하게 하지 않음 — 조사 중에 시도했고 더 나빠졌음. 규칙 9·10 을 함께 재작성한 수정 후보 회차에서 모델이 「That was a clear and natural sentence.」로 발음에 문제가 없다고 판정했음. 즉 「never for a mild accent」를 앞세우면 분기 진입이 더 줄어듦.

문구 변경은 실물 왕복으로만 판정됨 — 단위 테스트로는 이 거동을 잴 수 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 심한 발음(p1k 류)에서 문법이 아니라 발음을 다루는 것을 실물 왕복으로 확인한다 — 같은 픽스처로 최소 2회 같은 방향이어야 한다
- [ ] #2 느슨하게 하는 방향으로 가지 않는다 — 분기 진입이 줄어드는 것을 함께 잰다(문제 없다고 판정하는 회차가 늘지 않는지)
- [ ] #3 규칙 4·11 의 one-per-turn 계약을 깨지 않는다 — 발음 교정이 그 턴의 한 교정임을 유지한다
<!-- AC:END -->
