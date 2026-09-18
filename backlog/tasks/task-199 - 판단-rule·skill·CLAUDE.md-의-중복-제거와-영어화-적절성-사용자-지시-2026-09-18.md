---
id: TASK-199
title: '판단: rule·skill·CLAUDE.md 의 중복 제거와 영어화 적절성 (사용자 지시 2026-09-18)'
status: Done
assignee: []
created_date: '2026-09-18 04:53'
updated_date: '2026-09-18 05:11'
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
- [x] #1 중복 실재 위치를 문서 쌍으로 특정한다
- [x] #2 영어화 이득을 상시 로드 여부로 갈라 판정한다
- [x] #3 한글을 유지할 것의 판별 기준을 적는다
- [x] #4 판단 결과를 사용자에게 보고하고 실제 작업을 태스크로 등록한다
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

## 판단 확정 (2026-09-18 · 세션 ohmyenglish-30 실측)

### 1. 상시 로드의 실태를 다시 셌음 — 앞 판의 표가 두 자리 틀렸음

이 세션의 system reminder 에 실제로 실린 것을 세었음. `~/.claude/settings.json` 과 `CLAUDE.md` 에
로드 배선이 없으므로(`grep '^@'` 0건 · settings 에 rules 언급 0건) 관측이 유일한 근거임.

| 문서 | 줄 | 문자 | 한글 문자 | 상시 로드 |
|---|--:|--:|--:|---|
| `rules/task-management.md` | 264 | 11,134 | 3,587 | 예 |
| `rules/session-handoff.md` | 205 | 8,200 | 3,592 | 예 |
| `CLAUDE.md` | 108 | 7,757 | 2,462 | 예 |
| `rules/korean-writing-standard.md` | 98 | 3,614 | 1,660 | 예 |
| `rules/common/code-review.md` | 27 | 1,097 | 71 | **예** (앞 판은 「아니오」로 적었음) |
| `AGENTS.md` | 46 | — | — | **아니오** (이 세션 reminder 에 없음. 앞 판은 「예」로 적었음) |
| 상시 로드 합계 | **702** | **31,802** | **11,372** | |

⇒ 앞 판의 「748줄」은 `AGENTS.md` 를 넣고 센 값이라 **702줄**로 정정함.

### 2. 중복 실재 위치 — 문서 쌍으로 특정함 (AC#1)

`grep -c` 로 같은 문면이 두 곳에 있음을 확인했음. 여섯 자리 모두 `session-handoff.md` 가 짝임.

| # | 겹치는 것 | 쌍 | 판정 |
|--:|---|---|---|
| A | 훅 설계 근거 셋(`exit 2` 만 차단 · `stop_hook_active` 조기 종료 · 「잔여 태스크가 남았다」를 조건으로 쓰지 않음) | `task-management.md` §9 ↔ `session-handoff.md` 8항 | ⛔ 확정. 8항이 *"여기서 재서술하지 않음"* 이라 선언하고 셋을 다시 적었음 |
| B | 훅 표(SessionStart 가 주입하는 여섯 · Stop 이 `exit 2` 로 차단) | 같은 쌍 | ⛔ 확정. 열거 순서까지 같음 |
| C | 「훅이 막지 못하는 것 = 태스크 등록 누락」 | `CLAUDE.md` ↔ 위 둘 | ⛔ **3중** |
| D | 「갱신 리듬은 커밋과 같음」 · 「읽지 않고 착수하지 않음」 | `task-management.md` §3 ↔ `session-handoff.md` 3항 | ⛔ 확정 |
| E | 「태스크는 줄 번호가 아니라 ID 로 가리킴」과 그 근거 | `task-management.md` §1 원칙 2 ↔ `session-handoff.md` 4항 규율 2 | ⛔ 확정 |
| F | 「컨텍스트 백분율을 확신할 수 없으면 남은 토큰 수치를 보고함」 | `CLAUDE.md` ↔ `session-handoff.md` 5항 | ⛔ 확정 |
| G | 탈출구 이름 `BACKLOG_GATE=0` | `CLAUDE.md` ↔ `task-management.md` §9 | ⚠️ `session-handoff.md` 는 이름을 안 적어 규율을 지켰고 `CLAUDE.md` 가 적어 3중이 됨 |

