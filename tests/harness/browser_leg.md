# 브라우저 레그 (C계층) — 절차 정본

> 계획서 `docs/design/2026-09-05-frontend-test-agent-plan.md`의 **T1 산출물**. 시나리오 C1~C5의 판정은 여기 적힌 단정만으로 한다.
>
> **자기완결이다.** DB 접근·teardown·프리플라이트를 `tests/harness/README.md`나 `docs/ops/2026-08-26-test-harness.html`에 **위임하지 않는다** — 그 두 문서는 dev DB가 podman `:5433`에서 homebrew `postgresql@17`(:5432)로 이관된 뒤에도 `podman exec` 명령을 들고 있어(함정 H-T) 따라가면 앱이 보는 DB가 아닌 곳을 건드린다. 그 문서들의 정정은 계획서 T7이 소유하고 **이 문서는 그 수정에 의존하지 않는다.**
>
> 프론트엔드에는 테스트 러너가 0개이고 선언된 게이트(`npx tsc --noEmit` · `npx eslint app lib`)는 **렌더 결과를 재지 않는다.** 이 레그가 그 공백을 브라우저로 직접 관측해 메운다. **게이트가 아니다** — `app/frontend/**`를 바꾼 태스크의 9단계에서 프론트 게이트가 exit 0인 것을 먼저 확인한 뒤 부르고, 결과는 게이트 수치와 **별도 항목**으로 보고한다.

## §1. 계측 대조 규칙 — 이 문서가 낡지 않게 하는 유일한 수단

> `app/frontend/**`의 **렌더·색·오디오 경로**를 바꾼 태스크는, 이 문서의 단정 중 **그 경로를 재는 단정을 함께 갱신**해야 완료다. 갱신하지 않으면 다음 회차가 거짓 초록을 낸다.

게이트로는 이 부패를 잡지 못한다 — **계측이 낡으면 초록으로 낡는다.** 실측 선례: `runs/2026-08-26-run-1.md`가 C1~C4 전건 PASS를 내면서 `F-1 · HIGH`(다크모드에서 확정 전사문 대비 1.05:1)를 잡아냈고, **그 F-1의 지시된 수정**(하드코딩 색 → CSS 토큰)이 run-1의 C2 단정(`#999` 문단 개수)을 무효로 만들었다. 지금 그 단정을 그대로 돌리면 개수는 **항상 0 → 자동 통과**다. 감지가 실패한 것이 아니라 **수정과 계측을 함께 옮기는 일**이 실패했다.

## §2. 프리플라이트 — 전부 직접 돌려 출력을 읽는다

하나라도 어긋나면 **단정 평가로 넘어가지 않는다.** 「관측」은 T1 작성 시점에 작성자가 직접 돌린 출력이다.

| # | 명령 | 통과 조건 | 관측 (2026-09-06) |
|---|---|---|---|
| P1 | `curl -s http://localhost:8002/health` | `{"status":"ok"}` — **`version` 키가 있으면 StockAgent다. 즉시 멈춘다** | `{"status":"ok"}` (`version` 없음) |
| P2 | `cat app/frontend/.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:8002` | 일치 |
| P3 | `git check-ignore -v app/frontend/.env.local` | 무시됨을 확인한다 — **P2가 없는 머신에서는 폴백이 `http://localhost:8000`이고 그것은 StockAgent다**(`lib/config.ts:API_BASE`). 조용히 남의 앱을 검증한다 | `app/frontend/.gitignore:34:.env*` |
| P4 | `brew services list \| grep postgresql` | `postgresql@17  started` | `postgresql@17 started` |
| P5 | `ps -o lstart= -p $(lsof -nP -iTCP:8002 -sTCP:LISTEN -t)` → `find app/backend/app -name '*.py' -newermt '<그 시각>'` | **결과가 비어야 한다.** 백엔드는 `--reload` 없이 뜨므로 소스가 프로세스보다 새로우면 갱신되지 않는다 | 회차마다 다시 잰다 |
| P6 | `curl -s localhost:3000 -o /dev/null -w '%{http_code}'` | `200` | 회차마다 다시 잰다 |
| P7 | `grep -c 'superpowers-chrome' .claude/settings.local.json` | `2` 이상 (`Skill(superpowers-chrome:browsing)` + `mcp__…chrome__use_browser`) | `2` |
| P8 | `ps aux \| grep -c '[p]ytest'` | `0` — 테스트 DB가 실행마다 DROP/CREATE되는 공유 자원이다 (함정 H-X) | 회차마다 다시 잰다 |
| P9 | §7의 DSN 확인 명령 | `ohmyenglish` | `ohmyenglish` |

