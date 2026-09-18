---
id: TASK-202
title: '중복 제거·영어화 ③: CLAUDE.md 의 원장 근거 재서술을 가리키기로 줄이고 영어로 옮긴다'
status: Done
assignee: []
created_date: '2026-09-18 05:11'
updated_date: '2026-09-18 05:27'
labels: []
dependencies:
  - TASK-201
ordinal: 263000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 판단 §2 C·F·G. CLAUDE.md 가 정본을 가리키면서 근거와 탈출구 이름을 함께 적어 3중이 된 자리를 줄인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 BACKLOG_GATE 이름과 cleanup 금지 근거를 지우고 정본을 가리키기만 한다
- [x] #2 컨텍스트 백분율 지시의 중복을 session-handoff.md 5항 한쪽으로 모은다
- [x] #3 모델용 지시문을 영어로 옮기고 사용자 지시 원문·반말 폐기 경위는 한글로 둔다
- [x] #4 Personal Rules 와 Tools 절의 항목 수가 보존됨을 대조한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 실측)

| 지표 | 한글판 | 영어판 |
|---|--:|--:|
| 줄 | 108 | 163 |
| 한글 문자 | 2,462 | 164 |
| **입력 토큰** | **5,330** | **3,244** (**39.1% 감소**) |

### AC 별 증거

- **#1** `BACKLOG_GATE`·「보관 폴더」·「파싱 범위」가 이 파일에 **각 0건**임. 남긴 것은 가리키기뿐임 —
  게이트의 차단 조건·설계 근거·탈출구는 `task-management.md` §9 · `cleanup` 금지는 그 문서 §6.
- **#2** 「컨텍스트 백분율」·`total_tokens` 가 **0건**임. 그 지시는 `session-handoff.md` 5항이 단독으로
  가짐. ⇒ `<work_continuity>` 에 남은 항목이 둘에서 **하나**로 줄었고 본문 문구도 「하나」로 고쳤음.
- **#3** 산문을 영어로 옮겼음. 한글로 남긴 것은 반말 폐기 줄 전체(사용자 결정 원문과 취소선 원문이
  그 안에 있음)와 `slacksend` 코드블록 주석 셋뿐임(164자).
- **#4** Personal Rules 불릿 **5개 → 5개** · Tools 의 h2 **1개 → 1개** 로 보존됨.

### 낡을 수 있던 참조를 함께 확인했음

`<work_continuity>` 의 「②-1」 을 가리키던 자리(Goal-Driven Execution 예외)를 「item 1」 로 고쳤음.
리포 전체에서 `②-1`·`②-2` 참조가 0건임. `task-management.md` 가 `CLAUDE.md <work_continuity>` 를
가리키는 세 자리는 여전히 유효함(등록 누락을 다시 못박는 자리가 실재함).

### 세 문서 합계

입력 토큰 **20,719 → 12,738**(**38.5% 감소** · 7,981 토큰). 세부는 `task-management` 8,184 → 5,390 ·
`session-handoff` 7,205 → 4,104 · `CLAUDE.md` 5,330 → 3,244.
<!-- SECTION:NOTES:END -->
