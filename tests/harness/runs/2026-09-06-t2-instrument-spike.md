# T2 스파이크 — `instrument.js` 신설 + 실측 (`TASK-19`)

> 2026-09-06 · 실행 주체: **`.claude/agents/frontend-verifier.md`** 에이전트(3회차: A=throw 확인 ·
> B=정상 관통 · C=무음 대조 + 타이밍 추적). 절차 정본 `tests/harness/browser_leg.md`.
> 대상: `tests/harness/instrument.js`(커밋 `bcf0daf`, 292줄).
>
> ⚠️ **이 기록은 사후 편집하지 않는다.** 팀리드가 직접 확인한 것과 확인하지 못한 것을 §5에서 가른다.

---

## 1. 판정 요약 — AC 4건

| AC | 판정 | 요지 |
|---|---|---|
| ① 반환값 `'instrumented'` | **PASS**(에이전트) | 문자열이 그대로 왔다 — Promise 아님. 동기 IIFE 판단이 맞았다 |
| ② 후킹 대상 부재 시 throw | **PASS**(에이전트) | `delete WebSocket.prototype.send` 후 `계측 대상 부재: WebSocket 체인에 send 가 없다`. `window.__omy` 미설정 = 오염 없음. 확인 후 재로드·복원 |
| ③ `start`의 소유 프로토타입 | **PASS**(에이전트) | `startOwner: AudioBufferSourceNode` · `createBufferSourceOwner: BaseAudioContext` |
| ④ A1-7 음성 대조 | ⛔ **판별력 없음** — §11-4가 "쓸 수 없다"로 닫혔다 | 아래 §2 |

⚠️ **`TASK-19`를 `Done`으로 올리지 않았다.** ①~③은 브라우저 관측이고 팀리드가 재현하지 못했다.
④는 팀리드가 **코드로 독립 확인**했으므로 결론이 산다(§5).

## 2. ④ A1-7 — 측정도 대조도 성립하지 않는다

**측정**: `sent = {audio: 0, end_session: 0, unparsed: 0, other: 1}` · `sentAudioBytes: 0`.
원인은 후킹 고장이 아니다 — 세션이 **23ms에 자기종료**한다(DB `ended_at - started_at = 23.001 ms`).
스텁 `events()`에 페이싱이 없어 15프레임을 한 번에 쏟고 `page.tsx`가 결과 화면으로 이탈한다.
캡처 프레임 하나는 512샘플@16kHz = **32ms**가 필요하므로 **첫 프레임이 만들어지기 전에 끝난다.**
`학습 종료` 버튼에 도달하지 못한다(클릭 직후 DOM이 `0 buttons`) → `end_session`도 0이다.

**대조**: 무음 스트림이 **원리적으로 0을 낼 수 없다.**

| | frames | nonZeroFrames | totalB64Len |
|---|---|---|---|
| gain 1 (톤) | 146 | 146 | 199,728 |
| gain 0 (무음) | **146** | 0 | **199,728** |

`lib/audio.ts`의 캡처 워클렛 `process()`가 **진폭과 무관하게** 512샘플마다 `postMessage`한다 —
무음 게이트가 없다. `silentMic` 스위치 자체는 동작한다(같은 그래프 RMS 0.705 → 0.000).
**계수도 바이트 길이도 동일하고 다른 것은 PCM 내용뿐인데 계측은 그것을 기록하지 않는다.**

## 3. 덤으로 얻은 값

| 항목 | 값 | 판정 |
|---|---|---|
| `recv` (2회차·3회차 동일) | `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1 · session_failed 0` | A1-1·A1-2·A1-3 기대값 일치, **2회 재현** |
| URL | `/results/<uuid>` 두 회차 | A1-6 성립 |
| `utterances` | 세션당 **+6**, 화자 교대, transcript가 `FIXTURE_TURNS` 축자 | A1-8 일치 |
| `started` | 2회차 `count 0` / 3회차 `count 1, when [0]` | ⛔ **기대값 3이 안 나오고 회차마다 다르다** |
| `finalLines` | 2회차 `[]` / 3회차 픽스처 6줄 축자 일치 | ⛔ **레이스** |
| `snapshots` | 2회차 6개 전부 6줄 / 3회차 6개 전부 `[]` | ⛔ **레이스 (`finalLines`와 반대로 움직인다)** |

**`started`가 3이 아닌 이유 — 에이전트가 코드를 읽어 짚었다**: `page.tsx`의 `case "audio"`가
`enqueueAudioFrame(voiceRef.current, …)`을 부르고 그 함수는 `if (!voice) return`으로 조용히 반환한다.
`voiceRef.current`는 `await VoiceIo.start(...)`(안에서 `audioWorklet.addModule`을 기다린다)가 끝난
뒤에야 채워진다. 즉 **프레임은 `recv` 계수까지 도달하지만 앱이 버린다** — `enqueueAudio`에 닿지
않으므로 `createBufferSource`도 `start`도 불리지 않는다.

## 4. 결함 목록 — 고치지 않고 보고받았다

**`instrument.js` (팀리드 소유)**

1. `session_ended`에 **동기로** 찍는 `finalLines`가 React commit 전이라 `[]`가 될 수 있다.
2. 진단용 rAF 스냅샷은 반대로 `router.push` 이후에 떠서 `[]`가 될 수 있다. **1·2가 서로 반대로
   실패하므로 A1-5에 쓸 경로가 어느 회차에도 보장되지 않는다.** §11-7은 닫히지 않았다.
