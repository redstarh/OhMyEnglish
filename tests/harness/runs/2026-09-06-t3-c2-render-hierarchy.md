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
  판정 회차 **4회 독립 일치**. 실행체 게이트가 **단정 56건을 검사해 전건 통과**(§3-c에서 그 게이트의
  판별력까지 관측했다 — 리뷰가 첫 판을 뚫었고 그 구멍을 닫은 결과다).

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
- **앱 소스를 망가뜨려 FAIL을 관측하지는 않았다** — §10이 그것을 금지한다(앱 소스를 고치지 않는다).
  ⚠️ **다만 §3-c에서 게이트 자체의 판별력은 관측했다**(무력화 19종 + red→green 2건 + 배선 양방향).
  가르는 말: **「앱이 어긋나면 이 게이트가 FAIL을 낸다」는 확인됐고, 「지금 앱이 그 어긋남을 갖고 있지
  않다」는 4회 회차의 관측이다.** 앱 변이 실측은 여전히 미실행이다.
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
→ 절차에 **`Page.bringToFront`를 넣고, user activation을 추론하지 말고
`navigator.userActivation.hasBeenActive`로 직접 단정한다**(스크립트가 그렇게 한다).

⛔ **이 자리에 있던 판별 문장은 반증됐다 — 지우지 않고 반례와 함께 남긴다**(2026-09-06 재검토 MEDIUM-B).
이전 서술: *"가르는 값은 `resumeLog` 길이와 `socketUrls`다: 배경 탭이면 `socketUrls`가 **비어 있고**,
`H-AE`면 소켓은 열린다."* **뒤쪽 절이 틀렸다.** 반례(같은 날 §3-d에서 팀리드가 직접 만들었다):
:8002를 내린 회차가 `socketUrls=[]`인데 `resumeLog` **2건** · `appHandlerAttached=true`였다 —
**클릭은 닿았고 소켓만 열리지 않았다.** `meta.socketUrls`는 **`send`가 불릴 때만** 채워지므로
「빈 것」은 「소켓 없음」이 아니라 **「전송 관측 없음」**이다.
→ **가르는 값은 `resumeLog` 길이 하나가 최상류다.** 4갈래 판별의 정본은 **`pitfalls.md` H-AH**이고
구현은 `c2_render_hierarchy.py:classify_failure`다(갈래마다 테스트가 박혀 있다).
⚠️ **이 문장이 정정 뒤에도 30분 넘게 남아 있었다** — `pitfalls.md`와 `browser_leg.md` §6은 고쳤는데
**증거의 소유자인 이 기록만 낡았다.** 재검토가 그것을 잡았다. 「본문을 고치고 그것을 설명하는 문장을
안 고친다」의 또 한 사례이고, **회차 기록도 그 대상이라는 것**이 새로 배운 것이다.

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

## 3-c. 독립 리뷰가 이 실행체를 뚫었다 — 두 지적을 수용해 게이트를 넣었다

**리뷰 결과(2026-09-06, code-reviewer 위임)**: HIGH **1건** · MEDIUM **1건**. 팀리드가 `grep`으로
**직접 대조해 둘 다 사실임을 확인**하고 수용했다(형식적 동의가 아니다).

| # | 무엇이 틀렸는가 | 어떤 입력에서 어긋나는가 |
|---|---|---|
| **HIGH-1** | `browser_leg.md` §5 A2-2의 **음성 대조 ②(probe 두 값이 서로 다름)가 코드에 없었다.** 값을 **인쇄만** 하고 `muted1`과 `fg1`을 비교하는 자리가 없었다(`grep -an muted1` → 108·421·425·451·452·453뿐). 유일한 확인은 **사람이 rgb 문자열을 눈으로 보는 수기 단계**였다(이 기록 §1-4) | `globals.css`에서 `--foreground-muted`와 `--foreground`가 **같은 값으로 회귀**하면 `partial.color == muted1` 참 · `final.color == fg1` 참 · **모드 간 차이도 그대로 참** → **인쇄되는 모든 불리언이 True인데 위계 계약은 사라진다.** A2-3은 이 경우를 못 잡는다(다크 블록 삭제와 다른 경우다) |
| **MEDIUM-1** | **§6-0의 "0이 아니면 그 회차는 ERROR"가 게이트가 아니라 출력이었다.** `prefixedCount`가 `102·139·184·417`에만 나오고 0과 비교되지 않았다. `recv.partial`·`recv.final`(주입 창의 「경쟁 프레임 0」 전제)도 기록만 됐다 | 실수로 `VOICE_ADAPTER=stub`에 대고 돌리면 실물 `partial` 프레임이 **같은 상태**를 덮어 측정이 조용히 무의미해진다 |

