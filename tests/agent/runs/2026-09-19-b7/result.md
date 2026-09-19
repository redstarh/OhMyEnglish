# B7 회차 — 재발화 판정의 원인 확정 (TS-34 AC#2 · TASK-236)

**목적은 원인 확정 하나임.** B6 회차가 「재발화가 판정되지 않고 종료 수렴으로 `incorrect`」를
관측하고 원인을 **미확정**으로 남겼음(`TASK-236`). 후보 둘을 가리는 것이 이 회차의 전부임.

- ㉮ **드라이버 탓** — 재발화가 코치의 시범 도중에 도착해 코치가 그것을 재발화로 듣지 못함
- ㉯ **앱·프롬프트 탓** — 타이밍이 맞아도 코치가 판정 tool 을 부르지 않음

## §0. 판정 — ㉮ 임. ㉯ 는 반증됨

**코치의 턴이 끝난 것을 프레임으로 확인한 뒤에 재발화를 흘리면, 앱은 그 재발화를 판정으로
닫았음.** 실물 1회차에서 둘째 `pronunciation` 프레임이 왔고 DB 행이 판정값으로 닫혔음.

| 관측 | B6 (앞 회차) | **B7 (이 회차)** |
|---|---|---|
| 둘째 `pronunciation` 프레임 | 오지 않았음 | **왔음** — `t=21.881` · `outcome=correct` |
| `outcome` | `incorrect` (종료 수렴) | **`correct`** (판정) |
| `spoken_form` | `null` | **`i finished the report and shared the results with my team`** |
| `resolved_at` 과 세션 종료 | **같음** ⇒ `resolve_dangling` | **1.839초 먼저** ⇒ 판정이 닫았음 |

⇒ **㉯ 는 반증됨.** 앱은 재발화를 듣고 판정 tool 을 부르며, 그 값을 `spoken_form` 과 함께 남김.
⇒ B6 의 관측은 **그 회차 드라이버가 만든 것**임.

⚠️ **㉮ «안»의 어느 성질이 B6 을 깨뜨렸는지는 가르지 못했음.** 후보가 둘 남아 있고 이 회차는
그것을 분리하지 않았음 — §5-3 이 그 경계를 적음. 가른 것은 「드라이버냐 앱이냐」까지임.

## §1. 환경 — 착수 전제를 그 자리에서 재검증했음

| 전제 (착수 지시) | 그 자리에서 잰 명령 | 결과 |
|---|---|---|
| 백엔드 `:8002` 가 스텁으로 떠 있음 | `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` | 맞음 — pid 92720 · `VOICE_ADAPTER=stub` |
| 프런트 `:3000` 은 호출 세션이 소유함 | 같은 명령 | 맞음 — pid 98298 · **회차 전후로 손대지 않았음** |
| 픽스처 `p2k.wav`·`p2a.wav` | `wave` 로 규격 확인 | 맞음 — 16kHz/16bit/mono · **3.792초**·**2.957초** |
| SigV4 는 `app/backend/.env` 에만 있음 | 백엔드를 `env -u AWS_BEARER_TOKEN_BEDROCK` 으로 띄움 | 실물 호출 1건 성공 |

- **HEAD**: 착수 시 `f7bca64` → **회차 중 `000530b` 로 움직였음**(호출 세션이 08:26:30Z 에 커밋).
  ⇒ **실물 회차(08:36:43~08:37:06Z)가 돌던 커밋은 `000530b`** 임. 그 커밋은 docs 만 건드렸고
  회차 중 `.py` 소스는 한 건도 바뀌지 않았음(`evidence/13-head-and-shared-instance.txt` —
  변한 것은 내 백엔드 재기동이 만든 `__pycache__/*.pyc` 뿐임).
- **DB 스키마**: `current_schema()` = `ohmyenglish`.
- ⚠️ **`find -newermt` 을 처음에 틀리게 걸었음** — 인자가 지역시각(KST)으로 해석되어 UTC 08:25 로
  적은 것이 실제로는 전날 23:25Z 가 됐고, 그래서 앱 소스 전부가 「방금 바뀐 것」으로 나왔음.
  실제 mtime 은 02:56Z·03:03Z 였음. **그 오독을 결론으로 쓰지 않고 `stat` 으로 다시 쟀음.**

