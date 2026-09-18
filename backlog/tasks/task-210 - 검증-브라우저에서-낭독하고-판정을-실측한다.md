---
id: TASK-210
title: '검증: 브라우저에서 낭독하고 판정을 실측한다'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 07:29'
labels: []
dependencies:
  - TASK-209
ordinal: 271000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 전체. ⛔ localhost:3000 으로 열고 ?mode= 쿼리를 쓰지 않는다(H-CA·H-CC). ⛔ 회차 뒤 teardown_session.py 로 세션을 걷는다(TASK-193).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 일부러 한 낱말을 빼고 읽어 그 낱말이 빠짐으로 표시되는 것을 본다
- [x] #2 두 번째 조회가 전사를 다시 하지 않는 것을 확인한다
- [x] #3 회차 뒤 큐가 늘지 않은 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## ⛔ 착수 전에 볼 것 — `TASK-206` 이 실물로 확인하지 못한 둘

1. **프레임을 다 보낸 «뒤» 이벤트를 읽는 순서가 흐름 제어에 걸리지 않는가.** 스텁에서는 걸리지 않고
   그 순서라야 보낸 프레임 수가 결정적이어서 그렇게 뒀음. 소켓 계층은 보내기와 읽기를 동시에 하므로
   리듬이 다름. 걸리면 동시 형태로 바꾸고 프레임 수 단정을 다시 설계해야 함.
2. **파일이 갑자기 끝나도 Nova 가 final 전사문을 내는가.** VAD 가 침묵으로 판정을 닫으므로 끝에
   침묵을 덧붙여야 할 수 있음. ⛔ 필요하다는 증거를 이 회차가 만든 뒤에 붙임.

## ⛔ 이 회차가 함께 확인할 것 — `TASK-204` 의 고침

회차 전 `select count(*) from llm_calls where purpose='nova'` 를 세어 두고, 회차 뒤 **새 행 하나**를
읽음. 확인할 것 둘: ⑴ `output_tokens` 가 **0 이 아님**(코치가 말했으므로) ⑵ 값이 216/0 이 아님.
그 값이 `TASK-189` §6 의 비어 있는 「낭독 전사 비용」 칸을 채움.

## 실물 Nova 로 서비스 층을 먼저 쟀음 (2026-09-18) — 브라우저 없이

⛔ **브라우저 회차를 짜기 «전에» 위험한 미지를 값싸게 쟀음.** CDP 브라우저가 떠 있지 않고 쉐도잉
낭독 흐름을 태우는 드라이버가 아직 없어서, 서비스 함수를 직접 불러 실물 Nova 를 한 번 탔음.

입력: `say -v Samantha` 로 만든 **낱말 하나를 뺀** 낭독 —
클립 `"All right, so here we are in front of the elephants"` 에서 `front` 를 빼고 읽음.
`afconvert -f WAVE -d LEI16@16000 -c 1` 로 16kHz·모노·16bit 로 맞췄음.

### ⛔ 발견 1 — 침묵이 없으면 전사가 «아예» 오지 않는다

| 회차 | 오디오 | 전사 |
|---|---|---|
| 1 | 2.6초 (침묵 없음) | **`''`** (빈 문자열) |
| 2 | 4.6초 (끝에 2초 침묵) | **`'alright, so here we are in of the elephants.'`** |

⇒ `TASK-206` 이 「증거가 나온 뒤에 붙인다」고 미뤄 둔 침묵을 **증거와 함께 넣었음**
(`_TRAILING_SILENCE_BYTES` · 테스트 둘이 그것을 고정하고 뮤테이션에서 2건이 죽음).
⚠️ **실사용 입력에는 침묵이 없음** — 학습자가 「읽기 끝」을 누른 순간 파일이 끊기므로 이 값은
선택이 아니라 필수임.

### 발견 2 — 보내기·읽기 순서는 실물에서도 걸리지 않았음

프레임을 다 보낸 «뒤» 이벤트를 읽는 순서로 실물 전사를 받았음 ⇒ `TASK-206` 의 미지 ①이 닫혔음.

### 발견 3 — 낱말 대조가 실물 전사에서 「빠짐」을 정확히 잡았음