⚠️ **설정 파일을 고치지 않는다.** P7이 실패하면 `.claude/settings*.json`·`.mcp.json`을 **편집하지 말고** 무엇이 없는지 적어 **"캡틴 몫"으로 보고하고 멈춘다.** 권한 설정은 사용자 소유다.

**기동 순서**(L4): DB(:5432) → 백엔드(:8002) → 프론트(:3000) → 브라우저. CORS가 `http://localhost:3000` 하드코딩이라 **두 번째 프론트를 :3001에 띄울 수 없다.** 플래그(`VOICE_ADAPTER` 등)는 **`app/backend/.env`를 고치지 않고 환경변수로만** 넘긴다 — 복구를 잊으면 영구화된다.

```bash
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning   # --reload 없음
cd app/frontend && npm run dev                                                          # :3000
```

## §3. 회차를 연다 — `.harness/browser_run_id.txt`

계획서 §13-4 미결(회차를 열 것인가)을 **여기서 닫는다: 연다.** 근거 둘 — ① §8의 복원 SQL이 `run_id`로 범위를 좁힌다. 회차 없이 돌면 "최근 세션"을 DB에서 추정해야 하고 그러면 캡틴이 같은 시각에 만든 세션을 지울 수 있다. ② `harness_sessions`는 "무엇을 지웠는지"의 감사 기록이다.

⚠️ **`.harness/run_id.txt`를 덮지 않는다** — `ws_session.py`가 **import 시점에** 그 파일을 읽으므로 다른 세션의 진행 중 회차 포인터를 하이재킹한다(작성 시점에 그 파일이 실재한다). 브라우저 레그는 **별도 파일** `.harness/browser_run_id.txt`를 쓴다. 새 수단이 아니라 파일명 하나다.

```bash
cd app/backend && .venv/bin/python -c "
import sys; sys.path.insert(0,'../../tests/harness')
from psql_cli import psql
print(psql(\"insert into harness_runs (git_commit, note) values ('$(git rev-parse --short HEAD)','browser-leg') returning id\"))
" | tr -d ' \n' > ../../.harness/browser_run_id.txt
```

이 파일에 **개행이나 psql 부산물이 섞이면 안 된다** — 값이 SQL에 그대로 들어간다(1회차에서 `INSERT01`이 섞여 세션 하나가 미등록으로 남았다). **브라우저 레그에는 세션 자동 등록 훅이 없다**(세션을 만드는 주체가 브라우저다) → **teardown 직전에 시간창 스윕으로 등록한다**(§8 ①-a).

## §4. 계측 자기검사 — 조용히 퇴화하면 시끄럽게 죽인다

계측 스크립트(`tests/harness/instrument.js`, 계획서 T2 산출물)는 아래를 만족해야 하고 하나라도 어긋나면 **ERROR로 끝낸다. 단정 평가로 넘어가지 않는다.**

1. `eval` 반환값이 정확히 `'instrumented'`다.
2. 후킹 대상의 **존재를 먼저 단정**하고 없으면 throw한다. 조용히 건너뛰면 계수가 0이 되고 **0은 "고장"과 구별되지 않는다.**
3. ⚠️ 두 대상은 **형태가 달라 같은 방식으로 단정할 수 없다.** `WebSocket`의 `onmessage`는 **접근자 프로퍼티**라 `Object.getOwnPropertyDescriptor(WebSocket.prototype,'onmessage')`가 `get`/`set`을 준다. `createBufferSource`는 **메서드**이고 명세상 `BaseAudioContext`에 있어 `AudioContext.prototype`에서는 **`undefined`일 것으로 본다** — **어느 쪽이 이 Chrome에서 성립하는지는 T2에서 실측해 확정한다**(§11-2). 여기서 정답을 단정하지 않는다.
4. `window.__omy`가 없거나 `recv`에 기대 키가 빠져 있으면 **PASS를 낼 수 없다.**

