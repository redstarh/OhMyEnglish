# 회차 기록 — T3 C2 렌더 위계 (A2-1 · A2-2 · A2-3) · `TASK-21` AC #2·#3·#4

- **일시** 2026-09-06 (UTC 12:52 ~ 13:0x) · **회차** `.harness/browser_run_id.txt` = `bd747c39-8790-4991-b38b-95934f0ceda3`
- **HEAD** `c652c2d` · 브랜치 `design/first-vertical-slice`
- **모드** 백엔드 `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false`(주입 창 확보 · 실물 모델 호출 0회)
- **계측** `tests/harness/instrument.js` sha256 **`846f130f2cf73365ae00765b37300e00e3c1c5b1cb1ae6152f9a02b7fc16ae93`**(43119B).
  **페이지 안에서 계산해 파일 해시와 대조했다** — 전사 드리프트 0(§10-3). 계측은 이 회차에서 **고치지 않았다.**
- **실행체** `tests/harness/c2_render_hierarchy.py`(이 회차에 신설)
- **증거 사본(추적됨)** — ⚠️ **`.harness/`는 `.git/info/exclude`로 제외라 그쪽 파일은 사라진다.**
  baseline TSV와 같은 이유로 **`runs/`에 사본을 뒀다**: `2026-09-06-t3-c2-eval-return.json`(판정 회차 2차) ·
  `…-eval-return-partial.json`(partial 회차) · `…-c2-{light,dark}.png` · `…-c2-{light,dark}-partial.png`
- **판정** **`PASS`** — A2-1 · A2-2 · A2-3 세 단정 전건, **라이트·다크 두 모드**에서.

---

## 1. 직접 확인한 것

### 1-1. 판정 회차 (`--phase both`, 모드별 1문서 1세션)

| 항목 | light | dark |
|---|---|---|
| 페이지가 보고한 스킴 (`matchMedia`) | `light` | `dark` |
| **주입 전**(`active` 도달 후) 접두 `<p>` — §6-0 | **0** | **0** |
| 같은 시점 `사유: ` `<p>` (창 이탈 판별) | **0** | **0** |
| 같은 시점 `대화를 기다리는 중...` 존재 (컨테이너 마운트 증거) | `true` | `true` |
| probe `--foreground-muted` (1차 / 2차) | `rgb(89, 89, 89)` / **동일** | `rgb(154, 154, 154)` / **동일** |
| probe `--foreground` (1차 / 2차) | `rgb(23, 23, 23)` / **동일** | `rgb(237, 237, 237)` / **동일** |
| partial 주입 후 접두 `<p>` 개수 | **1** | **1** |
| 그 줄의 `getComputedStyle().color` | `rgb(89, 89, 89)` → **muted probe와 일치** | `rgb(154, 154, 154)` → **일치** |
| final 주입 후 접두 `<p>` 개수 | **1** | **1** |
| 그 줄의 색 | `rgb(23, 23, 23)` → **foreground probe와 일치** | `rgb(237, 237, 237)` → **일치** |
| partial 문구가 문서에 잔존하는가 | **false**(사라졌다) | **false** |
| `recv` | `session_started 1` · `partial 0` · `final 0` · `audio 0` · `session_failed 0` | 동일 |
| `injected` | **2** | **2** |
| `snapshotCounts` | `[0, 1, 1]` | `[0, 1, 1]` |
| 타이밍 (클릭 기준) | `active` **17 ms** · partial **+18 ms** · final **+35 ms** · eval 반환 **65 ms** · 스크린샷 **137 ms** | `active` **16 ms** · **+17** · **+34** · **60** · **142** |
| user activation | `visible` · `focused true` · `hasBeenActive true` · `isActive true` | 동일 |

**창 안이었다**: `CONNECT_TIMEOUT = 10.0 s`인데 전 과정이 클릭 후 **65 ms**에 끝났고(창의 **0.65 %**),
전 구간에서 `사유: ` `<p>`가 **0개**였다(§6의 창 이탈 판별). 스크린샷도 **137 ms**에 떴으므로
**창 안 화면이다** — §10이 경고한 "자동 저장 파일이 창 밖 상태를 담는다"에 걸리지 않았다.

