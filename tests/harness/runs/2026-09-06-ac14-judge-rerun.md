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

_기록: 2026-09-06. `TASK-31` AC #14의 산출물이고 **AC #1을 다시 체크한 근거**다._
_AC #15·#16은 각각 `ee040ee`·`97a553e`가 소유한다._