**계수 지점은 `createBufferSource`다** — `lib/audio.ts:enqueueAudio`가 `:167`에서 `sampleCount === 0`을 early-return한 뒤 `:175`에서 프레임당 **정확히 한 번** 부른다(직접 읽어 확인). `window.Audio`를 세는 run-1 방식은 **항상 0**이다: `lib/audio.ts` 모듈 docstring 제목이 "왜 `MediaRecorder`와 `new Audio()`를 쓰지 않는가"이고 재생은 `VoiceIo.enqueueAudio`가 한다.

## §5. 단정 표 — 기대값의 유도 방식과 음성 대조

**유도 방식**: ⓐ 픽스처에서 **연역** · ⓑ 런타임에 토큰/API에서 **유도** · ⓒ 그 둘이 불가능(이유를 적는다). ⚠️ **"코드 인용이 붙어 있다"는 기준이 아니다** — 하드코딩된 `#595959`도 `globals.css` 인용을 가질 수 있고 그러면 **인용이 붙은 채로 썩는다.**

**ⓐ의 근거**: `app/backend/app/audio_gateway/fixtures.py:FIXTURE_TURNS`는 **3턴**이고 세 응답 모두 **7 단어**다. `stub.py:_partial_prefixes`가 `sorted({max(1,7//3), max(1,2*7//3)})` = `{2,4}` → **턴당 partial 2개**. `stub.py:StubVoiceAdapter.events`가 턴마다 `agent final → user partial ×2 → user final → TONE_WAV_FRAME`을 낸다. **픽스처가 바뀌지 않는 한 다른 값이 나올 수 없다** — 관측에서 귀납한 값이 아니다. run-1이 같은 값을 적은 것은 **보강 정황이지 독립 확증이 아니다**(그 기록이 스스로 작성자=검증자임을 적었다). `>=`를 쓰지 않고 **등호로 조인다** — `>=`는 프레임이 중복 도달해도 통과한다.

### C1 — 세션 관통 (`VOICE_ADAPTER=stub`)

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A1-0 | idle 화면 추천 이유 줄 | 접두 `오늘 이걸 연습해요:`(`page.tsx:NEXT_PLAN_PREFIX`)를 가진 `<p>` 개수 == `GET /api/sessions/next-plan`의 `reason`이 null이면 0, 아니면 1 — **ⓑ API에서 유도**(화면의 상류라 순환이 아니다) | **학습 시작 클릭 후 그 `<p>`가 0개다** — `page.tsx:271`이 `state === "idle"`로 가둔다. 사라지지 않으면 이 요소가 계획 표시라는 전제가 무효다 (상태 전이) |
| A1-1 | `recv.final` | **6** = 3턴 × (agent 1 + user 1) — ⓐ | `VOICE_ADAPTER=stub_unresponsive` → **0** (환경변수) |
| A1-2 | `recv.partial` | **6** = 3턴 × 2 — ⓐ | 같은 대조 → **0** (환경변수) |
| A1-3 | `recv.audio` | **3** = 3턴 × `TONE_WAV_FRAME` 1 — ⓐ | 같은 대조 → **0** (환경변수) |
| A1-4 | 재생 예약(`createBufferSource` 호출 수) | **3** — ⓐ. `enqueueAudio`가 프레임당 1회(`audio.ts:175`) | 같은 대조 → **0** (환경변수) |
| A1-5 | 확정 줄 수 | 접두 `질문: `/`답변: `를 가진 `<p>` **6개** — ⓐ. I-8 병합(`page.tsx:123`)은 **연속 동일 화자**에만 걸리고 픽스처는 교대하므로 병합 0회 | **주입·세션 전 idle 화면에서 그 `<p>`가 0개다** (계측 생략) |
| A1-6 | 결과 화면 이동 | URL이 `/results/<session_id>` — **ⓑ `session_started` 프레임의 `session_id`를 계측이 기록해 대조** | `stub_unresponsive` → URL이 `/`에 남고 `사유: voice_adapter_connect_timeout`이 뜬다 (환경변수) |
| A1-7 | 마이크 합성 → WS 송신 | `sent > 0` — ⓑ 계측이 `sendAudio` 호출을 계수 | ⚠️ **T2에서 확정한다**(§11-4). 후보 ① 계측 생략 → `microphone_permission_denied` ② 합성 스트림을 **무음**으로 → `sent === 0`. headless Chrome이 가짜 장치로 `getUserMedia`를 성공시키면 ①은 FAIL을 못 낸다 → **둘 다 FAIL을 못 내면 A1-7을 채택하지 않는다** |
| A1-8 | DB 전사문 행 수 | `utterances` **6행** — ⓐ (final 6건. partial은 저장되지 않는다) | `stub_unresponsive` 세션의 `utterances` **0행** (환경변수) |

