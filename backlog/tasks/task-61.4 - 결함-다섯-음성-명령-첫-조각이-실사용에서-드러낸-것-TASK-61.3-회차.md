---
id: TASK-61.4
title: '결함 다섯: 음성 명령 첫 조각이 실사용에서 드러낸 것 (TASK-61.3 회차)'
status: To Do
assignee: []
created_date: '2026-09-14 23:15'
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
- [ ] #1 D1 을 고친다 — 명령·확인 발화의 writer 를 하나로 만들고 중복 행이 생기지 않는 것을 단정으로 못 박는다
- [ ] #2 D2 를 고친다 — 확인 답이 learning 으로 남지 않는 것을 단정으로 못 박는다
- [ ] #3 D4 를 고친다 — 명령으로 분류된 발화도 화면에 남는다(프레임 계약을 정하고 프론트까지 확인한다)
- [ ] #4 D3 의 방향을 사용자에게 받는다 — 프롬프트로 먼저 말하게 할지, 앱이 화면 문구로 대신할지
- [ ] #5 D5 의 방향을 사용자에게 받는다 — tool 에도 표지를 요구할지, 그 대가(정상 명령 차단)를 받아들일지
- [ ] #6 고친 뒤 실물 회차를 다시 돌려 D1·D2·D4 가 사라진 것과 D3·D5 의 결정이 이행된 것을 관측한다
<!-- AC:END -->