3. `meta.audioContextState`를 async `resume()` **직후 동기로** 써서 항상 resume 이전 값을 남긴다 →
   이 필드로 §11-3을 판정할 수 없다. 별도 probe로는 클릭 후 컨텍스트가 `running`이었다.
4. `WebSocket.prototype`을 전역으로 감싸 **Next dev HMR 소켓까지 센다** — `sent.other = 1`의 정체가
   `ws://localhost:3000/_next/hmr?...`였다. URL 스코프가 없어 `other`·`unparsed`는 앱 신호가 아니다.
5. `sentAudioBytes`가 목적을 달성하지 못한다(무음·유음 모두 199,728).
6. `config.silentMic`이 기록하는 어떤 계수도 바꾸지 못한다 — 대조 수단으로 무력하다.

**`browser_leg.md` (팀리드 소유)** — 8건. 요지: A1-7의 `end_session` 대조가 스텁에서 성립 불가 ·
§10의 "audio 0 + end_session 0 = 후킹 고장" 규칙이 **오진**을 낸다(후킹은 정상이고 원인은 세션 길이) ·
§11-4 후보 ②는 "0을 못 낸다"가 아니라 **구조적으로 0이 될 수 없다** · A1-4 기대값 3과 그 대조 ②가
이 구성에서 **측정 불가** · **§8-② teardown이 파괴적이고 멱등이 아니다**(§5) ·
§11 "1회차에서 닫힌 것"이 이 경로에 적용되지 않는다(계측이 `getUserMedia`를 교체하므로 **권한
대화상자가 아예 뜨지 않는다** — 두 회차 모두 `dialog::accept` 없이 세션이 열렸다) ·
§2 P5가 지금 실패한다(백엔드보다 새로운 소스 3건).

## 5. 팀리드가 직접 확인한 것 / 못한 것

**직접 확인 (CONFIRMED)**

| 주장 | 확인 방법 | 결과 |
|---|---|---|
| 무음 게이트가 없다 | `lib/audio.ts`의 워클렛 `process()`를 읽었다 | ✅ `if (!channel) return true`는 입력 부재만 걸른다. 진폭과 무관하게 512샘플마다 `postMessage` |
| teardown이 캡틴 데이터를 덮었다 | 앱과 같은 접속 문자열로 쿼리 | ✅ `pronunciation_an_as_a` = `2 / 2026-09-03 13:51:26.680389+00` — **복원됨**, drift 0 |
| 그 파괴의 **근본 원인** | `frequency` writer 전수 grep + 컬럼 대 행 수 대조 | ✅ writer가 **둘**(`analysis.py` occurrence · `pronunciation.py` attempts). 그 패턴은 컬럼 2인데 occurrence **0**, 나머지 6개는 정확히 일치 |
| 보존 대상 2행 | 쿼리 | ✅ `session_plans` 1 · `learner_notes` 1 (baseline·회차후·teardown후 3시점 모두) |
| P5가 지금 실패한다 | 고친 P5를 직접 실행 | ✅ 실패. **단 사유가 하나 더 있다**(아래) |

**⚠️ 팀리드가 잘못 판단했다가 정정한 것 1건.** DB 수치를 **사후에** 조회해 "어긋난다"고 판단했다 —
`learning_sessions` 7행·`utterances` 92로 변화가 없었고 23ms 세션이 어디에도 없었다. **teardown이
걷어간 값이라 사후에는 볼 수 없는 것이었고 에이전트의 3열 기록(baseline 7 → 회차 후 9 → teardown 후
7)이 옳았다.** → **규약**: 하네스 회차는 **baseline / 회차 후 / teardown 후 3열**을 반드시 남긴다.
그것이 없으면 사후 대조가 원리적으로 불가능하다.

**팀리드가 확인하지 못한 것** — 브라우저 관측 전부: 반환값 · throw · 프로토타입 소유자 ·
프레임 계수 · 146프레임/199,728바이트 · 23.001ms · 타이밍 추적. 재현에는 브라우저가 필요하고
그 자리가 이 에이전트의 존재 이유다. **`PASS`로 확정하지 않고 이 기록에 출처를 남긴다.**

**팀리드가 추가로 찾은 것 (에이전트가 보고하지 않았다)**: P5는 `/tmp/omy-backend.log`의 생성 시각을
쓰는데 **그 로그가 지금 도는 백엔드의 것이 아니었다** — 로그 pid **15648**(종료됨) 대 실행 pid
**41641**. 즉 **다른 프로세스의 기동 시각과 소스를 비교**하고 있었다. ⚠️ 고치는 과정에서 팀리드가
**P8과 글자 그대로 같은 거짓 양성**을 밟았다: 명령줄을 스캔했더니 `"--port 8002"`를 담은 **검사
스크립트 자신의 셸**이 잡혀 "백엔드 2개"가 나왔다 → `lsof`로 듣는 pid를 찾는 형태로 고쳤다.

---

_기록: 2026-09-06. §1~4는 에이전트 보고, §5는 팀리드의 독립 확인이다. 결함은 이 회차 이후_
_`browser_leg.md`(§8-②·③ · P5)와 `docs/ops/pitfalls.md`(H-AB·H-AC)에 반영했고, `instrument.js`_
_결함 6건은 후속이 소유한다._