### C2 — 렌더 위계 (측정 절차는 §6. **라이트·다크 두 모드 필수**)

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A2-1 | partial 줄은 muted | 접두 `<p>` 1개 + 그 `getComputedStyle(...).color` == **probe 유도 muted 값** — ⓑ | **주입을 아예 생략한 회차에서 접두 `<p>`가 0개**(§6-0). 이것이 없으면 주입이 조용히 실패해도(`ws.ts:isServerEvent` 게이트가 프레임을 거르거나 `ws.ts:74`의 `catch`가 파싱 실패를 삼키는 경로) 측정과 대조가 **둘 다** 통과한다 (주입 생략) |
| A2-2 | 확정 줄은 foreground | partial 줄이 사라지고(`setPartialLine(null)`) 접두 `<p>` 1개의 색 == **probe 유도 foreground 값** — ⓑ | ① 위와 같은 주입 생략 ② **probe 두 값이 실제로 서로 다름** — 같으면 위계 단정이 무의미하게 통과한다 (probe 비교) |
| A2-3 | 토큰이 모드별로 다르다 | 라이트의 muted 유도값 ≠ 다크의 muted 유도값 — ⓑ | **같은 모드에서 두 번 읽으면 같은 값이다** — 다르면 `Emulation.setEmulatedMedia`가 실제로 걸리지 않았다는 증거 (모드 전환 생략) |

### C3 결과 화면 · C4 교정 카드 · C5 발음 배지

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A3-1 | 5상태 라벨 | `분석 중`·`확정`·`부분 실패`·`연결 실패`·`분석 대상 없음`(`results/[sessionId]/page.tsx:STATUS_LABEL`) 중 **해당 1건만** 보인다 — **ⓒ 하드코딩**: 라벨은 화면이 소유하는 한국어 문구이고 API는 기계값(`status`)만 준다 → 상류에 같은 문자열이 없어 유도 경로가 없다. ⚠️ 항진명제 아님을 확인했다 — 다섯 문자열의 프론트 내 다른 출현은 **전부 주석**이다(`app/page.tsx:69`·`:305`, `lib/api.ts:4`) | **나머지 4개 라벨이 동시에 보이지 않는다.** `results/[sessionId]/page.tsx:141`이 `STATUS_LABEL[status]`를 한 번만 렌더하므로 둘 이상 보이면 이 단정은 무의미하다 (다른 4상태 세션 재방문) |
| A3-2 | 없는 세션 | 존재하지 않는 uuid로 방문하면 **5개 라벨 전부 부재** + 오류 문구 — ⓑ | 실제 세션 방문 시 그 오류 문구가 **부재**해야 한다 (URL 조작 · 상호 대조) |
| A4-1 | 교정 카드 구조 | 접두 `원문:`·`교정문:`를 가진 `<p>`가 **각 N개**, N = `GET /api/sessions/{id}/results`의 `corrections.length` — **ⓑ API에서 유도**(상류라 순환이 아니다). 라벨 없는 셋째 줄이 **비어 있지 않다** | `corrections`가 빈 세션(`no_utterances`)에서 두 접두가 **0개** (세션 재방문) |
| A4-2 | 이유 문구 관통 | API `corrections[i].reason` 문자열이 DOM에 있다 — ⓑ. ⚠️ **대조 전에 `reason`이 빈 문자열이 아님을 단정한다** — 빈 문자열은 어떤 DOM에도 "있다"로 나온다. 비었으면 FAIL이 아니라 **BLOCKED**(모델이 안 채운 것이지 화면 결함이 아니다) | `reason`에 sentinel을 덧붙인 변형 문자열이 DOM에 **없어야** 한다 — 포함 검사가 항상 참을 내지 않음을 증명한다 (문자열 변형) |
| A5-1 | 배지 4 outcome | `pending`·`correct`·`incorrect`·`unclear`를 각각 주입 → `app/page.tsx:PRONUNCIATION_BADGE`의 문구 4종 — **ⓒ 하드코딩**: 프레임은 기계값 `outcome`만 나르고 문구는 화면 상수다. ⚠️ 세 문구는 `/results/*`의 `OUTCOME_LABEL`에도 있다 → **세션 화면(`/`) 스냅샷에서만** 재고 결과 화면 스냅샷으로 재지 않는다 | **주입하지 않으면 배지 요소가 DOM에 부재**(`app/page.tsx:328`의 `{pronunciation && …}`) (주입 생략) |
| A5-2 | `target_sound` 미렌더 | 주입한 `target_sound`에 **sentinel 값**을 넣고 DOM 전체에서 **0건** — ⓑ 런타임 유도(설계서 §10 미결 4) | **같은 프레임의 `outcome` 문구는 있어야 한다**(A5-1) — DOM 검색 자체가 동작함을 증명한다. 둘 다 0이면 주입이 실패한 것이다 (동일 프레임 대조) |