## §2. 공유 인스턴스 판정 (§2-6) — 공유임

포트 `:8002`·`:3000` 이 둘 다 선점돼 있었고 회차 중 HEAD 가 움직였음 ⇒ **공유로 판정함.**
지킨 것 셋:

1. **전역·공유 상태를 바꾸지 않았음.** `app_setting` 류·오디오 장치 구성을 건드리지 않았음.
   백엔드 어댑터 전환은 착수 지시가 명시로 허용한 범위임(그리고 회차 끝에 되돌렸음 — §7).
2. **프런트 `:3000` 을 죽이지 않았음** — 회차 전후 pid 가 같음(98298).
3. **상태 판정에 boolean 을 쓰지 않고 식별자를 대조했음.** 회차 도중 `learning_sessions` 가 착수
   값보다 1 많았고, 그것을 「남의 세션」으로 단정할 뻔했음. `started_at` 으로 식별자를 대조해
   **내 첫 스텁 예비 회차(08:29:39Z · `513d4d6c`)** 임을 확인했음 — 그 회차는 드라이버가
   `ConnectionClosedOK` 로 죽어 session_id 를 못 남겼던 것임(§3-1). 걷었음.

## §3. 관측 수단을 먼저 세웠음 — 드라이버는 회차 디렉터리에 씀

⛔ **대상 소스를 고치지 않았음.** `tests/harness/ws_session.py` 는 머리말에
*"보내면서 받지 않는다"* 를 계약으로 적었고 그것이 B6 의 한계를 만든 자리이지만, 그 파일은 대상
소스이므로 손대지 않고 **새 드라이버를 회차 디렉터리에 썼음**.

- 드라이버: `tests/agent/runs/2026-09-19-b7/b7_turnwait.py`
- 가짜 서버(판별력 검사용): `tests/agent/runs/2026-09-19-b7/b7_fake_ws.py`

### 착수 지시가 요구한 네 가지를 어떻게 지켰는가

| # | 요구 | 이 드라이버가 한 것 |
|---|---|---|
| 1 | 첫 발화를 흘린 뒤 **읽기로 전환**해 `pronunciation` 프레임이 오는 것을 먼저 확인 | 보내기·받기를 **동시에** 도는 두 태스크로 갈랐고, 첫 발화 뒤 `await_first_tool` 단계에서 첫 프레임을 **기다림**. 못 잡으면 둘째 발화를 흘리지 않고 `blocked_no_observability` 로 끝냄 |
| 2 | 턴 종료를 **시각이 아니라 프레임**으로 판정 | §3-2 의 규칙 |
| 3 | 프레임마다 **도착 시각을 각자** 기록 | 받기 루프가 프레임마다 `t`(단조)·`wall`(UTC)·`phase` 를 씀. 이 회차는 404 프레임에 **서로 다른 `t` 값 132개** — B6 은 311 프레임 전부가 `t=32.728` 한 값이었음 |
| 4 | 둘째 발화 뒤 판정 tool 을 충분히 기다림 | 상한 **75초**로 걸었고 실제로 **0.27초**에 왔음(§4) |

### §3-1. 스텁으로는 이 측정이 성립하지 않음 (실측)

`audio_gateway/stub.py` 의 `events()` 는 고정 대본을 다 내놓으면 제너레이터가 끝나고 세션이 곧
닫힘. 예비 회차에서 **세션이 41ms 만에 닫혔음**(`evidence/01-stub-dryrun.json` ·
`verdict=blocked_closed_during_utt1`). 발음 tool 이 없고 턴을 이어 가지 않음.

⇒ 그래서 스텁 예비 회차의 값어치는 **드라이버의 기계 부품**(동시 송수신 · 프레임별 시각 · 닫힘
처리)을 확인한 것뿐임. 첫 예비 회차는 닫힘을 예외로 터뜨려 여태 모은 프레임을 통째로 잃었고,
그것을 고쳐(닫힘을 조용히 기록) 두 번째 예비 회차가 JSON 을 남겼음.

### §3-2. 턴 종료를 무엇으로 판정했는가 — ⛔ 시각 간격이 아님

**프레임 두 조건을 «모두» 만족해야 턴 종료임.**

> `agent final >= 1` **AND** `'audio' 프레임이 4000ms 동안 0건`

