# AC #14 재확인 회차 — `judgeFinalLines` 재설계의 red→green (`TASK-31`)

> 2026-09-06 · 실행 주체 **팀리드 본인** · 절차 정본 `tests/harness/browser_leg.md` ·
> 회차 **`700164a3-8657-4e16-8daa-617e6f12f734`** · `WINDOW_START` `2026-09-06 08:44:49.578865+00`
>
> 계측 sha256 **`face761b53f6b3e9e9a026b0b678e54c1ad70b99418f1aa05147890670cfb446`** (27735 바이트).
> 임시 CORS 서버(`127.0.0.1:54663`)로 파일을 그대로 받아 페이지 안에서 sha256을 계산해 디스크값과
> 대조했다 — **전사 드리프트가 구조적으로 0이다.**
>
> 브라우저 세션 디렉터리 **`~/Library/Caches/superpowers/browser/2026-09-06/session-1788669540950/`**
> (액션 `020`~`027`). 백엔드 pid **38202** · `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false`.
>
> ⚠️ **이 기록은 사후 편집하지 않는다.**

---

## 1. 판정 — **AC #14 `PASS`. 그리고 AC #1이 이것으로 닫힌다**

| 물음 | 판정 |
|---|---|
| 이전 판이 거짓 FAIL을 내던 데이터가 이제 통과하는가 | **통과한다** (합성 + **실물 2회** 모두) |
| 음성 대조가 여전히 FAIL을 내는가 | **낸다** — 합성 7건 · 실물 회차의 런타임 대조 4건, 전부 FAIL |
| 이전 판이 통과시켰던 구멍이 막혔는가 | **막혔다** — 「중간 0 낙하 후 상승」이 이전 `true` → 새 `false` |
| **같은 입력으로 2회 돌려 판정이 같은가** (H-AF의 요구) | **같다** — 실물 회차 A·B 둘 다 `pass: true` |

## 2. 무엇을 고쳤나

내용·순서 판정을 **적립된 최대치 스냅샷**에서 **종단 동기 스냅샷**(`finalLinesAtTerminal`)으로 옮겼다.
적립(`snapshots`)은 **초과 검출과 단조성**만 담당한다. 판정은 4항목 전부 참이어야 PASS다 —
`terminalPresent` · `terminalMatches` · `noExcess` · `nonDecreasing`.

**뿌리**: partial 줄이 확정 줄과 **같은 접두 구조**를 쓴다(`page.tsx:313~317` 대 `:307~311`) →
`count`는 "확정 줄 수"가 아니라 "확정 + partial"이고, 과도 상태가 최대치에 **먼저** 닿으면
`find`가 그것을 고른다. `find`는 방아쇠였고 뿌리는 선별이었다.

**채택하지 않은 두 대안과 이유** — 둘 다 독립 리뷰가 지적했거나 문서가 금지한다:
- **"최대치 전부를 후보로 두고 하나라도 일치"** → **거짓 PASS**가 된다. I-8 병합
  (`page.tsx:123~124`)은 **개수를 바꾸지 않고 텍스트만** 바꾸므로 뒤쪽이 오염돼도 앞쪽의 올바른
  최대치 하나로 통과한다. 계측 docstring이 스스로 금지한 "골라내기"를 부분집합 안에서 되살린다.
- **색으로 확정/partial 가르기** → 둘의 유일한 구조적 차이가 색이고(`--foreground` 대
  `--foreground-muted`) `browser_leg.md` §6이 색을 선별에 쓰는 것을 금지한다.

`nonDecreasing`도 함께 고쳤다: 이전 판의 `|| c === 0`은 **중간의 0까지** 통과시켰다 →
**마지막에 오는 0만** 허용한다(중간의 0은 언마운트·재마운트이므로 이상이다).

## 3. red→green — 합성 9시나리오. **이전 판 로직을 참조 구현으로 나란히 돌렸다**

전건이 기대와 일치했다(`allAgree: true` · `negativesAllFailUnderNew: true`).

| 시나리오 | 이전 판 | 새 판 | 새 판의 사유 |
|---|---|---|---|
| 정상 1회차 실측 계열(`0,1,2,2,2,3,4,4,4,5,6,0`) | pass | **pass** | 무회귀 |
| **정상 2회차 실측 계열**(`…,5,6,6,0` — 첫 6이 과도 상태) | **fail** | **pass** | 거짓 FAIL이 고쳐졌다 |
| 종단 본문 삭제 | fail | fail | `terminalMatches` |
| 종단 순서 뒤바뀜 | fail | fail | `terminalMatches` |
| **종단에 partial 오염** | fail | fail | `terminalMatches` |
| 초과 렌더(최대치 7) | fail | fail | `noExcess` |
| **종단 스냅샷 부재(`null`)** | fail | fail | `terminalPresent` (신규 방어) |
| **중간에 0으로 떨어졌다 다시 오름** | **pass** ⛔ | **fail** | `nonDecreasing` (구멍이 닫혔다) |
| 개수 감소(6→4) | fail | fail | `nonDecreasing` |

