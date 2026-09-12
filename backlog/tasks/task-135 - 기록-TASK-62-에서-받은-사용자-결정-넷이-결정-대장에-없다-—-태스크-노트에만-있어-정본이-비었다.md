---
id: TASK-135
title: '기록: TASK-62 에서 받은 사용자 결정 넷이 결정 대장에 없다 — 태스크 노트에만 있어 정본이 비었다'
status: Done
assignee: []
created_date: '2026-09-12 23:39'
updated_date: '2026-09-12 23:41'
labels: []
dependencies: []
ordinal: 148000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-62 를 진행하며 받은 사용자 결정 넷(범위는 결과 화면까지 · 재생성 없음 · 문구는 한국어이고 인용은 영어 원문 · job 을 따로 둠)이 그 태스크 노트에만 남았음. 결정의 정본은 docs/ops/captain-instruction-register.md 이고(handoff · rules/task-management.md §4 가 결정을 층 ③으로 보내라고 정함) 대장의 결정 번호는 87 에서 88 로 이어짐 — 즉 그 넷은 번호를 못 받았음. 태스크가 보관되거나 노트가 길어지면 결정 근거가 사실상 사라짐.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 결정 넷을 대장에 등재한다 — 무엇이 걸려 있었나 · 정한 것 · 기각한 대안을 결정 88 과 같은 형식으로 적는다
- [x] #2 번호가 시간 순서와 어긋나는 것(넷이 결정 88 보다 먼저 받은 것)을 그 항목에 명시한다
- [x] #3 TASK-62 노트의 그 줄이 대장을 가리키게 고친다 — 두 곳에 같은 내용을 두지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-13 (세션 ohmyenglish-f4).

결정 89 로 등재했음 — 물음 넷의 표(범위 · 재생성 · 문구 언어 · 구조)와 기각한 대안을 대장에 옮겼고, 각 항의 근거 문단은 `docs/design/2026-09-13-session-summary-design.md` §2.2 를 가리켰음(두 곳에 같은 근거를 쓰지 않음).

AC#2 — 번호가 시간 순서와 어긋나는 것을 항목 머리에 적었음: 넷은 결정 88 보다 먼저 받았고 그날 대장에 적지 않아 뒤늦게 번호를 줬음. 재발 방지 문장도 같은 자리에 뒀음(결정을 받은 턴에 대장에 적는다).

AC#3 — TASK-62 노트의 그 줄을 「결정 89 가 정본임」으로 바꿨음. 넷의 내용을 노트에서 지웠으므로 중복이 0 임.

⚠️ 이 태스크는 코드 변경이 0이라 게이트를 다시 돌리지 않았음 — 만진 것은 md 셋(대장 · TASK-62 노트 · 이 노트)뿐임.
<!-- SECTION:NOTES:END -->
