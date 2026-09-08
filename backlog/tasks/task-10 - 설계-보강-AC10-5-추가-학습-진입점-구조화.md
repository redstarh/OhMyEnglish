---
id: TASK-10
title: '설계 보강: AC10-5 추가 학습 진입점 구조화'
status: To Do
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-07 22:19'
labels:
  - caps-req
dependencies:
  - TASK-2
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 13. AC10-5(추가 학습에서 발음 집중 세션)는 미완료이고 근거가 '추가 학습 진입점 0곳'이다. 진입점을 구조화한 뒤 누락되지 않도록 설계에 반영한다. 항목 7 §4-7(일일 목표 후 자유 추가 학습)과 같은 진입점을 쓴다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 추가 학습 진입점을 하나로 구조화한다(발음 집중·자유 추가 학습이 같은 문을 쓰는지 결정)
- [ ] #2 TASK-2(일일 권장량)와의 관계를 명시 — 권장량을 넘긴 뒤 들어가는 문인지
- [ ] #3 설계에 반영하고 AC10-5와 §4-7 두 판정이 어떻게 바뀌는지 적는다
- [ ] #4 쉐도잉 과제(TASK-27 설계)의 진입점을 이 구조 안에서 함께 정한다 — TASK-27 옛 AC#6 이 「여기서 따로 정하면 두 곳이 갈라진다」며 소유자를 이 태스크로 지목했다
- [ ] #5 즉시 드릴 진입(TASK-7 설계 docs/design/2026-09-08-immediate-drill-entry-design.md)이 넘긴 요구 3건을 이 구조에 반영한다 — learning_source 후보 2개 중 택1 · started_via=ui · 「질문 답변 5개」는 새 세션 전제
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ **`TASK-45` 가 이 태스크의 몫 일부를 선점했음 — 캡틴 결정 34·35 가 허용했고, 무엇을 선점했는지
적는 것이 그 결정의 제약임** (2026-09-09 기록).

**선점된 것 (이미 만들어져 있음 · 되돌리기 쉬운 형태로 짰음)**:
- `app/backend/app/services/sessions.py` 의 `start_shadowing_session(pool, user_id)` — 세션을
  `mode='shadowing'` 으로 열고 클립 1개를 붙임(수준 일치 우선 → 없으면 가장 이른 행).
- `api/ws.py` 의 **`?mode=shadowing`** — 그 함수의 **호출 표면**임. 알 수 없는 모드는 말하기로
  떨어지고 경고를 남김.
- `session_started` 에 실리는 `shadowing` payload(클립 + 재생 속도·반복 횟수) · 낭독 턴 신호
  `shadowing_turn_start`/`_end` · 프론트 `lib/ws.ts` 의 `ShadowingSetup` 타입과 전송 메서드 둘.

⛔ **이 태스크가 여전히 소유하는 것 넷**:
1. **어느 화면·어느 버튼이 `?mode=shadowing` 으로 연결하는가** — 프로토콜은 있고 **UI 가 없음.**
   프론트 메서드도 호출자가 없음.
2. **추가 학습 5종의 배치·우선순위** (AC#1·#2) — 결정 34·35 가 「최소한만 만든다」로 제약해
   `TASK-45` 가 손대지 않았음.
3. **전사문을 문장으로 쪼개는 규칙** — PRD §7 이 「문장 단위로 제공한다」를 요구하는데 서버는
   클립 전사문 **전체**를 넘김. 설계서 §3.2 가 색인을 저장하지 않기로 한 것과 같은 이유로 그 규칙은
   화면 몫임.
4. **`sessionSocketUrl()` 에 모드를 붙이는 URL 조립** — 프론트가 쉐도잉으로 붙는 길이 아직 없음.

⚠️ **설계서 §12 의 빈칸 하나가 남아 있음**: 「쉐도잉 세션이 말하기 발판을 어떻게 다루는가」.
**캡틴 결정 37 이 그중 하나만 닫았음** — `drill_turns_expected`(결정 16 의 관측 지표 · `TASK-36` 이
읽음)를 쉐도잉 세션에 쓰지 않도록 막았음. **Nova 스트림은 쉐도잉 세션에서도 열림**(낭독 중에는 아무것도
보내지 않으므로 오염은 없고 비용만 있음) — 그것을 없애려면 `session_socket` 의 어댑터 생성·릴레이
경로가 모드로 갈라져야 하고, 그 구조는 이 태스크가 화면을 정할 때 다시 바뀔 수 있음.

**AC#4 는 이 선점으로 절반이 이행됐음** — 진입점의 **계약**(설계서 §12 요구 1~5)은 전부 구현됐고,
남은 것은 그 진입점을 **어디에 두는가**임. 이 태스크가 그것을 정할 때 `start_shadowing_session` 의
**호출자만** 바뀌면 되도록 짰음.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:19
---
정리(2026-09-08 팀리드): AC 2건을 추가했다. 둘 다 다른 태스크가 「TASK-10 이 소유한다」고 노트·AC 에 적었는데 이 태스크의 AC 에는 없어서, 원장만 보면 요구가 사라진 상태였다 — 훅이 잡지 못하고 사람이 소유하는 유일한 누락(CLAUDE.md work_continuity ②)이 정확히 이 형태다. 출처: TASK-27 옛 AC#6 · TASK-7 노트(2026-09-08 「TASK-10 에 요구 목록 넘김」).
---
<!-- COMMENTS:END -->
