# T13 판별 실험 — `finalLines` 동기 스냅샷 대 MutationObserver 적립 (`TASK-31` AC #13)

> 2026-09-06 · 실행 주체 **팀리드 본인**(에이전트에 위임하지 않았다 — 위임한 T5a가 문제 조건을
> 구조적으로 회피한 것이 이 항목이 살아남은 이유다) · 절차 정본 `tests/harness/browser_leg.md` ·
> 회차 `c9745e3b-cfb8-4982-bc2d-cc827ead6b41` · `WINDOW_START` `2026-09-06 04:45:24.928818+00`
>
> 계측 sha256 **`0be00c20a99c4fa998b8740ac05f90cf98ce0c132d87fea5aa39ca7afa19658f`** (23917 바이트).
> 임시 CORS 서버(`127.0.0.1:54662`)로 파일을 그대로 받아 페이지 안에서 sha256을 계산해 디스크값과
> 대조했다 — **전사 드리프트가 구조적으로 0이다.** 서버는 회차 후 정리했다(리스너 없음 확인).
>
> ⚠️ **이 기록은 사후 편집하지 않는다.**

---

## 1. 판정 — **AC #13 `PASS`(실험 수행). 그 실험이 결함 2건을 새로 찾았다**

| 물음 | 판정 | 근거 요지 |
|---|---|---|
| `settle` 없이 같은 tick에 연달아 주입하면 줄을 잃는가 | **잃는다 (동기 스냅샷)** | L1b: `final`×2 + 종단을 **1.1 ms 안에, 사이에 `await` 0개**로 주입 → 동기 스냅샷 **4곳 전부 `[]`** |
| 그 조건에서 MutationObserver 적립이 살아남는가 | **살아남는다** | L1b: 주입 후 ≈3 ms에 `count:2` + `texts` 정확 일치 적립. `judgeFinalLines` `pass:true`, 음성 대조 3/3 FAIL |
| 실제 `session_ended` 경로에서도 동기 스냅샷이 `[]`인가 | ⛔ **아니다 — 이 관측이 T2의 기제 서술을 반증한다** | L2·L2r2 **2회 모두** `finalLinesAtTerminal`이 픽스처 6줄과 **정확히 일치**(`finalLinesAtTerminalMatchesExpected: true`) |
| 재설계가 "회차 운"을 없앴는가 | ⛔ **아니다. 2회차가 거짓 FAIL을 냈다** | L2r2: `judge.pass:false` · `textsMatchAtMax:false`. 아래 §5 |

**두 조건이 서로 다른 답을 낸다는 것이 이 회차의 핵심이다.** 하나만 봤으면 어느 쪽이든 틀린 결론을 냈다.

## 2. 프리플라이트 — P1~P9 전건 직접 실행, 전건 통과

`P1 {"status":"ok"}`(`version` 없음) · `P2 NEXT_PUBLIC_API_BASE=http://localhost:8002` ·
`P3 app/frontend/.gitignore:34:.env*` · `P4 postgresql@17 started` ·
`P5 pid 30860 · 기동 01:08:30 전 · 소스 32건 → 통과` (레그 2 앞에서 재기동 후 재실행:
`pid 38202 · 기동 00:39 전 · 소스 32건 → 통과`) · `P6 200` · `P7 2` · `P8 pytest 0건` ·
`P9 /opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish`.

**§8-0 drift 가드**: baseline 표 실재 · drift **0** · baseline **7**행. drift 0이라 **재스냅샷하지
않았다**(T5a가 세운 선례 — 결과가 같고 검증된 사본을 하나 더 지킨다). 추적된 파일 사본
`tests/harness/runs/2026-09-06-pattern-baseline.tsv`가 DB와 **7건 전건 일치**함을 직접 대조했다
(`pattern_key`·`frequency`·`last_seen_at`).

## 3. ⛔ 레그 1 = **ERROR**. §6-0 대조가 잡아냈다 — 그리고 그 원인이 절차의 공백이었다

첫 시도는 `active`에 도달하지 못했다: `gotActive:false` · `waitingText:false` · 접두 `<p>` **0**.
**그 0을 "주입 전 0"으로 읽으면 거짓 통과다** — 컨테이너가 마운트된 적이 없어 주입한 `final`이
그릴 자리가 없었고, 그러면 "`snapshots`가 0에 머물렀다"는 적립에 대해 **아무것도 말하지 않는다.**
T5a D-7이 §6-0을 `active` 도달 후로 옮긴 것이 정확히 이 실패를 막았다.

