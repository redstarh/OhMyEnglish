---
id: TASK-208
title: '구현 ④: POST /api/shadowing/recordings/{utterance_id}/readback'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:41'
labels: []
dependencies:
  - TASK-206
  - TASK-207
ordinal: 269000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4. 요청할 때 계산한다 — job 을 만들지 않는다. readback_transcript 가 이미 있으면 전사를 건너뛴다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 전사가 없으면 만들고 있으면 건너뛰는 것을 테스트로 고정한다
- [x] #2 응답이 낱말 단위 대조를 실어 준다
- [x] #3 남의 발화 id 로 부르면 거부한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 · TDD)

`services/readback.judge_readback` · `api/results.py:judge_recording_readback` ·
`tests/integration/test_readback_api.py` (테스트 **6건**).

### ⛔ 설계서의 경로가 리포 규칙과 어긋나 있었고 고쳤음

첫 판은 `POST /api/shadowing/recordings/{utterance_id}/readback` 이었음. 그런데
`api/shadowing.py` 머리말이 규칙을 이미 소유함 — **클립은 여러 세션이 공유하는 제품 자산이라 그
아래 두지만, 낭독은 학습자 음성이므로 세션 경계가 개인정보 경계**임. ⇒ 실제 경로는
`POST /api/sessions/{session_id}/recordings/{utterance_id}/readback` 이고 `recording_url` 과 같은
자리임. 설계서 §4 를 정정했음.

### AC 별

- **#1** 전사가 없으면 만들고 있으면 건너뛰는 것을 테스트가 고정함. 건너뛰는 것을 «보려면» 저장된
  값을 스텁의 문장과 다르게 둬야 함 — 그렇게 뒀음.
- **#2** 응답이 `words`(낱말마다 `word`·`verdict`) · `clipTranscript` · `readbackTranscript` 임.
  `dict[str, object]` 로 돌려줌(이 리포 관행 · `api/vocab.py` 가 근거를 가짐).
- **#3** 다른 세션 아래에서 부르면 404 임. ⛔ **그 경계를 두 갈래로 나눠 잼** — 아래 참조.

### ⛔ 뮤테이션이 실제 구멍을 찾아냈음 — 세션 경계를 재는 테스트가 하나 모자랐음

`and session_id = $2` 를 `or 1=1` 로 완화했는데 **6건 가운데 아무것도 실패하지 않았음.**
기전: 전사가 없는 갈래에서는 `load_recording` 이 세션을 다시 걸러 대신 막아 줌. 그런데 **전사가
이미 있으면 `load_recording` 을 아예 부르지 않으므로 그 자리에서는 쿼리의 세션 조건이 유일한
가드**임 ⇒ 그 갈래를 재는 테스트를 더했고 그 뒤 뮤테이션이 죽었음(**1 failed**).

| 뮤테이션 | 결과 |
|---|---|
| 세션 조건만 완화(`or 1=1`) | 테스트 추가 **전 5 passed(생존)** → **후 1 failed(죽음)** |
| 항상 다시 전사 | **1 failed** |
| 전사를 저장하지 않음 | **1 failed** |
| 발화 종류 조건 제거 | **6 passed(생존)** — 아래가 이유임 |

⚠️ **발화 종류 필터는 어떤 테스트로도 관측되지 않음.** 스키마 두 겹이 그 경로를 미리 닫음 —
`utterances_audio_only_for_shadowing`(포인터)과 029 의 `utterances_readback_only_for_shadowing`
(전사문). ⇒ 그 필터를 **「지금 무엇을 막는다」로 적지 않고** 스키마가 느슨해질 때를 위한 겹으로
남겼음. 테스트 docstring 이 그 사실을 가짐.

### ⚠️ 뮤테이션 판정이 한 번 거짓이었음 — `H-CF` 로 남겼음

넷을 한 셸에서 잇달아 돌렸더니 셋이 살아남은 것으로 나왔음. `sed` 는 적용됐음(`grep` 으로 확인).
따로 떼어 `__pycache__` 를 지우고 돌리니 죽었음 — **같은 초 안의 연속 수정에서 낡은 바이트코드가
재사용됨.** ⛔ 그 거짓 생존을 「테스트가 약하다」로 읽으면 없는 결함을 고치게 되고, 반대로 진짜
생존을 캐시 탓으로 돌리면 진짜 구멍을 지나침 — 이 회차에서 세션 경계가 실제로 후자였음.

### 그 밖에

⛔ `usage_sink` 를 넘김 — 낭독 전사는 Nova 호출이므로 빼면 비용이 어느 집계에도 안 나타남
(`services/usage.py`). ⚠️ Nova 쪽 기록 자체가 값을 못 싣는 것은 `TASK-204` 가 가짐.
⛔ **빈 전사를 저장하지 않음** — 저장하면 다시 눌러도 영원히 빈 판정이 돌아옴.

### 게이트

`pytest` **1383 passed**(1377 → +6) · `ruff` 0 · `ruff format` **301 files** · `ty` 0 — 넷 다 exit 0.
<!-- SECTION:NOTES:END -->