## §6. C2 측정 절차 — 타이밍에서 떼어낸다

run-1의 스로틀 스크립트는 **회수 불가로 확정**됐다(지목된 CDP 캐시 세션이 존재하지 않고 전체 캐시에 `__omy` 0건). 스텁 `events()`에 지연을 넣지 않는다 — ① 생산 코드에 테스트 전용 경로 ② D계층 통합 테스트가 스텁 타이밍에 의존 ③ `sleep`이 모든 백엔드 테스트를 느리게 한다. 검증하려는 규칙("partial은 muted, final은 foreground")은 **시간의 함수가 아니다**:

0. **주입 전에 센다** — 접두 `<p>`가 **0개**임을 확인한다. 0이 아니면 그 회차는 **ERROR**다(측정으로 넘어가지 않는다). 이것이 A2-1·A2-2의 음성 대조다.
1. `partial` 프레임만 주입 → 접두 `<p>`가 **1개**로 늘었음을 확인하고 `getComputedStyle(...).color`를 읽는다.
2. `final` 프레임 주입 → 다시 읽는다. partial 줄이 사라졌는지와 확정 줄의 색을 함께 단정한다.

**대상 요소를 색으로 고르지 않는다.** 색은 *재려는 값*이므로 선별에 쓰면 자기순환이다. `--foreground-muted`는 `app/frontend/app/page.tsx`에 **7건** 있고(`grep -c`로 확인) partial 줄과 무관한 muted 요소가 최소 5개다(`듣고 있어요...` `:321` · `사유: {failureReason}` `:355` · 안내 문구 등) — "muted 요소가 있다" 형태의 단정은 **주입이 실패해도 통과한다.** 선별은 **구조로만** 한다: `<strong>`의 텍스트가 `질문: `/`답변: `인 `<p>`. 그 접두를 가진 `<p>`는 확정 줄(`page.tsx:307~312`)과 partial 줄(`:313~317`) **둘뿐**이고, 어느 것이 무엇인지는 **주입한 프레임이 정한다.**

**기대값은 하드코딩하지 않고 런타임에 유도한다.** 임시 probe 요소에 `style.color = 'var(--foreground-muted)'`를 걸고 `getComputedStyle(probe).color`를 읽는다. ⚠️ `getPropertyValue('--foreground-muted')`를 직접 비교하지 않는다 — 그쪽은 `#595959` 형태로 측정 대상의 `rgb(89, 89, 89)`와 문자열이 다르다. probe를 거치면 **같은 엔진이 같은 표현으로** 정규화한다. **단정의 정본은 색값이 아니라 `globals.css` 머리주석의 위계 계약**이다(`:5~7` — "강조 대상은 `--foreground`, 덜 강조할 보조 문구는 `--foreground-muted` … '덜 강조'를 밝기가 아니라 **대비**로 표현하기 때문에 배경이 뒤집혀도 살아남는다"). 팔레트가 바뀌어도 이 단정은 살아남는다. 모드 전환은 `measure_contrast.py`가 이미 쓰는 CDP `Emulation.setEmulatedMedia`를 재사용한다(새 수단 0개).

