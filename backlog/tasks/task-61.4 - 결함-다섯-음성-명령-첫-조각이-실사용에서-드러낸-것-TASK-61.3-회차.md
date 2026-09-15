---
id: TASK-61.4
title: '결함 다섯: 음성 명령 첫 조각이 실사용에서 드러낸 것 (TASK-61.3 회차)'
status: Done
assignee: []
created_date: '2026-09-14 23:15'
updated_date: '2026-09-15 05:05'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 179000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정본은 tests/harness/runs/2026-09-15-task61-3-voice-command-app-leg/README.md §3 임. D1·D2·D4 는 구현 결함이고 D3·D5 는 판단이 앞에 있다.

D1 같은 발화가 두 번 저장된다 — 전사문 경로(표지 판정)와 tool 경로(heard)가 각각 적는다.
D2 확인 답이 learning 으로도 저장된다 — 분석기가 「네 종료해주세요」를 교정 대상으로 본다.
D3 코치가 확인 질문을 소리로 말하지 않는다(audio 0) — 학습자가 무엇을 확인해야 하는지 듣지 못한다.
D4 명령으로 분류된 발화에 final 프레임을 보내지 않는다 — 화면에 아무 줄도 남지 않는다.
D5 모델이 표지 없이도 명령으로 읽고 앱이 tool 을 그대로 신뢰한다 — ARM-C 가 그 오인식을 관측했다. ⚠️ 세션이 닫히지 않은 것은 확인이 오지 않았기 때문이고 그것이 결정 102 ③의 값어치다.

⚠️ 상충: tool 에도 표지를 요구하면 D5 를 막지만, 표지의 ASR 이 불안정해(같은 픽스처 2회 중 1회는 all my english) 정상 명령까지 막는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 D1 을 고친다 — 명령·확인 발화의 writer 를 하나로 만들고 중복 행이 생기지 않는 것을 단정으로 못 박는다
- [x] #2 D2 를 고친다 — 확인 답이 learning 으로 남지 않는 것을 단정으로 못 박는다
- [x] #3 D4 를 고친다 — 명령으로 분류된 발화도 화면에 남는다(프레임 계약을 정하고 프론트까지 확인한다)
- [x] #4 D3 의 방향을 사용자에게 받는다 — 프롬프트로 먼저 말하게 할지, 앱이 화면 문구로 대신할지
- [x] #5 D5 의 방향을 사용자에게 받는다 — tool 에도 표지를 요구할지, 그 대가(정상 명령 차단)를 받아들일지
- [x] #6 고친 뒤 실물 회차를 다시 돌려 D1·D2·D4 가 사라진 것과 D3·D5 의 결정이 이행된 것을 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 D1·D2·D4 를 고쳤고 D3·D5 의 방향을 사용자에게 받았음(결정 104). 세션 ohmyenglish-65 · TDD.

고친 것:
- D1·D2: 기록의 writer 를 전사문 경로 하나로 만들었음. tool 경로가 heard 를 저장하지 않고, requested 뒤 «한 발화»를 확인 답으로 읽어 command_confirmation 으로 적음(_classify_user_final). ⇒ 중복 행 0 · 확인 답이 learning 으로 남지 않음.
- D4: 명령·확인 발화도 final 프레임으로 방송하고 utterance_type 을 함께 실었음. 프론트 ServerEvent 에 그 필드를 더했고 화면 로직은 바꾸지 않았음(줄이 남는 것까지가 이 AC 의 요구임).
- D5(결정 104): 표지가 없는 턴의 tool 을 실행하지 않음(_marker_seen). 막을 때 warning 을 남겨 그 크기를 셀 수 있게 했음.
- D3(결정 104): 프롬프트 규칙 13 을 「확인 질문을 소리로 먼저 하고 그 다음 tool 을 부른다」로 고쳤음.

게이트 여섯: pytest 1222 passed(13.6s) · ruff · ruff format --check 49 files · ty · tsc --noEmit · eslint(둘 다 0줄).
무력화 셋을 직접 돌려 전부 잡히는 것을 확인했음 — ① 표지 검사를 끔 → without_the_marker 실패 ② 확인 대기 상태를 없앰 → command_confirmation 실패 ③ utterance_type 을 프레임에서 뺌 → broadcast_so_the_screen 실패.
⚠️ 프롬프트 단정을 처음 「out loud」로 썼다가 규칙 6(JSON 을 소리로 읽지 마라)에 걸려 곧 통과하는 «거짓 양성»이 됐음 — 결함을 겨냥한 문면으로 고쳤음.

