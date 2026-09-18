---
id: TASK-220
title: '품질 리뷰: TASK-214~217 변경분 (/simplify 4각)'
status: Done
assignee: []
created_date: '2026-09-18 19:33'
updated_date: '2026-09-18 19:56'
labels: []
dependencies: []
ordinal: 281000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
표준 지시 「주요 개발 뒤 /simplify」에 따른 품질 패스. ⛔ 2026-09-19 1차 시도가 미수신으로 끝났음 — reuse·simplification·efficiency·altitude 네 에이전트를 병렬로 띄웠고 8분 뒤 넷 다 idle 이 됐지만 결과를 하나도 내지 않았음(직접 제출 요청까지 보냈고 그래도 응답 없음). idle 은 완료가 아니라는 것을 다시 확인한 사례임. ⇒ 2차 시도는 codex 리뷰어로 좁은 범위(신설 transcribe.py · factory 의 create_transcriber·create_voice_adapter 갈래 · nova 의 사용량 기록과 transcribe_only · port 의 Transcriber)에만 건다. 범위 정본은 rules/common/code-review.md 와 메모 codex-review-scope-must-be-narrow 임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 수신하고 심각도로 분류한다
- [x] #2 CRITICAL·HIGH 가 없거나 고친다
- [x] #3 게이트 여덟이 통과한 상태로 남는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-19 — 시도 다섯 번 전부 미수신

1. `/simplify` 4각(reuse·simplification·efficiency·altitude) 병렬 → 17분 동안 running/idle 을
   오갔고 결과 0건. `SendMessage` 로 직접 제출을 요청했더니 다시 running 이 됐다가 또 idle.
2. codex 리뷰어(좁은 범위) → 8분 뒤 같은 모양으로 idle · 결과 0건.

⇒ 표본 다섯 · 에이전트 종류 둘이므로 원인을 **이 세션의 전달 경로**로 좁히는 것이 맞음. 다만
그 귀속도 확정이 아님(다른 세션에서 같은 위임이 되는지 재 보면 갈림).

⛔ **자기 리뷰로 대신하지 않았음** — `CLAUDE.md` 가 쓰기와 검증을 같은 컨텍스트에서 하는 것을
금지함. 다음 세션이 받는 것이 이 태스크의 남은 몫임.

⚠️ 내가 쓴 코드의 가독성 한 자리는 직접 고쳤음(`7915356` — `factory` 의 지시문 선택 삼중 조건식을
`if/elif/else` 로 펼침 · 동작 같음 · 게이트 통과). 리뷰 패스가 아니라 마무리로 분류함.

게이트는 통과 상태로 남겨 둠(AC3): pytest 1397 · ruff 0 · format 304 · ty 0 · tsc 0 · eslint 0 ·
next build 0.

## 2026-09-19 — 리뷰가 «도착했음». 앞의 「미수신」 판단은 틀렸음

다섯 리뷰어가 20분쯤 뒤에 결과를 냈음. ⇒ **원인이 「전달 경로 고장」이 아니라 「지연」이었음.**
`idle` 이 완료가 아니라는 것은 그대로 맞지만, `idle` 이 「끝났다」의 반증도 아님 — 표본 다섯으로
전달 경로를 의심한 것은 **너무 이른 귀속**이었음.

결과: **CRITICAL 0 · HIGH 0 · MEDIUM 3 · LOW 2** (+ 앞선 넓은 범위 회차의 하네스·테스트 지적).

### 고친 것

| 등급 | 자리 | 무엇 |
|---|---|---|
| MEDIUM | `factory.py` | 삼중 조건식 → `if/elif/else`(커밋 `7915356`) |
| MEDIUM | `nova.py` | `transcribe_only` → `declare_tools: bool = True`. 세 불리언 가운데 이것만 팩토리→어댑터 경계를 넘었고, 어댑터가 하는 판단은 봉투 키 하나뿐임 |
| LOW | `transcribe.py` | `_FRAME_BYTES` 에 `RECORDING_CHANNELS` 를 곱함. 없으면 채널이 2 가 될 때 100ms 가 50ms 가 되고 정렬 검사도 통과해 조용함 |
| LOW | `factory.py` | `create_transcriber` 가 스텁 설정을 스스로 거절함. 가드가 호출자에만 있으면 불변식 주장이 헛됨 |
| reuse | 하네스 A/B | 어댑터 손조립 → `create_voice_adapter` 경유. A 팔이 제품 경로와 같은 지시문을 받는 것이 강제됨 |
| reuse | 하네스 A/B | `_load_pcm` 삭제 → `ws_session.read_lpcm` 재사용(같은 규격 검사의 세 번째 복제였음) |
| reuse | 테스트 | `_imported_names` 복사본 둘 → `conftest.imported_names` 한 벌 |
| simplify | 테스트 | 밑줄만 다른 단정 둘 → 표기 정규화 뒤 한 번 |
| simplify | teardown | 상한 루프 → `limit=sys.maxsize` 한 번. 정책 함수에 새 스위치를 만들지 않음 |
| altitude | teardown | 삭제 순서 계약이 dict 키 위치에 실려 있던 것을 문장 순서로 옮김 |
| efficiency | 하네스 A/B | 마지막 팔 뒤의 `sleep(1.0)` 제거 |
| 기타 | `results.py` | 복제된 「30초」 삭제 — 상수가 정본임 |

### 넘긴 것 (근거 있음)

- MEDIUM `_user_finals` → `asyncio.timeout().reschedule()`: 리포에 `asyncio.timeout` 자리가 0 이고
  `wait_for` 가 10 곳임. 실물 계측으로 정한 타이밍 코드에 새 관용구를 들이는 거래가 나쁨.
- `asdict` 는 받았고 `Counter` 는 넘겼음 — 앞의 것은 필드 누락을 막지만 뒤의 것은 세 줄을 한 줄로
  바꾸는 것뿐임.
- altitude 3(`transcribe.py` 가 `app.services` 를 import 해 팩토리의 방향 불변식이 전이로 깨짐):
  상수를 `app/models/` 로 옮기는 별 작업임 ⇒ `TASK-221` 로 등록함.
- `close()` 의 `try/finally` 에 닿을 수 있는 예외 경로가 없는 것: 이 변경이 만든 구조가 아님.

### 재확인 (실측)

게이트 여덟 통과: `pytest` **1399 passed** · `ruff` 0 · `format` 304 · `ty` 0 · `tsc` 0 ·
`eslint` 0 · `next build` 0. 팩토리 경유로 바꾼 A/B 를 실물로 다시 돌려 수치 재현을 확인했고
(`llm_calls` 18 → 20) teardown 래퍼도 다시 계측했음(3 · 규칙 밖 파일 남음 · 빈 디렉터리 걷힘).
<!-- SECTION:NOTES:END -->
