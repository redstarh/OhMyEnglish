---
id: TASK-203
title: '검증: 규칙 셋을 옮긴 뒤 뜻 보존과 실제 주입을 확인한다'
status: Done
assignee: []
created_date: '2026-09-18 05:11'
updated_date: '2026-09-18 05:30'
labels: []
dependencies:
  - TASK-202
ordinal: 264000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 판단 §5 가 요구한 검증 단계. 번역은 게이트로 검증할 수 없으므로 항목 수 대조와 실제 주입 관측이 유일한 수단이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 상시 로드 줄 수·문자 수를 다시 세어 702줄 대비 줄어든 값을 적는다
- [x] #2 새 세션에서 세 문서가 실제로 주입되는 것을 관측한다
- [x] #3 문서끼리 가리키는 자리 전부가 유효함을 grep 으로 확인한다
- [x] #4 뒤집힌 결정의 경위와 사용자 지시 원문이 유실되지 않았음을 대조한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 검증 결과 (2026-09-18 실측)

### AC#1 — ⛔ 이 AC 가 지정한 지표(줄·문자)가 반대 방향을 가리켰음

| 문서 | 줄 (전 → 후) | 입력 토큰 (전 → 후) |
|---|---|---|
| `CLAUDE.md` | 108 → 163 | 5,330 → 3,244 |
| `rules/task-management.md` | 264 → 307 | 8,184 → 5,390 |
| `rules/session-handoff.md` | 205 → 225 | 7,205 → 4,104 |
| `rules/korean-writing-standard.md` | 98 → 98 | 3,339 (유지) |
| `rules/common/code-review.md` | 27 → 27 | 380 (유지) |
| **합계** | **702 → 820 (16.8% 증가)** | **24,438 → 16,457 (32.7% 감소)** |

⛔ **줄 수로는 「늘었음」이고 토큰으로는 「32.7% 줄었음」임.** AC 를 쓸 때 줄·문자를 지표로 고른 것이
틀렸고 그 교훈은 `docs/ops/pitfalls.md` `H-CE` 가 소유함. **이후 상시 로드 감축은 토큰으로만 잼.**

### AC#2 — 새 세션에서 주입을 직접 관측했음

`claude -p` 로 새 세션을 띄우고 `--disallowedTools "Read,Bash,Grep,Glob,Task,Edit,Write,WebFetch,Skill"`
로 파일 읽기를 전부 막은 뒤 제목 줄을 물었음. 다섯 문서의 제목을 경로와 함께 그대로 냈음 —
`# Absolute Rules (절대 규칙)` · `# Task Management (작업 태스크 관리)` ·
`# 한국어 작성 표준 (Korean Writing Standard)` · `# Session Handoff (세션 인계)` ·
`# Code Review Standards`.
⇒ 세 문서의 **새 영어 제목이 주입된 것**과 **상시 로드가 이 다섯뿐인 것**이 함께 확인됐음
(`AGENTS.md` 는 없음 — TASK-199 §1 의 정정이 맞았음).

### AC#3 — 가리키는 자리 전부가 유효함

세 문서에서 뽑은 경로 참조 22건 중 `~/.claude` 아래 19건이 전부 실재함. 실재하지 않은 셋
(`docs/design/` · `docs/ops/pitfalls.md` · `docs/superpowers/plans/`)은 **리포 상대 경로**이고
이 리포에 실재함(`docs/superpowers/plans/` 는 쓰지 않기로 한 자리라 없는 것이 맞음).
절 번호 참조도 전부 해소됨 — `task-management.md` §1·§3·§4·§6·§9 와 `session-handoff.md` 3·4·5·8항.

### AC#4 — 뒤집힌 경위와 사용자 인용이 유실되지 않았음

사용자 지시 원문 인용 셋이 한글 그대로 같은 개수로 남았음 —
`session-handoff.md` 의 tmux 인용 2건 · `/clear` 인용 1건 · `CLAUDE.md` 의 반말 폐기 줄 1건.
뒤집힌 결정의 경위 다섯 자리가 남았음 — `session-handoff.md` 의 5항(트리거 폐기) · 8항(두 번 뒤집힘) ·
각주(skill 신설 판정) · `task-management.md` 의 기각한 대안 포인터와 「번호를 의도적으로 보존」 둘.
<!-- SECTION:NOTES:END -->