## 4. 실물 회차 2건 — 합성이 아니라 살아 있는 데이터에서 갈렸다

| | 회차 A | 회차 B |
|---|---|---|
| `recv` | `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1` | 동일 |
| `started.count` · `afterRecvAudio` | **3** · `[1,2,3]` | **3** · `[1,2,3]` |
| `snapshotCounts` | `0,1,2,2,3,4,4,4,5,6,6,6,0` | `0,1,2,2,2,3,4,4,4,5,6,6,6,0` |
| `finalLinesAtTerminal` | 픽스처 6줄 **정확 일치** | 픽스처 6줄 **정확 일치** |
| **`judge.pass`** | **`true`** | **`true`** |
| `atMaxDiagnostic`의 마지막 줄 | **`답변: I need`** ← partial | **`답변: I need`** ← partial |
| **이전 로직을 같은 데이터에** | (A에서는 재지 않았다) | **`oldJudgeOnThisRound: false`** |
| 음성 대조 4건 | 4/4 FAIL | 4/4 FAIL |
| `injected` | 0 (주입 0건 — 전부 서버 프레임) | 0 |

⚠️ **두 회차 모두 첫 최대치가 partial 과도 상태였다.** 즉 이전 판이라면 **정상 회차 두 건이 다
FAIL**이었다. 회차 B에서 이전 로직을 같은 런타임 데이터에 직접 돌려 **`false`**를 관측했고 같은
데이터에 새 로직은 **`true`**였다 — **red→green이 합성이 아니라 실물에서 증명됐다.**

## 5. ⚠️ 관측 하나 — `stub`에서는 §6-0의 "0개" 대조가 경합한다

회차 B의 `prefixedPAtActive`가 **1**이었다(A는 0). 세션 전체가 20~30 ms라, 폴링이 `학습 종료`를
본 시점에 이미 첫 줄이 그려져 있었다. **§6-0의 "0이 아니면 ERROR"는 §6(C2 주입 절차) 소유이고
그 절차는 `stub_unresponsive`(프레임 0건)에서 돌기 때문에 이 회차와 충돌하지 않는다.**
⚠️ 다만 **그 규칙을 C1(`stub`) 회차에 적용하면 정상 회차를 ERROR로 만든다** — 적용 범위를
혼동하지 말 것. 문서를 고치지는 않았다(§6이 이미 주입 절차로 한정한다).

## 6. DB 3열 (§10) — 대상 표 6개

| 표 | baseline | 회차 후 | teardown 후 |
|---|---|---|---|
| `learning_sessions` | 7 | 9 | **7** |
| `analysis_jobs` | 34 | 42 | **34** |
| `utterances` | 92 | 104 | **92** |
| `error_patterns` | 7 | 7 | **7** |
| `session_plans` | **1** | **1** | **1** |
| `learner_notes` | **1** | **1** | **1** |

**teardown**: ①-a `INSERT 0 2` → ① `DELETE 2` → ② **`UPDATE 0`**(복원식 — 재계산 SQL을 던지지
않았다) → ③ `DELETE 0` → ④ 대조 3건 전건 통과(`error_patterns` 7 = baseline 7 · drift **0** ·
남은 회차 세션 **0**). 캡틴 패턴 `pronunciation_an_as_a` = `2 / 2026-09-03 13:51:26.680389+00`
**무손상**(teardown 후 직접 조회). 회차 시작 전 drift도 **0**이었다.

**⑤ 프로세스**: 이 회차는 백엔드를 바꾸지 않았다 — pid **38202** · `VOICE_ADAPTER=stub` ·
`WORKER_ENABLED=false` · `/health` `{"status":"ok"}`가 회차 전후 동일. `.env`를 열지 않았다.
임시 CORS 서버는 회차 후 정리한다.

## 7. 게이트

`app/backend` cwd에서 **595 passed** · `ruff check` 통과 · `ruff format --check` **32 files** ·
`ty check` 통과. 게이트 밖 기준선 유지 — `ruff check ../../tests ../../scripts` **6 errors** ·
`ruff format --check ../../tests` **4 files**(늘지 않았다). 앱 코드는 건드리지 않았다.

## 8. 팀리드가 직접 확인한 것 / 못 한 것