**근본 원인 — 격리 프로브로 확정했다(추측 아님). 양쪽을 다 봤으므로 판별력 미확인이 아니다:**

| 조건 | `navigator.userActivation` | `new AudioContext({sampleRate:16000})` | `ctx.resume()` |
|---|---|---|---|
| CDP 클릭 **없음** | `isActive:false` · `hasBeenActive:` **false** | `suspended` | **2500 ms 안에 resolve 안 됨** (`resumeMs` 2506, state 여전히 `suspended`) |
| 무해한 CDP 클릭(`h1`) **뒤** | `isActive:false` · `hasBeenActive:` **true** | **`running`** | **RESOLVED 0 ms** |

`addModule`은 두 조건 모두 **2 ms**(T5a 값과 일치) → 병목이 아니다.
합성 클릭(`element.click()`)은 핸들러 **안에서 재도** `isActive:false`·`hasBeenActive:false`였다 —
**JS 합성 클릭은 user activation을 만들지 않는다.**

→ `VoiceIo.start`가 **`lib/audio.ts:143 await context.resume()`에서 매달린다.** 그 줄의 주석은
*"사용자 제스처 뒤에 불리므로 여기서 resume이 통한다"*고 적는데, **하네스의 합성 클릭에는 그 전제가
성립하지 않는다.** `setState("active")`는 `VoiceIo.start` **뒤**(`page.tsx:218`)라 컨테이너가 영원히
안 뜬다. 화면은 `connecting`에 머물고 `failed`도 아니다 — 그래서 **오진하기 쉽다.**

⚠️ **기제는 "제스처 안에서 생성"이 아니라 sticky activation이다.** `isActive`가 이미 `false`로
만료된 뒤에도 `hasBeenActive:true`면 `resume()`이 통했다. `browser_leg.md` §11-3의
*"제스처(클릭) 안에서 생성하면 `running`"*은 방향은 맞지만 기제 서술이 부정확하다.

**그래서 절차가 이렇게 된다 — §6의 「전 과정을 한 `eval`에」와 충돌하지 않는다:**
① `navigate`(새 문서 — `__omy` 중복 방어를 통과한다) → ② **무해한 요소를 CDP로 한 번 클릭**
(sticky activation을 얻는다. 세션을 열지 않는 요소를 고른다 — 이 회차는 `h1`) → ③ 계측 설치 →
④ **클릭·주입·판독을 한 `eval`에.** 창은 ④에서야 열리므로 라운드트립이 창을 먹지 않는다.

**계측이 이 차이를 스스로 증언했다**: 활성화 없이 설치한 판은 `meta.audioContextState:"suspended"`,
활성화 뒤에 설치한 판은 **`"running"`**이었다(같은 파일·같은 해시).

## 4. 레그 1b — 같은 tick 주입. **동기는 잃고 적립은 살아남는다**

`hasBeenActive:true` 문서에서 재실행. 클릭 **0.5 ms** → `session_started` **10.5 ms** →
`active` **10.8 ms**(`waitingText:true`이고 접두 `<p>` **0** → **§6-0 대조가 이번엔 공허하지 않다**).

**주입 블록에 `await`가 하나도 없다. 3프레임 span 1.1 ms.**

| 관측 지점 | 값 |
|---|---|
| `final`(agent) 직후 동기 | `[]` |
| `final`(user) 직후 동기 | `[]` |
| **종단 프레임 처리 직전** 동기 (래퍼가 찍는 자리) | **`[]`** |
| 종단 프레임 직후 동기 | `[]` |
| 주입 직후 `snapshots.length` | **1** (적립이 아직 안 돌았다) |
| 주입 후 ≈3 ms (t=14) | `live` = 두 줄 정확 · `snapshots.length` **2** |
| URL 전환 | t=34.1 까지 `/`, t=51.6 에 `/results/35b82305-…` |
| `snapshots` | `count:0` → **`count:2`(texts 정확)** → `count:0` |
| `judgeFinalLines` | **`pass:true`** (maxCount 2 · textsMatchAtMax · nonDecreasing) |
| 음성 대조 | 문구변형 `false` · 순서뒤바뀜 `false` · 초과 `false` — **3/3 FAIL** |
| `recvUnchangedByInject` | `true` · `injected` 0→3 |

