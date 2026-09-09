---
id: TASK-67
title: '결함(HIGH): 앱 프롬프트에서 report_pronunciation_coaching 이 한 번도 호출되지 않는다 — 코칭 발화는 나온다'
status: Done
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-09 16:31'
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
⛔ 2026-09-09 정정 — 이 태스크의 결론이 너무 강했음. 「앱 프롬프트로는 불리지 않는다」가 아님.

빠진 변수는 다중 턴임. 내 팔 열 개가 전부 단일 발화였고 앱은 다중 턴으로 돎 — 사각이 정확히 앱이 도는 자리였음. 다른 세션(ohmyenglish-15)이 TASK-65 를 파다 찾았고 내가 직접 재현했음.

내가 직접 돌려 얻은 것 — 앱 프롬프트 · toolChoice 강제 없음 · 발화 둘(p2a→p2k):
  toolUse 1 · target_sound "th_as_s" · outcome pending · audioOutput 197 · 코칭 발화 정상
즉 발화와 tool 을 동시에 얻음. 다른 세션 표본은 4회 중 3회에서 tool 이 왔음.

DB 도 같은 방향임(내가 직접 쿼리): pronunciation_attempts 4행 전부 signal_source='nova_tool' 이고 target_sound 가 4행 전부에 있음(am_as_i_m · w_as_vw · an_as_a ×2). 출처는 실물 마이크 세션 둘임 — bbfc3908(mic-1) 3행 · 7b43ce56(mic-2) 1행.

반증된 것 둘:
① 「앱 프롬프트로는 한 번도 불리지 않는다」 — 거짓. 단일 발화에서만 참이었음.
② 「턴마다 코칭 발화와 tool 호출 중 하나만 얻는다」 — 거짓. audioOutput 이 0 이 아님.

⛔ 이것은 내 방법 결함임 — 재는 단위를 앱이 도는 단위와 맞추지 않았음. 그 사실을 숨기지 않고 적음.

참인 범위로 좁힌 원래 관측: 앱 프롬프트 + 스파이크 경로 + **단일 발화** p1k.wav 에서 tool 0건이고, 같은 조건에서 스파이크 프롬프트는 1건임. C1(규칙 9 게이트가 문법으로 라우팅) · C2(규칙 10 형태) 는 그 범위 안에서 여전히 관측된 것이고, 다중 턴에서 그 둘이 어떻게 움직이는지는 재지 않았음.

⚠️ 결정 49 가 이 전제 위에서 내려졌음. 대장의 결정 49 항목에 정정을 남겼고 사용자에게 재결정을 요청함. 후속은 TASK-78(다른 세션 등록 — 앱 경로 확인 · 오는 조건과 안 오는 조건 가르기 · 종단으로 복습 시계까지 · 사용자 재결정)이 소유함.
⛔ 재결정을 받기 전에는 toolChoice 강제를 제품 경로에 넣지 않음 — 결정 49 의 그 부분은 이 정정에 걸리지 않음.
<!-- SECTION:NOTES:END -->