### 1-2. `outerHTML` — 제3자가 재확인할 수 있는 형태로 남긴다 (§10-1)

두 모드에서 **글자 그대로 같았다**(색은 `getComputedStyle`이 모드별로 다르게 계산한다):

```html
<!-- partial -->
<p style="color: var(--foreground-muted); margin: 0.4rem 0px;"><strong>질문: </strong>PARTIAL_PROBE_ALPHA 부분 전사문 표본</p>
<!-- 확정 -->
<p style="color: var(--foreground); margin: 0.4rem 0px;"><strong>질문: </strong>FINAL_PROBE_BETA 확정 전사문 표본</p>
```

⚠️ **이것이 독립 증거를 하나 더 준다** — 인라인 스타일이 **토큰 자체**(`var(--foreground-muted)`)이고
색값이 아니다. 즉 계산색 등호와 **별개 경로로** 위계 계약이 확인됐다. `globals.css` 머리주석의 계약
(강조=`--foreground` · 보조=`--foreground-muted`)이 코드에 그대로 반영돼 있다.

### 1-3. 눈으로 본 것 — 스크린샷 4장을 **내가 열어서 봤다**

| 파일 | 무엇이 보이는가 |
|---|---|
| `.harness/evidence/c2-light.png` | 흰 배경 · 확정 줄이 **거의 검은색** · 버튼 `학습 종료` |
| `.harness/evidence/c2-dark.png` | 검은 배경 · 확정 줄이 **거의 흰색** · 버튼 `학습 종료` |
| `.harness/evidence/c2-light-partial.png` | 흰 배경 · 같은 자리 문구가 **회색**(확정보다 눈에 띄게 흐리다) |
| `.harness/evidence/c2-dark-partial.png` | 검은 배경 · 문구가 **회색**(확정 흰색보다 흐리다) |

`질문: ` `<strong>`도 부모 `<p>`의 색을 물려받아 partial 회차에서는 함께 흐려진다 — 위계가 줄 단위로 성립한다.

### 1-4. 음성 대조가 실제로 값을 갈랐다

| 대조 | 결과 |
|---|---|
| A2-1·A2-2 — **주입 전 접두 `<p>` 0개**(§6-0, `active` 도달 후) | **0 → 1**로 움직였다. 주입이 조용히 실패한 회차가 아니다 |
| A2-2 ② — **probe 두 값이 서로 다름** | light `rgb(89,89,89)` ≠ `rgb(23,23,23)` · dark `rgb(154,154,154)` ≠ `rgb(237,237,237)` |
| A2-3 — **모드 간 토큰이 다름** | muted `rgb(89,89,89)` ≠ `rgb(154,154,154)` · fg `rgb(23,23,23)` ≠ `rgb(237,237,237)` |
| A2-3 — **같은 모드 두 번 읽으면 같음** | 4회 전부 1차 == 2차. `Emulation.setEmulatedMedia`가 실제로 걸렸다는 증거는 **페이지가 보고한 스킴이 요청과 일치**한 것이다(불일치면 스크립트가 죽는다) |
| 선별의 자기순환 배제 | 대상을 **`<strong>`의 `질문: `/`답변: ` 접두로만** 골랐다 — 색은 선별에 쓰지 않았다(§6) |

**판별 논리**: partial의 색이 fg probe와 **다르고** 확정의 색이 muted probe와 **다르므로**, 앱이 두 토큰을
뒤바꿔 렌더하면 두 등호가 **동시에 깨진다.** 즉 이 단정은 뒤바뀜에 대해 판별력이 있다.

### 1-5. DB 3열 (§10 ⛔ — 하나라도 빠지면 사후 대조가 불가능하다)

`WINDOW_START` = `2026-09-06 12:52:18.538408+00`

| 표 | baseline | 회차 후 | teardown 후 |
|---|--:|--:|--:|
| `learning_sessions` | 7 | 11 | **7** |
| `analysis_jobs` | 34 | 38 | **34** |
| `utterances` | 92 | 92 | **92** |
| `error_patterns` | 7 | 7 | **7** |
| `session_plans` (보존) | 1 | 1 | **1** |
| `learner_notes` (보존) | 1 | 1 | **1** |
| baseline drift | 0 | 0 | **0** |

