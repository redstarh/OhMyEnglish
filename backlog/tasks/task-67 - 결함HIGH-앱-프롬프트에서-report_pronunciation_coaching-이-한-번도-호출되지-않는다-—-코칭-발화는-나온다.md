---
id: TASK-67
title: '결함(HIGH): 앱 프롬프트에서 report_pronunciation_coaching 이 한 번도 호출되지 않는다 — 코칭 발화는 나온다'
status: Done
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-09 22:34'
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
- [x] #1 원인 후보 넷을 하나씩 배제하거나 확정한다 — 배제하지 못한 것은 배제하지 못했다고 적는다
- [x] #2 규칙 9 의 name the sound 미이행도 같은 원인인지 다른 원인인지 가른다 — tool 미호출과 함께 움직이는지 따로 움직이는지 본다
- [x] #3 고친 뒤 같은 재현 명령으로 toolUse 가 오는 것을 확인한다. ⛔ 통제 대조를 함께 남긴다 — 스파이크 프롬프트 팔이 여전히 오는지도 재서 프롬프트 변경이 원인임을 못박는다
- [x] #4 target_sound 가 payload 에 실리는지 확인한다 — 규칙 10 이 Always include target_sound 를 지시하지만 스파이크 팔 관측 4회 전부 누락이었다. 그것이 없으면 패턴·next_review_at·review_tasks 가 생기지 않는다(services/pronunciation.py:214 의 SQL 조건)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⛔ 2026-09-10 정정 둘째 — 낱말이 틀렸음. 이 태스크가 말한 「앱 프롬프트」는 앱 프롬프트가 아님.

스파이크의 --app-prompt 는 **기반 프롬프트만** 실음. 내가 직접 확인했음 — SYSTEM_PROMPT 가 2,339자이고 스파이크가 그것을 APP_SYSTEM_PROMPT 로 import 함. 앱이 실제로 보내는 것은 build_system_prompt(인자 6개)가 계획·무대·초점을 붙여 조립한 것임.

⛔ 스파이크 주석이 그 사실을 적어 뒀고 내가 그것을 읽고도 뜻을 못 알아봤음 — 「build_system_prompt 를 쓰지 않고 기반 프롬프트만 가져온다」. 방법 결함 둘째임(첫째는 단일 발화로 재고 다중 턴을 결론한 것).

다른 세션이 조립본을 --prompt-file 로 실어 통제 대조를 닫았음: 기반 프롬프트 팔 11회(코칭 3 · tool 이 온 회차 3) / 조립본 3회 전부 코칭 0 · tool 0 / 브라우저 앱 경로 2회 전부 0. 발화가 앱 경로와 거의 글자까지 같음. 즉 밀어내는 것은 규칙 9·10 이 아니라 **계획 블록**임(Focus on·무대·힌트가 전부 문법을 가리킴). ⚠️ 그 수치는 그쪽 실측이고 내 증거가 아님 — 내가 확인한 것은 프롬프트 길이와 import 경로임.

⚠️ 수치가 2026-09-10 에 한 번 정정됐음 — 처음에 「15/15 · 코칭 4 · tool 5」로 왔고 내가 「tool 이 코칭보다 많다」는 어긋남을 지적해 다시 셌음. 원인은 회차 수와 tool 이벤트 수를 같은 열에 섞은 것임. 지금 값은 회차 단위 11/11 이고 target_sound 는 tool 이벤트 6건 전부임.

⛔ 그래서 이 태스크가 확정했다고 적은 C1(규칙 9 게이트)·C2(규칙 10 형태)는 **기반 프롬프트 범위의 관측**임. 앱이 실제로 보내는 조립본에서는 계획 블록이 앞서므로 그 둘이 원인의 자리를 유지하는지 재지 않았음. TASK-75(규칙 9 라우팅)도 같은 범위 제약을 받음.

정정된 사실 관계: tool 배선은 문제 아님(문장 되말하기 ⟺ tool 11/11 회차 · target_sound 는 tool 이벤트 전건). 문제는 지금 앱 설정에서 **코칭 자체가 일어나지 않는 것**임. 후속은 TASK-78 이 소유함.
<!-- SECTION:NOTES:END -->