`front` 만 `missing` 이었음(AC#1 의 실질). ⚠️ 그런데 **전사기가 `All right` 을 `alright` 로 합쳐**
`All`·`right,` 두 낱말이 `different` 로 잡혔음 — 학습자가 틀리지 않은 자리임. **낱말 단위 대조의
알려진 한계이고 학습자에게 불리한 방향**이라 구현 docstring 에 남겼음.

### 발견 4 — `TASK-204` 의 고침이 실물에서 확인됐음

| 회차 | `llm_calls` 새 행 |
|---|---|
| 침묵 없음(전사·응답 0) | input **216** · output **0** · in_speech 150 |
| 침묵 붙임(전사 옴) | input **1,853** · output **15** · in_speech **229** |

⇒ 216/0 을 벗어났고 **output 이 0 이 아님.** ⚠️ 동시에 **앞선 네 행의 216/0 이 「이른 snapshot」이
아니라 「아무것도 일어나지 않은 세션의 정직한 총계」일 수 있음이 드러났음** — 첫 회차가 그 값을 그대로
재현했음. `TASK-204` 의 고침 자체는 옳지만(배수 없이는 뒤 이벤트를 못 본다) **네 행의 원인 진단은
단정하지 않음.**

### 낭독 전사 한 번의 비용 — `TASK-189` §6 의 빈 칸을 채움

입력 **1,853** 토큰(음성 229) · 출력 **15** 토큰 · 모델 `amazon.nova-2-sonic-v1:0`.
⚠️ 단가를 곱하지 않음 — 이 리포에 Nova 단가표가 없음.

### ⛔ 남은 것 — 화면 관측 (AC#1 의 「보이는 것」 · AC#2 · AC#3)

서비스 층은 닫혔고 **화면에 그렇게 뜨는지는 아직 안 봤음.** 필요한 것 셋:
⑴ `--remote-debugging-port=9222` 로 Chrome 기동(지금 없음) ⑵ 쉐도잉 낭독 흐름을 태우는 드라이버
(`p_app_path.py` 의 마이크 대체 + `TASK-183` 의 진입 순서를 합침) ⑶ `:8014` 백엔드와
`.env.local` 재지정·되돌리기(`TASK-183` 이 그 절차를 가짐).
⛔ **회차 뒤 `teardown_session.py` 로 세션을 걷음**(`TASK-193`).
⚠️ 이 회차는 세션을 만들지 않았으므로 걷을 것이 없음 — 남긴 것은 `llm_calls` 두 행(비용 기록)임.

## 실서버(:8014 · `VOICE_ADAPTER=nova`)에서 AC#2·AC#3 을 닫았음 (2026-09-18)

브라우저 대신 **H-BD 가 적어 둔 우회로**를 썼음 — 마이크가 목적이 아니면 앱 서비스 함수로 상태를
만들고 HTTP 로 판정만 부름. 세션 하나를 열고 낭독 발화 한 행과 PCM 파일을 두고 엔드포인트를 두 번 불렀음.

| 회차 | 결과 |
|---|---|
| 1차 | `HTTP 200` · **2.29초** · 전사 `'alright, so here we are in of the elephants.'` · 낱말 11 · `missing=['front']` |
| 2차 | `HTTP 200` · **0.00초** · 같은 전사 · 같은 판정 |

- **AC#2 닫힘** — 2.29초 → **0.00초** 가 「다시 전사하지 않았다」의 판별력임. `llm_calls` 의 nova 행도
  **6 → 7 로 한 번만** 늘었음(둘째 호출은 0건).
- **AC#3 닫힘** — teardown 뒤 `analysis_jobs` **111 → 111** · 세션 잔여 **0행**.
- ⛔ 라우터 배선·설정·어댑터 생성이 **실서버에서** 동작함을 확인했음(테스트는 스텁 어댑터와 테스트 DB
  를 쓰므로 이 겹은 그쪽이 못 봄).

### ⛔ 이 회차가 결함 하나를 찾았음 — teardown 이 파일을 남겼음

`파일 잔여: True` 였음. DB 행은 cascade 로 걷혔지만 **디스크의 낭독 PCM 이 고아로 남았음.**
앱에는 고아 파일 스윕이 있으나(`recordings.sweep_orphan_recording_files`) **워커가 꺼진 개발
환경에서는 돌지 않음** ⇒ `teardown_session.py` 가 세션 디렉터리를 함께 걷도록 고쳤음
(`recordings_removed`). Nova 를 부르지 않는 확인 회차에서 `recordings_removed: 1` ·
파일·디렉터리 잔여 **없음**을 봤음. 앞 회차가 남긴 고아 디렉터리도 지웠음(`assets/audio` 0개).

### ⛔ 남은 것 하나 — AC#1 의 「화면에 그렇게 보이는 것」

판정이 HTTP 로 옳게 나오는 것은 확인했으나 **화면 렌더는 아직 안 봤음.** 필요한 것 셋은 그대로임:
⑴ 전용 Chrome(`--remote-debugging-port=9333 --user-data-dir=/tmp/... --use-fake-device-for-media-stream
--use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required` · `H-BD` 의 레시피)
⑵ **쉐도잉 낭독 흐름 드라이버가 아직 없음** — `p_app_path.py` 의 마이크 대체는 `instrument.js` 의
`window.__omy` 에 매여 있고 그 드라이버는 «말하기» 세션을 태움. 낭독 흐름(쉐도잉 진입 → 따라 읽기 →
읽기 끝 → 판정 보기)을 태우는 드라이버를 새로 써야 함 ⑶ `.env.local` 재지정·되돌리기.
⚠️ 픽스처는 이미 있음 — `/tmp/readback_pad.wav`(`say` + `afconvert` · 끝에 침묵 2초).

## ⛔ 브라우저 회차로 AC#1 을 닫았음 (2026-09-18) — 그리고 회차가 결함 하나를 더 잡았음

드라이버를 새로 만들었음: `tests/harness/p_readback_leg.py`. 계측(`instrument.js`)을 설치하지 않고
마이크 대체와 DOM 관측만 함 — 재는 것이 낭독 흐름과 판정 화면이라 필요 없는 의존을 늘리지 않았음.
세션 ID 는 **판정 요청 URL 을 `fetch` 랩으로 잡아** 얻음(시각창을 쓰지 않음).

스택: 전용 Chrome(`9333` · `H-BD` 레시피) · `:8002` 를 새 코드 + `VOICE_ADAPTER=nova` 로 재기동 ·
픽스처는 `say` + `afconvert` 로 만든 **클립에서 `coffee` 를 뺀 낭독**(14.9초 · 끝에 침묵 2초).

### ⛔ 결함 — 첫 final 하나만 받아 여섯 문장 클립의 전사가 두 문장에서 끊겼음

1차 회차의 저장 전사: `'i usually wake up at seven. first, i check my phone for messages.'`
⇒ 화면에서 **맞음 13 · 빠짐 32** 로, 학습자가 «읽은» 32낱말이 빠짐으로 표시됐음.
실물 Nova 는 끊어 읽는 자리마다 final 을 내는데 `transcribe_readback` 이 첫 것만 받았음.
⇒ **조용해질 때까지 모아 이어 붙이도록 고쳤음**(`_user_finals` · `_QUIET_AFTER_FINAL_S=3.0`).
⛔ 조용함은 **마지막 학습자 final 뒤로 흐른 시간**으로 재야 함 — 낭독이 끝나면 코치가 말하기 시작해
「아무 이벤트도 없음」은 오지 않음. RED 를 먼저 봤고(스텁 세 턴 가운데 첫 답만 왔음) 고친 뒤 초록.

### AC#1 — 고친 뒤 화면에서 확정했음

| 관측 | 값 |
|---|---|
| 버튼 | 클립 듣기 · 따라 읽기 · **내 낭독 듣기** · **낭독 판정 보기** · 학습 종료 |
| 낭독 전 | 「내 낭독 듣기」·「낭독 판정 보기」 **둘 다 없음** (서버 프레임을 받은 뒤 나타남) |
| 판정 | 낱말 45개 · **맞음 44 · 빠짐 1** — 그 하나가 일부러 뺀 **`coffee.`** |
| 장식 | 취소선 1 · 밑줄 0 · 없음 44 · 색은 `--danger`(`rgb(255,138,138)`) 1 · `--foreground` 44 |
| 저장 전사 | 여섯 문장 전부 (`'… then i make a cup of. after that, …'`) |
| 안내 | 「밑줄은 다르게 읽은 낱말이고 취소선은 빠뜨린 낱말이에요.」 |
| 마이크 | `gumCalls=1` · `played=1` · 16kHz |

**스크린샷을 직접 봤음**(`/tmp/readback-final.png`) — `coffee.` 만 빨간 취소선이고 나머지는 평문임.
⚠️ 첫 스크린샷에서 **취소선이 낱말 뒤 공백까지 덮어** 다음 낱말에 붙어 보였음 ⇒ 공백을 `span` 밖으로
빼고(`Fragment`) 다시 관측해 확정했음. 화면을 안 봤으면 못 잡았을 결함임.

### 정리

회차 넷을 다 걷었음(`teardown_session.py`) — `analysis_jobs` **111 → 111** · `assets/audio` **0개** ·
내 세션 잔여 0. Chrome 과 임시 프로필 제거. `:8002` 는 **`VOICE_ADAPTER=stub` 으로 복원**(health 200).
⚠️ `llm_calls` 의 nova 행은 4 → 15 로 늘었음 — 비용 기록이므로 남김.

### 게이트 여덟

`pytest` **1386 passed** · `ruff` 0 · `ruff format` **302 files** · `ty` 0 · `tsc` 0 · `eslint` 0 ·
`next build` 0(`/` 가 `○` Static 유지).
<!-- SECTION:NOTES:END -->