**고친 것**: 순수 함수 **`check_leg(d, phase)`·`check_cross(results)`** 를 넣고 `main_async` 끝에서
호출한다. 어긋나면 **비영 종료**다. 인쇄되던 모든 불리언이 이제 게이트다 + 공허 통과 방어(probe 값이
`rgb` 문자열인지) + 초과 렌더(`max(snapshotCounts) <= 1`) + 한 문서 한 세션(`recv.session_started == 1`)이
더해졌다.

### 게이트가 **판별력을 갖는지** 관측했다 — "게이트가 있다"는 지표가 아니다

**① 조건별 무력화** — `tests/harness/test_c2_gates.py`, **23 passed**(직접 실행).
입력은 **실물 회차 반환값**이고 그 위에 **한 필드씩** 변이를 얹어 *그 조건이* 어긋나는지 본다
(손으로 만든 픽스처는 데이터 생성 경로의 결함에 눈이 먼다 — `H-AF`가 그 형태였다). 변이 **19종**:
두 토큰 동일화 · 주입 전 접두 `<p>` 1개 · 대기문구 부재 · 창 이탈 3종 · probe 재판독 갈림 · probe 빈 문자열 ·
partial이 fg로 렌더 · partial 2개 · 확정이 muted로 렌더 · partial 잔존 · final 부재 · 경쟁 프레임 ·
세션 둘 · 핸들러 미부착 · 주입 수 부족 · 초과 렌더 · 적립 공백 · 모드 불일치.

**② red→green을 직접 관측했다.** 리뷰가 지목한 두 조건을 **메모리에서만** 제거해(파일 불변) 같은
무력화 입력을 넣었다:

| 조건 | 게이트 제거판 | 현재 판 |
|---|---|---|
| HIGH-1 (두 토큰 동일) | 그 조건 어긋남 **0건** → **통과시킨다** | **1건** — `A2-2 대조 ② 위반: muted 와 foreground 가 같은 값이다(rgb(89, 89, 89))` |
| MEDIUM-1 (주입 전 `<p>` 1개) | **0건** → **통과시킨다** | **1건** — `§6-0 위반: 주입 전 접두 <p>가 1개다` |

**③ 배선을 종단으로 쟀다** (단위만 재면 배선이 무보호로 남는다 — `H-AB`):
게이트가 든 판으로 실제 회차를 돌려 **`판정 (단정 56건 검사) · PASS · exit 0`**,
모드를 하나만 돌리면 **`A2-3 미평가` FAIL · exit 1**. 양방향을 다 봤다.

### 3·4차 회차 — 값은 1·2차와 같다

회차 `e3f3751a-fe98-4a42-b955-f7140f49da9b` · `WINDOW_START` `2026-09-06 13:28:39.999155+00`.
`--phase both` 2회 + `--schemes light` 1회(의도된 FAIL) + `--phase partial` 1회.
색 4개·개수·`recv`·`snapshotCounts`·주입 전 0 전부 **1·2차와 동일** → **판정 회차 4회 독립 일치**.
`--phase partial`도 **48건 검사 PASS**.

**3차의 DB 3열**: `learning_sessions` 7 → **15** → **7** · `analysis_jobs` 34 → **42** → **34** ·
`utterances` **92** 불변 · `error_patterns` **7** 불변 · `session_plans`·`learner_notes` 세 시점 모두 **1** ·
drift 세 시점 모두 **0**. teardown: ①-a `INSERT 0 8` · ① `DELETE 8` · ② `UPDATE 0` · ③ `DELETE 0` ·
남은 회차 세션 **0**. 백엔드는 `stub`으로 복원(`/health` ok).

⚠️ **§2의 미확정 항목이 재현됐다 — 그리고 이제 판정을 오염시킬 수 없다.** 스크립트 호출 7회에 세션
**8건**이 생겼다(1차 4회 → 6건 · 2차 2회 → 2건 · 3차 7회 → 8건). **여전히 방아쇠 미확정이고 매번은
아니다.** 다만 새 게이트가 `recv.session_started == 1`을 **문서마다** 단정하므로, 남는 세션이 측정
회차에 섞이면 **그 회차가 FAIL로 죽는다** — 오염이 조용히 통과하는 경로는 닫혔다.

