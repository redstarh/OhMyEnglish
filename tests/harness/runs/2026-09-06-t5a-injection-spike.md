# T5a 주입 스파이크 — CDP 프레임 주입 (`TASK-20`)

> 2026-09-06 · 실행 주체 **`.claude/agents/frontend-verifier.md`** 에이전트 · 절차 정본
> `tests/harness/browser_leg.md` · 회차 `757e1041-255b-49c9-89ca-6ab6f3089a46` ·
> `WINDOW_START` `2026-09-06 03:40:14.213266+00`
>
> 환경: 백엔드 pid **30860** · `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false` ·
> 프론트 :3000. **호출자(팀리드)가 세운 프로세스다** — §8-⑤를 건너뛴 근거가 그것이다(§5).
>
> ⚠️ **평가한 계측 판은 sha256 `66384c910601b28eb74ef787ed2d338ee90c5eecc6910804c2fc8ebcec3affe7`
> (15289 바이트)다.** 회차 **후** docstring 정정으로 `e1342aca8d6a31a750b72c7b9658d45c83ecb6e3c041b1d363646da37b66c2e0`
> (15806 바이트)가 됐고 **실행 코드 변경은 0줄이다**(팀리드가 `git diff`로 확인). 재현할 때 해시
> 불일치를 결함으로 오독하지 말 것.
>
> ⚠️ **이 기록은 사후 편집하지 않는다.**

---

## 1. 판정 — **AC 4건 전건 `PASS`. 가장 넓게 걸렸던 미결이 닫혔다**

| AC | 판정 | 요지 |
|---|---|---|
| ① `pronunciation` 배지 4종 | **PASS** | 4 outcome 순차 주입 → 배지 요소 **정확히 1개** + 문구 **등호** 일치 |
| ② `partial` 주입 | **PASS** | 접두 `<p>` **0 → 1** · `답변: PARTIAL_TEXT_ALPHA` |
| ③ `final` 두 갈래 | **PASS** | 첫 final 새 줄 · 같은 화자 연속 **불변(1)** · 다른 화자 **1 → 2** |
| ④ 주입 창 | **PASS** | 주입 완료 **256 ms** = 창의 **2.6%** · 창 실측 **10,023 ms** |

**2회 독립 회차가 일치했다.** → `browser_leg.md` §11의 미결 **5·6이 닫혔고 2·3도 함께 닫혔다**.
**C5 폐기와 §7-6 직렬 큐 대안 둘 다 불필요하다.**

## 2. 프리플라이트 — 에이전트가 전건 직접 실행, 전건 통과

`P1 {"status":"ok"}`(`version` 없음) · `P2 NEXT_PUBLIC_API_BASE=http://localhost:8002` ·
`P3 app/frontend/.gitignore:34:.env*` · `P4 postgresql@17 started` ·
**`P5 pid 30860 · 기동 04:16 전 · 소스 32건 → 통과`** · `P6 200` · `P7 2` · `P8 pytest 0건` ·
`P9 ohmyenglish`. 추가로 `ps -p 30860 -Eww`로 두 환경변수를 직접 확인했다.

**§4 계측 자기검사**: `eval` 반환값 `'instrumented'` 정확 일치 · 계약 키 4개
(`recv`·`sent`·`started`·`finalLines`) 전부 존재 · 후킹 소유자 3개 실측 —
`onmessage`→`WebSocket` · `send`→`WebSocket` · **`start`→`AudioBufferSourceNode`**
(`createBufferSource`→`BaseAudioContext`). **§11-2의 답이다.**

⚠️ **계측을 손으로 옮겨 적지 않았다** — 임시 CORS 서버로 파일을 그대로 받아 `eval`하고 페이지 안에서
sha256을 계산해 대조했다. **전사 드리프트가 구조적으로 0이다.** 서버는 회차 후 정리했다
(팀리드 확인: 54661 리스너 없음).

## 3. 단정별 실측값 (2회차)

**① 배지** — 기대값을 `app/frontend/app/page.tsx:PRONUNCIATION_BADGE` 블록을 파싱해 **유도**했다
(하드코딩 아님). `pending`→`🔊 발음 교정 중` · `correct`→`✓ 좋아요` · `incorrect`→`다시 연습해요` ·
`unclear`→`잘 안 들렸어요`. **음성 대조 3건이 전부 실제로 FAIL을 냈다**: ⓐ 주입 전 배지 요소 **0개**
(`active` 도달 후에도 0) ⓑ 순차 주입에서 같은 요소 텍스트가 **4번 다 바뀌었다**(상수 렌더면 안 바뀐다)
ⓒ 기대값+`"X"` 변형이 **4/4 불일치**(등호가 항진명제가 아님). 덤으로 **A5-2**: `target_sound`의
sentinel `ZZSENTINELSOUND9137`이 DOM 전체에 **0건**이면서 같은 프레임의 배지 문구는 **있었다**.

