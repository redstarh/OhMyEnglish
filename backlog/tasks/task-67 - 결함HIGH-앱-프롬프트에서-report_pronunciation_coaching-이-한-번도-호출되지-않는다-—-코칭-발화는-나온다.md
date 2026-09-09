---
id: TASK-67
title: '결함(HIGH): 앱 프롬프트에서 report_pronunciation_coaching 이 한 번도 호출되지 않는다 — 코칭 발화는 나온다'
status: To Do
assignee: []
created_date: '2026-09-09 14:22'
labels: []
dependencies: []
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
test Agent 회차(runs/2026-09-09-task37-p-layer-agent.md)가 찾고 팀리드가 직접 재현했다. 앱의 nova.SYSTEM_PROMPT 를 실어 p1k.wav(한글로 전사될 만큼 심한 발음)를 보내면 규칙 9 의 코칭 거동은 실제로 발화된다 — 팀리드 실측 문구: 'I think you said "I think I found three very useful videos." Did I hear that right? Can you say that sentence again for me, slowly? Just like this: "I found three very useful videos."'. 그런데 규칙 10 이 지시한 report_pronunciation_coaching 호출이 0건이다. 통제 대조: --app-prompt 를 제거하면 toolUse 1건이 오고 payload 는 target_form + outcome=pending 이다(팀리드 직접 관측). 표본은 agent 3회(p1k 2회 · p2k 1회) + 팀리드 2회이고 전부 같은 방향이다 — 간헐이 아니다. ⛔ 5차수의 「규칙 9 의 never for a mild accent 가 원인」 설명은 p1m(mild) 표본에만 걸리고 이 표본을 덮지 못한다. ⛔ 원인 미확정 — 후보는 규칙 10 의 강제력 · 규칙 11 one-per-turn · 규칙 2 와의 경합 · 모델의 tool 우선순위이고 어느 것도 배제되지 않았다. ⚠️ 팀리드가 추가로 관측한 것: 그 코칭 발화가 규칙 9 의 「name the sound that was off」도 이행하지 않았다 — 어긋난 소리를 지목하지 않았다. 즉 미이행이 tool 하나가 아니다. 재현: cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1k.wav --tools --app-prompt
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 원인 후보 넷을 하나씩 배제하거나 확정한다 — 배제하지 못한 것은 배제하지 못했다고 적는다
- [ ] #2 규칙 9 의 name the sound 미이행도 같은 원인인지 다른 원인인지 가른다 — tool 미호출과 함께 움직이는지 따로 움직이는지 본다
- [ ] #3 고친 뒤 같은 재현 명령으로 toolUse 가 오는 것을 확인한다. ⛔ 통제 대조를 함께 남긴다 — 스파이크 프롬프트 팔이 여전히 오는지도 재서 프롬프트 변경이 원인임을 못박는다
- [ ] #4 target_sound 가 payload 에 실리는지 확인한다 — 규칙 10 이 Always include target_sound 를 지시하지만 스파이크 팔 관측 4회 전부 누락이었다. 그것이 없으면 패턴·next_review_at·review_tasks 가 생기지 않는다(services/pronunciation.py:214 의 SQL 조건)
<!-- AC:END -->