⚠️ **추적 사본 6개를 게이트가 든 판의 회차로 갱신했다** — 커밋되는 증거가 최종 코드에서 나온 것이 되게.

---

## 3-d. 리뷰 나머지(MEDIUM 3건 · LOW 2건) — 전부 대조하고 수용했다

첫 리뷰의 잘린 뒷부분이 도착했다. **다섯 건 전부 `grep`·`sed`로 직접 확인했고 전부 사실이었다.**

| # | 무엇 | 고친 것 |
|---|---|---|
| **MEDIUM-2** | **§6이 금지한 부분일치 폴백이 코드에 남아 있었다.** 문서(§6)는 *정확일치 → 없으면 새 탭*인데 코드는 정확일치 → **부분일치** → 새 탭이었다. `--url-substring localhost:3000` 기본값으로 `/results/<id>` 탭을 잡아 그 위에서 `Page.navigate`로 지운다 — **이 회차가 함정으로 적은 바로 그 하이재킹이 폴백으로 살아 있었다.** docstring이 위험만 경고하고 폴백 존재는 밝히지 않아 읽는 사람에게 정반대 인상을 줬다 | **경로를 지웠다.** `find_target(port, exact)`로 서명을 줄이고 `--url-substring` 인자를 없앴다 |
| **MEDIUM-3** | **실패한 회차가 `H-AH` 판별에 필요한 데이터를 버렸다.** 가장 흔한 실패인 `active` 8초 시간초과는 `window.__omy`를 읽기 **전에** 종료하고 JSON 쓰기는 루프 뒤라 **아티팩트 0건**이었다. 이 회차의 원인 판정은 팀리드가 나중에 살아 있는 페이지를 손으로 들여다봐 겨우 얻었다 — **스크립트가 자기 진단을 재현하지 못했다** | `dump_failure`를 넣었다. 실패 시 계측 상태 + 화면을 `.harness/evidence/c2-<모드>-failure.{json,png}`에 남기고 요약을 예외 메시지에 붙인다 |
| **MEDIUM-4** | **§5가 A2-3의 음성 대조로 지목한 것이 판별력 0이었다.** *"같은 모드에서 두 번 읽으면 같은 값이다"* — 실행체가 그 두 번을 **같은 tick에** 읽으므로 **원리적으로 갈릴 수 없다.** A2-3의 PASS는 정당하지만 그 근거는 **문서가 이름 붙인 대조가 아니라 실행체의 게이트**였다 | §5 A2-3의 대조 칸을 정정했다 — 실제 대조는 ① **페이지가 보고한 스킴 == 요청**(다르면 회차를 죽인다) ② **단일 모드는 `미평가`이고 PASS가 아니다**. 두 번 읽기는 **진단으로** 강등하고 코드 주석도 함께 고쳤다 |
| **LOW-1** | **`3규약`이 어디에도 없는 라벨이었다.** `grep -arn '3규약'`이 **내 스크립트 두 줄만** 냈다. 게다가 개수가 원본에서 이미 틀렸다 — `H-AE`의 대응은 **4단계**다 | 인용을 실제 소유자(`browser_leg.md` §6 · `H-AE` 대응 ②)로 바꿨다 |
| **LOW-2** | **`§4-4` 인용이 틀렸다.** "한 문서에 세션 하나"는 §4-4(키 계약)가 아니라 **§5 A1-5**(`browser_leg.md:254`)와 `instrument.js:367`에 있다 | 세 곳의 인용을 고쳤다 |

### ⭐ 고치는 과정에서 **공허 통과를 실물로 관측했다** — 백엔드를 내린 회차

`dump_failure`의 실패 경로를 태우려고 **:8002를 완전히 내리고** 회차를 돌렸다. 결과가 결정적이다:

```
주입 전 접두 <p>: 0 · 사유 <p>: 0 · 대기문구: True
partial 줄 count=1 color=rgb(89, 89, 89) → muted 일치: True
확정   줄 count=1 color=rgb(23, 23, 23) → fg   일치: True · partial 문구 잔존: False
recv={'session_started': 0, ...}                          ← 서버 프레임이 0건이다
```

