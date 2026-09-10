---
id: TASK-92
title: 코치가 되불러 주는 교정 문장이 잘못 발음된 낱말을 그대로 담음 (pile ← file)
status: To Do
assignee: []
created_date: '2026-09-10 14:20'
updated_date: '2026-09-10 14:30'
labels: []
dependencies: []
ordinal: 95000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현: 1) cd app/backend 2) .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav pq08.wav --tools --app-prompt 3) ASSISTANT textOutput 을 읽음.

기대: 발음 오류를 교정하지 않기로 했다면(규칙 9 게이트) 교정 문장에도 그 낱말이 들어가지 않아야 함. 들어간다면 목표 낱말(file)로 들어가야 함.

실제: 시제·주어만 고치고 잘못 발음된 낱말을 정답 문장으로 되불러 줌 — 'Did you mean to say "I finished the first version of the pile"?' / 'Let'"'"'s try this sentence together. Say: "I finished the first version of the pile."' 학습자 관점에서는 앱이 틀린 발음을 승인한 것임.

증거: tests/harness/runs/2026-09-10-task90-pq-phoneme/PQ-pq08-20260910T140652Z.json · 회차 기록 §7-4 (tests/harness/runs/2026-09-10-task90-pq-phoneme.md)

HEAD: 36c3162 (앱 프롬프트 nova.py 는 adf462c 상태 · 회차 중 미변경)
시나리오: PQ 계층 pq08 (tests/harness/scenarios-PQ-qwen-phoneme.md §4.2) · 상위 회차 TASK-90

제안: 규칙 9·11 이 「코칭하지 않기로 한 턴」의 교정 문장 처리를 정하지 않음. 문법 교정 문장을 되불러 줄 때 발음 오류 낱말을 목표 낱말로 두라는 절을 검토함. ⛔ 이 회차는 원인을 특정하지 않았고 표본 1건임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pq08 을 같은 봉투로 다시 돌렸을 때 교정 문장에 pile 이 들어가지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 앱 경로에서 미재현 — 결함 범위를 좁힘 (팀 리드 확인).

같은 pq08.wav 를 p_app_path.py 로 앱 경로에 흘렸더니 agent 가 pile 을 언급하지 않았음. 'I see you mentioned finishing a version. Could you tell me more about what you finished? For example, you could say "I finished a project" or "I finished an email." What did you finish?' 로 되물었음.

전사도 갈렸음 — 스파이크는 '해피니시 the first version of the pile.'(혼재) 이고 앱 경로는 'he finished the first version of the pile.'(라틴) 임. 경로가 전사의 문자 체계까지 바꾸는 것은 TASK-65 가 다룬 현상과 같은 방향임.

⛔ 따라서 이 결함은 지금 스파이크 경로 표본 1건뿐이고 제품 경로의 결함으로 단정할 수 없음. 증거: tests/harness/runs/2026-09-10-task90-pq-phoneme/app-path-pq08.json · app-pq08-session.png · 회차 기록 §13.

⚠️ 다만 앱 경로에서 얻은 것이 따로 있음 — pile 이 전사에 남았는데 agent 가 그것을 무시하고 회피했음. 즉 「틀린 발음을 승인」은 아니지만 「전사에 남은 발음 오류를 다루지 않음」임. 그 판정의 소유는 TASK-87·TASK-67 쪽임.
<!-- SECTION:NOTES:END -->