**증거(§10-1)** — 판정 대상 요소의 `outerHTML`을 반환값에 실었다:
```html
<p style="color: var(--foreground); margin: 0.4rem 0px;"><strong>질문: </strong>SAMETICK_Q_ALPHA</p>
<p style="color: var(--foreground); margin: 0.4rem 0px;"><strong>답변: </strong>SAMETICK_A_BETA</p>
```

⚠️ **`inject()`는 `finalLinesAtTerminal`을 채우지 않는다 — 구조적이다.** `omy.inject`가
`appHandler`를 **직접** 부르므로 계수와 동기 스냅샷을 담당하는 **래퍼를 우회한다**
(`instrument.js:415`). 그래서 위 「종단 직전」 값은 **내가 같은 자리를 흉내낸 것**이고
계측 필드 자체는 이 레그에서 `null`이었다. **주입 레그만으로는 그 필드를 평가할 수 없다** —
레그 2가 필요한 이유가 이것이다.

⚠️ **같은 tick 조건은 하네스가 만든 것이고 서버가 만드는 것이 아니다**(레그 2가 그것을 보였다).
즉 이 결함은 **주입으로 A1-5를 재는 방식의 결함**이고 앱의 결함이 아니다.

## 5. 레그 2 — 실제 `session_ended` 경로 (`VOICE_ADAPTER=stub`). **2회차가 갈렸다**

백엔드를 `stub`으로 재기동했다(pid 30860 → **38202**, `WORKER_ENABLED=false` 유지, 로그
`/tmp/omy-backend.log`, P5 재통과). 주입 0건 — 전부 서버가 보낸 프레임이다(`injected: 0`).

**두 회차 공통**: `recv` = `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1 ·
session_failed 0` · `started.count` **3** == `recv.audio` **3** · `sent.foreign` 1(HMR 소켓) ·
`finalLinesAtTerminal`이 픽스처 6줄과 **정확히 일치**.

| | 1회차 | 2회차 |
|---|---|---|
| 클릭 → `session_started` | 11.2 ms | 7.8 ms |
| `session_ended` 도착 | 28.5 ms | 21.7 ms |
| URL 전환 | 50.7 ms | 45.9 ms |
| `snapshots` 건수 | **12** | **13** |
| `snapshotCounts` | `0,1,2,2,2,3,4,4,4,5,6,0` | **`0,1,2,2,2,3,4,4,4,5,6,6,0`** |
| `judgeFinalLines` | **`pass:true`** | ⛔ **`pass:false`** (`textsMatchAtMax:false`) |
| 음성 대조 4건 | 4/4 FAIL | 4/4 FAIL |
| `sent.audio` | 1 (`bytes` 1368 · `nonZeroFrames` **1**) | **0** (`socketUrls`에 앱 소켓이 없다) |

### ⛔ 결함 A — `judgeFinalLines`의 `atMax`가 **첫** 최대치를 고른다. 거짓 FAIL을 낸다

2회차의 최대치 **6이 두 개**다. `instrument.js:286`이
`omy.snapshots.find((s) => s.count === maxCount)` — **`find`는 첫 항목이다.** 그 첫 번째가
과도 상태였다:

```
["질문: What do you usually do after work?", "답변: I usually go to gym after work.",
 "질문: What do you usually do on weekends?", "답변: I usually go to office by subway.",
 "질문: What do you need to do tonight?", "답변: I need to finish"]        ← 마지막이 partial
```

`답변: I need to finish`는 **partial**이다. `stub.py:_partial_prefixes`를 직접 따라가면
`"I need to finish my homework tonight."`은 7단어이고 `cuts = {7//3=2, 14//3=4}` →
`["I need", "I need to finish"]`가 나온다. 즉 **`count 6` = 확정 5 + partial 1**이다.

원인은 **선별이 확정 줄과 partial 줄을 구별하지 못하는 것**이다 — `LINE_PREFIXES`가 둘을 함께
잡는다(§6이 그렇게 설계했다: *"그 접두를 가진 `<p>`는 확정 줄과 partial 줄 둘뿐"*). 그래서
`count`는 "확정 줄 수"가 아니라 "확정 + partial 수"다.

⚠️ **재설계가 없앤다고 적은 "회차 운"이 없어지지 않았다 — 자리만 옮겼다.**
「언제 찍을까」의 운 → 「어느 최대치를 고를까」의 운. 1회차는 최대치 스냅샷이 1개라 통과했고
2회차는 2개라 실패했다. **같은 코드·같은 픽스처·같은 어댑터인데 판정이 뒤집혔다.**