- ⒜ **agent `final` 프레임** — 근거는 `app/backend/app/audio_gateway/nova.py:1070` 임.
  `stopReason == END_TURN` 에서 `_flush_pending_agent_text()` 를 돌리고 그것이 agent final 을
  만듦. ⇒ **agent final 프레임 자체가 Nova 의 턴 경계 신호가 WS 로 새어 나온 것**임.
- ⒝ **`audio` 프레임의 정지** — `audio` 는 코치의 음성이므로 그것이 멈춘 것이 「코치가 말을
  마쳤다」임. (`tests/harness/p_app_path.py` 의 `QUIET_MS` 와 같은 판정임.)

⛔ **음성이 «한 건도» 오지 않은 경우는 ⒝ 를 만족시키지 않게 못 박았음** — 그것은 「조용하다」가
아니라 「아직 시작하지 않았다」이고, 그것을 턴 종료로 읽는 것이 함정 문서가 `tui-idle` 로 경고한
오판과 같음.

### §3-3. 판별력 증명 — 같은 수단이 두 결과를 «다르게» 냈음

⛔ 「둘째 프레임이 오지 않았다」를 결론으로 쓰려면 그 판정이 **반증될 수 있어야** 함. 실물 회차가
2회로 제한됐으므로 그 검사를 가짜 서버로 먼저 했음 — 같은 WS 규약으로 B6 의 프레임 지형을 흉내
내고 **둘째 `pronunciation` 프레임만 다르게** 둔 두 판을 돌렸음.

| 판 | 가짜 서버 | 드라이버 verdict | 원자료 |
|---|---|---|---|
| A | 둘째 프레임을 보냄 | **`second_tool_arrived`** | `evidence/02-fake-emit-second.json` |
| B | 보내지 않음 | **`second_tool_absent`** | `evidence/03-fake-no-second.json` |

두 판이 **다른** verdict 를 냈고 턴 종료도 프레임으로 정확히 잡혔음(A: 음성 정지 3.012초 뒤 ·
B: 3.028초 뒤). ⇒ 이 판정에는 판별력이 있음. **그 뒤에 실물을 1회 돌렸음.**

⚠️ 가짜 서버는 앱을 대신하지 않음 — 잰 것은 **내 관측 수단**뿐임.

## §4. 실물 회차 1회 — 프레임 근거

**세션** `5b370010-9ab1-429c-a3ff-27e30f334864` · `mode=pronunciation` ·
08:36:43.159966Z ~ 08:37:06.870254Z · 드라이버 경과 23.723초.
호출: `--quiet-ms 4000 --first-tool-wait-s 75 --turn-wait-s 90 --second-wait-s 75 --drain-s 25`.
원자료 `evidence/07-real-round-frames.json` · DB `evidence/08-post-real-round-db.txt`.

프레임 집계: `session_started` 1 · `speech_start` 2 · `speech_end` 2 · `final` 3 · `partial` 4 ·
**`pronunciation` 2** · `audio` 388 · **`interrupted` 1** · `session_ended` 1. (404 프레임 ·
서로 다른 `t` 값 132개.)

### §4-1. 도착 순서와 시각 — 비-audio 프레임 전부

| `t` (초) | 단계 | 프레임 | 내용 |
|--:|---|---|---|
| 0.203 | utt1 | `session_started` | |
| 1.160 | utt1 | `speech_start` | |
| 4.835 | utt1 | `final` user | 첫 발화의 전사 — **한글로 왔음**(강한 억양판) |
| 4.888 | utt1 | `speech_end` | |
| **6.230** | await_first_tool | **`pronunciation`** | `outcome=pending` · `target_sound=th_as_t` |
| 6.230 | await_first_tool | `partial` agent | 시범 시작 |
| 9.946 | await_turn_end | `partial` agent | `…with that soft " th" sound: "I finished the report…"` |
| 11.720 | await_turn_end | `partial` agent | `Can you repeat the whole sentence now…` |
| **13.348** | await_turn_end | **`final` agent** | ⇒ `END_TURN` 이 새어 나온 자리 (⒜ 성립) |
| 17.692 | utt2 | `speech_start` | |
| 17.693 | utt2 | `interrupted` | §5-2 |
| 21.089 | utt2 | `final` user | `i finished the report and shared the results with my team` |
| 21.198 | utt2 | `speech_end` | |
| **21.881** | await_second_tool | **`pronunciation`** | **`outcome=correct`** · `target_sound=th_as_t` |
| 21.924 | closing | `partial` agent | `Great job! You pronounced the  th" sound correctly in that sentence.` |
| 23.723 | closing | `session_ended` | |