**색 단정 전건이 True다.** 주입은 앱 핸들러를 **직접** 부르므로 소켓과 무관하고, `active`도
`VoiceIo.start` 뒤에 서므로 백엔드 없이 도달한다. → **게이트가 없던 판이라면 백엔드가 아예 없는
회차가 초록으로 통과했다**(`main_async`가 무조건 0을 돌려줬다). 새 게이트가 잡았다:

```
FAIL  [light] 한 문서에 세션이 하나여야 한다: session_started=0
FAIL  A2-3 미평가: 모드가 ['light'] 하나뿐이다 — 판별력 미확인은 PASS 가 아니다(§10)
```

이것이 MEDIUM-1이 말한 위험의 **실물 표본**이다. 설계로 추론한 것이 아니라 관측했다.

### ⛔ 그 실험이 **내 새 판별 문구의 반례**도 만들었다 — 세 곳을 정정했다

`dump_failure`를 그 상태에서 돌리니 `socketUrls=[]`인데 **`resumeLog` 2건 · `appHandlerAttached=True`**
였다 — **클릭은 정상으로 닿았고 소켓만 열리지 않았다.** 그런데 첫 판의 판별 문구는
*"`socketUrls`가 비었다 → H-AH(배경 탭)"*라고 **틀린 답**을 냈다.
원인: `meta.socketUrls`는 **`send`가 불릴 때만** 채워지므로 소켓이 열려 있어도 빈다.

→ **가장 상류의 지표는 `resumeLog` 길이다**(계측의 `getUserMedia` 대체본이 호출마다 `tryResume()`를
부른다). 4갈래로 갈라 `classify_failure`로 구현하고 **`pitfalls.md` H-AH의 판별표와
`browser_leg.md` §6의 「가르는 값」 문장을 함께 고쳤다**(세 곳이 같은 말을 하도록).
정정 후 같은 상태에서 다시 돌리니 **`백엔드가 없거나 연결이 실패했다`**로 옳게 갈랐다.

⚠️ **이 정정은 첫 판을 쓴 지 30분 안에 났다** — 그 판별표는 **관측 1건에서 일반화한 것**이었고
두 번째 관측이 바로 반증했다. 표본 1건으로 판별표를 쓰지 않는다.

### 5차 회차 — 바뀐 코드로 종단 확인

회차 `c50f335f-c7e2-4796-ac04-c319e5db6df9` · `WINDOW_START` `2026-09-06 13:42:51.480148+00`.
**`판정 (단정 56건 검사) · PASS · exit 0`** — `find_target` 새 서명, `dump_failure` 배선,
정정된 주석 전부를 실은 판이다. DB 3열: `learning_sessions` 7 → **9** → **7** ·
`analysis_jobs` 34 → **36** → **34** · `utterances` **92** 불변 · 보존 2표 세 시점 모두 **1** · drift **0**.
teardown ①-a `INSERT 0 2` · ① `DELETE 2` · ②③ `0` · 남은 회차 세션 **0**. 백엔드 `stub` 복원(`/health` ok).
⚠️ **이 회차는 세션이 정확히 2건이었다** — §2·§3-c의 미확정 항목이 또 재현되지 않았다.

⚠️ **`dump_failure`의 검증 범위를 정확히 적는다**: 함수 본체(eval · 파일 쓰기 · 요약 포맷 ·
`classify_failure`)는 **살아 있는 페이지에 직접 호출해 2회 태웠다**(`c2-selftest*-failure.json`).
**`except SystemExit` 래퍼 3줄이 실제 앱 실패에서 발동하는 것은 관측하지 못했다** — 백엔드를 내려도
`active`에 도달해 그 경로를 밟지 않았기 때문이다. 그 3줄은 **코드 읽기로만 확인했다.**

---

## 3-e. 재검토 2차 — MEDIUM 6건 · LOW 6건. **전부 대조하고 수용했다**

리뷰어가 재검토에서 **게이트 조건 수를 독립적으로 셌다**(레그당 `need()` **27** × 2 + `check_cross` 2 =
**56**, partial은 23×2+2=**48**) — 내 실행체 출력과 일치한다. 나도 다시 세서 같은 값을 얻었다.
그리고 **자기 변이 10종을 만들어 전부 CAUGHT**을 확인했다(특히 `None == None`으로 등호가 공허하게
참이 되는 두 조합이 rgb 가드에 먼저 걸린다).