**판별력은 살아 있다** — 음성 대조 4건(문구변형·순서뒤바뀜·초과·부족)이 양 회차 모두 FAIL을 냈다.
이것은 **거짓 FAIL**이고 거짓 PASS가 아니다. 그래서 위험의 방향은 안전하지만, **A1-5를 이 함수로
판정하면 정상 구현이 무작위로 FAIL한다.**

### ⛔ 결함 B — `nonDecreasing`이 `|| c === 0`으로 언마운트를 통과시킨다

`instrument.js:285`가 `counts.every((c,i) => i===0 || c >= counts[i-1] || c === 0)`이다.
마지막 항목이 `count:0`(언마운트)인데 `nonDecreasing`이 양 회차 모두 `true`였다 — **0으로의 낙하를
예외로 허용**하기 때문이다. 언마운트를 넘기려는 의도는 읽히지만, **그 예외가 "중간에 0으로
떨어졌다가 다시 오르는" 진짜 이상도 함께 통과시킨다.** 이 회차는 그 형태를 관측하지 못했으므로
**결함으로 단정하지 않고 미확인 위험으로 남긴다.**

### 관측 — T2의 기제 서술을 반증한다

T2와 계측 docstring(`instrument.js:141~146`)과 `browser_leg.md` §5 A1-5는
*"동기는 React commit 전이라 `[]`가 되고 rAF는 `router.push` 후라 `[]`가 된다"*고 적는다.
**실제 서버 경로에서는 동기 스냅샷이 2회 모두 정상이었다.** 기제는 이렇다: 실제 WebSocket
프레임은 **각자 자기 task로** 도착하므로 React가 그 사이에 commit한다(적립이 partial이 자라는
것까지 11~12건 남겼다 — 중간 commit의 직접 증거다). 같은 tick에 몰리는 것은 **주입만 하는 일**이다.

→ **T2의 `[]`가 "commit 이전 도착"이었다는 서술은 이 회차가 지지하지 않는다.**
대안 가설(**LIKELY, 미확정**): T2도 레그 1과 같은 실패, 즉 **컨테이너가 마운트된 적이 없어서**
`[]`였다. T2 회차는 `active` 도달을 기록하지 않았고 같은 날 같은 하네스로 같은 증상을 재현했으므로
이쪽이 더 단순한 설명이다. **T2 기록을 사후 편집하지 않으므로 여기에만 적는다.**

## 6. 덤으로 닫힌 것 — `stub`이라야 재는 값들

- **A1-4 계수·태깅이 측정됐다**(§11-3의 남은 몫): `started.count` **3** == `recv.audio` **3**,
  2회 일치. `started.calls`의 `afterRecvAudio`가 **1·2·3**으로 프레임마다 하나씩 붙는다 →
  "어느 프레임이 통과했는지"가 추론이 아니라 기록이다. `when`은 1회차 `0.032·0.232·0.432`,
  2회차 `0·0.2·0.4`(큐가 비어 있어 즉시 재생).
- **A1-7의 유음 쪽 표본이 생겼다**: 1회차 `sent.audio 1` · `sentAudioBytes 1368` ·
  `sentAudioNonZeroFrames` **1**. ⚠️ **무음 대조(`config.silentMic=true`)는 돌리지 않았다 →
  A1-7은 여전히 「판별력 미확인」이고 `PASS`로 올리지 않는다.**
- **§10의 3갈래 판별이 실제로 작동했다**: 2회차는 `sent.audio 0`이고 `socketUrls`에 앱 소켓이
  **없었다**. 그런데 `sent.foreign 1`(HMR)이라 후킹은 살아 있다 → 문서의 2번 갈래
  (**세션이 너무 짧다 → BLOCKED, 화면 결함 아님**)가 정확히 맞았다. 세션 전체가 **22 ms**다.

## 7. ⛔ `browser_leg.md` §4-4가 낡았다 — 계약 키가 코드와 어긋난다

§4-4(줄 169)는 계약 키로 **`finalLines`**를 요구하고 *"하나라도 빠져 있으면 PASS를 낼 수 없다"*고
적는다. **재설계된 계측에 그 키가 없다** — `finalLinesAtTerminal` + `snapshots`로 갈렸다.
브라우저에서 직접 확인: `keyState.finalLines = "ABSENT"`(2회 관측). §5의 A1-5(줄 232)는
`judgeFinalLines` 기반으로 갱신됐는데 **§4-4는 따라가지 않았다.**
→ 문자 그대로 따르면 이 회차는 §4에서 ERROR로 끝나야 한다. **문서 한쪽이 조용히 낡은 형태다.**