### §4-2. 「타이밍이 맞았다」의 근거 — 둘째 발화가 코치의 턴 «밖»에 도착했음

⛔ ㉯ 를 반증하려면 이것을 먼저 보여야 함(착수 지시). `audio` 프레임을 둘째 발화 전후로 갈라 셌음:

| 값 | `t` (초) |
|---|--:|
| 코치의 시범 음성 **첫** `audio` | 6.357 |
| 코치의 시범 음성 **마지막** `audio` | **13.342** |
| agent `final`(턴 경계) | 13.348 |
| **턴 종료 판정** (음성 정지 4.008초 뒤) | **17.350** |
| **둘째 발화 송출 시작** | **17.350** |
| 둘째 발화 뒤 코치 음성이 **다시** 시작된 `t` | 22.049 |

- 둘째 발화 «전» `audio` 344건(6.357~13.342) · 둘째 발화 «뒤» `audio` 44건(22.049~22.816).
  ⇒ **13.342 와 22.049 사이에 코치의 음성이 0건임.** 둘째 발화는 그 구멍 안에서 흘렀음.
- 둘째 발화는 코치의 마지막 음성보다 **4.008초 뒤**, agent final 보다 **4.002초 뒤**에 시작했음.
  ⇒ 시범 도중이 아니라 **턴이 닫힌 뒤**에 도착했음.

### §4-3. 둘째 발화 뒤 얼마나 기다렸는가

상한을 **75초**로 걸었고, 실제로는 송출이 끝난 뒤 **0.27초**에 둘째 `pronunciation` 프레임이 왔음
(`second_tool_waited_s = 0.27` · 그 사이 흘린 무음 8프레임). ⇒ 기다림이 부족했을 여지가 없음.

### §4-4. DB — 판정이 세션 종료 «전»에 닫았음

`pronunciation_attempts` 는 **1행**임(두 tool 호출이 한 행을 열고 닫는 것이 설계임 —
`record_attempt` 가 최신 `pending` 을 닫음):

| 열 | 값 |
|---|---|
| `outcome` | **`correct`** |
| `spoken_form` | **`i finished the report and shared the results with my team`** |
| `target_form` | `I finished the report and shared the results with my team.` |
| `target_sound` | `th_as_t` |
| `signal_source` | `nova_tool` |
| `created_at` | 08:36:49.375977Z |
| `resolved_at` | 08:37:05.031683Z |
| 세션 `ended_at` | 08:37:06.870254Z |

⇒ **판정이 세션 종료보다 1.839초 먼저 났음.** 그것이 `resolve_dangling` 의 종료 수렴과 가르는
자리임 — B6 은 두 시각이 같았음.

`utterances` 3행(user·agent·user)이고 seq 3 이 재발화임. 이 회차는 `error_patterns` 를 만들지도
갱신하지도 않았음(`correct` 이므로) — 오늘 `last_seen_at` 인 행 0건으로 확인했음.

## §5. 곁에서 나온 관측 셋 — ⛔ 새 결함으로 올리지 않았음

착수 지시가 「관측 결과는 `TASK-236` 에 덧붙이고 새 결함을 만들지 말 것」을 명시했으므로 셋 다
결함으로 올리지 않았음. ⚠️ **⑴ 은 뿌리가 다르므로 별건 결함으로 올릴지를 호출 세션이 정할 자리임.**

### §5-1. `sound_check` 가 비었음 — 코치가 소리를 12번 인용했는데도

이 회차의 행은 `sound_check` 가 **NULL** 임. B6 의 행은 `matched` 였음. 앱과 **같은 창**으로
코치 발화를 읽어 `sound_check_verdict` 를 직접 돌려 기전을 확인했음
(`evidence/09-sound-check-probe.txt`):

| 입력 | 판정 | 인용 토큰 추출 |
|---|---|---|
| 이 회차의 코치 발화 그대로 | **`None`** | **없음** |
| 같은 글에서 **여는 따옴표 뒤 공백만** 없앤 것 | **`matched`** | `th`·`the`·`with` |
| B6 의 코치 발화 문면 | `matched` | `th`·`the`·`this` |

