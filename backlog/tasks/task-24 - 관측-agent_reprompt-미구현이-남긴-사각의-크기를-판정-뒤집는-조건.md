---
id: TASK-24
title: '관측: agent_reprompt 미구현이 남긴 사각의 크기를 판정 (뒤집는 조건)'
status: Awaiting Decision
assignee: []
created_date: '2026-09-06 00:20'
updated_date: '2026-09-07 23:31'
labels: []
dependencies:
  - TASK-37
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

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:17
---
정리(2026-09-08 팀리드): To Do → Awaiting Decision. 근거는 TASK-13과 같다(실물 Nova 왕복이 필요하고 캡틴 확인 대상). AC#4가 TASK-13과의 묶음을 이미 요구하므로 TASK-36까지 셋을 한 세션으로 묶는다.
---

created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행 TASK-37 을 건다 — 중복이 실재했다. 이 태스크 AC#1·#2(사각 구간의 턴 수를 세고 퍼센트를 산출)는 TASK-37 AC#8(「A-4(agent_reprompt 미구현 구간)와 B-2(대조군) 관측 결과를 기록한다」)와 같은 관측이다. 두 태스크가 같은 실물 세션을 각각 요구하고 있었다. 갈라 둔다: 관측은 TASK-37 이 치르고, 이 태스크는 그 데이터로 AC#3(캡틴 결정을 뒤집을 크기인지)만 판정한다. AC 문장은 고치지 않았다 — 실측 출처가 TASK-37 임을 이 노트가 소유한다.
---

created: 2026-09-07 23:31
---
TASK-44 가 넘긴 요구(2026-09-08 · 코드 리뷰 MEDIUM-3): **agent_reprompt 감지기를 만들면 review.py 의 _PRONUNCIATION_HISTORY_SQL 에 signal_source 필터를 넣을지 함께 판정해야 한다.** 지금 그 쿼리의 correct_times 는 signal_source 를 거르지 않는다 — 설계서 §3.2 를 그대로 따른 것이고 현재는 도달 불가다(유일한 보조 신호 생산자 note_transcript 가 unclear + target_sound=None 만 낸다 · 팀리드 직접 확인). ⛔ 그런데 이 태스크가 agent_reprompt 로 outcome='correct' + target_sound 를 남기는 순간, **학습자가 Nova 에게 다시 말하지 않았는데 복습 단계가 접힌다.** 더 나쁜 것은 record_signal 이 refresh_review 를 부르지 않아(§5.5 가 두 진입점만 배선) 즉시가 아니라 **나중에 조용히** 반영된다는 점이다 — 진단이 어려운 형태다. 근거 주석은 그 쿼리 자리에 남겼다.
---
<!-- COMMENTS:END -->