`utterances`가 92로 불변인 것은 정상이다 — `stub_unresponsive`는 `final`을 0건 보내고 주입은 DB를 거치지 않는다.

**teardown 실행 결과**: ①-a `INSERT 0 6` · ① `DELETE 6` · ② `UPDATE 0`(drift가 0이라 만질 행이 없다) ·
③ `DELETE 0` · ④ 패턴 **7**(baseline과 같다) · drift **0** · 남은 회차 세션 **0**.
baseline은 회차 전에 추적된 사본 `runs/2026-09-06-pattern-baseline.tsv`와 **7행 정확히 일치**함을 확인한 뒤 떴다.

⑤ 프로세스 복원: 백엔드를 받은 상태(`VOICE_ADAPTER=stub` · `WORKER_ENABLED=false`)로 되돌렸고
`/health`가 `{"status":"ok"}`다. **`app/backend/.env`는 열지도 고치지도 않았다**(모드는 환경변수로만 넘겼다).

---

## 2. 직접 확인하지 **못한** 것 — 통과로 적지 않는다

- ⚠️ **회차 창 안에 세션이 6건 생겼고 그중 2건(`d073405c…`·`50920614…`)의 방아쇠를 특정하지 못했다.**
  4건은 내 4회차(2모드 × 2단계)로 설명되지만, 나머지 2건은 **선행 `GET /api/sessions/next-plan`이 없는**
  WS 접속이다(백엔드 로그 직접 확인) — 즉 **이미 로드된 문서에서 `startSession`이 두 번 더 돌았다.**
  그것을 할 수 있는 것은 `app/page.tsx:283`(`학습 시작`)·`:357`(`다시 시도`) 두 버튼뿐이고
  **자동 재시도 경로는 없다**(`setTimeout`·`setInterval`·reconnect 0건, grep 직접 확인).
  → **기제 미확정.** 남겨 둔 채로 두 건 전부 등록·삭제했고 ④ 대조는 깨끗하다.
  → 판정에는 영향이 없다: 각 회차의 반환값이 `recv.session_started == 1` · `partial/final == 0` ·
  `snapshotCounts` `[0,1,1]`로 **그 문서에 세션이 하나였음을 자기 증명**한다.
- **A2-1·A2-2의 무력화 실측(코드를 실제로 망가뜨려 FAIL을 관측)은 하지 않았다.** 판별력의 근거는
  §1-4의 **값이 실제로 갈렸다**는 관측이고, 앱 소스 변이는 이 회차의 범위가 아니다(§10 — 앱 소스를 고치지 않는다).
- **실물 Nova에서의 거동은 미확인이다.** 이 회차는 `stub_unresponsive` + CDP 주입이다.
- **`--foreground-muted`를 쓰는 다른 요소들**(`듣고 있어요...` 등)은 이 회차에서 재지 않았다 — C2의 대상이 아니다.

---

## 3. 이 회차가 새로 알아낸 함정

### H-후보 ① **배경 탭에서는 브라우저 회차가 성립하지 않는다** — `H-AE`와 증상이 같다

`Page.bringToFront` 없이 돌린 첫 시도가 `active` 도달에 실패했다(8초 시간초과). 그때 직접 읽은 계측 상태:

```
appHandlerAttached: false · socketUrls: [] · recv 전부 0
audioContextState: "suspended" · resumeLog[0].afterAwait: null   ← 영원히 pending
```

`resumeLog`가 **1건**(설치 시점의 `tryResume()`)뿐이라는 것이 결정적이다 — 계측의
`getUserMedia` 대체본이 `tryResume()`를 부르므로, 2건이 아니라는 것은 **`getUserMedia`가 호출되지 않았다**,
즉 `startSession`이 시작조차 안 했다는 뜻이다. **클릭이 페이지에 닿지 않았다.**

⚠️ **이 증상은 `H-AE`(합성 클릭이라 `context.resume()`이 pending)와 구별할 수 없게 닮았다.**
가르는 값은 `resumeLog` 길이와 `socketUrls`다: 배경 탭이면 `socketUrls`가 **비어 있고**,
`H-AE`면 소켓은 열린다. → 절차에 **`Page.bringToFront`를 넣고, user activation을 추론하지 말고
`navigator.userActivation.hasBeenActive`로 직접 단정한다**(스크립트가 그렇게 한다).

