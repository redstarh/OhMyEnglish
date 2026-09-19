---
id: TASK-251
title: '말로 하는 즉시 드릴 요청(PRD.md:70 「이 패턴으로 연습 만들어줘」)이 TASK-233 이 닫힌 뒤에도 소유자가 없다'
status: To Do
assignee: []
created_date: '2026-09-19 12:07'
labels: []
dependencies: []
ordinal: 315000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현: ① app/backend/app/models/voice_command.py 의 ControlCommand 는 여섯이다 — end·show_report·next_question·start_additional·pause·resume ② 그 가운데 즉시 드릴에 닿는 것은 start_additional 뿐이고 TARGET_REQUIRED 에 들어 target 을 반드시 받는데, AdditionalTarget 값역은 conversation·scenario_intake·pronunciation·shadowing 넷이라 «패턴 키를 실을 자리가 없다» ③ 즉 음성으로 '이 패턴으로 연습 만들어줘' 를 말해도 어느 패턴인지 전달할 경로가 없다 ④ practice_current_pattern 은 app/ 안 0건 그대로다. / 기대: PRD.md:70 은 사용자는 '질문 더 주세요', '이 패턴으로 연습 만들어줘'라고 «요청해» 즉시 드릴을 생성할 수 있다 로 적는다. 앞의 것(next_question)은 음성 명령으로 구현돼 있고 뒤의 것은 없다. requirements-summary.md:53-54 도 같은 요구를 인용 두 줄로 적는다. / 실제: TASK-241 이 구현한 것은 결과 화면의 링크(경로 B)이고, 그 소스 주석(app/frontend/app/results/[sessionId]/page.tsx:179-181)이 '문구를 「연습 만들어줘」로 적지 않는다 — 그것은 PRD.md:70 이 예시로 든 «말로 하는» 요청이고(경로 A) 이 버튼은 화면에서 누르는 것이다' 로 두 경로를 명시로 갈라 둔다. 경로 A 는 TASK-7 이 범위 밖으로 갈라 두었고 TASK-7 은 Done 이며, 그 소유자 부재를 이어받은 TASK-233 도 경로 B 만 구현하고 Done 이 되었다 ⇒ 요구는 살아 있고 소유자가 다시 없다. / 증거: tests/agent/runs/2026-09-19-b8/result.md 7 · TASK-233 Implementation Notes(같은 갈림을 적어 둔 자리) / HEAD: e482afa / 시나리오: TS-36 AC#3 (그 AC 의 괄호 인용이 가리키는 것이 경로 A 의 문구다 — 이 회차가 관측한 것은 경로 B 다) / 제안: 결정이 먼저다 — ⑴ 경로 A 를 이 슬라이스에서 구현한다면 start_additional 에 패턴 키를 실을 자리를 열어야 하고(AdditionalTarget 확장 또는 별도 필드) 실물 Nova 없이는 관측이 안 되는 대가를 함께 받는다 ⑵ 아니면 PRD.md:70 에서 그 인용을 «철회»해 요구를 닫는다(TASK-246 이 R10-4 에 쓴 것과 같은 모양). ⛔ 어느 쪽도 고치지 않았음 — 이 회차는 관측만 함
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 PRD.md:70 의 두 인용 가운데 「이 패턴으로 연습 만들어줘」가 구현되었거나, PRD 에서 철회되어 요구가 닫혔다
<!-- AC:END -->
