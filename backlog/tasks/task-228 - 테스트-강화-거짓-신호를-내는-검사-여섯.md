---
id: TASK-228
title: '테스트 강화: 거짓 신호를 내는 검사 여섯'
status: Done
assignee: []
created_date: '2026-09-19 01:03'
updated_date: '2026-09-19 03:27'
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
- [x] #1 여섯 자리가 강화되고 강화 전에 각각 거짓 통과를 재현해 둔다
- [x] #2 test_schema.py 의 _CHECK_VALUE_RE 를 대문자까지 넓힌다
- [x] #3 수집 개수가 줄지 않고 게이트 여덟이 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 여섯 자리를 강화했음 — 각각 «강화 전 거짓 통과»를 먼저 재현했음 (2026-09-19)

⛔ 테스트를 지운 것은 0건임. 하나는 이름만 바꿔 남겼음(뜻이 달라졌으므로).

| # | 자리 | 재현한 거짓 통과 | 강화 |
|---|---|---|---|
| ⑴ | `test_config.py` 자격증명 격리 | 경로를 `aap/` 로 오타 내니 rc=1·stdout 0줄로 **통과**했음. ⚠️ 이 환경의 `grep` 은 없는 경로에도 1 을 내므로 **rc 가름만으로는 못 잡음** | 양성 대조(세 문자열이 `app/config.py` 에 보이는지) + rc∈(0,1) + 면제를 **정확 경로**로. 이전 면제는 줄 전체 부분문자열이라 주석이 `config.py` 를 언급만 해도 그 줄이 면제됐음(직접 확인) |
| ⑵ | `test_plan_models.py` CEFR | 마이그레이션 001 에서 `'C2'` 를 빼니 **통과**했음(같은 회차에서 새 단정은 실패) | `test_schema.py` 에 SQL CHECK 를 입력으로 받는 단정을 새로 두고 두 표(`users`·`session_plans`)를 함께 잼. 기존 단정은 **순서**를 재는 자리로 개명해 남겼음(`_one_step_or_same` 이 `index()` 를 쓰므로 순서도 계약임) |
| ⑵ | `test_schema.py` 정규식 | 소문자 전용이라 CEFR 값역을 **0건** 뽑았음(`[]`) | `[A-Za-z_0-9]` 로 넓혔음. 기존 스키마 단정 67건 회귀 0 |
| ⑶ | `test_weekly_report_job.py` 상한 | 프롬프트 문면의 `최대 {max_points}개` 를 `최대 5개` 로 굳혀도 **통과**했음 | 조립한 프롬프트를 실제로 읽어 상한 **두 자리**가 파서와 같은지 잼 + 다른 수가 실리지 않는지 함께 잼 |
| ⑷ | `smoke_analysis.py` | `"the" in target_form` 이 `there`·`them`·`these`·`another`·`whether`·`together` 에 전부 참임(실측 표) | 낱말 경계 정규식으로 바꿨음. ⚠️ `a/an/the` 같은 정상 형태는 통과해야 하므로 경계를 «낱말 문자»로만 잡았음 |
| ⑸ | 결정성 단정 둘 | `frozenset` 을 넘기고 `PYTHONHASHSEED=random` 4회를 돌리니 단정은 매번 통과하는데 프롬프트 sha256 이 **네 번 모두 달랐음** | 무대 쪽: 제품의 순서를 붙드는 것이 `_STAGE_CATEGORIES_SQL` 의 `order by 1` 하나임을 재는 단정을 새로 뒀음(그 줄을 지우면 실패함 — 확인). 총평 쪽: 입력이 `str`·`int` 둘뿐이라 그 구멍이 없다는 사실을 문면에 적었음 |
| ⑹ | `test_pronunciation_service.py` | `link_pattern` 이 시도에 `pattern_id` 를 쓰지 않게 하니(패턴 행은 생김) 네 단정 **전부 통과**했음 | 비교 전에 `is not None` 을 먼저 잼 — 같은 슬립 입력에서 이제 실패함 |

## 게이트 여덟 (직접 돌림)

`pytest` **1419**(직전 1417 · 새 단정 2건 · 줄지 않았음) · `ruff` 0 · `ruff format` 306 files · `ty` 0 · `tsc` 0 · `eslint` 0 errors/경고 1(기준선) · `next build` `/`=`○` Static.

⚠️ 재현에 쓴 슬립 입력은 전부 되돌렸음 — 마이그레이션 001 · `weekly_report.py` 문면 · `scenario_generator` 의 `order by` · `pronunciation.link_pattern` 넷을 `git checkout` 으로 복구하고 게이트를 다시 돌렸음.
<!-- SECTION:NOTES:END -->
