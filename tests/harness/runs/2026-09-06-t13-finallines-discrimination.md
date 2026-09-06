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

## 10. 사후 추가 — 독립 리뷰 판정과 그것이 정정한 것 (2026-09-06, 같은 날)

⚠️ **§1~9의 관측은 고치지 않았다.** 아래는 별도 컨텍스트의 critic이 반증을 시도한 결과이고,
**틀린 것은 관측이 아니라 §1 표의 표현 하나**다. 조용히 덮지 않기 위해 절을 덧붙인다.

판정: **C1 `PASS`(후반절 하향) · C2 `CHALLENGE`(사실은 맞고 표현이 과하다) · C3 `PASS` ·
C4 `CHALLENGE` · C5 `PASS`(흠 2건)**.

### ⛔ 정정 1 — §1 표의 "반증한다"는 과하다. 본문 §5의 눈금이 맞다

세 출처가 같은 주장을 하지 않는다. 계측 docstring(`instrument.js:141~146`)이 말하는 것은
*"동기 스냅샷도 rAF도 **회차 운에 걸린다**"*이고 **바로 다음 문장이 "T5a는 여유가 9.7초라 동기가
통했다"**다 — 동기 성공 사례를 이미 품은 서술이다. **그리고 이 회차의 레그 1b(동기 `[]`)는 그 주장을
반증한 것이 아니라 확증했다.** 조건 없는 일반문은 **`browser_leg.md:232`(§5 A1-5)의
*"동기 스냅샷은 React commit 전이라 `[]`가 되고"* 하나뿐**이므로 반증 대상은 거기로 한정된다.
→ **정확한 표현: "실제 서버 경로에서는 성립하지 않았다"**(§5 본문이 이미 그렇게 적었다).

### 정정 2 — "적립이 살아남는다"의 일반화는 `LIKELY`다 (n=1이고 기제를 안 적었다)

살아남은 기제: `goToResults`(`page.tsx:92~98`)가 상태를 건드리지 않고 `router.push`만 하며, App
Router의 내비게이션이 transition + RSC 왕복이라 **urgent 커밋이 먼저 난다**(URL 전환 t=51.6 대
적립 t≈14가 그 증거다). **언마운트가 같은 커밋에 합쳐지는 구성이 생기면 `snapshots`는 `count:2`를
영영 못 본다.** 관측은 `CONFIRMED`, 일반화는 `LIKELY`.

### 정정 3 — H-AF의 대응 첫 판이 거짓 PASS로 들어갔다. `pitfalls.md`에서 고쳤다

*"최대치 지점 전부를 후보로 두고 하나라도 일치하는지"*로 고치면 **`page.tsx:123~124`의 I-8 병합이
개수를 바꾸지 않고 텍스트만 바꾸므로**, 병합이 망가져 뒤쪽이 오염돼도 앞쪽의 올바른 최대치 하나로
통과한다 — docstring `:150~153`이 금지한 **골라내기를 최대치 부분집합 안에서 되살린다.**
**뿌리는 `find`가 아니라 선별이 partial을 계수에 넣는 것이고 `find`는 방아쇠다.**
덤: 이 함수의 "합성 5시나리오 판별력 실측"은 스냅샷 배열을 손으로 넣은 것이라 **partial 오염을
원리적으로 발견할 수 없었다** — 판정 함수의 합성 테스트는 **데이터 생성 경로**의 결함에 눈이 멀다.

### C4 — critic이 지적한 반례는 실재한다. 다만 A/B 통제는 이미 이 회차 안에 있었다

**반례**: `t5a-injection-spike.md:75`가 클릭 → `active` **6 ms**를 적고 `:58`이 그 시점 화면으로
`setState("active")` 도달을 확인한다. 전 과정을 한 `eval`에 넣었으니 그 클릭은 in-page 합성이고,
그러면 T5a는 **합성 클릭으로 `resume()`을 통과했다** — H-AE를 문자 그대로 적용하면 실패해야 했다.
§3이 T5a와 대조한 곳은 `addModule` 2 ms(**판별력 없는 지표**) 한 곳뿐이고 6 ms는 §3·§9에 없다.
**지적이 옳다.**

**그러나 기제 쪽은 critic이 credit한 것보다 강하다 — 같은 문서 안의 A/B가 있다.**
프로브 A(`005-eval`)와 프로브 B(`007-eval`)는 **같은 문서**이고 그 사이에 있던 변화는
`006-click`(CDP, `h1`) **하나뿐**이다: `resume()` TIMEOUT/`suspended` → **RESOLVED 0 ms/`running`**.
같은 Chrome(pid 22762 · 포트 9222 · 프로필 `superpowers-chrome`) · 같은 플래그 · 2초 간격.
→ critic이 배제하지 못했다고 한 대안("인스턴스·프로필·기동 플래그가 달랐다")은 **이 쌍을 설명할 수
없다.** 액션 순서도 아티팩트가 증명한다(아래).

