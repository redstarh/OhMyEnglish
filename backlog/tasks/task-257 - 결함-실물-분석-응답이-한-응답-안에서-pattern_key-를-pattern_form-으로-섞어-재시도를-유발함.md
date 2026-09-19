---
id: TASK-257
title: '결함: 실물 분석 응답이 한 응답 안에서 pattern_key 를 pattern_form 으로 섞어 재시도를 유발함'
status: Done
assignee: []
created_date: '2026-09-19 16:18'
updated_date: '2026-09-19 16:55'
labels: []
dependencies: []
ordinal: 321000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관측 출처: TASK-256 재실행 회차(2026-09-20 · 격리 DB · 증거 tests/harness/runs/2026-09-20-task256-worker-rerun/responses.jsonl 의 call 1). 한 analyze_utterance job 의 응답에서 findings[0] 은 pattern_key 를 올바로 쓰고 findings[1] 은 같은 자리에 pattern_form 을 씀. 파서(AnalysisResult)가 거부해 job 이 재시도되고 두 번째 호출(call 10)은 두 항목 모두 pattern_key 로 와 done 으로 끝남. ⇒ 계약 자체는 지켜졌음(거부·회복이 설계대로 돎). 대가는 유료 호출 1건과 지연이고, 배열 항목 수가 늘면 그 확률이 커짐. 판단할 것 둘: ⑴ 프롬프트가 키 이름을 findings 의 «각 항목»에 대해 못박는지 ⑵ 파서에서 pattern_form 을 alias 로 받는 것은 값역을 넓히는 일이라 기본은 받지 않는 쪽임. ⛔ 고치기 전에 앞 회차 응답들로 재현 빈도를 먼저 셈 — 표본 1건으로 프롬프트를 바꾸면 무엇이 좋아졌는지 잴 수 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 responses.jsonl 두 회차(2026-09-20 두 폴더)에서 pattern_form 등장 빈도를 세어 기록함
- [x] #2 프롬프트가 findings 각 항목의 키 이름을 못박는지 확인하고 그 결과를 적음
- [x] #3 고치기로 정했으면 수정 뒤 회차를 다시 돌려 그 자리에서 재발하지 않음을 관측함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
처리 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 정본은 tests/harness/runs/2026-09-20-task257-prompt-fix.md 임. AC#1 빈도: 회차 셋을 합쳐 analysis 호출 19건 · findings 항목 38개 · 키 위반 1건(TASK-256 회차의 pattern_form 1건)임. AC#2 프롬프트 확인: _OUTPUT_RULES 의 형식 예시가 findings 를 «한 항목»으로만 보여 주고 키 이름을 항목 단위로 못박는 문장이 없었음 — 그것이 두 번째 항목부터 이름이 흔들리는 기전임. AC#3 수정과 관측: 그 자리에 「findings 의 모든 항목이 아래 키 이름을 글자 그대로 쓴다. 항목마다 키를 다시 짓지 마라.」를 더하고 단위 테스트를 세웠음(test_prompt_requires_the_same_keys_in_every_finding_item · 그 줄을 지우면 실제로 죽는 것을 확인했음 · 전체 1424 passed). 수정 뒤 회차는 호출 10건 · 재시도 0건 · 단정 9건 통과 · 키 위반 0건임. ⛔ 「빈도가 낮아졌다」는 주장하지 않음 — 수정 후 표본이 항목 12개뿐이라 위반 0건은 수정 전 조건에서도 흔한 결과임. 이 회차가 말하는 것은 모호함이 없어졌고 나빠진 것이 없다는 둘뿐임. ⛔ 틀린 키 이름(pattern_form)을 프롬프트에 적지 않았고 형식 예시를 두 항목으로 늘리지도 않았음 — 두 판단의 근거는 그 상수 위 주석이 가짐.

⛔ 정정 (2026-09-20 · TASK-258 이 더 큰 표본으로 재측정했음). 이 태스크를 닫을 때 내가 관측 1건(항목 26개에 1건)을 근거로 빈도를 「항목의 약 4% · 호출의 약 8%」라 사용자에게 보고했는데 그것이 틀렸음 — 수정 «전» 프롬프트로 항목 296개를 재서 위반 0건임(4% 였다면 10건 이상). 0건 관측의 95% 상한으로 보면 0.5% 아래이고 회차까지 합치면 항목 628개에 1건(0.16%)임. ⇒ 프롬프트 한 줄의 근거는 「모호함을 없앰」 하나이고 「빈도를 낮춤」이 아님. 그 문면으로 analysis.py 의 주석과 회차 노트를 고쳐 적었음. 주된 방어는 파서의 거부와 job 재시도임. 정본은 tests/harness/runs/2026-09-20-task258-contract-ab.md 임.
<!-- SECTION:NOTES:END -->