**`SessionStart` 3중 언급은 중복이 아니었음** — `skills/session-wrap/SKILL.md` 의 한 자리(137행)는
훅을 직접 돌리는 **명령**이고 「훅이 무엇을 하는가」를 재서술하지 않음. 층 분리가 그쪽에서는 지켜졌음.

### 3. 영어화 판정 — 상시 로드 여부로 갈랐음 (AC#2)

- **skill 은 호출할 때만 로드됨** ⇒ 영어화의 토큰 이득이 작음. 가장 긴 `skill-stocktake`(193줄)도
  부르지 않는 세션에서는 0임. ⇒ **skill 은 고치는 것만 그때 바꿈**(기존 규칙 그대로).
- **상시 로드 702줄 · 한글 11,372자가 이득이 큰 쪽임.** 그 가운데 `code-review.md` 는 이미 영어이고
  `korean-writing-standard.md` 는 한글 유지 대상이므로 **실제 대상은 셋 · 한글 9,641자**임.
- ⚠️ **토큰 절감 배수는 이 턴에 측정하지 않았음** — 문자 수만 실측했음. 배수를 적지 않음.
- ⛔ **측정된 이득이 하나 더 있고 그것이 토큰보다 확실함**: 한글 음절이 `hangul-sanity.py` 훅에 걸려
  **문서 작성 자체가 막히는 마찰**이 2026-09-18 에 두 번 실재했고 이 턴에도 한 번 더 났음.

### 4. 한글을 유지할 것의 판별 기준 (AC#3)

**기준 한 줄**: 사람이 읽거나 뜻이 한국어에 매여 있으면 한글로 둠. 모델만 읽는 지시문이면 영어로 옮김.

1. **사용자 지시 원문 인용** — 바꿀 수 없음. 예: `session-handoff.md` 8항의
   *"작업이 한번 끝날때 마다 tmux세션을 띄울 필요는 없어"* · `CLAUDE.md` 의 반말 폐기 경위.
2. **`rules/korean-writing-standard.md` 본문 전체** — 규칙의 대상이 한국어 어법이고 표의 예시가
   한국어 그 자체임. 영어로 옮기면 규칙이 자기 예시를 잃음. ⇒ **번역하지 않음.**
3. **한국어 출력을 담은 실측 기록** — 관측값이 한글 문면이면 그대로 둠.

### 5. 순서 판정 — 중복 제거를 먼저 하고 문서 하나를 한 번만 고침

⛔ **기존 규칙이 일괄 번역을 이미 금지함**(`korean-writing-standard.md` 머리말:
*"기존 skill·rule 을 일괄 번역하지 않음 — 손대는 문서만 그때 바꿈"*). 그 금지를 우회하지 않고
**중복 제거가 그 문서를 고치는 일이 되는 것**으로 성립시킴 ⇒ 문서 단위로 **중복 제거와 영어화를
한 번에** 함. 두 번 고치면 같은 자리를 두 언어로 두 번 검토해야 함.

⛔ **중복 제거를 번역보다 먼저 하는 이유**: 겹친 문면을 먼저 지우지 않으면 **같은 문장을 두 번 옮기고
두 언어로 갈라진 두 판이 남음.** 그리고 중복 제거는 지우는 일이라 뜻이 미끄러질 위험이 0 에 가까움.

### 6. 관측만 하고 태스크로 등록하지 않은 것 — 범위 밖임

두 규칙 문서 끝의 개정 각주가 상시 로드에서 약 34줄을 차지함(`task-management.md` 14 ·
`session-handoff.md` 20). 이것은 **중복이 아니라 분량**이고 사용자 지시(중복 제거·영어화)의 범위 밖임.
⚠️ 줄이려면 규율 4-3(뒤집힌 결정의 경위를 남김)과 충돌하는 자리를 갈라야 하므로 별 결정이 필요함.

### 7. 등록한 후속 작업

`TASK-200`(task-management) → `TASK-201`(session-handoff) → `TASK-202`(CLAUDE.md) → `TASK-203`(검증).
정본이 `task-management.md` §9 이므로 그 문서를 먼저 확정하고 `session-handoff.md` 가 그것을 가리키게 함.
<!-- SECTION:NOTES:END -->
