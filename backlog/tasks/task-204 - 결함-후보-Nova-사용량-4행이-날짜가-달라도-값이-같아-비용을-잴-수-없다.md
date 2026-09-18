---
id: TASK-204
title: '결함 후보: Nova 사용량 4행이 날짜가 달라도 값이 같아 비용을 잴 수 없다'
status: Done
assignee: []
created_date: '2026-09-18 05:42'
updated_date: '2026-09-18 06:55'
labels: []
dependencies: []
ordinal: 265000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-189 의 비용 크기를 재려고 llm_calls 를 읽다가 드러났다. purpose='nova' 4행이 2026-09-12·17·18·18 로 날짜가 다른데 input_tokens 216 · input_speech_tokens 150 · input_text_tokens 66 · output 전부 0 으로 «완전히 같다». 코치가 소리로 말하므로 output_speech_tokens 가 0 일 수 없다 ⇒ 스트림 합계가 아니라 어느 고정 지점(promptStart·설정)만 적히는 것으로 보인다. TASK-124 의 목표(Nova 도 llm_calls 에 적는다)가 절반만 이뤄졌고, 그 결과 Nova 축의 비용을 우리 데이터로 잴 수 없다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 네 행이 같은 값인 기전을 코드에서 특정한다
- [x] #2 Nova 스트림의 실제 입력·출력 토큰이 어디서 오는지 확인한다
- [x] #3 고칠 수 있으면 고치고 못 고치면 그 한계를 문서에 남긴다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 · 결함 확정 후 고쳤음)

### AC#1 — 기전을 코드에서 특정했음. 「같은 값」은 우연이 아니었음

⛔ **`close()` 가 종료 이벤트를 보내기 «전에» 기록했음.** 그 순서는 `TASK-124` 가 *"아래 종료 절차가
예외로 빠지면 기록을 건너뛴다"* 를 막으려고 일부러 고른 것이었고 그 걱정은 옳았음 — 그러나 그 순서
때문에 **종료 뒤에 오는 이벤트를 못 봄.**

⇒ 순서를 **「종료 → 배수 → 기록」** 으로 바꾸고 기록을 `finally` 에 두어 **두 보장을 다 지켰음.**
배수는 `_drain_for_final_usage()` 이고 상한 2.0초 · `asyncio.shield` 로 감싸 펌프 취소의 정본이
아래 자리에 남게 했음.

### AC#2 — 값이 어디서 오는지 실물 산출물로 확인했음 (비용 0)

리포 안의 실물 캡처 `tests/harness/runs/2026-09-11-task97-tool-payload/B0-r2.json` 를 직접 읽었음 —
`usageEvent` 가 **23번** 오고 키는 매번 같음(`totalInputTokens`·`totalOutputTokens`·`details`…).

| 이벤트 | input | output |
|---|--:|--:|
| 1 | 22 | 0 |
| 2 | 172 | 0 |
| 3 | 173 | 0 |
| **4** | **216** | **0** |
| … | … | … |
| 23 | 759 | 270 |

⛔ **저장된 네 행의 216/0 은 그 열의 «네 번째» 이벤트와 정확히 같음.** 즉 마지막이 아니라 이른
snapshot 을 적고 있었음. 그리고 `isinstance` 가드가 뒤 이벤트를 버린 것이 **아님**(키가 매번 다 있음)
— 처음 세운 가설이 그것이었고 실물 캡처가 반증했음.

### AC#3 — 고쳤음. TDD 로 갔음

테스트 `test_close_records_the_final_usage_that_arrives_after_termination` 를 먼저 썼음.
⚠️ **첫 판의 RED 가 다른 이유로 빨갰음**(아무것도 기록되지 않음 · `0 == 1`) — 펌프가 앞 이벤트를
소화할 틈이 없었기 때문임. 틈을 주니 **`(216, 0) == (759, 270)`** 으로 «실사용 증상 그대로» 빨개졌음.
고친 뒤 초록. 배수 호출을 지우는 뮤테이션에서 다시 `(216, 0)` 으로 죽음(캐시를 비우고 확인 · `H-CF`).

⚠️ **기존 테스트로는 이 결함이 보이지 않았음** — 그 테스트가 `_collect` 로 스트림을 먼저 비운 뒤
닫음. 소켓 계층은 세션 끝에 읽기를 멈추므로 **실사용 형태가 이쪽**임.

### ⛔ 남은 확인 — 실물 세션 한 번이 필요함

이 고침이 실제로 큰 값을 적는지는 **실물 Nova 세션 뒤 `llm_calls` 새 행**으로만 확정됨.
`TASK-210` 노트에 그 확인을 넘겼음. 그것이 오면 `TASK-189` §6 의 빈 비용 칸도 함께 채움.

### 게이트

`pytest` **1384 passed**(1383 → +1) · `ruff` 0 · `ruff format` **301 files** · `ty` 0 — 넷 다 exit 0.
<!-- SECTION:NOTES:END -->
