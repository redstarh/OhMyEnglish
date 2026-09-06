---
id: TASK-24
title: '관측: agent_reprompt 미구현이 남긴 사각의 크기를 판정 (뒤집는 조건)'
status: To Do
assignee: []
created_date: '2026-09-06 00:20'
labels: []
dependencies: []
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-8 조사에서 발견. R10-4 보조 신호 2개 중 agent_reprompt(되묻기 문구 감지)는 캡틴 결정(2026-08-28)으로 만들지 않는 의도적 미충족이다 — 결정 원문은 docs/design/2026-08-27-pronunciation-echo-design.md 「미결 — 캡틴 확인 필요」 항목 2이고 근거는 §3.1 경고 블록이다. 그런데 같은 설계서 §8 「이 설계의 약점」 항목 2가 뒤집는 조건을 스스로 적어 뒀다: 'Nova가 놓쳤고 전사문도 한글이 아닌' 구간은 아무 기록도 남지 않으며 '그 구간이 실제로 얼마나 되는지는 5차수 관측 대상이다 — 크면 판단을 다시 본다'. ⚠️ 그 관측을 소유한 태스크가 어디에도 없었다(TASK-13은 미결정 3·4만 담는다). 주인 없는 뒤집는 조건은 조용히 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실물 Nova 왕복 세션에서 '발음을 놓쳤는데 전사문이 한글도 아닌' 턴 수를 센다
- [ ] #2 그 사각이 전체 발음 시도 중 몇 퍼센트인지 산출하고 표본 수를 함께 적는다
- [ ] #3 캡틴 결정을 뒤집을 만한 크기인지 판정하고 근거를 남긴다 — 뒤집지 않는 경우도 그 판정을 기록한다
- [ ] #4 TASK-13(발음 키 값역)과 같은 마이크 세션에 묶어 비용을 한 번만 치른다
<!-- AC:END -->
