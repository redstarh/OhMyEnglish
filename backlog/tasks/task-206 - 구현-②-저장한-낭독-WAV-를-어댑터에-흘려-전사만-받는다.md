---
id: TASK-206
title: '구현 ②: 저장한 낭독 WAV 를 어댑터에 흘려 전사만 받는다'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:25'
labels: []
dependencies:
  - TASK-205
ordinal: 267000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4-2. 코치 응답은 버린다. ⛔ 되돌리는 조건(배치 STT 로 옮김)이 있으므로 이 함수 하나만 갈면 되도록 경계를 좁게 둔다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 WAV 경로를 받아 전사문을 돌려주는 함수 하나로 좁힌다
- [x] #2 코치 응답을 버리는 것과 그 이유를 코드가 밝힌다
- [x] #3 전사가 비면 판정을 만들지 않고 그 사실을 돌려준다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 · TDD)

`services/readback.transcribe_readback` · `tests/unit/test_readback_transcribe.py` (테스트 **6건**).

### AC 별

- **#1** WAV 경로 하나를 받아 전사문 하나를 돌려주는 함수임. 어댑터는 **만들어 받음**
  (`make_adapter`) — 결정 131 의 되돌리는 조건(배치 STT 로 옮김)이 **이 함수 하나만** 갈면 되게 하는
  경계임. 프레임 크기·상한도 인자라 테스트가 통제함.
- **#2** `_first_user_final` 이 `speaker == "user"` 이고 `kind == "final"` 인 것만 받고 그 이유를
  코드가 밝힘(어댑터가 대화형이라 코치 전사문과 오디오가 함께 옴). 테스트 `_AgentOnlyAdapter` 가
  agent 것만 내는 갈래를 고정함.
- **#3** 얻지 못하면 빈 문자열임 — agent 만 오는 갈래와 **아무 응답이 없는 갈래**(`wait_for` 상한)
  둘 다 빈 문자열이고 어느 쪽에서도 어댑터를 닫음.

### 뮤테이션 넷이 다 죽었음

| 뮤테이션 | 결과 |
|---|---|
| agent 전사문도 받음 | **2 failed** |
| 어댑터를 닫지 않음 | **3 failed** |
| 프레임을 보내지 않음 | **2 failed** |
| 타임아웃을 삼키지 않음 | **1 failed** |

⚠️ 처음 쓴 「코치 것을 안 돌려준다」 테스트가 **빈 문자열만 단정해 아무것도 안 하는 구현에서도
통과**했음(RED 에서 잡았음) ⇒ 흘려보낸 프레임 수를 함께 단정해 판별력을 만들었음.

### ⛔ 실물 Nova 로 확인되지 않은 것 둘 — `TASK-210` 이 봄

1. **프레임을 다 보낸 뒤 이벤트를 읽는 순서**가 흐름 제어에 걸리지 않는지. 이 순서라야 보낸 프레임
   수가 결정적이라 그렇게 뒀고, 소켓 계층은 보내기와 읽기를 **동시에** 한다(다른 리듬임).
2. **파일이 갑자기 끝나도 Nova 가 final 을 내는지.** VAD 가 침묵으로 판정을 닫으므로 끝에 침묵을
   덧붙여야 할 수 있음. ⛔ **필요하다는 증거가 나온 뒤에 붙임** — 지금 붙이면 근거 없는 코드임.

### 게이트

`pytest` **1377 passed**(1371 → +6) · `ruff` 0 · `ruff format` **300 files** · `ty` 0 — 넷 다 exit 0.
⚠️ `H-BW` 에 또 걸렸음(한글 docstring 한 줄이 101열) — 고쳤음.
<!-- SECTION:NOTES:END -->
