---
id: TASK-228
title: '테스트 강화: 거짓 신호를 내는 검사 여섯'
status: To Do
assignee: []
created_date: '2026-09-19 01:03'
labels: []
dependencies: []
ordinal: 289000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222) 도구낡음 지적 여섯. 각각 증명이 붙어 있고 전문은 그 노트가 정본이다. 전부 동작변경=아니오. ⛔ 테스트를 지우지 않고 강화한다. ⑴ test_config.py:657 — grep 이 대상에 닿았는지 검사하지 않아 「디렉터리 없음」과 「일치 0건」이 구별 불가(BSD grep 의 rc·stdout·stderr 가 모두 같음). 면제가 줄 전체 부분문자열이라 주석이 config.py 를 언급만 해도 같은 줄의 실제 참조가 면제된다. 양성 대조 추가 + 정확 경로 면제 + returncode in (0,1) 가름. 그 가름의 선례가 test_shadowing_seed.py:181 이고 그것은 이 세션의 TASK-219 가 만든 것이다. ⑵ test_plan_models.py:404 — 이름은 SQL CHECK 일치를 약속하는데 본문은 리터럴 튜플이다. test_schema.py:1665 _check_values 가 올바른 걸음걸이이나 그 정규식이 소문자 전용이라 CEFR 대문자를 못 뽑는다(먼저 넓혀야 한다). ⑶ test_weekly_report_job.py:257 — 프롬프트 빌더를 import 하지 않아 어떤 입력으로도 실패할 수 없다. ⑷ scripts/smoke_analysis.py:392 — 'the' in target_form 이 there·them·these·another 에도 참이다. 낱말 경계를 준다. ⑸ test_scenario_prompt.py:98 · test_summary_prompt.py:95 — 한 프로세스에서 순수 함수를 두 번 부르므로 프로세스 간 불안정이 관측 창 밖이다(PYTHONHASHSEED=random 4회에서 단정은 통과하고 바이트는 달랐다). ⑹ test_pronunciation_service.py:628 — None == None 으로 만족된다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 여섯 자리가 강화되고 강화 전에 각각 거짓 통과를 재현해 둔다
- [ ] #2 test_schema.py 의 _CHECK_VALUE_RE 를 대문자까지 넓힌다
- [ ] #3 수집 개수가 줄지 않고 게이트 여덟이 통과한다
<!-- AC:END -->