**② partial** — 선별은 `<strong>` 텍스트가 `질문: `/`답변: `인 `<p>`로만(색 미사용).
§6-0 대조가 FAIL을 낼 수 있음을 확인: 주입 전 0개이고 **`active` 도달 후에도 0개**였다
(그 시점 화면 문구 `대화를 기다리는 중...`, 버튼 `학습 종료`) → **0이 "컨테이너 부재" 때문이 아니다.**

**③ final** — `page.tsx:handleServerEvent`의 `case "final"`을 직접 읽어 유도했다.
ⓐ 첫 final(agent): `질문: FINAL_ONE_AGENT`, partial 텍스트가 DOM에서 **`true` → `false`**로 사라짐
(`setPartialLine(null)` 확인). ⓑ 같은 화자 연속: 줄 수 **불변(1)**,
`질문: FINAL_ONE_AGENT FINAL_TWO_AGENT`(공백 하나로 병합). ⓒ **판별력 대조** — 다른 화자 final 주입 →
**1 → 2**, `답변: FINAL_THREE_USER`. 따라서 ⓑ의 "늘지 않는다"는 **공허하지 않다.**

**`recv` 무오염 — 설계 주장에서 관측으로 승격**: `session_started` **후**에 기준선을 잡고 8프레임을
주입해 `recvUnchangedByInject: true` · `injected` **0 → 8**. ⚠️ 1회차에는 기준선을
`session_started` **전**에 잡아 `false`가 나왔고 **그것은 회차 스크립트 결함이지 주입 오염이 아니다** —
에이전트가 스스로 그렇게 구분해 보고했다.

## 4. 실측 대기값 — §11-1을 닫는 값

| 구간 | 값 |
|---|---|
| 클릭 → `active` | **6 ms** (1회차 6 ms) |
| 클릭 → `session_started` | **9 ms** |
| `session_started` → 8프레임 주입 완료 | **256 ms** (클릭 기준 265 ms · 1회차 271 ms) |
| `session_started` → `session_failed` (창 실측) | **10,023 ms** (1회차 10,071 ms) |
| 주입 1건당 double-rAF settle | 약 **33 ms** (스냅샷 시각 23·56·89·123 / 156·189·223·256) |
| AudioContext 프로브 | 생성 즉시 **`running`** 1 ms · `addModule` 2 ms · `resume` 0 ms |
| **에이전트 라운드트립 (실제 병목)** | `click` → 다음 `eval` 도달 **약 30 s** · 실패 회차 첫 스냅샷이 pre-click 마커로부터 **37,992 ms** |

폴링: `session_started`·`active`는 **2 ms** 간격(1회차 5 ms)에 10회 이내로 잡혔다.
`session_failed`는 20 ms 간격·상한 15 s로 걸어 약 **9.77 s**에 잡혔다.

## 5. teardown — 새 §8을 정확히 따랐다

**§8-0 drift 가드를 실제로 돌렸다**: `to_regclass` → `t`, drift → **0**, baseline **7**행,
`error_patterns` **7**. drift 0이라 "표가 있고 drift 0" 갈래를 탔고 **재스냅샷하지 않았다**
(⚠️ 문서는 재스냅샷으로 진행하라고 적었으나 drift 0이면 결과가 같고 검증된 사본을 가진 기존 표를
두는 쪽이 사본을 하나 더 지킨다 — **결과 동일, 의도적 선택**이라고 보고했다). 회차 후 drift도 **0**.

**§8-②를 복원으로 했다 — 재계산 SQL을 한 번도 던지지 않았다.** `UPDATE 0`.
순서: ①-a `INSERT 0 3`(scenario `T5a`) → ① `DELETE 3` → ② `UPDATE 0` → ③ `DELETE 0` → ④ 대조 3건
(`error_patterns` 7 = baseline 7 · drift 0 · 남은 회차 세션 0).

| 표 | baseline | 회차 후 | teardown 후 |
|---|---|---|---|
| `learning_sessions` | 7 | 10 | **7** |
| `analysis_jobs` | 34 | 37 | **34** |
| `utterances` | 92 | 92 | **92** |
| `error_patterns` | 7 | 7 | **7** |
| `session_plans` | **1** | **1** | **1** |
| `learner_notes` | **1** | **1** | **1** |

