---
id: TASK-67
title: '결함(HIGH): 앱 프롬프트에서 report_pronunciation_coaching 이 한 번도 호출되지 않는다 — 코칭 발화는 나온다'
status: Done
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-09 16:12'
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
2026-09-09 조사 완료 · AC1·AC2·AC4 닫음 · AC3 는 결정 49 로 「고치지 않는다」가 확정돼 닫음. 회차 기록은 tests/harness/runs/2026-09-09-task67-tool-call-investigation.md 가 소유함.

⛔ 같은 픽스처(p1k.wav)로 팔 열 개를 이 세션에서 내가 직접 돌렸음(실행 11회 · H4 만 2회). 기준선도 내가 다시 재현했음 — 남의 관측을 A/B 의 한 쪽으로 쓰지 않았음. toolConfiguration 은 모든 프롬프트 팔에서 같음을 코드로 확인했으므로 팔 사이 차이는 시스템 프롬프트 글자뿐임.

⛔ 뺄셈이 아니라 덧셈으로 확정했음. 앱 프롬프트에서 절을 빼는 방식(H1·H2·H3)은 셋 다 0건이라 원인을 가르지 못했음. 작동하는 양성 대조에 앱 요소를 하나만 더하자 곧바로 갈렸음.

확정된 원인 둘:
C1 — 규칙 9 의 게이트가 심한 발음을 문법으로 라우팅함(n=2 · 두 회차 발화 문구 동일). 이것은 tool 과 별개의 학습자 가시 결함이라 TASK-75 로 분리 등록했음.
C2 — 규칙 10 의 지시 형태가 호출을 막음. 낱말이 아님 — You MUST 를 더해도 0건이었음.

AC1 배제: ④ 모델의 tool 미지원 — 배제(양성 대조 + 기제 탐침). ③ 규칙 2 · ② 규칙 11 — 필요조건 아님(그 규칙이 없는 프롬프트에서 실패 재현). ⚠️ 충분조건인지는 재지 않았음. ① 규칙 10 의 강제력 — 부분 확정(형태가 원인).

AC2 — 소리 지목 미이행과 tool 미호출은 따로 움직임. H2 는 게이트가 있어도 소리를 지목했으나 tool 은 0건이고, H4 는 둘 다 없음. 관측으로 갈랐음.

AC4 — 누락의 원인이 프롬프트가 아니라 호출의 부재였음. 강제 호출 팔이 앱 프롬프트를 한 글자도 바꾸지 않은 채 {"target_sound":"th_as_s","target_form":"...","outcome":"pending"} 을 실어 보냈음. nova.py 의 _pronunciation_tool_configuration() docstring 이 예측했던 것이 관측으로 확인됐음. ⚠️ 다만 그 payload 가 services/pronunciation.py 의 SQL 조건을 통과해 실제로 저장되는 것까지는 보지 않았음.

AC3 — 「고친 뒤 toolUse 가 오는 것을 확인한다」를 **고치지 않는 것으로** 닫음. 결정 49 (2026-09-09) 가 보조 신호로 축소를 확정했고 toolChoice 강제를 제품 경로에 넣지 않기로 했음. 근거: 기제는 실재하나(Nova 가 toolChoice 를 거부하지 않고 앱 프롬프트 그대로 toolUse 를 냄) 같은 회차에서 audioOutput 이 0 이고 코칭 발화가 사라짐 — 말하기 코치가 말을 잃는 것은 받아들일 수 없음. auto 는 생략과 같음. 통제 대조는 AC3 이 요구한 그대로 남겼음 — 스파이크 프롬프트 팔이 여전히 toolUse 를 내는 것을 내가 직접 재서 확인했고, 그것이 세 팔의 0건이 유효한 관측임을 보증함.

⛔ 결정 49 의 대가를 함께 남겼음 — 보조 신호로는 복습 시계가 도달 불가임(note_transcript 가 target_sound=None 만 냄). 코드가 이미 적어 둔 사실이고 review.py:207~216 을 직접 읽어 확인했음. 판정은 TASK-74 가 소유함.

⚠️ 하네스에 팔 둘을 더했음(--prompt-file · --tool-choice). 기본값이 없어 기본 팔은 앱과 글자 그대로 같음. 게이트 넷 직접 쟀음: pytest 884 passed · ruff check exit 0 · format unformatted 0 · ty check All checks passed · 게이트 밖 ruff All checks passed · format unformatted 0 · 스파이크 --help exit 0.
<!-- SECTION:NOTES:END -->