**T5a 쪽은 확인 불가다 — 아티팩트가 없다.** T5a §9가 지목한
`~/Library/Caches/superpowers/browser/2026-09-05/session-1788623621742/`는 **존재하지 않고**, 그날의
유일한 디렉터리(`session-1788595762448`)는 **비어 있다**(직접 `ls`). 즉 T5a의 6 ms가 어떤 클릭이었는지
**원리적으로 확인할 수 없다.** 가장 단순한 설명(**LIKELY, 미확정**): T5a의 ERROR 회차 `045`~`047`이
CDP 클릭·`dialog` 액션을 썼고 그 뒤 리로드가 없었다면 **sticky activation이 문서 수명 동안 유지**되어
합성 클릭만으로 통했다. 리로드는 sticky activation을 초기화한다 — 그래서 **새 문서마다 CDP 클릭을
다시 하라**는 H-AE의 지시 자체는 두 관측과 모두 정합한다.

⚠️ **결론: H-AE의 기제는 `CONFIRMED`(문서 내 A/B), T5a 성공의 원인 규명은 `UNRESOLVED`.**
H-AE는 틀려도 증상이 나지 않는 절차라 오류가 숨는다 — 그 위험을 여기 적어 둔다.

### critic이 지적한 누락 — 브라우저 세션 디렉터리 (여기 채운다)

이 회차는 **`~/Library/Caches/superpowers/browser/2026-09-06/session-1788669540950/`**(파일 64개)를
썼다. 액션 순서가 A/B를 문서로 증명한다:
`001-navigate → 002-eval(설치) → 003-eval(합성클릭)` = **CDP 클릭 없음 → 실패** ·
`004-navigate → 005-eval(프로브A) → **006-click** → 007-eval(프로브B) → 008-eval(설치) → 009-eval` ·
`010-navigate → **011-click** → 012·013-eval` · `014-navigate → **015-click** → 016-eval`.
→ **한 브라우저 세션 안에서 CDP 클릭 없는 1회는 실패, 있는 3회는 성공.**
⚠️ **Chrome 기동 플래그는 기록하지 못했다**(`browser_mode`가 headless·포트·프로필만 준다).

### 이 회차가 뽑지 않았던 결론 — A1-5의 정본 조합 (critic 제안, 채택)

실제 서버 경로에서 `finalLinesAtTerminal`이 신뢰 가능한 것은 우연이 아니다: WebSocket `message`는
프레임마다 **별개 task**로 디스패치되고 React 18은 task 경계에서 flush하므로 **커밋 개입이 구조적**이다.
그리고 같은 tick은 **주입만** 만들며 주입 시나리오(C2·C5)는 `finalLines`를 쓰지 않는다.
→ **A1-5의 정본은 `finalLinesAtTerminal`(내용 등호) + `snapshots`의 `max ≤ 기대`(초과 검출) 조합**이
지금 데이터가 가리키는 방향이다. **이 회차는 강등된 수단이 멀쩡하고 승격된 수단이 깨졌음을 동시에
보였는데 §1~9는 앞쪽만 적었다.** AC #14가 이 방향을 소유한다.

### 범위 밖 발견 — `instrument.js:264`의 NUL 2개 (팀리드가 재현)

byte **15764·15784**, 둘 다 264줄, 내용은 `last.texts.join("\x00") === texts.join("\x00")`.
**동작은 무해하다**(NUL 구분자가 공백보다 안전하다). 해로운 것은 도구다 — 이 셸의 `grep`은
shell-snapshot 함수 래퍼이고 `ugrep -I`를 붙여 **그 파일을 통째로 건너뛴다**: 셸 `grep -c const`
**출력 없음·rc=1** 대 `command grep -c const` **37**. ⚠️ **이 회차에서 실제로 사고를 냈다** — 팀리드가
그 파일의 최상위 키를 grep해 빈 출력을 받고 **"내 정규식 탓"으로 넘겼다**(브라우저의 `keyState`로
대체 확인한 것이 우연히 맞는 선택이었다). 그리고 **`Read`는 NUL을 공백처럼 보여주므로** 264줄을
`join(" ")`로 오독했다. 함정 **H-AG** · 수정은 **AC #16**이 소유한다.

### critic이 확인하지 못한 것 (읽기 전용 제약 준수)

DB 3열 · teardown 결과 코드 · 보존 2행 무손상 · 음성 대조 4/4 FAIL과 `snapshots` 배열 · P5 실측값.
**대신 인용 정확도를 표본 전건 대조해 일치**를 확인했다(`page.tsx`·`audio.ts:143`·`instrument.js`
`:285`·`:286`·`:415`·`config.py:66`·계측 sha256·23917 B).

---

_기록: 2026-09-06. `TASK-31` AC #13의 산출물이다. **결함 A·B와 §4-4 낡음은 이 회차가 새로 찾은_
_것이고 이 태스크에서 고치지 않았다** — 원장에 별건으로 등재한다(방식이 지시된 항목을 산출물로_
_대체하지 않기 위해서다). §10은 같은 날 독립 리뷰의 판정을 덧붙인 것이고 §1~9의 관측은 고치지_
_않았다 — 바뀐 것은 §1 표의 「반증한다」라는 표현과 두 결론의 확신도다._
