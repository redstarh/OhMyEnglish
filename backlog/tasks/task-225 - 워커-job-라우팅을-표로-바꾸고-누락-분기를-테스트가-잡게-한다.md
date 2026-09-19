---
id: TASK-225
title: 워커 job 라우팅을 표로 바꾸고 누락 분기를 테스트가 잡게 한다
status: To Do
assignee: []
created_date: '2026-09-19 01:02'
labels: []
dependencies: []
ordinal: 286000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222) 에서 세 갈래가 지목했고 codex 가 테스트 공백을 확인했음. analysis_worker.py:220-239 가 job 종류를 if/elif 로 갈라내고 나머지 전부를 process_analysis 로 보낸다. 그래서 analyze_utterance 는 라우팅 어디에도 이름으로 적히지 않고, 새 종류를 더하며 분기를 빼먹으면 그 job 이 5회 재시도 뒤 영구히 failed 로 굳는다 — 크래시도 사용자 오류도 없이 기능만 조용히 멈춘다. ⛔ 그 사고가 실제로 있었음: 2026-09-14 에 누군가 SUMMARIZE_WEEK 분기를 지웠는데 21건이 통과했고, 그래서 test_worker.py 에 그 분기만 라우팅 테스트가 생겼다. ⚠️ scenario·summarize 두 분기는 같은 공백이 지금도 열려 있다(그 테스트들은 process_scenario·process_summary 를 직접 불러 run_worker 를 우회함). 깊은 변경: job_type→handler 매핑 하나를 두고 analyze_utterance 를 명시 키로 넣고, 표에 없는 종류는 report_failure 로 보낸다. 그러면 analysis.py:564 의 종류 가드가 죽고 네 자리의 경고 주석이 한 자리로 접힌다. ⚠️ 라우팅을 표로 바꾸는 것 자체가 codex 가 지목한 회귀 위험 1번이므로 테스트를 먼저 세운다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 다섯 종류 전부에 run_worker 경유 라우팅 테스트가 있다
- [ ] #2 라우팅이 표 한 자리에 있고 analyze_utterance 가 명시 키다
- [ ] #3 표에 없는 종류가 report_failure 로 간다
<!-- AC:END -->