**주입 창** — `VOICE_ADAPTER=stub_unresponsive`로 띄운다. `audio_gateway/session.py:102`가 `session_started`를 `_connect()`(`:104` → `:126 asyncio.wait_for(self._adapter.start(), …)`)보다 **먼저** 보내고, `stub.py:70`의 `await asyncio.Event().wait()`는 영원히 끝나지 않으므로 소켓이 살아 있고 경쟁 프레임이 **0인 구간**이 열린다(세 줄 모두 직접 읽어 확인). ⚠️ **창은 유한하다 — `session.py:53 CONNECT_TIMEOUT = 10.0`.** 10초가 지나면 `session_failed`가 오고 `page.tsx:355`가 **또 다른 muted `<p>`**(`사유: …`)를 그린다. 그 요소엔 접두가 없으므로 **접두 `<p>` 개수로 창 이탈을 판별한다.** 창을 넘겼으면 **FAIL이 아니라 ERROR로 보고하고 재시도한다.** 창에서 주입이 실제로 먹는지는 **PLAUSIBLE·미실행이고 T5a ④가 확정한다**(§11-6).

⚠️ T5a에서 CDP 주입이 실패해 지연 방식으로 내려가야 한다면 **단일 직렬 큐로만** 간격을 벌린다. 프레임마다 독립 `setTimeout`을 걸면 `final`이 지연된 `partial`보다 먼저 디스패치되어 재려는 전이가 성립하지 않는다.

## §7. DB 접근 — 이 문서가 정본이다

**`tests/harness/psql_cli.py`만 쓴다. `podman exec`를 쓰지 않는다.** 이 헬퍼는 `DATABASE_URL`(`scripts/db_utils.py:base_dsn`)을 따라가므로 설정이 가리키는 DB에 붙는다.

```bash
cd app/backend && .venv/bin/python -c "
import sys; sys.path.insert(0,'../../tests/harness')
from psql_cli import psql, psql_binary
print(psql_binary()); print(psql('select current_database()'))
"
```

작성자가 직접 돌린 출력(2026-09-06): `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish`. 세 사실이 여기 걸린다 — **백엔드 venv가 필요하다**(`db_utils`가 최상단에서 `asyncpg`를 import한다) · **`DATABASE_URL`은 환경변수로만 읽는다**(`app/backend/.env`만 고쳐도 반영되지 않는다. 기본값 `postgresql://ohmy:ohmy@localhost:5432/ohmyenglish`가 현재 `.env`와 일치한다) · **homebrew `postgresql@17`은 keg-only라 `psql`이 PATH에 없다**(`psql_binary()`가 keg를 찾는다).

⚠️ **DB 공유가 스키마 수준이다.** 같은 데이터베이스 `ohmyenglish` 안에 다른 프로젝트의 `en_coach` 스키마가 있고 소유자가 다르다(직접 확인: `en_coach:en_coach` · `public:pg_database_owner` · `current_user = ohmy`). **우리 것은 `public` 하나뿐이다** → `pg_dump`를 범위 없이 돌리면 `permission denied for schema en_coach`로 막힌다. **`-n public`을 붙인다.**

## §8. teardown — 매 태스크의 일부다

공유 dev DB를 파괴적으로 쓴다. **세션 수·패턴 수·`frequency`를 baseline과 대조하는 것까지가 끝**이다. 전제: 회차 시작 시각(`WINDOW_START`)과 `.harness/browser_run_id.txt`(§3). SQL은 §7의 헬퍼로 던진다. `00000000-0000-0000-0000-000000000001`은 시드 사용자 id다.

**0. 회차 시작 전에 baseline을 뜬다** (없으면 캡틴의 패턴을 함께 지울 위험을 배제할 수 없다). `frequency`·`last_seen_at`을 함께 뜬다 — 마지막 대조(④)가 그 두 값을 요구한다.

```sql
drop table if exists harness_pattern_baseline;
create table harness_pattern_baseline as
  select id, pattern_key, frequency, last_seen_at from error_patterns
   where user_id = '00000000-0000-0000-0000-000000000001';
```

**①-a 세션을 시간창 스윕으로 등록한다** (자동 등록 훅이 없다 — §3):

```sql
insert into harness_sessions (run_id, session_id, scenario)
select '<browser_run_id>', s.id, '<C1|C2|…>'
  from learning_sessions s
 where s.user_id = '00000000-0000-0000-0000-000000000001'
   and s.started_at >= '<WINDOW_START>'
on conflict do nothing;
```

**① 세션 삭제** — cascade가 `utterances` → `{error_occurrences, analysis_jobs}`까지 지운다:

```sql
delete from learning_sessions
 where id in (select session_id from harness_sessions where run_id = '<browser_run_id>')
   and id not in (<§9의 보존 id 목록>);
```