**직접 확인**: 계측 sha256·바이트(디스크 대 페이지 내 계산, 회차마다 대조) · `page.tsx:307~317`을
열어 확정/partial의 구조적 차이가 **색뿐**임을 확인 · `page.tsx:123~124` I-8 병합 · 합성 9건과
실물 2건의 반환 JSON · DB 3열과 teardown 결과 코드 5개 · 프리플라이트(백엔드 pid·모드·`/health`·
프론트 200) · 게이트 4종과 게이트 밖 기준선 2종.

**못 한 것 (통과로 적지 않는다)**:
- **실물 Nova에서 종단에 partial이 남는 구성** — 픽스처는 턴마다 user final로 끝나 구조적으로
  보장되지만 Nova는 **미확인이다.** 그 경우 `terminalMatches`가 FAIL을 내므로 **거짓 PASS는 아니고
  거짓 FAIL이 될 수 있다.** `browser_leg.md` §5 A1-5에 남은 한계로 적었다.
- **A1-7 무음 대조**(`config.silentMic`) — 이 회차에서도 돌리지 않았다. **판별력 미확인 유지.**
- **T5a의 `active` 6 ms 반례** — 아티팩트가 존재하지 않아 원인 규명 불가. `UNRESOLVED` 유지
  (T13 기록 §10이 소유한다).
- **Chrome 기동 플래그** — `browser_mode`가 headless·포트·프로필만 주므로 기록하지 못했다.

---

## 9. 사후 추가 — 독립 코드리뷰가 `CHANGES REQUESTED`를 냈고 8건을 고쳤다

⚠️ **§1~8의 관측은 고치지 않았다.** 아래는 별도 컨텍스트의 code-reviewer 판정과 그 반영이며,
**리뷰 주장은 형식적으로 수용하지 않고 전건 재현했다**(`node`로 파일에서 함수를 그대로 뽑아 실행).
회차 **`d590d8dc-26f9-4a3e-8287-a1debf7bf383`** · `WINDOW_START` `2026-09-06 09:06:28.032414+00` ·
계측 sha256 **`6dd2a6b3979616e6186be44610a5b07a0eed7c4147ebc6abaae22eed7568712d`**(34392 바이트).

판정: **HIGH 3 · MEDIUM 4 · LOW 1.** `common/code-review.md`의 "Approve: No CRITICAL or HIGH"에
따라 **Approve 불가**였다. → **AC #14·#1의 체크를 되돌린 뒤 고쳤다.**

| # | 지적 | 내가 재현한 값 | 반영 |
|---|---|---|---|
| **H1** | 같은 파일 docstring **4곳**이 새 판정과 정반대를 말한다 | 읽어서 확정 — `:138`("종단 스냅샷은 진단용, 단정은 `snapshots`") · `:141`("`snapshots`가 A1-5 정본") · `:150-153`(**제거한 그 ②를 계약으로 처방**) · `:368-372`(값을 만드는 줄 바로 위에서 "진단용") | 네 블록 전부 재작성. `:150-153`의 옛 3항목 처방을 **삭제**하고 "판정의 정본은 `judgeFinalLines` docstring 하나다"를 박았다 |
| **H2** | `expected=[]`면 **백지 화면이 PASS** | `pass=true`, 4항목 전부 `true` | `need(Array.isArray)` + `need(length>0)` — 이 파일의 컨벤션대로 **이름 있는 오류**로 죽인다 |
| **H3** | "커밋 개입이 **구조적**"이라는 근거가 성립하지 않는다 | 반박 불가 — `stub.py:events()`에 `await asyncio.sleep`이 **0줄**임을 직접 읽었다. React의 flush도 매크로태스크다 | **주장을 「관측 6회·기제 미확정」으로 낮췄다**(코드·`browser_leg.md` 양쪽). **`exactStateSeen` 진단 필드 신설** — 조용한 실패를 보이게 한다 |
| **M1** | `noExcess`가 `===`인데 문서 3곳은 `≤` | `max=5` + 종단 6줄 정확 → **`pass=false`**(거짓 FAIL) | `<=`로 고쳤다. "기대 개수 도달"은 `terminalMatches`가 이미 단정한다 |
| **M2** | `terminalPresent`는 `pass`의 **죽은 조건** | `terminal=null`·비배열 모두 두 플래그가 **함께** false | `pass`에서 뺐다. 독립 조건은 **셋**임을 코드·문서·handoff에 정정 |
| **M3** | "판정 불가"를 "FAIL"로 접는다 | `page.tsx`의 `onClose` 경로는 앱의 **정상 경로**인데 종단 스냅샷이 없다 | **`judgeable` 필드 신설** — `false`면 `FAIL`이 아니라 **`측정 불가`**로 보고한다 |
| **M4** | 「한 페이지 1세션」 전제가 미문서화 + 종단 스냅샷에 first-wins 가드 없음 | 두 세션 계열 → `nonDecreasing=false` | 래퍼에 **first-wins 가드**(`=== null`) + 절차에 "세션마다 `navigate`" 명시 |
| **L1** | `expected=null`이 익명 `TypeError`, **문자열이 `pass=true`** | `'abcdef'` → **`pass=true`**(문자열 인덱싱이 먹었다) | H2와 같은 가드로 함께 닫혔다 |