### H-후보 ② 플러그인 Chrome의 탭은 회차 사이에 사라진다

판정 회차와 partial 회차 사이에 `http://127.0.0.1:9222/json/list`가 **0건**이 됐다(Chrome 프로세스는 살아 있었다).
→ 실행체가 **없으면 `PUT /json/new`로 전용 탭을 만든다.** 남의 탭을 뒤지지 않는다.

### H-후보 ③ `--url-substring localhost:3000`은 `/results/<id>` 탭을 먼저 집는다

`measure_contrast.py`의 부분일치 그대로 쓰면 목록 앞에 있던 `/results/…` 탭을 잡아 **남의 화면을 하이재킹한다**
(실측: 그 탭이 첫 번째였다). → **정확 일치를 먼저 고른다.**

---

## 3-b. 2차 독립 회차 — 값이 전건 일치했다

실행체의 문자열 두 개(sha256 계산식·`학습 시작` 선별식)를 lint 때문에 줄바꿈했으므로 **읽는 것으로
끝내지 않고 다시 돌렸다.** 회차 `6b5bbcf0-01a9-4c00-beee-f639c80632f4` · `WINDOW_START` `2026-09-06 13:07:16.762834+00`.

| 항목 | 1차 | 2차 |
|---|---|---|
| light muted / fg | `rgb(89, 89, 89)` / `rgb(23, 23, 23)` | **동일** |
| dark muted / fg | `rgb(154, 154, 154)` / `rgb(237, 237, 237)` | **동일** |
| partial 색 == muted probe (두 모드) | true | **true** |
| 확정 색 == fg probe (두 모드) | true | **true** |
| 주입 전 접두 `<p>` / `사유:` `<p>` | 0 / 0 | **0 / 0** |
| `recv.session_started` · `partial` · `final` | 1 · 0 · 0 | **1 · 0 · 0** |
| `injected` · `snapshotCounts` | 2 · `[0,1,1]` | **2 · `[0,1,1]`** |
| 클릭→eval 반환 | 65 / 60 ms | **59 / 59 ms** |

**2차의 DB 3열**: `learning_sessions` 7 → 9 → **7** · `analysis_jobs` 34 → 36 → **34** ·
`utterances` **92** 불변 · `error_patterns` **7** 불변 · `session_plans`·`learner_notes` 세 시점 모두 **1** ·
drift 세 시점 모두 **0**. teardown: ①-a `INSERT 0 2` · ① `DELETE 2` · ② `UPDATE 0` · ③ `DELETE 0` ·
남은 회차 세션 **0**.

⚠️ **2차에서는 창 안 세션이 정확히 2건이었다** — §2의 미확정 2건이 재현되지 않았다. 그것이 원인을
확정해 주지는 않지만 **회차마다 생기는 것은 아니라는 사실**은 확정한다.

⚠️ **증거 파일의 소유 관계**: `.harness/evidence/c2-{light,dark}.png`와 `c2-render-hierarchy.json`은
**2차 회차가 덮어썼다**(값은 1차와 일치). `c2-{light,dark}-partial.png`와
`c2-render-hierarchy-partial.json`은 **1차의 partial 회차**가 소유한다.

---

## 4. 이 회차가 신설한 자산

`tests/harness/c2_render_hierarchy.py` — §6의 실행체. 지키는 것은 파일 머리주석이 소유한다.
**새 수단이 아니다**: `measure_contrast.py`와 같은 디버깅 포트 9222 + CDP over websocket이고,
모드 전환도 같은 `Emulation.setEmulatedMedia`다. 라운드트립이 밀리초라 §6 ⛔("전 과정을 한 `eval`에")를
지키면서 창(10 s)에 여유가 압도적으로 남는다(**0.65 %** 사용).

⚠️ **`--phase partial`은 판정용이 아니다** — partial 상태를 **눈으로 보기 위해** 그 지점에서 멈추는 회차다.
판정은 `--phase both`(기본)가 낸다.