**② `frequency`·`last_seen_at` 재계산** — 앱과 **같은 식**으로 다시 센다(`services/analysis.py`). 앱이 `+1`을 하지 않고 항상 실제 행 수에서 재계산하므로, 하네스 행을 지운 뒤 같은 식을 돌리면 **하네스가 없었던 것과 같은 값**이 된다:

```sql
update error_patterns p
   set frequency = agg.occurrences, last_seen_at = agg.last_seen_at
  from (select ep.id, count(eo.id) as occurrences, max(u.created_at) as last_seen_at
          from error_patterns ep
          left join error_occurrences eo on eo.pattern_id = ep.id
          left join utterances       u  on u.id = eo.utterance_id
         where ep.user_id = '00000000-0000-0000-0000-000000000001'
         group by ep.id) agg
 where p.id = agg.id;
```

**③ baseline에 없던 0-occurrence 패턴만 삭제**:

```sql
delete from error_patterns p
 where p.user_id = '00000000-0000-0000-0000-000000000001'
   and p.id not in (select id from harness_pattern_baseline)
   and not exists (select 1 from error_occurrences eo where eo.pattern_id = p.id);
```

**④ 대조 — 여기까지가 teardown이다.**

```sql
select count(*) from error_patterns where user_id = '00000000-0000-0000-0000-000000000001';   -- baseline 행 수와 같아야 한다
select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id
 where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at;           -- 0이어야 한다
select count(*) from learning_sessions s join harness_sessions h on h.session_id = s.id
 where h.run_id = '<browser_run_id>';                                                          -- 보존 id 개수와 같아야 한다
```

**⑤ 프로세스·환경 복원**: 백엔드를 §2의 baseline 명령으로 되돌리고 `curl localhost:8002/health`로 확인한다. `.env`는 고치지 않았으므로 복원할 것이 없다.

**보존 대상 — ①에서 제외하고 보고에 적는다**: (a) **§9의 C3용 `session_id` 5개** — 지우면 다음 회차가 실물 Claude 1회를 다시 쓴다. (b) **실패한 시나리오의 세션** — 재현 근거를 지우면 재현할 수 없어지는 것이 더 비싸다.

## §9. 실물 Claude 호출 상한 — **1회** · 보존 session_id

상한 1회는 발명값이 아니다 — 이 리포는 실물 검증을 1회 단위로 승인해 왔다(`S2-L2` 실물 계획 생성 1회 · 슬라이스 1 `L1`·`L2` · `G-6`의 `W-live` 1회·`E2E-S` 1회 · `G-4` 실물 마이크 1회). **실물 호출이 필요한 태스크는 C3·C4(계획서 T4) 하나뿐이다** — C1·C2·C5는 `VOICE_ADAPTER=stub`이고 분석 워커를 쓰지 않으므로 **0회**다. **재실행 비용은 0으로 만든다**: 최초 1회만 세션을 만들어 분석을 돌리고 그 `session_id`를 아래에 적어, 이후 회차는 `/results/<id>`를 **재방문**한다(세션을 새로 만들지 않으므로 화면 검증이 백엔드 재기동과 분리된다).

| 상태 | `session_id` |
|---|---|
| `analyzing` (C3a) · `final` (C3b) · `partial_failure` (C3c) · `connection_failed` (C3d) · `no_utterances` (C3e) | **5개 전부 T4에서 실측해 채운다** |

⚠️ 이 5개는 **teardown ①에서 제외한다**(§8 보존 대상 a).

## §10. 판정 어휘와 보고

산출물은 `PASS` / `FAIL` / `BLOCKED` / `ERROR` 넷 중 하나 + **단정별 근거 파일 경로**다(`use_browser`가 DOM 액션마다 자동 저장하는 `.png`·`.html`·`.md`·`-console.txt`). 새 어휘를 만들지 않는다.