**리뷰가 옳게 기각한 것**(내가 채택하지 않은 대안): 없다 — **8건 전부 수용했다.**
반박한 것도 없다. ⚠️ 다만 **H3을 근거로 이전 판을 되살리지 않았다** — 이전 판이 거짓 FAIL을 낸 것은
실측이다. 고친 것은 **근거의 강도와 관측 수단**이다.

### 고친 뒤 재검증

**합성** — 가드 4건이 **전부 THROW**(`[]`·`null`·`undefined`·문자열) · 정상 2계열 **무회귀 pass** ·
`max=5`+종단정확이 **pass로 전환**(M1) · 음성 7건 전부 `pass=false` ·
**`exactStateSeen`의 의미 판별**: 적립·종단 **함께 오염** → `false`(=앱 결함) / 적립 정상·**종단만 짧음**
→ `true`(=하네스가 순간을 놓쳤다). **이것이 H3의 「조용한 실패」를 보이게 만든 장치다.**

**실물 2회** (리뷰 후 재실행):

| | 회차 A | 회차 B |
|---|---|---|
| `recv` | `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1` | 동일 |
| `snapshotCounts` | `0,2,2,2,3,4,4,4,5,6,6,6,0` | `0,1,2,2,2,3,4,4,5,6,6,6,0` |
| **`judge.pass`** | **`true`** | **`true`** |
| `judgeable` · `exactStateSeen` | `true` · `true` | `true` · `true` |
| `atMaxDiagnostic` 마지막 줄 | **`답변: I need`**(partial) | **`답변: I need`**(partial) |
| 가드 3건 | **전부 THREW** | — |
| **first-wins 실물 판별** | 종단 프레임을 한 번 더 주입 → **`firstWinsHolds_viaInject: true`** | — |
| 이전 로직을 같은 데이터에 | — | **`oldJudgeOnThisRound: false`** |
| 음성 대조 4건 | 4/4 FAIL | 4/4 FAIL |

⚠️ **이제 실물 6회 연속 `atMaxDiagnostic`의 마지막 줄이 partial이다**(T13 2 + 재확인 2 + 리뷰 후 2).
**이전 판의 거짓 FAIL은 드문 경우가 아니라 기본값에 가까웠다.**

**DB 3열**: `7·34·92·7·1·1` → `9·42·104·7·1·1` → **`7·34·92·7·1·1`**. teardown ①-a `INSERT 0 2` →
① `DELETE 2` → ② **`UPDATE 0`** → ③ `DELETE 0` → ④ 전건 통과(drift **0** · 남은 회차 세션 **0**) ·
캡틴 패턴 `2 / 2026-09-03 13:51:26.680389+00` **무손상**.

**게이트**: **595 passed** · `ruff check`·`format --check`·`ty` 전부 exit 0 · 게이트 밖
`ruff check ../../tests ../../scripts` **Found 6 errors**(기준선 유지) ·
`format --check ../../tests` **4 files would be reformatted**(기준선 유지, `--diff` 계수도 **4**).
⚠️ 그 명령의 "already formatted" 집계가 `find`로 센 `tests/**/*.py` **30개**와 맞지 않는다(53 대 30).
**게이트 지표가 아니고 원인을 해결하지 못했다 — 그렇게 적는다.**

### 리뷰가 지적한 커버리지 공백 중 아직 안 메운 것

- **`:373-375`(종단 프레임에서 `snapshotNow()`를 찍는 자리)를 실패 방향으로 밟는 합성 케이스가 없다.**
  실물 6회가 그 경로를 **통과 방향으로만** 밟았다. first-wins는 실물에서 판별했지만 **합병으로 종단이
  짧아지는 회차는 아직 관측하지 못했다** — `exactStateSeen`이 그때를 식별하도록 넣은 것이 지금 할 수
  있는 최선이다. **관측되면 그 회차 기록이 이 공백을 닫는다.**
- **A1-7 무음 대조** — 여전히 안 돌렸다. **판별력 미확인 유지**(`TASK-30` 소유).

---