| # | 무엇 | 대조 결과 · 고친 것 |
|---|---|---|
| **③ 판별력 미관측 8건** | 27개 조건 중 **19개만** 변이로 덮여 있었다. 게이트는 나머지도 잡지만 **테스트가 안 본다.** 대칭 논거로 넘길 수 없는 둘: **`final["count"] == 1`**(`partial["count"]`와 **다른 코드 경로**) · **`partial.color` rgb 가드**(이 커밋이 새로 넣은 방어인데 형제만 덮였다) | 8건 + 공허 등호 조합 2건을 변이로 추가 → **변이 29종**. 리뷰어의 열거 기준으로 **27/27 관측**이 됐다(그 27↔라벨 매핑은 리뷰어의 것이고 내가 독립 재유도하지는 않았다 — 27이라는 수와 8건 각각의 변이 통과는 직접 확인했다) |
| **① `classify_failure` 갈래 2의 의미가 틀렸다** | **사실이다.** `page.tsx` 순서를 직접 읽었다: `:177 getUserMedia` → `:185 new SessionSocket` → `:205 await VoiceIo.start` → `:218 setState("active")`. 그리고 `ws.ts:70`이 **생성자에서** `onmessage`를 붙인다 → `VoiceIo.start` 실패는 `appHandlerAttached=true`를 남기므로 **그 갈래에 도달할 수 없다** | 문구를 실제 구간(`:177`~`:185` = `getUserMedia` 거부 경로)으로 고치고, **계측이 `getUserMedia`를 대체하므로 정상 회차에서는 거의 도달하지 않는다**는 사실을 함께 적었다. **회귀 방지 테스트**를 박았다(`VoiceIo.start` 문구가 되살아나면 red) |
| **① 창 이탈 갈래 누락** | **사실이다.** `session_started==1`인데 `session_failed>=1`이면 창을 넘긴 것이고 §6이 이름 붙이고 처방까지 정한 **유일한 실패**인데(FAIL이 아니라 ERROR + 재시도) 갈래 4로 떨어졌다 | `recv.session_failed >= 1` 갈래를 3·4 사이에 넣었다. **`session_started >= 2`(한 문서 두 세션) 갈래도** 함께 넣었다 |
| **② `BaseException`이 과하다** | **사실이다.** `asyncio.CancelledError`는 3.8+에서 `BaseException`이라 **협조적 취소를 삼켜 문자열로 바꾼다**. `KeyboardInterrupt`도 삼킨다 | `except (Exception, SystemExit)`로 좁혔다. 원래 예외를 가리지 않는다는 판정(문자열 보존 + `from exc`)은 그대로 유효하다 |
| **② `Cdp.call` 무타임아웃** | 소켓이 **열린 채 무응답**이면 진단이 영구히 매달린다 — 하필 페이지가 굳은 실패 경로에서 도는 코드다 | 진단 `eval`과 스크린샷을 `asyncio.wait_for(..., DIAG_TIMEOUT_S)`로 감쌌다. `Cdp.call` 전반의 무타임아웃은 **기존 결함으로 남긴다**(이 회차 범위 밖) |
| **MEDIUM-A** | **§10의 3번째 갈래가 반증된 추론을 그대로 들고 있었다** — *"`socketUrls`가 비어 있다 → 그때만 후킹 고장 = ERROR"*. 내 반례가 정확히 그것을 반증한다 | §10-3을 ⛔로 정정했다. ⚠️ **1번 갈래는 유효하다**(비어 있지 **않으면** 후킹은 살아 있다 — 한쪽 방향만 성립) |
| **MEDIUM-B** | **이 기록 §3(H-후보 ①)에 반증된 문장이 남아 있었다.** `pitfalls.md`와 `browser_leg.md`는 고쳤는데 **증거의 소유자만 낡았다** | 지우지 않고 **반례와 함께 반증 표시**를 했다(§3 참조). **회차 기록도 「함께 고쳐야 하는 문장」의 대상**이라는 것이 새로 배운 것이다 |
| **MEDIUM-C** | `classify_failure`는 **분기 4개·테스트 0개**이고 **첫 판이 실제로 틀렸던 함수**다 | 갈래 **7종** 픽스처 + 배타성 + 회귀 방지 = 테스트 **9건** 추가. 순서를 바꾸면 red 다 |
| **MEDIUM-D** | **§6 문단이 접합됐다** — 삽입한 게이트-테스트 블록 뒤에 기존 실행체 주장(`새 수단이 아니다` … `판정은 --phase both가 낸다`)이 붙어 **실행체 이야기가 테스트 문단 안에** 있었다 | 실행체 주장을 실행체 문단으로 되돌리고 테스트 문단을 pytest 결과에서 끊었다 |
| **LOW** (6건) | 머리주석이 규약 소유자로 지목됐는데 **게이트 규약이 없었다** · `--phase partial`도 이제 판정을 내는데 문서는 "판정에 쓰지 않는다" · `check_cross`가 **세 번째 모드 이후를 조용히 버린다** · §5 A2-1·A2-2 대조가 "생략한 회차"라 적는데 실제는 **같은 회차의 주입 전 시점** · **매직넘버**(JS `8000`/`3000`/`16`, Python 대기값) · **`Page.navigate`의 `errorText` 미확인** | 전부 고쳤다. 상수에 이름을 줬고(`ACTIVE_TIMEOUT_MS` 등 — ⚠️ 그 값은 `H-AH`가 진단 signature로 인용하니 바꿀 때 그 문장도 함께 고친다), 치환을 `measure_js()` 한 곳으로 모았고, 3모드 이상은 **버리지 않고 어긋남으로 올린다**, `errorText`는 이름 있는 실패로 죽인다 |