**보존 2행은 세 시점 모두 1행이고, 그 두 표를 대상으로 하는 SQL을 아예 던지지 않았다**(`count(*)`만).

**§8-⑤는 의도적으로 건너뛰었다** — 프로세스가 호출자 소유다. 대신 무변경 증거 3개를 남겼다:
리스너 pid **30860**(회차 시작과 동일) · `VOICE_ADAPTER=stub_unresponsive`·`WORKER_ENABLED=false`
(동일) · `/health` `{"status":"ok"}`. `app/backend/.env`를 열지도 않았다. → **§8에 예외 절을 넣었다.**

## 6. ⚠️ `finalLines` — T2와 어긋나는 관측. **T2의 결함은 살아 있다**

T2는 `session_ended` 동기 스냅샷이 React commit 전이라 `[]`가 된다고 보고했고, 이 회차는
`session_failed` 시점에 정상 동작해 `["질문: FINAL_ONE_AGENT FINAL_TWO_AGENT", "답변: FINAL_THREE_USER"]`
를 남겼다. **에이전트가 자기 관측으로 T2를 반박하지 않았다 — 그것이 옳은 처리다:**

- **사실**: 8프레임을 한 `eval` 안에서 **순차로** 주입하고 매 주입 뒤 double-rAF로 33 ms씩 기다렸다.
  주입은 `session_started`로부터 256 ms에 끝나고 종단 프레임은 **10,023 ms**에 왔다 → 스냅샷 시점에
  **약 9,767 ms 전에 이미 commit된 DOM**이 있었다.
- **따라서 이 결과는 타이밍 안전성을 증명하지 않는다.** "여유가 9.7초일 때 동작했다"만 보였다.
- **에이전트가 밝힌 한계 2개**: `[]`를 한 번도 관측하지 못했고, **실제 `session_ended` 경로를 아예
  밟지 않았다**(`stub_unresponsive`는 그 프레임을 보내지 않는다 — 본 종단 프레임은 `session_failed`
  하나뿐이다). 연속 주입 사이에 항상 settle을 넣어 **문제 조건을 구조적으로 회피했다.**
- **T2 쪽 `[]`의 기제가 "commit 이전 도착"이라는 것은 에이전트의 추측이다** — 그렇게 표시했다.

→ **§11-7의 답으로 채택하지 않는다. `TASK-31`의 그 항목은 살아 있다.**
**판별에 필요한 실험**(아직 아무도 돌리지 않았다): `settle()` 없이 `final` 직후 종단 프레임을
**같은 tick에** 연달아 주입하고 `finalLines`가 줄을 잃는지 본다. 재현되면 결함은 "동기 스냅샷 지점"이고
수정 방향은 §11-7이 미정으로 남긴 rAF/MutationObserver 쪽이다.
⚠️ **AC ①~④ 판정에는 영향이 없다** — 넷 중 어느 것도 `finalLines`에 의존하지 않는다.

## 7. `instrument.js` — **기능 결함 0건.** 관측 2건과 미실행 3건

- 후킹 3개 전부 설치 · 계약 키 4개 존재 · 반환값 정확 · **중복 주입 방어가 실제로 동작**.
- **관측(결함 아님)** ① docstring이 "`eval` await 여부를 미결로 남기지 않기 위해"라고 적었으나
  **`eval`은 promise를 await한다**(250 ms sleep → `elapsed: 260`). **팀리드가 직접 재확인**(`254`)하고
  **docstring의 거짓 근거를 정정했다** — 결정(동기 IIFE)은 유지, 근거만 교체.
  ② `meta.audioContextState`는 `tryResume()` 안에서만 갱신되는 **시점 기록**이다(활성화 전 `suspended`,
  후 `running`).
- **미실행**: `start` 후킹의 **계수 경로**(`stub_unresponsive`가 `audio` 0건 → `started.count` 0 ·
  `when` `[]`) · `config.silentMic` · `probeColor`. **A1-4의 계수와 `when` 대조는 이 회차에서 평가 불가다.**

## 8. `browser_leg.md` 결함 8건 — 에이전트는 고치지 않았고 팀리드가 반영했다

