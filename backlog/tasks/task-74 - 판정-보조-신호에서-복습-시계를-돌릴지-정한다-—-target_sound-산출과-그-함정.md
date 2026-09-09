---
id: TASK-74
title: '판정: 보조 신호에서 복습 시계를 돌릴지 정한다 — target_sound 산출과 그 함정'
status: To Do
assignee: []
created_date: '2026-09-09 16:11'
labels: []
dependencies: []
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 결정 49 가 만든 후속임. 근거는 tests/harness/runs/2026-09-09-task67-tool-call-investigation.md 와 대장의 결정 49 임.

결정 49 가 발음 판정을 보조 신호로 축소했음. 그 결과 발음 신호는 기록되지만 복습 시계로 이어지지 않음 — note_transcript 가 outcome='unclear' + target_sound=None 만 내고 복습 SQL 은 target_sound 가 비지 않은 행만 봄.

⛔ 이것은 새로 발견한 것이 아니고 코드가 이미 적어 둔 사실임 — app/backend/app/services/review.py:207~216. 팀리드가 그 줄을 직접 읽어 확인했음.

⚠️ 그 주석이 함정도 함께 적어 뒀음. 보조 신호가 outcome='correct' + target_sound 를 내는 순간 ① 학습자가 다시 말하지 않았는데 복습 단계가 접힘 ② record_signal 이 refresh_review 를 부르지 않아(설계서 §5.5 가 두 진입점만 배선함) 즉시가 아니라 나중에 조용히 반영돼 진단이 어려움.

즉 「target_sound 를 채우자」로 바로 가면 그 둘을 밟음. 먼저 정할 것은 「보조 신호가 복습 단계를 전진시킬 자격이 있는가」임 — 한글 전사는 「학습자가 무엇을 틀렸는지」가 아니라 「ASR 이 언어 판별을 뒤집었다」는 관측이므로 소리를 지목하지 못함.

선택지 셋(초안 — 이 태스크가 판정함):
① 보조 신호는 기록만 하고 복습 시계는 tool 경로에만 걸림. 결정 49 아래에서는 복습이 발음에 대해 돌지 않는다는 뜻이고 그 사실을 문서에 명시함.
② 우리가 target_sound 를 산출함. 한글 전사문에서 소리를 추정하는 것은 발명값이 되므로 근거가 필요함.
③ signal_source 로 필터를 걸어 보조 신호를 단계 전진에서 배제하고, 별도의 「관측됨」 축으로만 셈. review.py 의 그 주석이 「필터를 지금 넣지 않는 이유: 설계가 정하지 않은 동작을 발명하지 않는다」로 남긴 자리임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 보조 신호가 복습 단계를 전진시킬 자격이 있는지 판정하고 근거를 남긴다 — 자격이 없다고 판정하는 경우도 기록한다
- [ ] #2 판정에 따라 review.py:207~216 의 주석을 갱신한다 — 그 주석이 「다음 감지기를 만드는 태스크가 이 줄을 함께 판정한다」를 요구한다
- [ ] #3 복습 시계가 발음에 대해 돌지 않는 상태를 유지한다면 그 사실을 설계서와 AC 문서에 명시한다 — 조용히 두지 않는다
<!-- AC:END -->
