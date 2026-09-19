---
id: TASK-259
title: '결함: 바뀔 수 없는 입력에 5회 재시도가 걸려 유료 호출 4건이 낭비됨 (무대 생성의 null category)'
status: Done
assignee: []
created_date: '2026-09-19 16:57'
updated_date: '2026-09-19 17:17'
labels: []
dependencies: []
ordinal: 323000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관측: 무대 생성 프롬프트가 「축 1(무대)이 전사문에 없으면 category 를 null 로 내라」고 «지시»하는데(scenario_generator._AXES · _OUTPUT_RULES) parse_scenario 는 그 답을 ScenarioValidationError 로 거부하고 process_scenario 가 report_failure → fail_or_retry 로 보냄. 입력이 같으므로 재시도해도 같은 답이 오고, MAX_ATTEMPTS=5 까지 유료 호출 5건을 낸 뒤 failed 로 닫힘 — 첫 호출에서 이미 결론이 정해진 사안에 4건이 낭비됨. ⚠️ 설계서 2026-09-12-scenario-generator-design.md §5 가 「거부는 fail_or_retry 가 5회까지 재시도한 뒤 failed」를 기존 관행으로 적어 두었으므로 이것은 «문서화된 결정의 정제»이고 문서를 함께 고쳐야 함. 같은 계열이 하나 더 있음 — process_scenario 의 docstring 이 「전사문이 비면 재시도가 무의미하다(입력이 같다). 지금은 그것도 report_failure 로」라고 이미 적어 둠. 선례는 process_weekly 의 「사실이 0건인 주는 모델을 부르지 않고 빈 값으로 done」임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스텁으로 null category 응답을 넣어 재시도 횟수와 모델 호출 수를 직접 세어 기록함 (유료 호출 0건)
- [x] #2 실물 모델이 무대 없는 전사문에서 실제로 null 을 내는지 표본으로 확인함 — 도달 불가면 고치지 않고 그 사실을 적음
- [x] #3 바뀔 수 없는 입력의 거부를 첫 시도에 종결시키고 그 자리에 단위 테스트를 세움
- [x] #4 설계서 §5 의 재시도 문면을 고치고 근거를 적음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
처리 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 정본은 tests/harness/runs/2026-09-20-task259-null-retry.md 임. AC#1 대가(스텁 · 유료 0건): 재시도 5회 · 모델 호출 5건 · 백오프 1·2·3·4분 뒤 failed. AC#2 도달 가능성(실물 8호출): 무대를 말하지 않은 전사문에서 8회 전건 category=null 이고 8회 전건 파서 거부 — 결정론적 경로임(드문 흔들림이 아님). 순서를 지켰음: 대가를 먼저 세고 도달 가능성을 그 다음에 쟀으며, 도달 불가였다면 고치지 않을 자리였음. AC#3 수정: ScenarioNoStage(ScenarioValidationError 하위) 신설 · jobs.fail_terminally·report_terminal_failure 신설(attempts 를 올리지 않음) · process_scenario 가 종결(null·빈 전사문)과 재시도(그 밖의 계약 위반)를 가름 · 단정 넷을 짝으로 세웠음(종결만 재면 전부 종결시키는 구현도 통과함). 고친 뒤 같은 실험에서 호출 1건 · attempts 1 · failed 를 관측했음. 전체 스위트 1428 passed. AC#4 설계서 §5 에 「정제 2026-09-20」 절을 더했음 — 그 문서가 「거부는 5회까지 재시도」를 기존 관행으로 적어 두었기 때문임. ⛔ done 으로 닫지 않은 근거도 적었음: 남길 행이 없어 done 이 흔적 없는 성공이 되고 「왜 무대가 없는가」를 물을 자리가 사라짐. ⚠️ 남은 자리 하나 — 학습자에게 알리는 화면이 없음(요구사항 쪽 결정이라 발명하지 않았음).
<!-- SECTION:NOTES:END -->