## 10. 사후 추가 — 3차 리뷰. **내가 물어서 나온 지적이 유일한 코드 결함이었다**

회차 **`a43a54a3-626b-446e-a8ac-00778c874609`** · `WINDOW_START` `2026-09-06 09:20:41.034465+00` ·
계측 sha256 **`378372be0ac5f7f1…`**(39449 바이트 · 612줄).

리뷰 판정: **코드 축 Approve**(CRITICAL 0 · HIGH 0)이고 8건 + NEW-1 닫힘 확인. 남은 3건 중 **코드는
하나**였고 그것은 **내가 재검증 요청에서 스스로 물은 것**이다.

### ⛔ Q_B — `<=`가 변이 내구성을 잃었다. 내가 재현했다

내 물음: *"`noExcess`를 `<=`로 바꾼 뒤 도달 검출이 `terminalMatches` 하나뿐인데, 초과 검출과 도달
검출이 한 조건에 몰린 것이 아닌가."* → **그렇다.** `H-AB`의 방식대로 **배선 줄만** 무력화했다
(`terminalMatches`의 **길이 검사만** 잃는 변이):

| 시나리오 | 현재(`<=`) | 변이 | 변이 + `reachedExpected` |
|---|---|---|---|
| **앱이 5줄만 렌더(진짜 결함)** | false | ⛔ **true = 거짓 PASS** | **false** |
| 정상 6줄 | true | true | **true**(무회귀) |
| 적립 max5 · 종단 6줄(적립 잘림) | ⚠️ **true** | true | **false** |
| 초과 렌더 max7 | false | false | false |

옛 `===`는 1행을 `noExcess`(5 ≠ 6)로 막았다. `<=`는 `5 <= 6`이 참이라 통과시킨다.
**3행도 중요하다** — 현재 코드가 **잘린 적립으로 낸 판정을 조용히 통과**시키고 있었다.

→ **되돌리지 않고 갈랐다**: `noExcess`(`<=`, 초과 검출) + **`reachedExpected`(`>=`, 도달 검출)**를
둘 다 `pass`에 넣는다. 강도는 옛 `===`와 같고(`<=` ∧ `>=` ⟺ `==`) **사유가 갈린다.**

### `verdict` — 진단 필드가 안 읽히는 위험을 규약에서 **구조**로 내렸다

리뷰 권고를 채택했다. 회차는 `pass`를 해석하지 말고 **`verdict` 한 값을 베껴 적는다**:
`PASS` · `UNMEASURABLE_NO_TERMINAL` · `REMOUNT_OR_TWO_SESSIONS` · `APP_EXCESS_RENDER` ·
`HARNESS_TRUNCATED_ACCRUAL` · `APP_UNDER_RENDER` · `HARNESS_MISSED_TERMINAL_MOMENT` ·
`APP_CONTENT_MISMATCH`.

⚠️ **리뷰가 제안한 라벨을 그대로 쓰지 않고 한 갈래를 더 쪼갰다** — 제안형은 `maxCount < 기대`를
`NEVER_REACHED_EXPECTED` 하나로 묶는데, **그 안에 앱 결함과 하네스 사고가 섞인다.** 가를 수 있다:
정상 순서에서 `|종단| <= maxCount`이므로 **`maxCount < |종단|`이면 적립이 잘린 것**이고 같으면
**앱이 덜 그린 것**이다. 실측으로 갈렸다 — 「앱이 5줄만 렌더」→ `APP_UNDER_RENDER` /
「적립 max5·종단 6줄」→ `HARNESS_TRUNCATED_ACCRUAL`. **라벨이 앱 결함을 하네스 사고로 오분류하면
그 자체가 새 함정이다.**

### 리뷰가 정정한 것 / 내가 정정한 것

- **리뷰가 M1 등급을 MEDIUM → LOW로 내렸다** — 자기가 제시한 failure_scenario(`max=5` + 종단 6줄)가
  **도달 불가 입력**임을 스스로 밝혔다(12,440 조합 전수 비교: `pass`가 갈린 **60건 전부** `M < |T|`).
- **그 철회된 입력이 내 코드 주석과 `browser_leg.md` 두 곳에 근거로 박혀 있었다**(NEW-2). 사실로
  갈았다 — 이제 근거는 **변이 실측**이고, "도달 불가 입력을 회귀 테스트로 만들지 마라"를 함께 적었다.
- **`exactStateSeen`을 `pass`에 넣지 않은 근거가 부정확했다**(리뷰 지적). 연접으로 넣으면 골라내기가
  되살아나지 않는다 — 그건 **이접**이어야 한다. **진짜 이유**: `pass`의 항이 되면 그것은 「원인 중
  하나」가 되어 **"왜 `pass`가 거짓인가"를 지목하지 못한다.** 근거를 그렇게 갈았다.