- **음성 대조에서 FAIL이 나지 않으면 그 단정은 무효다.** PASS라고 보고하지 않는다.
- 계측 `eval` 반환값이 `'instrumented'`가 아니면 **ERROR로 끝낸다**(§4). 주입 창 이탈도 **ERROR**다(§6).
- `sent === 0`은 FAIL이 아니라 **BLOCKED**다(headless AudioContext가 자동재생 정책으로 suspend될 수 있다) → `show_browser`로 headed 재시도. `corrections[].reason`이 빈 문자열이면 역시 **BLOCKED**다(A4-2).
- **수치는 그 회차에 직접 돌린 출력만 적는다.** 계산값·낡은 값 금지. **앱 소스를 고치지 않는다** — 실패는 고치는 것이 아니라 보고하는 것이다.
- **보고를 그대로 믿지 않는다** — 호출자가 단정 하나는 직접 재현한다. 행 수는 직접 세고 화면은 자동 저장된 `.html`·`.png`를 직접 읽는다. 불일치하면 **직접 검증이 이기고 보고를 폐기한다.**
- 브라우저 레그 결과를 **게이트 수치와 섞어 보고하지 않는다.**

## §11. 아직 답을 발명하지 않은 것

| # | 무엇 | 어디서 닫는가 |
|---|---|---|
| 1 | **타임아웃·재시도·폴링 대기 값 전부.** 유일하게 근거 있는 값은 `results/[sessionId]/page.tsx:POLL_INTERVAL_MS = 2000`이고 그것은 **앱의 값**이지 대기 상한이 아니다 | **T2·T4 실행에서 실측**해 그 출력으로 정한다 |
| 2 | `createBufferSource`를 **어느 프로토타입에서** 단정하는가(§4-3) | **T2 실측** |
| 3 | headless AudioContext가 suspend되는가 | **T2 스파이크.** `sent === 0`이면 BLOCKED → `show_browser` |
| 4 | **A1-7의 음성 대조가 실제로 FAIL을 내는가** | **T2 스파이크.** 둘 다 못 내면 A1-7을 채택하지 않는다 |
| 5 | **CDP `onmessage` 주입이 실제로 되는가** — 가장 넓게 걸린 미결. C5와 C2 2단계 측정이 함께 여기 걸린다 | **T5a 스파이크(T3보다 먼저).** 실패하면 C5는 폐기하고 C2는 §6의 직렬 큐 대안으로 내려간다 |
| 6 | §6의 **주입 창이 실제로 먹는가**(10초 안에 2단계가 끝나는가) | **T5a ④** |
| 7 | 확정 줄 수(A1-5) **스냅샷 시점의 방법** — 소프트 내비게이션은 `window.__omy`를 파괴하지 않으므로 계측이 `final`마다 DOM 개수를 배열에 적립한다. rAF인지 MutationObserver인지는 미정 | **T2에서 실측해 확정한다** |
| 8 | C3용 보존 `session_id` 5개(§9) | **T4에서 채운다** |

1~6은 계획서가 "실측 후 정한다"로 남긴 항목을 **그대로 넘긴 것**이다(§13-1·3c·3·3b·2 + N-3). 7·8은 이 문서가 새로 남겼다. **이 문서가 닫은 계획서 미결 2건**: §13-4(회차를 여는가 → **연다**, `.harness/browser_run_id.txt` · §3) · §13-9(`e8b7e17`의 추천 이유 한 줄 → **A1-0으로 넣는다.** 새 시나리오를 만들지 않는다 — 계약이 `page.tsx:271`·`:277`에서 읽히고 기대값이 API에서 유도되며 음성 대조가 상태 전이로 성립한다).

## §12. 자기검증

- **단정 18건** — C1 9(A1-0~A1-8) · C2 3(A2-1~A2-3) · C3 2(A3-1~A3-2) · C4 2(A4-1~A4-2) · C5 2(A5-1~A5-2).
- **음성 대조 빈칸: 0건.** §5의 세 표에서 「음성 대조」 칸을 세어 확인했다. A1-7의 칸은 비어 있지 않다 — 후보 2개와 **T2에서 둘 다 실패하면 채택하지 않는다**는 판정 규칙이 들어 있다.
- **유도 방식 분류**: ⓐ 픽스처 연역 6건(A1-1~A1-5, A1-8) · ⓑ 런타임 유도 10건(A1-0, A1-6, A1-7, A2-1~A2-3, A3-2, A4-1, A4-2, A5-2) · **ⓒ 하드코딩 2건(A3-1, A5-1) — 각각 왜 유도가 불가능한지를 표에 적었고, 항진명제가 아님을 프론트 전체 grep으로 확인했다**(다섯 라벨의 다른 출현은 전부 주석이다).
- 이 문서는 **문서를 절 제목으로, 코드를 `파일:심볼`로** 가리킨다. 인용한 줄은 전부 작성 중 직접 읽어 확인했다.