기전: 이 회차의 코치는 소리를 `" th"` 처럼 **여는 따옴표 뒤에 공백을 넣어** 인용했고(그런 자리가
**12곳**), `services/pronunciation._QUOTED_TOKEN_RE` 는 따옴표 바로 뒤에 글자가 오기를 요구하므로
토큰을 하나도 뽑지 못했음 ⇒ `None` ⇒ `sound_check` 를 비워 둠.

⚠️ **이것이 잘못된 배제를 내지는 않음.** 그 함수의 계약이 *"「맞다」를 증명하지 않는다 —
「어긋났다」만 증명한다"* 이고 `None` 은 안전한 쪽임(정상 기록을 복습에서 지우지 않음).
잃은 것은 **결정 82 가 세운 검증 신호 자체**임 — 어긋남을 잡을 기회가 그 회차에서 0이 됨.
⚠️ **간헐임** — 모델의 인용 문체에 달렸고 B6·B7 이 실제로 갈렸음.
**제안**(직접 고치지 않았음): 그 정규식이 여는 따옴표 뒤 공백을 건너뛰게 하는 안. 단위 테스트가
그 문면을 못 박는 자리를 함께 봐야 함.

### §5-2. `interrupted` 프레임 1건 — 코치가 4초 전에 조용해졌는데도

`t=17.692` 의 `speech_start` 바로 뒤 `t=17.693` 에 `interrupted` 가 왔음. 코치의 마지막 음성은
`t=13.342` 였으므로 **4.35초 조용한 뒤에 시작한 발화**가 barge-in 으로 표시됐음.
⚠️ **결함으로 올리지 않았음** — 그 프레임은 화면 상태일 뿐이고(`session.py` 가 방송만 함) 이
회차의 판정은 정상으로 났음. 다만 「학습자가 기다렸는데 끼어든 것으로 표시된다」는 화면 쪽
관측이라 배지·화면 영역(A5-1·A5-2)을 볼 회차의 재료로 적어 둠.

### §5-3. ㉮ 안의 기전을 가르지 못했음 — 남은 후보 둘

이 회차가 가른 것은 「드라이버냐 앱이냐」까지임. **B6 의 드라이버가 어느 성질로 그 결과를
만들었는지는 분리하지 않았음.**

1. **재발화의 도착 시점** — B6 은 코치의 턴 종료를 기다리지 않았음.
2. **소켓 역압(backpressure)** — B6 은 *"보내면서 받지 않는다"* 가 계약이라 30여 초 동안 소켓을
   읽지 않았음. B6 의 모든 프레임이 `t=32.728`(송출이 끝난 직후)에 한꺼번에 읽힌 것이 **수신
   버퍼가 찼다**는 뜻이고, 그러면 서버의 쓰기가 막혀 `_pump_adapter_events` 가 함께 멈춤.
   B6 에서 **사용자의 둘째 `final` 이 코치의 첫 `partial` «보다 먼저»** 온 순서가 그 정지와
   맞아 떨어짐 — 이 회차는 그 순서가 반대였음(코치 partial `t=6.230` → 사용자 둘째 final `t=21.089`).

⇒ 이 회차의 드라이버는 둘을 **함께** 고쳤으므로 어느 하나만으로 재현되는지는 모름.
⚠️ **가르려면 실물 1회가 더 필요하고, 1회로 갈렸으므로 돌리지 않았음**(착수 지시).
⚠️ 그리고 그 구별은 **대상 앱의 결함과 무관**함 — 둘 다 드라이버의 성질임.

## §6. 비용과 실물 호출 횟수

| 항목 | 값 |
|---|---|
| **실물 Nova 세션** | **1회** (허용 2회 · ⛔ 1회로 갈렸으므로 2회차를 돌리지 않았음) |
| `llm_calls` | 착수 **38** → 회차 뒤 **39** · **증가분 1** |
| 그 호출 | `bedrock` · `amazon.nova-2-sonic-v1:0` · `purpose=nova` · 입력 음성 토큰 363 · 출력 음성 토큰 843 · 08:37:06.868Z |
| `analysis_jobs` | 착수 111 → 회차 중 116(+5) → **teardown 뒤 111** |
| 스텁 예비 회차 | 2회 (Bedrock 호출 **0건**) · 가짜 서버 회차 2회 (호출 0건 · DB 미접촉) |

