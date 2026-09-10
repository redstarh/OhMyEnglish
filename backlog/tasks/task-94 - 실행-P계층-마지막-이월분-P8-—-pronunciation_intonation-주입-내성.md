---
id: TASK-94
title: '실행: P계층 마지막 이월분 P8 — pronunciation_intonation 주입 내성'
status: To Do
assignee: []
created_date: '2026-09-10 17:27'
labels: []
dependencies: []
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
4차수부터 미실행으로 남은 유일한 P 항목이다. scenarios-P §4 의 P8 단정: inject_errors.py 로 pronunciation_intonation 카테고리를 «직접» 주입해 저장·조회·렌더가 깨지지 않는지 본다. 저장 경로 자체는 카테고리를 차별하지 않아야 한다. ⛔ 실물 Nova 호출이 필요하지 않다 — 주입이므로 비용이 낮고 값어치가 높다. 지금 이 카테고리는 error_patterns CHECK 에 허용돼 있고(직접 확인) pronunciation_an_as_a 행이 실재하지만, 그 행은 pronunciation_attempts 에서 frequency 를 세므로 error_occurrences 가 0행이다(H-AX) — 주입 경로가 그 비대칭을 어떻게 다루는지가 이 시나리오의 핵심이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 inject_errors.py 로 pronunciation_intonation 패턴을 주입하고 error_patterns·error_occurrences 에 무엇이 생기는지 기록한다 — frequency 를 어느 writer 가 세는지 함께 확인한다
- [ ] #2 결과 API 와 결과 화면이 그 카테고리를 깨지지 않고 렌더하는지 확인한다 — 스크린샷을 직접 열어 본다
- [ ] #3 복습 과제가 생기는지 본다. 생기면 shadowing 매핑 의도(scenarios-E L3)와 실제가 갈리는지 적는다
- [ ] #4 회차 전에 browser_leg.md §8-0 절차대로 스냅샷을 뜨고 teardown 후 어긋난 행 0 을 확인한다 — 주입도 DB 쓰기다
<!-- AC:END -->