| # | 무엇 | 반영 |
|---|---|---|
| D-1 | §10의 증거 모델이 §6의 10초 창과 **구조적으로 충돌**한다 | ✅ §10 재작성 — 창 안 관측은 **`eval` 반환값이 증거**이고 `outerHTML`·`innerHTML`을 실어 보낸다 |
| D-2 | §3의 두 명령이 **cwd가 어긋난다** — 앞 블록이 `cd app/backend`로 끝나 뒤 검증이 `FileNotFoundError` | ⏳ **미반영** — `TASK-31`로 넘겼다 |
| D-3 | §6·§11-6이 **병목을 잘못 짚었다**(페이지 256 ms 대 라운드트립 30 s) | ✅ §6에 ⛔ **"전 과정을 한 `eval`에 넣는다"**를 박았다 |
| D-4 | §11-1 대기값 실측 | ✅ §4 표 + §11-1 갱신 |
| D-5 | §8-⑤가 **호출자 소유 프로세스와 충돌**한다 | ✅ 예외 절 추가(무변경 증거 3개) |
| D-6 | `-console.txt`가 **빈 스텁**이다 | ✅ §10에 명시. 팀리드 확인: **58바이트**, `# TODO: Console logging not yet implemented` |
| D-7 | §6-0 대조를 **`active` 도달 후에** 재면 강해진다 | ✅ §6-0에 박았다 |
| D-8 | §6의 창 이탈 판별 **근거가 틀렸다** | ✅ 정정. 팀리드가 `page.tsx`를 읽어 확인 — 컨테이너가 `active\|ending`으로 갇혀 `failed`에서 **통째로 언마운트**된다(접두 `<p>` **2 → 0**) |

**창 이탈 ERROR 회차(`045`~`047`)**: `click` 다음 `eval`에서 주입하려 했으나 라운드트립 ~30 s로 창을
넘겼다 → 화면이 이미 `사유: voice_adapter_connect_timeout`. **§6·§10대로 FAIL이 아니라 `ERROR`로
처리하고 재시도**했고, 전 과정을 한 `eval`에 넣은 뒤 **2회 연속 성공**했다. 중간에 `VoiceIo.start`
지연을 의심해 프로브를 돌렸으나 **무혐의**였다(§4 표).

## 9. ⚠️ 증거의 소유자 — 이 회차의 약점

**자동 저장 아티팩트로 AC ①②③을 재확인할 수 없다.** `054-eval.html`에 `aria-live` 0건 ·
주입 문구 0건 · 배지 문구 0건이고 `voice_adapter_connect_timeout`만 1건이다 — **주입 실패가 아니라
캡처 시점이 창 밖**이기 때문이다(D-1). 에이전트가 `outerHTML`을 반환값에 싣지 않아
**재현 경로가 "같은 payload를 다시 돌린다" 하나뿐이다.**

→ **§10에 그 규약을 박았고 다음 회차부터 적용한다.** 이 회차의 값은 위 §3에 옮겨 둔 것이 전부다.
증거 파일 위치: `~/Library/Caches/superpowers/browser/2026-09-05/session-1788623621742/` —
2회차 `052`~`054`, 1회차 `049`~`051`, 계측 자기검사 `043`, AudioContext 프로브 `048`,
ERROR 회차 `045`~`047`.

## 10. 팀리드가 직접 확인한 것

| 주장 | 결과 |
|---|---|
| 계측 sha256 · 바이트 | ✅ `66384c9106…3affe7` · **15289** 일치 |
| `CONNECT_TIMEOUT = 10.0` | ✅ `session.py:53` 실재 |
| 임시 CORS 서버 정리 | ✅ 54661 리스너 없음 |
| DB 6표 + drift | ✅ **7·34·92·7·1·1** · drift **0** · `pronunciation_an_as_a` `2 / 2026-09-03 13:51:26.680389+00` |
| `eval`이 promise를 await하나 | ✅ **await한다** (`elapsed: 254`) → docstring 근거를 정정했다 |
| `-console.txt`가 스텁인가 | ✅ **58바이트** 두 줄 |
| `failed`에서 컨테이너 언마운트 | ✅ `page.tsx`가 `active\|ending`으로 가두고 `failed`는 별도 블록 |

**확인하지 못한 것**: AC ①②③의 DOM 관측값 자체(§9의 이유로 재현 경로가 payload 재실행뿐이다) ·
대기값 실측치 · teardown SQL의 각 결과 코드. **재현했으면 그렇게 적고, 못 했으면 이렇게 적는다.**

---

_기록: 2026-09-06. §1~7은 에이전트 보고, §8은 팀리드의 반영, §10은 팀리드의 독립 확인이다._
_에이전트가 자기 관측으로 T2를 반박하지 않고 판별 실험을 명시한 것(§6)은 이 회차의 가장 좋은 처리다._