## 8. DB 3열 (§10) — 대상 표 6개

| 표 | baseline | 회차 후 | teardown 후 |
|---|---|---|---|
| `learning_sessions` | 7 | 11 | **7** |
| `analysis_jobs` | 34 | 44 | **34** |
| `utterances` | 92 | 104 | **92** |
| `error_patterns` | 7 | 7 | **7** |
| `session_plans` | **1** | **1** | **1** |
| `learner_notes` | **1** | **1** | **1** |

중간값(주입 레그 2건만 끝난 시점): `9 · 36 · 92 · 7 · 1 · 1` — `stub_unresponsive`는 전사문을
만들지 않으므로 `utterances`가 **92 불변**인 것이 그 어댑터의 서명이다.

**teardown**: ①-a `INSERT 0 4` → ① `DELETE 4` → ② **`UPDATE 0`**(복원식이므로 재계산 SQL을 한 번도
던지지 않았다) → ③ `DELETE 0` → ④ 대조 3건 전건 통과(`error_patterns` 7 = baseline 7 · drift **0** ·
남은 회차 세션 **0**). 캡틴 패턴 `pronunciation_an_as_a`는 `2 / 2026-09-03 13:51:26.680389+00`으로
**무손상**이다(teardown 후 직접 조회).

**보존 대상 (b)를 적용하지 않은 이유를 명시한다**: §8은 "실패한 시나리오의 세션"을 남기라고 한다.
2회차의 FAIL은 **판정 함수의 결함**이고 그 증거는 `eval` 반환값의 `snapshots` 배열이다 — DB 행은
재현에 기여하지 않는다. 그리고 재현 비용이 **0**이다(`stub` + `WORKER_ENABLED=false` → 실물 모델
호출 0회). 그래서 4건 전부 지웠다. **§9의 보존 `session_id` 5개는 아직 비어 있다(T4 몫).**

**⑤ 프로세스**: 백엔드를 이 회차가 **바꿨다** — `stub_unresponsive`(pid 30860) →
**`stub`(pid 38202)**. `.env`에 `VOICE_ADAPTER` 키가 없고 앱 기본값이 `"stub"`(`config.py:66`)이므로
지금 상태가 §2 baseline과 **일치**한다. `WORKER_ENABLED=false`만 비용 가드로 의도적으로 유지했다
(기본값은 `True`). `.env`는 열지도 고치지도 않았다(`grep`으로 두 키의 부재만 확인).

## 9. 팀리드가 직접 확인한 것 / 못 한 것

**직접 확인**: 계측 sha256·바이트(디스크 `shasum` 대 페이지 내 `crypto.subtle`, 3회 일치) ·
`page.tsx:92-98`·`:109-131`·`:149-160`·`:218`을 열어 읽음 · `lib/audio.ts:129·138·143` ·
`instrument.js:285-290`(`find`와 `|| c === 0`) · `stub.py:_partial_prefixes`를 손으로 따라가
`"I need to finish"`가 partial임을 계산 · `fixtures.py:FIXTURE_TURNS` 6문장 · `config.py:66` ·
DB 3열 전부 직접 쿼리 · teardown 결과 코드 5개 · 프리플라이트 9건 · 프로세스 env 2건.

**못 한 것 (통과로 적지 않는다)**:
- **A1-7 무음 대조** — `config.silentMic=true` 회차를 돌리지 않았다. **판별력 미확인.**
- **T2의 `[]` 기제** — 대안 가설이 더 단순하지만 T2 조건을 재현하지 않았다. **미확정(LIKELY).**
- **결함 B(`|| c === 0`)** — 그 예외가 실제 이상을 통과시키는 회차를 관측하지 못했다. **미확인 위험.**
- **자동 저장 `.png`/`.html`** — 창 밖(결과 화면) 상태만 담는다. 창 안 증거는 §4·§5의 반환값이다
  (§10-1대로 `outerHTML`을 반환값에 실었다).
- **`-console.txt`** — 여전히 빈 스텁이다. 콘솔 로깅을 레그 1 **뒤에** 켰으므로 그 회차의 콘솔은
  없다. 있다고 적지 않는다.

---

_기록: 2026-09-06. `TASK-31` AC #13의 산출물이다. **결함 A·B와 §4-4 낡음은 이 회차가 새로 찾은_
_것이고 이 태스크에서 고치지 않았다** — 원장에 별건으로 등재한다(방식이 지시된 항목을 산출물로_
_대체하지 않기 위해서다)._