- **리뷰가 NEW-1을 냈으나 절반이 낡은 관측이었다** — `browser_leg.md`는 `c90f32f`(**09:11:19Z**)에서
  이미 고쳤고 리뷰 보고는 **09:08:27Z**다. 남은 절반(`:169`의 `snapshots` 계약 키)은 진짜였고 고쳤다.
  ⚠️ **리뷰가 `instrument.js`도 두 번 낡은 트리로 봤다**(`6dd2a6b3…` 대 당시 `8972333a…`) — 커밋
  시각을 대조해 구별했다. **낡은 관측을 근거 없이 기각하지도, 그대로 받지도 않았다.**
- ⚠️ **리뷰가 잡지 못한 잔여 낡은 블록 1건을 내가 찾았다** — `snapshots` docstring의 *"타이밍에
  걸리지 않는 유일한 방법은 바뀔 때마다 전부 적립하는 것"*. **그것이 틀렸다는 것이 `H-AF`다.**

### 채택하지 않은 제안 — 「접두 불변」 진단 (기각이 아니라 보류)

`S[k].texts`에서 마지막 줄을 뺀 것이 `S[k+1].texts`의 접두여야 한다는 것. 마지막 줄만 제외하면
partial과 I-8 병합이 **둘 다** 자동 배제되어 **확정 줄 오염만** 정확히 본다 — 설계가 좋다.
보류 이유: **리뷰가 스스로 "판별력 미측정"이라 밝혔다**(회차 기록에 `texts` 전문이 없어 실물로 못
돌렸다). 판별력을 재지 않은 대조를 넣으면 이 리포가 반복해 밟은 **"대조 있음 = 판별력 있음"** 오독을
새로 만든다(§12가 금지하는 형태다). **실물 회차가 `texts` 전문을 남기게 된 뒤에 측정하고 정한다.**

### 재검증 (실물 2회 · 회차 `a43a54a3`)

| | 회차 A | 회차 B |
|---|---|---|
| `recv` | `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1` | 동일 |
| `snapshotCounts` | `0,1,2,2,3,4,4,5,6,6,6,0` | `0,1,2,2,3,4,4,4,5,6,6,6,0` |
| **`verdict`** | **`PASS`** | **`PASS`** |
| 4항목 + 진단 | `terminalMatches`·`noExcess`·`reachedExpected`·`nonDecreasing` 전부 참 · `exactStateSeen` 참 · `judgeable` 참 | 동일 |
| `atMaxDiagnostic` 마지막 줄 | **`답변: I need`**(partial) | **`답변: I need`**(partial) |
| 가드 3건 | — | **전부 THREW** |
| first-wins 실물 판별 | — | **`firstWins: true`** |
| 음성 대조 `verdict` | 문구변형·순서 → `APP_CONTENT_MISMATCH` · 초과기대 → `APP_UNDER_RENDER` · 부족기대 → `APP_EXCESS_RENDER` | — |

⚠️ **실물 8회 연속** `atMaxDiagnostic` 마지막 줄이 partial이다(T13 2 + 3회 재확인 6).

**합성 재검증**: 가드 4건 전부 THROW · `verdict` 8종 분류 전건 기대 일치 · 변이 내구성 복구(위 표) ·
실물 계열 2건 무회귀.

**DB 3열**: `7·34·92·7·1·1` → `9·42·104·7·1·1` → **`7·34·92·7·1·1`**. teardown ①-a `INSERT 0 2` →
① `DELETE 2` → ② **`UPDATE 0`** → ③ `DELETE 0` → ④ 전건 통과(drift **0** · 남은 회차 세션 **0**) ·
캡틴 패턴 무손상. **게이트**: 595 passed · `ruff`·`ty` exit 0 · 게이트 밖 **6 errors** · **4 files**.

### 여전히 못 메운 것 (통과로 적지 않는다)

- **`:373-375`(종단 스냅샷 자리)를 실패 방향으로 밟는 표본 0건.** 리뷰가 방법을 제시했다 —
  `stub.py`를 건드리지 않고 **래퍼를 통과시키는 같은-tick 주입**(별도 진입점, `recv` 오염을 명시).
  **동의하고 다음 회차 몫으로 남긴다** — `exactStateSeen`은 그 회차를 **식별**하는 장치이고 그 주입은
  식별 장치가 **작동함을 증명**하는 장치다. 둘은 짝이고 지금은 앞쪽만 있다.
