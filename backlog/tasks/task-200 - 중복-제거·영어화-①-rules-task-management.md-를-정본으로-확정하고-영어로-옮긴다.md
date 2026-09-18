---
id: TASK-200
title: '중복 제거·영어화 ①: rules/task-management.md 를 정본으로 확정하고 영어로 옮긴다'
status: Done
assignee: []
created_date: '2026-09-18 05:11'
updated_date: '2026-09-18 05:19'
labels: []
dependencies: []
ordinal: 261000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 판단 §2 A·B·D·E 와 §5 순서 판정에 따라 원장 규칙 문서를 먼저 확정한다. 이 문서가 훅의 정본이므로 순서상 첫째다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 §9 가 훅의 차단 조건·설계 근거·탈출구의 유일한 자리임을 그 문서에서 확인한다
- [x] #2 본문을 영어로 옮기고 한글 유지 기준 셋에 걸리는 자리는 한글로 둔다
- [x] #3 §1~§10 의 절 번호와 각 절의 항목 수가 보존됨을 대조한다
- [x] #4 다른 문서가 가리키는 자리(§4·§6·§9)가 그대로 유효함을 grep 으로 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 실측)

### 토큰 실측이 전제를 두 번 뒤집었음

| 지표 | 한글판 | 영어판 | 방향 |
|---|--:|--:|---|
| 줄 | 264 | 307 | 늘었음 |
| 문자 | 11,134 | 17,505 | 늘었음 |
| 한글 문자 | 3,587 | 193 | 줄었음 |
| UTF-8 바이트 | 18,548 | 18,097 | 2.4% 줄었음 |
| **입력 토큰** | **8,184** | **5,400** | **34.0% 줄었음** |

⛔ 줄·문자·바이트만 보고 「영어가 짧다」를 반증된 것으로 판정하려 했음. 토크나이저를 통과시켜야
갈렸음 — 한글은 음절마다 토큰이 갈려 바이트당 토큰이 영어의 두 배가 넘음.
⚠️ `aws bedrock-runtime count-tokens` 는 이 계정에서 못 씀(두 주체 다 `bedrock:CountTokens` 없음).
`invoke-model` 에 `max_tokens: 1` 을 주고 `usage.input_tokens` 를 읽는 것이 실제로 되는 길이고
`docs/ops/pitfalls.md` `H-CE` 가 그 명령을 소유함.

### AC 별 증거

- **#1** 게이트 문면 전부가 §9(215~261행) 안에만 있음 — `BACKLOG_GATE` 246·257 · `exit 2` 224·239 ·
  `stop_hook_active` 241 · `G1`~`G5` 231~235 · `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` 242.
- **#2** 남은 한글은 세 종류뿐임 — 명령 안의 자리표시자·주석(82~94·132~136·172행) ·
  훅이 실제로 내는 라벨(73~74·223행) · 다른 문서의 한글 절 이름 인용(44·253행) · 상태 표의 이전 기호
  (54~59행). 산문은 0건임.
- **#3** 항목 수가 전부 같음 — 번호 항목 9 · 불릿 32 · 표 행 20 · h3 2 · 절 10 · G 행 5 ·
  코드블록 20줄.
- **#4** 다른 문서가 가리키는 §3·§4·§5·§6·§9 가 모두 같은 내용을 갖고 절 번호 열이 §1~§10 로 보존됨.

한글판은 `~/.claude/backups/rules-2026-09-18/task-management.md` 에 있음.
<!-- SECTION:NOTES:END -->