⛔ AC#6(실물 회차 재확인)은 남았음 — D3 은 문면만 고친 것이고 코치가 실제로 말하는지는 실물로만 확인됨.

2026-09-15 AC#6 회차를 돌렸음 — 정본은 tests/harness/runs/2026-09-15-task61-4-refix-verify/README.md 임. Nova 3세션(예비 1회를 표지 재시도에 씀) · Claude 0회.

D3 고쳐짐: 코치가 확인을 소리로 물었음(audio 61 · 2/2). 앞 회차 같은 조건에서 0 이었음.
D1 고쳐짐: 같은 발화의 행이 하나뿐임(앞 회차는 2건씩).
D4 간접 확인: 명령 발화가 화면 줄에 렌더됐음. ⚠️ 표지가 깨져 learning 으로 분류된 발화라 voice_command 유형의 프레임 자체는 이 회차가 못 봤음.
⛔ D2 미관측: requested 가 표지 검사에 막혀 확인 대기 상태가 서지 않았고, 그래서 그 경로를 시험하지 못했음. 단위·통합 테스트로는 무력화까지 확인했으나 실물 관측은 아님 — 두 사실을 섞지 않음.

⛔ AC#6 을 닫지 않았음(부분 충족).

⚠️ 결정 104 의 D5 대가가 실측으로 커졌음: 영어 표지가 같은 픽스처에서 4회 중 3회 깨졌음(all my english). 결정할 때 인용한 근거는 2회 중 1회였음. 한국어 표지는 1/1 로 성공했음. ⇒ 사용자에게 올릴 후보 둘 — ① 관측된 변이를 표지 후보에 더함(대가: 「all my english is bad」 같은 학습 발화가 명령으로 분류될 수 있음) ② 그대로 감수함(대가: 영어 음성 종료가 대개 안 먹힘).

2026-09-15 결정 105 뒤 한국어 팔 둘을 돌렸음(Nova 2 · 회차 §6-2). 표지가 살아난 발화가 voice_command 한 행으로 저장되고 프레임이 화면에 남는 것을 관측했음 — D1·D4 가 명령 경로에서 확정됐음. 표지 검사가 정상 명령을 막지 않았음(voice_command 프레임 1).

⛔ D2 는 아직 미관측이고 원인이 코드가 아님: 한국어 명령에서 코치가 침묵하므로(audio 0 · 2/2) 드라이버의 둘째 픽스처 문턱이 발동하지 않고 settle 이 next-wait 보다 먼저 끝나 확인 발화가 흐르지 않았음. 다음 회차는 --next-wait-ms 를 --settle-ms 보다 훨씬 작게(예: 6000 / 25000) 두면 1세션으로 닫힘. 상한을 다 썼으므로 늘리지 않았음.

⚠️ 새 관측: 코치의 발화가 언어에 따라 갈림 — 영어 명령에서는 확인을 소리로 물었고(4/4) 한국어에서는 침묵했음(2/2). 원인 미확정(프롬프트가 영어이고 규칙 13 이 영어 예시를 드는 것이 후보임).

하네스 확장 하나: p_app_path.py 의 런타임 계수기에 voice_command 키를 더했음(instrument.js 무변경 · sha256 대조 유지).

2026-09-15 AC#6 을 닫았음 — 회차 §6-3(Nova 1세션 · 드라이버 대기 조합을 --next-wait-ms 6000 / --settle-ms 25000 으로 둠). 한국어 명령 한 팔에서 voice_command 1행 + command_confirmation 1행 · learning 0행 · voice_command 프레임 2건(requested·confirmed) · 세션이 confirmed 로 닫혔음(completed).

⇒ D1·D2·D4 가 실사용에서 확정됐고, 표지 검사(결정 104)가 정상 명령을 막지 않는 것과 확인 절차(결정 102 ③)가 도는 것을 같은 팔이 함께 보였음.

⛔ 남은 것 하나를 TASK-61.5 로 등록했음 — 한국어 명령에서 코치가 침묵함(누적 0/3). D3 은 영어에서만 고쳐진 것이고, 그 팔에서 확인 발화가 흐른 것은 하네스가 시간으로 밀어 넣었기 때문임.
<!-- SECTION:NOTES:END -->