- **A1-7 무음 대조** — 여전히 미실행. **판별력 미확인 유지**(`TASK-30` 소유).
- **실물 Nova에서 종단에 partial이 남는 구성** — 미확인.

---

## 11. 사후 추가 — 4차 리뷰. **내가 만든 `verdict`가 앱 결함을 하네스 탓으로 돌렸다**

회차 **`d616aa4c-d5f4-446d-9f20-9910a15d34c1`** · `WINDOW_START` `2026-09-06 09:30:03.729213+00` ·
계측 sha256 **`5c354e4418604bc6…`**(42767 바이트 · 648줄).

리뷰 판정: **Q_B 닫힘 · NEW-3 닫힘 · `browser_leg.md:169` 닫힘 · `noExcess` 새 근거 정확.**
새로 **NEW-4(HIGH) · NEW-5 · NEW-6 · 놓친 낡은 블록 1건**.

### ⛔ NEW-4 — `verdict`가 음성 대조 3건을 「하네스 사고」로 분류했다. **내 결함이다**

리뷰가 종단 오염 4모양을 넣어 돌렸고 **합병만이 아니라 순서 뒤바뀜·본문 치환·종단 partial 오염까지
전부 `HARNESS_MISSED_TERMINAL_MOMENT`**였다. 그 셋은 `browser_leg.md` A1-5가 **음성 대조로 이름 붙인
셋**이다 → **문서가 요구한 대조를 문서가 기각하게 된다.** `verdict`는 회차가 **해석 없이 베끼도록**
만든 값이라 틀린 라벨이 플래그가 틀린 것보다 파급이 크다.

⚠️ **내가 먼저 "그 반례는 도달 불가일 것"이라고 의심했고 그 의심이 틀렸다.** 리뷰 자신의
`|종단| <= maxCount` 논증으로 「적립에 정답 + 종단은 같은 개수인데 내용 다름」이 불가능해 보였는데,
**`page.tsx:123~124`의 I-8 병합이 개수를 바꾸지 않고 마지막 줄 텍스트만 치환한다** — 그래서 도달
가능하다. **직접 그 줄을 읽어 확인한 뒤 반박을 철회했다.**

**원인 한 줄**: 확정 줄이 append-only라 **종단이 어떻게 오염되든 적립에 정답 상태가 남을 수 있다** →
`exactStateSeen`은 「정답 상태가 언젠가 있었다」만 뜻하고 「하네스가 놓쳤다」를 못 가른다.
**판별자는 진접두 여부다** — 커밋 누락이 만드는 종단은 **짧고, 있는 만큼은 정확하다**.

`terminalIsPrefix`를 신설해 `verdict`의 마지막 분기에 함께 걸었다. 실측(같은 적립, 종단만 바꿈):

| 종단 모양 | 이전 | 지금 |
|---|---|---|
| 합병(진접두 5줄) | `HARNESS_MISSED_TERMINAL_MOMENT` | **동일**(정답) |
| 순서 뒤바뀜(6줄) | ⛔ `HARNESS_MISSED_TERMINAL_MOMENT` | **`APP_CONTENT_MISMATCH`** |
| 본문 치환(6줄) | ⛔ 같음 | **`APP_CONTENT_MISMATCH`** |
| 종단 partial 오염(6줄) | ⛔ 같음 | **`APP_CONTENT_MISMATCH`** |

⚠️ **합성만이 아니라 실물 적립에 그 4모양을 얹어 재확인했다**(회차 A) — 같은 결과다. 그리고 이
해석이 **코드 2곳과 `browser_leg.md` 2문장**에 문장으로도 들어가 있었다 → 같은 커밋에서 함께 고쳤다.

### NEW-5 — 같은 식을 5곳에서 다시 유도하고 있었다 (드리프트 생성기)

`maxCount <= expected.length` 3곳 · `maxCount >= expected.length` 3곳 · `snapshots.some(...)` 2곳.
`noExcess`를 고치면 `pass`·`verdict`가 따라오지 않아 **플래그와 `verdict`가 갈릴 수 있었다.**
지역 상수 5개(`noExcess`·`reachedExpected`·`exactStateSeen`·`terminalIsPrefix`·`pass`)로 뽑아
**각 1곳**으로 줄였다(직접 계수 확인).

### NEW-6 — `reachedExpected`를 더하면서 「셋/넷」이 다시 낡았다

`instrument.js`의 한 곳이 "셋", 다른 곳이 "넷", `browser_leg.md`는 **"셋"이라 적고 네 개를 열거**했다.
셋 다 "넷"으로 맞추고 **"개수를 말하는 문장은 조건을 더할 때마다 함께 고친다"**를 코드에 박았다.

