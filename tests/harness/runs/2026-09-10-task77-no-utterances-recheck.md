# 회차 기록 — 「분석 대상 없음」을 첫 판독으로 확정하지 않게 함 (TASK-77)

> 캡틴 결정(2026-09-10): *"몇 번 더 보고 정함"*. 선택지 셋 중 **결과 화면에서 유예**를 골랐고,
> `onClose` 를 실패로 갈라 결과 접근을 잃는 쪽은 고르지 않았음.

## 1. 창을 먼저 좁혔음 — codex 의 프레이밍보다 작음

`audio_gateway/session.py` 의 `_close_and_record` 순서를 직접 읽었음: ① 진행 중 저장 대기 ②
`_flush_analysis`(종료 경로 flush) ③ `adapter.close()` ④ `end_session` + `resolve_dangling`.
**종료 기록 전에 flush 가 돎** — 그래서 정상 세션이 `completed` 가 될 때 job 이 이미 걸려 있고
결과 화면이 `no_utterances` 를 볼 수 없음.

`TASK-70` 의 다른 지적을 고친 것도 이 경로를 좁혔음 — 실행 중 어댑터 오류가 이제 `failed` 로
기록되므로 R2 가 `connection_failed`(사실에 맞는 종단 상태)를 냄.

**남은 창 하나**: **종료 경로 flush 가 실패한 경우.** `_flush_analysis` 는 예외를 삼킴(의도임 —
분석 1건보다 세션·전사문이 중요함). 그러면 세션이 `completed` + job 0 이고 R2 규칙 2 가
`no_utterances` 를 냄. 뒤에 `flush_ended_sessions` 가 job 을 걸지만 화면은 이미 멈춰 있음.
기존 테스트 `test_a_failing_flush_loses_only_the_analysis_not_the_session` 이 그 상태를 고정함.

## 2. 고친 것

`shouldKeepPolling(status, noUtterancesSeen)` 을 만들어 **폴링 정지 판정을 한 곳에 모았음**
(`TASK-56`·`TASK-77` 이 각각 그 판정을 건드렸음). `no_utterances` 는 연속 판독 수가
`NO_UTTERANCES_RECHECKS` 를 넘을 때까지 이어 봄. 나머지 종단 상태는 그대로 즉시 멈춤.

⚠️ **`NO_UTTERANCES_RECHECKS = 3` 은 설계 발명값임** — 스윕이 언제 도는지 보장하는 계약이 없음.
비용은 「진짜로 분석할 것이 없던 세션이 같은 문구를 몇 초 늦게 본다」 하나임.
⛔ **무한으로 만들지 않았음** — 상한이 없으면 `TASK-56` 이 없앤 영구 폴링이 다른 상태로 되살아남.

## 3. 직접 잰 값 — 음성 대조 포함

계측은 `TASK-56` 이 만든 것과 같음(CDP `Page.addScriptToEvaluateOnNewDocument` 로 `fetch` 를 감싸
셈 — 백엔드 로그에 의존하지 않음). 관측창 14초 · 폴링 주기 2초.

| 화면 | 세션 | 호출 | 첫~끝 | 첫 주기 뒤 |
|---|---|--:|--:|--:|
| `no_utterances` | `d127dece` | **5** | 6.03s | **2** |
| `final` (음성 대조) | `6225ddaf` | 2 | 0.0s | **0** |

**`no_utterances` 는 다시 보고 멈췄고**(무한이 아님) **`final` 은 여전히 즉시 멈춤** — 종단 판정이
통째로 풀린 것이 아님. 그 음성 대조가 없으면 「전부 다시 본다」와 구별되지 않음.

⚠️ t≈0 의 2건은 개발 모드 Strict Mode 의 이펙트 이중 실행임(`TASK-56` 회차가 그 근거를 가짐).
그래서 판정을 **개수 등호가 아니라 「첫 주기 뒤에 오는가」와 상한**으로 잼.

## 4. 그 계측이 반증할 수 있음

⛔ **판별력을 무력화로 확인했음.** `NO_UTTERANCES_RECHECKS` 를 **0** 으로 내리고 같은 계측을
돌렸음:

```
  no_utterances  결과 API 호출 2건 · 첫~끝 0.0s · 첫 주기 뒤 0건
  FAIL  no_utterances 화면이 2건에서 멈췄다 — 재확인이 걸리지 않았다
  FAIL  no_utterances 화면이 첫 주기 뒤에 다시 부르지 않았다 — 재확인 0회다
```

되돌린 뒤 다시 PASS 임. 즉 이 계측은 **고침이 사라지면 그것을 말함.**

## 5. 게이트

프론트 `npx tsc --noEmit` exit 0 · `npx eslint app lib` exit 0. 백엔드 변경 없음.
⚠️ 이 거동은 **단위 테스트로 잴 수 없음** — JS 테스트 러너가 없고(`TASK-34` 가 그 사실을 확인함)
판정 대상이 브라우저의 폴링 타이머임. 그래서 계측이 브라우저 다리에 있음.
