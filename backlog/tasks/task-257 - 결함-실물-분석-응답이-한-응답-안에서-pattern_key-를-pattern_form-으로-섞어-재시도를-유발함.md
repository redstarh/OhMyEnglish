---
id: TASK-257
title: '결함: 실물 분석 응답이 한 응답 안에서 pattern_key 를 pattern_form 으로 섞어 재시도를 유발함'
status: To Do
assignee: []
created_date: '2026-09-19 16:18'
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
- [ ] #1 responses.jsonl 두 회차(2026-09-20 두 폴더)에서 pattern_form 등장 빈도를 세어 기록함
- [ ] #2 프롬프트가 findings 각 항목의 키 이름을 못박는지 확인하고 그 결과를 적음
- [ ] #3 고치기로 정했으면 수정 뒤 회차를 다시 돌려 그 자리에서 재발하지 않음을 관측함
<!-- AC:END -->