⚠️ `llm_calls` 는 비용 기록이라 teardown 으로 지우지 않았음 — 지우면 비용을 복원할 수 없음.
⛔ **워커를 켜지 않았음** — 백엔드를 두 번 다 `WORKER_ENABLED=false` 로 띄웠음(함정 `H-CD`).

## §7. 정리 — teardown 과 백엔드 복귀

**teardown 을 돌린 세션 3건** (모두 드라이버가 기록한 ID 로 골랐음 · 시각창으로 고르지 않았음):

| 세션 | 무엇 | 원자료 |
|---|---|---|
| `513d4d6c-c4b8-4339-9b53-990ce7858775` | 스텁 예비 1회차(드라이버가 죽어 ID 를 DB 에서 찾았음) | `evidence/04-teardown-stub-dryrun.txt` |
| `63771c89-6c2e-4e6c-b52e-c300d95e57e0` | 스텁 예비 2회차 | 같은 파일 |
| **`5b370010-9ab1-429c-a3ff-27e30f334864`** | **실물 회차** | `evidence/10-teardown-real-session.txt` |

회차 뒤 계수기가 착수 값으로 되돌아왔음(`evidence/11-post-teardown-counters.txt`):

| 표 | 착수 | 회차 끝 |
|---|--:|--:|
| `learning_sessions` | 27 | **27** |
| `utterances` | 175 | **175** |
| `analysis_jobs` | 111 | **111** |
| `pronunciation_attempts` | 7 | **7** |
| `error_patterns` | 9 | **9** |
| `review_tasks` | 15 | **15** |

⚠️ B6 이 손으로 지워야 했던 자리(`error_patterns`·`review_tasks`)는 이 회차에 **손댈 것이
없었음** — `outcome=correct` 이라 패턴을 만들지 않았고, 오늘 `last_seen_at` 인 행이 0건임을
확인했음.

**백엔드**: 회차 끝에 **`VOICE_ADAPTER=stub` · `WORKER_ENABLED=false` 로 되돌려 띄워 두었음**
(pid 77150 · `/health` 200 · 어댑터 재확인 503 = stub ·
`evidence/12-backend-restored-stub.txt`). 프런트 `:3000` 은 회차 전후 pid 가 같음(98298).

## §8. 원장 갱신

### TS-34 (테스트 원장 `tests/agent`) — `Blocked` 유지 · AC 3/4

- AC#1 ✅ (B6 에서 확인됨 · 이 회차도 시범을 다시 봄)
- **AC#2 ✅ 이 회차가 채웠음** — 재발화가 `correct` 로 «판정에 의해» 닫히고 `spoken_form` 이
  채워졌음. PRD R10-2·AC10-2 가 요구한 것이 실물 왕복으로 성립함.
- AC#3 ❌ 여전히 미충족 — 보조 신호(`korean_transcript`·`agent_reprompt`) writer 가 코드에
  0곳임. 결함 `TASK-237` 이 그 갈림을 사람의 결정으로 올려 두었음. **이 회차의 사거리 밖임.**
- AC#4 ✅

⚠️ 부분 확인이므로 `Done` 이 아님. 착수 지시대로 `Blocked` 로 둠.

### TASK-236 (작업 원장) — 노트에 이 회차의 관측을 덧붙였음

`--append-notes` 로 덧붙였음(⛔ `--notes` 는 본문을 덮으므로 쓰지 않았음).
그 결함의 AC#1(*"코치의 턴이 끝난 뒤에 재발화를 흘리는 수단으로 재현해, 재발화가 판정으로
닫히는지 실물 왕복으로 확인했다"*)이 **이 회차로 충족됐음.**

⛔ **상태 전환과 종결은 이 에이전트가 정하지 않음** — `TASK-236` 의 본문이 담은 항목 3(결정의
전제와 구현의 조건이 어긋난 자리 · 제품 판단)은 이 회차가 닫지 못함. 그 갈림을 호출 세션과
사람이 정할 자리이므로 상태는 그대로 두고 관측만 덧붙였음.