### 재검토 반영 후 종단 재확인 (회차 `3c8bcda5-a19b-40f9-a8cf-aeee46acf304`)

- 게이트 테스트 **23 → 42 passed**(변이 29 + `classify_failure` 9 + 나머지 4).
- 실행체 종단: `WINDOW_START` `2026-09-06 14:58:45.698936+00` → **`판정 (단정 56건 검사) · PASS · exit 0`**.
- **새 `errorText` 가드를 실제로 발동시켰다** — 프론트를 죽이지 않고 닿을 수 없는 URL로 쟀다:
  `--url http://localhost:9/` → `이동하지 못했다: net::ERR_UNSAFE_PORT — 프론트(:3000)가 떠 있나?` · **exit 1**.
- `measure_js()`가 치환자를 남기지 않는 것을 직접 확인(남은 치환자 **0개** · 길이 5280).
- DB 3열: `learning_sessions` 12 → **14** → **12** · `analysis_jobs` 45 → 47 → **45** ·
  `utterances`·`error_patterns`·`error_occurrences` **불변**(114·8·18) · drift **0** ·
  **§9 보존 5건 전부 생존**(직접 확인). 백엔드 `stub`·`WORKER_ENABLED=false` 복원.

⚠️ **여전히 미관측으로 남는 것**: `dump_failure`의 `except SystemExit` 래퍼가 **실제 앱 실패에서**
발동하는 것(§3-d와 같다 — 백엔드를 내려도 `active`에 도달한다). `classify_failure`는 이제 갈래마다
테스트가 있지만 **그 래퍼가 그것을 부르는 경로**는 여전히 코드 읽기로만 확인했다.

---

## 3-f. C2 재검토 결론과 그 뒤에 닫은 것

**리뷰 결론: `CHANGES REQUESTED`**(CRITICAL·HIGH 없음). 차단 사유 3건 — `classify_failure` 갈래 2
오귀속 · 창 이탈 갈래 누락 · MEDIUM-A(§10에 반증된 전제) · MEDIUM-B(이 기록에 반증된 문장). ⚠️ **리뷰는
`1157aa8`을 봤고 그 세 건은 `09337e1`에서 이미 고쳤다** — 재검토 대상은 그 커밋이다.

리뷰어가 독립 측정한 것(내 수치와 일치): 게이트 테스트 **23 passed** · 자기 변이 **10/10 CAUGHT** ·
`ruff` rc=0(**게이트 cwd에서** — 리포 루트에서 재다가 `H-A`를 밟고 스스로 정정했다) · 56건 산식.

### 그 뒤에 닫은 것 2건

