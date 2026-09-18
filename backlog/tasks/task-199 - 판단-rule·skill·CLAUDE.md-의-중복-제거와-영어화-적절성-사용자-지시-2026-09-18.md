---
id: TASK-199
title: '판단: rule·skill·CLAUDE.md 의 중복 제거와 영어화 적절성 (사용자 지시 2026-09-18)'
status: To Do
assignee: []
created_date: '2026-09-18 04:53'
updated_date: '2026-09-18 04:54'
labels: []
dependencies: []
ordinal: 260000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: 「다른 skill 이나 rule 로 중복부분 제거하고 영어로 쓰는게 적절한지 판단해줘, claude.md 도 포함해서. 한글이 꼭 필요한 것은 한글 유지」. ⚠️ 조사가 절반 진행된 상태에서 세션이 마감됐다 — 중간 결과는 노트에 있다. 판단이 끝나면 실제 작업을 별 태스크로 등록한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 중복 실재 위치를 문서 쌍으로 특정한다
- [ ] #2 영어화 이득을 상시 로드 여부로 갈라 판정한다
- [ ] #3 한글을 유지할 것의 판별 기준을 적는다
- [ ] #4 판단 결과를 사용자에게 보고하고 실제 작업을 태스크로 등록한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 조사 중간 결과 (2026-09-18 · 세션 마감으로 중단됨)

### 규모 실측 — 영어화 이득의 크기를 가르는 값

| 문서 | 줄 | 상시 로드 |
|---|--:|---|
| `rules/task-management.md` | **264** | 예 |
| `rules/session-handoff.md` | **205** | 예 |
| `CLAUDE.md` | **108** | 예 |
| `rules/korean-writing-standard.md` | **98** | 예 |
| `AGENTS.md` | 46 | 예 |
| `rules/common/code-review.md` | 27 | 아니오(가리켜서 읽음) |
| **상시 로드 합계** | **약 748** | |
| skill 최대 `skill-stocktake` | 193 | 아니오(호출 시) |
| skill `codebase-cleanup`·`session-wrap` | 189 · 158 | 아니오 |

⛔ **판정의 뼈대**: skill 은 **호출할 때만** 로드되므로 영어화의 토큰 이득이 작다. 이득이 큰 것은
**상시 로드 748줄**이다 ⇒ 우선순위는 `task-management.md`(264) · `session-handoff.md`(205) ·
`CLAUDE.md`(108) 순이다.

### ⛔ 중복이 실재함을 확인했음 — 두 문서가 「재서술하지 않는다」고 선언했는데 겹친다

`grep -l` 로 같은 키워드가 든 문서를 셌다:

| 키워드 | 있는 문서 |
|---|---|
| `exit 2` | `task-management.md` · `session-handoff.md` |
| `stop_hook_active` | `task-management.md` · `session-handoff.md` |
| 「8회」(cap) | `task-management.md` · `session-handoff.md` |
| `SessionStart` | `task-management.md` · `session-handoff.md` · `session-wrap` skill |
| `BACKLOG_GATE` | `CLAUDE.md` · `task-management.md` |
| `G1` | `task-management.md` 만 (겹치지 않음) |

⇒ **훅의 설계 근거 셋(`exit 2` 만 차단 · `stop_hook_active` 조기 종료 · 8회 cap)이 두 문서에 모두
적혀 있다.** `session-handoff.md` 8항이 *"차단 조건·설계 근거·탈출구의 정본은
`rules/task-management.md` §9 임 — 여기서 재서술하지 않음"* 이라 선언하고도 그 셋을 다시 적었다.
⚠️ 그 문서가 스스로 경고한 실패 모드(*"두 곳에 쓰면 한쪽이 조용히 낡는다"*)에 자신이 걸린 상태다.

### 남은 일 — 이어서 할 것

1. 위 중복 셋을 **한쪽으로 모으기**(정본은 `task-management.md` §9 — 그 선언을 따른다).
2. `SessionStart` 3중 언급을 보고 **skill 과 rule 사이의 층 분리**가 실제로 갈렸는지 확인.
3. `CLAUDE.md` ↔ `session-handoff.md` ↔ `task-management.md` 3중 관계를 훑어 남은 중복 찾기.
4. 영어화 판정: 상시 로드 넷은 이득이 크고, **한글을 유지할 것**은 이 셋으로 보인다 —
   ⑴ 사용자 지시 원문 인용(바꿀 수 없다) ⑵ `korean-writing-standard.md` 본문(예시가 한국어다)
   ⑶ 한국어 출력을 담은 실측 기록. ⚠️ 이 기준을 확정해 AC#3 을 채운다.
5. 판단을 보고하고 실제 변경을 별 태스크로 등록.

⚠️ **일괄 번역의 위험을 잊지 않는다** — `korean-writing-standard.md` 머리말에 이미 적었다:
번역 중 규칙의 뜻이 미끄러지는 위험이 토큰 이득보다 클 수 있다. ⇒ 문서 하나씩, 게이트 없이 검증할
수 없으므로 **뜻이 바뀌지 않았는지 사람이 읽어 확인하는 단계**가 필요하다.
<!-- SECTION:NOTES:END -->