### ⛔ 놓친 낡은 블록 1건 — `instrument.js` §4-b 절 머리 세 줄. **내 스윕이 놓쳤고 이유가 중요하다**

그 자리에 *"동기와 rAF 둘 다 회차 운에 걸렸다"* + *"타이밍에서 벗어나는 유일한 방법은 전부 적립하는
것"*이 **살아 있었다.** 첫 문장은 **지금 정본인 동기 종단 스냅샷을 조건 없이 부정**하고, 둘째는
`H-AF`가 반증한 문장이다. §4-b를 여는 사람이 **먼저** 읽는 세 줄이다.

⚠️ **내 grep이 왜 못 잡았나 — 도구가 아니라 마크다운이다.** 그 줄은
`**DOM이 바뀔 때마다 전부 적립**하는 것이다`이고 **강조 `**`가 검색 구절을 끊는다.** 리터럴
`전부 적립하는 것`은 **1건**(내 정정 문장)이고, 짧게 `전부 적립`으로 재면 **`[166, 285]`**다.
**`H-AG`와 같은 형태다 — 도구가 "없다"를 조용히 돌려주고 그것이 옳게 보였다.**
→ **판별: 낡은 문구를 지울 때는 구절이 아니라 그 안의 가장 짧은 고유 토큰으로 잰다.**
→ **더 나은 방법(리뷰가 쓴 것, 채택한다)**: 기억한 문구 목록이 아니라 **판정 어휘 전수 스윕** —
주석 줄 중 판정 관련 식별자·용어 20여 개 중 하나라도 든 줄을 **전부 뽑아 읽는다.** 기억에 의존하지
않으므로 「내가 잊은 문구」가 빠지지 않는다.

### 재검증 (실물 2회 · 회차 `d616aa4c`)

| | 회차 A | 회차 B |
|---|---|---|
| `recv` | `session_started 1 · partial 6 · final 6 · audio 3 · session_ended 1` | 동일 |
| `snapshotCounts` | `0,1,2,2,3,4,4,4,5,6,6,0` | `0,1,2,2,3,4,4,5,6,6,6,0` |
| **`verdict`** | **`PASS`** | **`PASS`** |
| 4항목 + 진단 | 전부 참 · `terminalIsPrefix` false · `exactStateSeen` true · `judgeable` true | 동일 |
| 가드 3건 | **전부 THREW** | — |
| **4모양 오분류 재확인** | **합병만 `HARNESS_MISSED`, 나머지 셋 `APP_CONTENT_MISMATCH`** | — |
| first-wins | — | **`firstWins: true`** |
| 음성 대조 `verdict` | — | 문구변형·순서 → `APP_CONTENT_MISMATCH` · 초과기대 → `APP_UNDER_RENDER` · 부족기대 → `APP_EXCESS_RENDER` |
| `atMaxDiagnostic` 마지막 줄 | partial | partial |

**합성**: `verdict` 분류 12종 전건 기대 일치 · 가드 4건 THROW · 실물 계열 2건 무회귀 ·
중복 유도 각 1곳 확인.
⚠️ **실물 10회 연속** `atMaxDiagnostic` 마지막 줄이 partial이다.

**DB 3열**: `7·34·92·7·1·1` → `9·42·104·7·1·1` → **`7·34·92·7·1·1`** · teardown ② **`UPDATE 0`** ·
drift **0** · 캡틴 패턴 무손상. **게이트**: 595 passed · `ruff check`·`format`·`ty` exit 0 ·
게이트 밖 **6 errors**·**4 files** · 프론트 `tsc`·`eslint` exit 0. 백엔드 pid **38202** 무변경.

### 여전히 못 메운 것

- **`:373-375` 자리를 실패 방향으로 밟는 표본 0건** — 리뷰가 방법을 제시했고(래퍼를 통과시키는
  같은-tick 주입, 생산 코드 0줄) **동의했다. 다음 회차 몫이다.**
- **A1-7 무음 대조** 미실행 · **실물 Nova 종단 partial** 미확인.
- **「접두 불변」 진단** 보류 유지(판별력 미측정). ⚠️ 리뷰가 **`terminalIsPrefix`는 그것과 다른 것**
  이라고 정확히 갈랐다 — 새 대조가 아니라 **이미 있는 두 신호의 해석 수정**이고 판별력이 위 표로
  측정됐다. 보류 대상이 아니었다.

---

_기록: 2026-09-06. `TASK-31` AC #14의 산출물이다. §9·§10·§11은 같은 날 독립 코드리뷰 2·3·4차의_
_판정과 그 반영이고 §1~8의 관측은 고치지 않았다. AC #15·#16은 각각 `ee040ee`·`97a553e`가 소유한다._