**① `find_target` 우선순위 테스트** — 리뷰가 1차부터 요구했고(T0 판정: "요구한 둘 중 하나는 아직
없다") 이제 있다. **MEDIUM-2가 났던 자리**를 고정한다: 목록 **앞**에 `/results/<id>` 탭이 있어도 정확
일치를 고른다 · `type != page`는 무시 · 정확 일치가 없으면 **부분일치로 떨어지지 않고 새 탭을 만든다** ·
탭 생성이 소켓을 안 주면 이름 있는 실패로 죽는다. `urlopen`을 가로채 4건. → 게이트 테스트 **46 passed**.

**② `dump_failure`의 `except SystemExit` 래퍼를 실제로 발동시켰다 — §3-d의 마지막 미관측이 닫혔다.**
리뷰어가 처방한 수단을 그대로 썼다: `ACTIVE_TIMEOUT_MS`를 **메모리에서만** 1 ms로 낮춰 한 회차.
결과(예외 메시지 전문에서):

```
페이지 예외: Error: 시간초과(3000ms): partial 줄 렌더
실패 진단 (클릭 후 3032ms) — H-AH/H-AE 판별용:
  → .harness/evidence/c2-light-failure.json · .harness/evidence/c2-light-failure.png
  socketUrls=['ws://localhost:3000/_next/hmr?...'] · resumeLog 2건 · appHandlerAttached=True
  recv={'session_started': 1, 'partial': 6, 'final': 6, 'audio': 3, 'session_ended': 1, ...}
```

**래퍼가 발동해 진단 파일 2개를 쓰고 `classify_failure`가 돌았다.** 코드 읽기가 아니라 관측이다.

### ⭐ 그 실험이 **갈래 하나를 더 요구했다** — 그리고 그것을 넣었다

위 덤프의 `session_ended: 1`을 보라. 백엔드가 `stub`(비-unresponsive)이라 세션이 **22 ms에 정상
종료**하고 앱이 결과 화면으로 이동해 **전사문 컨테이너가 사라졌다.** 그런데 판별은
*"`H-AE`나 세션 길이 쪽을 본다"*로 떨어졌다 — **원인은 어댑터 모드를 잘못 골랐다는 것**이고 처방이
전혀 다르다. → **`recv.session_ended >= 1` 갈래를 추가**하고 테스트를 박았다.
**리뷰가 지적한 「창 이탈 갈래 누락」과 같은 부류**이고, 그것을 고치려고 만든 실험이 **대칭인 나머지
한쪽**을 드러냈다.

---

## 4. 이 회차가 신설한 자산

`tests/harness/c2_render_hierarchy.py` — §6의 실행체. 지키는 것은 파일 머리주석이 소유한다.
**새 수단이 아니다**: `measure_contrast.py`와 같은 디버깅 포트 9222 + CDP over websocket이고,
모드 전환도 같은 `Emulation.setEmulatedMedia`다. 라운드트립이 밀리초라 §6 ⛔("전 과정을 한 `eval`에")를
지키면서 창(10 s)에 여유가 압도적으로 남는다(**0.65 %** 사용).

⚠️ **`--phase partial`은 판정용이 아니다** — partial 상태를 **눈으로 보기 위해** 그 지점에서 멈추는 회차다.
판정은 `--phase both`(기본)가 낸다.

`tests/harness/test_c2_gates.py` — **게이트의 판별력을 재는 테스트**(리뷰 뒤 신설, 23 passed).
✅ **게이트 안이다** — `app/backend/pyproject.toml:33`의 `testpaths = ["../../tests"]`가 리포의 `tests/`를
가리키므로 `.venv/bin/pytest -q`가 수집한다. **게이트 수치가 595 → 618 passed로 뛴 것이 그 증거다.**

⛔ **여기서 내가 한 번 틀렸고 데이터가 잡았다 — 남겨 둔다.** 이 파일과 §6, 테스트 머리주석에
**"게이트 밖이라 문서 규약으로 지킨다"**고 적었다. 근거는 "pytest는 rootdir 밖을 수집하지 않는다"는
**추론이었고 확인하지 않았다.** 게이트를 돌렸더니 618이 나와 반증됐다(정확히 23건 증가).
**교훈은 이 리포의 지배 실패 모드와 같은 형태다**: 검사 결과를 추론으로 설명하면 그 설명이 틀려도
검사는 초록이다. **없는 위험을 관리한다고 적으면 다음 세션이 진짜 위험을 놓친다.**

**절차 문서에 박은 것**(§6): 실행체 지목 · `Page.bringToFront` 필수 · 탭은 정확일치 우선/없으면 신설 ·
**인쇄하는 모든 불리언은 게이트여야 한다** · 게이트 테스트가 게이트 안이라는 사실.
**§7에 박은 것**: `en_coach` 스키마 존재를 `information_schema.schemata`로 확인하면 **거짓 「없다」**가
나온다(그 뷰는 소유 스키마만 보인다) → `pg_namespace`로 묻는다.
