# TASK-30 판별력 관측 — A3-1 · A4-1 · A4-2 (C3·C4)

> 절차 정본: `tests/harness/browser_leg.md` §2 프리플라이트 · §5 C3·C4 표 · §10 판정 어휘.
> 이 회차가 묻는 것은 PASS 판정이 아니라 **각 대조가 무력화에서 실제로 FAIL 을 내는가**다.
> 회차 성격: **읽기 전용**. 세션을 만들지 않고 `/results/<id>` 재방문만 했다. 어댑터는
> `VOICE_ADAPTER=nova` 이고 이 세 단정은 어댑터와 무관하다.
> 관측자: 프론트엔드 검증자 세션 (2026-09-09) · 앱 소스 변경 0줄.

## 0. 프리플라이트 — P1~P9 전건 직접 실행

| # | 명령 | 통과 조건 | 이 회차의 실제 출력 | 판정 |
|---|---|---|---|---|
| P1 | `curl -s http://localhost:8002/health` | `{"status":"ok"}` · `version` 키 없음 | `{"status":"ok"}` | 통과 |
| P2 | `cat app/frontend/.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:8002` | `NEXT_PUBLIC_API_BASE=http://localhost:8002` | 통과 |
| P3 | `git check-ignore -v app/frontend/.env.local` | 무시됨 | `app/frontend/.gitignore:34:.env*` (exit 0) | 통과 |
| P4 | `brew services list \| grep postgresql` | `postgresql@17 started` | `postgresql@17 started  redstar` | 통과 |
| P5 | §2 파이썬 한 덩이 | 낡은 소스 0건 | `P5: pid 55492 · 기동 04:51:36 전 · 소스 34건 → 통과` (exit 0) | 통과 |
| P6 | `curl -s localhost:3000 -o /dev/null -w '%{http_code}'` | `200` | `200` | 통과 |
| P7 | `grep -c 'superpowers-chrome' .claude/settings.local.json` | 2 이상 | `2` | 통과 |
| P8 | `ps -axo comm= \| awk -F/ '{print $NF}' \| grep -c '^pytest'` | `pytest 0건` | `P8: pytest 0건` (exit 0) | 통과 |
| P9 | §7 DSN 확인 | `ohmyenglish` | `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish` | 통과 |

**P5 는 출력이 비지 않았다** — 소스 34건을 실제로 검사하고 pid 55492 를 `lsof` 로 찾아 로그 pid 와
대조한 뒤 통과했다. §2 가 경고한 「명령이 오류로 끝났는데 출력이 비어 통과로 읽히는」 형태가 아니다.

**§8-⑤ 예외 적용 — 백엔드는 호출자 소유다.** 재기동·환경 복원을 하지 않았고 증거 3개를 남긴다:
`lsof -nP -iTCP:8002 -sTCP:LISTEN -t` = **55492**(회차 시작·종료 동일) ·
`ps -p 55492 -Eww` 에 **`WORKER_ENABLED=false` · `VOICE_ADAPTER=nova`**(회차 시작·종료 동일) ·
`/health` = `{"status":"ok"}`. `app/backend/.env` 를 열지 않았다.

## 1. 기대값의 유도 — 이 회차에서 다시 유도했다

전달받은 `/tmp/omy-expect.json` 을 **증거로 쓰지 않았다.** 두 출처에서 다시 유도해 대조했다.

- **ⓑ API 유도** (A4-1 의 N · A4-2 의 `reason`): `GET http://localhost:8002/api/sessions/<id>/results`
  를 6건 직접 호출했다. 산출물 `.harness/evidence/2026-09-09-task30-api-derived.json`
  (⚠️ `.harness/` 는 `.git/info/exclude:7` 로 무시되므로 **값의 소유자는 이 기록이다**).
- **ⓒ 하드코딩 라벨** (A3-1): `app/frontend/app/results/[sessionId]/page.tsx:STATUS_LABEL` 을
  **정규식으로 파싱해** 얻었다 — 손으로 옮겨 적지 않았다. 파싱 결과:
  `{'analyzing': '분석 중', 'final': '확정', 'partial_failure': '부분 실패', 'connection_failed': '연결 실패', 'no_utterances': '분석 대상 없음'}`

API 유도 결과 (6건):

| 라벨 | session_id | status | `corrections` 키 | N |
|---|---|---|---|--:|
| C3a | `210233be-ecaa-4409-a1af-8b7016cfe7e9` | `analyzing` | 부재 | — |
| C3b | `6225ddaf-90a8-43af-9aa8-e003921c75eb` | `final` | 있음 | 1 |
| C3c | `b2f0d169-3d90-431b-b842-cce21125052a` | `partial_failure` | 있음 | 0 |
| C3d | `76d9ef31-0d1b-4c50-b906-f16ee438080e` | `connection_failed` | 부재 | — |
| C3e | `d127dece-d1d1-4329-802d-9b8fd1067388` | `no_utterances` | 부재 | — |
| C3f | `e0c5e580-dfc0-4793-b02d-54cf4346c3c5` | `final` | 있음 | 2 |

여섯 건 모두 전달받은 값과 일치했다. `pronunciation` 은 6건 전부 **0**이다.

**소스 구조를 직접 읽어 확인한 것 2개** (`results/[sessionId]/page.tsx`):
- `main` 의 직계 자식은 `h1` → (`!sessionId` `<p>`) → (`sessionId && !result` `<p>`) →
  `result &&` 프래그먼트다. 프래그먼트는 DOM 노드를 만들지 않으므로 `{STATUS_LABEL[result.status]}`
  `<p>`(`:157`)가 `main` 의 직계가 된다. `result` 가 있으면 앞선 두 `<p>` 는 **둘 다 부재**다.
  → **`main > p` 의 첫째가 상태 요소다.** 관측이 이것을 뒷받침한다(아래 §2 의 `directPTexts`).
- 교정 카드(`:175~196`)는 `<div>` 하나에 `<p>` **셋**을 담는다: `<strong>원문:</strong>` ·
  `<strong>교정문:</strong>` · **라벨 없는** `{correction.reason}`.

## 2. 단정별 판정

| 단정 | 판정 | 판별력 관측 |
|---|---|---|
| A3-1 (5상태 라벨) | **PASS** | **있음** — 무력화(틀린 라벨)에서 FAIL **20/20** |
| A4-1 (교정 카드 구조) | **PASS** | **있음** — 대조 두 페이지에서 FAIL **2/2** |
| A4-2 (이유 문구 카드별 관통) | **PASS** | **있음** — 맞바꾼 기대값에서 FAIL **2/2** |

`BLOCKED`·`ERROR` 는 없다. A4-2 의 BLOCKED 조건(`reason` 이 빈 문자열)을 먼저 검사했고
**`reason_len` 51 · 63 으로 둘 다 비지 않았다** → BLOCKED 조건이 아니다.

### A3-1 — 5상태 라벨

**요소 지목**: `document.querySelector('main > p')` (첫 직계 `<p>`). DOM 전역 검색을 쓰지 않았다.
**수집한 값** — 5상태 세션을 차례로 재방문하며 같은 선택자로 읽은 `textContent`:

| 라벨 | status | 기대(소스 파싱) | 관측 `textContent` | 등호 | `main > p` 전체 |
|---|---|---|---|---|---|
| C3a | `analyzing` | `분석 중` | `분석 중` | True | `["분석 중"]` |
| C3b | `final` | `확정` | `확정` | True | `["확정"]` |
| C3c | `partial_failure` | `부분 실패` | `부분 실패` | True | `["부분 실패", "일부 발화는 분석하지 못했다 — 재시도되지 않습니다"]` |
| C3d | `connection_failed` | `연결 실패` | `연결 실패` | True | `["연결 실패"]` |
| C3e | `no_utterances` | `분석 대상 없음` | `분석 대상 없음` | True | `["분석 대상 없음"]` |

**다섯 값이 서로 다르다** (`len(set(...)) == 5`). 상태 요소의 `outerHTML` 은 다섯 회차 모두
`<p style="font-size: 1.25rem; font-weight: bold;">…</p>` 로 같은 자리다 → **같은 구조 요소가
상태에 의해 구동된다.** 상수를 렌더한다면 다섯 값이 같아야 했고 그렇지 않았다.

**판별력 관측 — 5×5 라벨 교차** (앱 무변경 · 기대값만 바꿔 다시 계산):

```
기대 분석 중     vs 관측 5개 -> = x x x x
기대 확정       vs 관측 5개 -> x = x x x
기대 부분 실패    vs 관측 5개 -> x x = x x
기대 연결 실패    vs 관측 5개 -> x x x = x
기대 분석 대상 없음 vs 관측 5개 -> x x x x =
대각 일치 5/5 · 비대각 일치 0/20 · 비대각 어긋남(FAIL) 20/20
```

→ **이 등호 검사는 틀린 기대값에서 실제로 FAIL 을 낸다.** 항진명제가 아니다.

⚠️ **「같은 요소」의 뜻을 정확히 적는다**: 회차는 전체 페이지 이동(`navigate`)으로 재방문했으므로
DOM **노드 동일성**이 아니라 **선택자 동일성**이다. §5 A3-1 이 "요소를 구조로 지목한다"고
정한 대로다. 소프트 내비게이션으로 노드 동일성까지 재지는 않았다(§5 는 그것을 요구하지 않는다).

### A4-1 — 교정 카드 구조 (primary = C3b, N=1)

**기대 N = 1** — API `corrections.length` 에서 유도(ⓑ). **관측**:

- 접두 `원문:` 을 가진 `<p>` = **1** · 접두 `교정문:` 을 가진 `<p>` = **1**
- 구조 기반 교차 확인(첫 자식이 `<strong>` 이고 그 텍스트가 접두인 `<p>`): 원문 **1** · 교정문 **1**
  → 접두 기반 계수와 구조 기반 계수가 일치한다(접두 문자열이 다른 곳에 우연히 있지 않다).
- 그 카드 `<div>` 의 `<p>` = **정확히 3개** · 라벨 없는 `<p>` = **1개** ·
  셋째 `<p>` 에 `<strong>` 없음 = True · **셋째 `<p>` 가 비어 있지 않다** = True
- 셋째 `<p>` 값: `gym처럼 늘 다니는 장소를 말할 때는 앞에 the를 붙여 'go to the gym'이라고 합니다.`

**음성 대조 둘을 모두 측정했다** (§5 표는 `no_utterances` 를, §9 는 C3c 를 지목한다 — 둘 다 쟀다):

| 대조 | status | API N | 원문 접두 | 교정문 접두 | 컨테이너 |
|---|---|---|--:|--:|---|
| C3c | `partial_failure` | 0 | **0** | **0** | **마운트됨** — `표시할 교정이 없습니다.` 를 그린다 |
| C3e | `no_utterances` | 키 부재 | **0** | **0** | **부재** — `main` 이 `h1` + 상태 `<p>` 둘뿐이다 |

C3e 의 `main` innerHTML 전문:
`<h1>학습 결과</h1><p style="font-size: 1.25rem; font-weight: bold;">분석 대상 없음</p>`

C3c 의 `main` innerHTML 전문:
`<h1>학습 결과</h1><p style="font-size: 1.25rem; font-weight: bold;">부분 실패</p><p>일부 발화는 분석하지 못했다 — 재시도되지 않습니다</p><div style="margin-top: 1rem;"><p>표시할 교정이 없습니다.</p></div>`

**판별력 관측** — primary 의 기대(N=1)를 대조 두 페이지에 그대로 적용해 다시 계산했다:
`C3c: 기대 1 대 관측 0 → FAIL` · `C3e: 기대 1 대 관측 0 → FAIL`. **2/2 에서 FAIL 이 났다.**
즉 이 계수는 페이지에 의해 구동되고 상수 1 을 내는 계측이 아니다 — primary 에서 1, 빈 세션에서 0.
카드 구현이 없으면 primary 가 0 이 되어 `0 == 1` 로 FAIL 한다.

### A4-2 — 이유 문구 카드별 관통 (primary = C3f, N=2) · 이 회차의 핵심

**BLOCKED 조건 선검사**: `reason` 길이 i=0 **51자** · i=1 **63자** — 둘 다 빈 문자열이 아니다.

**카드 짝짓기는 DOM 순서가 아니라 원문으로 했다** — `원문: {corrections[i].original_span}` 과
`textContent` 가 **완전 일치**하는 카드를 찾고, 후보가 정확히 1개일 때만 채택했다(둘 다 1개였다).

**본 단정** — 각 i 에서 그 카드의 라벨 없는 셋째 `<p>` 의 `textContent` == `corrections[i].reason`:

| i | 원문 | 기대 (`reason`) | 관측 (셋째 `<p>`) | 등호 |
|--:|---|---|---|---|
| 0 | `and present the project's details` | `앞의 went와 같은 어제 일이므로 present도 과거형 presented로 맞춰 줍니다.` | 같은 문자열 | True |
| 1 | `go to office` | `회사 사무실처럼 정해진 장소를 말할 때는 장소 명사 앞에 the를 붙여 go to the office라고 합니다.` | 같은 문자열 | True |

두 카드 모두 `<p>` **3개** · 라벨 없는 `<p>` **1개** · 셋째에 `<strong>` 없음.
어긋남 **0/2** → 본 단정 **PASS**.

**판별력 관측 — 대조 ② `reason` 맞바꾼 기대값** (⛔ 앱 소스 무변경 · **기대값만** 바꿔 재계산):

```
카드 i=0 (원문="and present the project's details")
     맞바꾼 기대 = corrections[1].reason = '회사 사무실처럼 정해진 장소를 말할 때는 장소 명사 앞에 the를 붙여 go to the office라고 합니다.'
     관측(셋째<p>)                      = '앞의 went와 같은 어제 일이므로 present도 과거형 presented로 맞춰 줍니다.'
     등호=False -> FAIL(어긋남)
카드 i=1 (원문='go to office')
     맞바꾼 기대 = corrections[0].reason = '앞의 went와 같은 어제 일이므로 present도 과거형 presented로 맞춰 줍니다.'
     관측(셋째<p>)                      = '회사 사무실처럼 정해진 장소를 말할 때는 장소 명사 앞에 the를 붙여 go to the office라고 합니다.'
     등호=False -> FAIL(어긋남)
교차 어긋남 2/2 → 판별력 있음
```

→ **`browser_leg.md` §11-9 와 §5 A4-2 가 「판별력 미확인」으로 남겨 둔 항목이 이 회차에서 닫혔다.**
C3f 가 서로 다른 두 패턴을 가져 교정 2건을 내고, 그래서 뒤바뀜을 실제로 잡는지 증명할 수 있었다.
⛔ **대조 ①(sentinel 변형)은 철회된 그대로 두었다** — 되살리지 않았다.

## 3. 수집한 원본 `eval` 반환값 — §10-1·2 (이 기록이 증거의 소유자다)

`.harness/` 는 git 무시 대상이고 브라우저 자동 저장 경로는 캐시 디렉터리라 사라질 수 있다.
그래서 판정 근거 두 건의 반환 JSON 전문을 여기 옮긴다.

**C3b** (`/results/6225ddaf-90a8-43af-9aa8-e003921c75eb`):

```json
{"waited_ms":0,"path":"/results/6225ddaf-90a8-43af-9aa8-e003921c75eb","statusText":"확정","statusOuterHTML":"<p style=\"font-size: 1.25rem; font-weight: bold;\">확정</p>","directPTexts":["확정"],"origPrefixCount":1,"corrPrefixCount":1,"origStructCount":1,"corrStructCount":1,"cards":[{"divTag":"DIV","pCount":3,"origText":"원문: go to gym","corrText":"교정문: go to the gym","thirdText":"gym처럼 늘 다니는 장소를 말할 때는 앞에 the를 붙여 'go to the gym'이라고 합니다.","thirdHasStrong":false,"thirdIsEmpty":false,"unlabeledCount":1,"divOuterHTML":"<div style=\"border: 1px solid rgb(221, 221, 221); border-radius: 8px; padding: 1rem; margin: 0.75rem 0px;\"><p style=\"margin: 0.25rem 0px;\"><strong>원문:</strong> go to gym</p><p style=\"margin: 0.25rem 0px;\"><strong>교정문:</strong> go to the gym</p><p style=\"margin: 0.25rem 0px; color: var(--foreground-muted);\">gym처럼 늘 다니는 장소를 말할 때는 앞에 the를 붙여 'go to the gym'이라고 합니다.</p></div>"}]}
```

**C3f** (`/results/e0c5e580-dfc0-4793-b02d-54cf4346c3c5`):

```json
{"waited_ms":1,"path":"/results/e0c5e580-dfc0-4793-b02d-54cf4346c3c5","statusText":"확정","statusOuterHTML":"<p style=\"font-size: 1.25rem; font-weight: bold;\">확정</p>","directPTexts":["확정","오늘은 드릴이 계획보다 짧았어요."],"origPrefixCount":2,"corrPrefixCount":2,"origStructCount":2,"corrStructCount":2,"cards":[{"pCount":3,"origText":"원문: and present the project's details","corrText":"교정문: and presented the project details","thirdText":"앞의 went와 같은 어제 일이므로 present도 과거형 presented로 맞춰 줍니다.","thirdHasStrong":false,"thirdIsEmpty":false,"unlabeledCount":1},{"pCount":3,"origText":"원문: go to office","corrText":"교정문: go to the office","thirdText":"회사 사무실처럼 정해진 장소를 말할 때는 장소 명사 앞에 the를 붙여 go to the office라고 합니다.","thirdHasStrong":false,"thirdIsEmpty":false,"unlabeledCount":1}]}
```

**C3a·C3c·C3d·C3e** (요약 — 전문은 위 §2 표와 `main` innerHTML 인용에 담겼다):
`C3a {"statusText":"분석 중","origPrefixCount":0,"corrPrefixCount":0,"allPCount":1}` ·
`C3c {"statusText":"부분 실패","origPrefixCount":0,"corrPrefixCount":0,"allPCount":3}` ·
`C3d {"statusText":"연결 실패","origPrefixCount":0,"corrPrefixCount":0,"allPCount":1}` ·
`C3e {"statusText":"분석 대상 없음","origPrefixCount":0,"corrPrefixCount":0,"allPCount":1}`

## 4. 사용한 CDP 절차 — 재현 방법

1. `mcp__…chrome__use_browser` `navigate` → `http://localhost:3000/results/<session_id>`
2. 같은 세션에서 `eval` 한 번. 반환값은 **JSON 문자열**이어야 한다 —
   ⚠️ **객체를 그대로 반환하면 도구가 `[object Object]` 로 접어 버려 증거가 사라진다**(실측).
   ⚠️ **top-level `await` 는 쓸 수 없다**(`ReferenceError: await is not defined`) →
   `(async () => { … return JSON.stringify(obj); })()` 형태로 감싼다.
3. `eval` 안에서 폴링을 기다린다: `main > p` 첫째의 `textContent` 가
   `결과를 불러오는 중입니다...` 가 아닐 때까지 100 ms 간격으로 최대 8,000 ms.
   실측 대기 시간은 6건 모두 **0~1 ms**(`navigate` 가 이미 첫 폴을 끝냈다).
4. 선택자: 상태 = `main > p` 첫째 · 접두 계수 = 모든 `p` 중 `textContent.startsWith('원문:')` ·
   구조 교차 확인 = `p.firstElementChild.tagName === 'STRONG'` 이고 그 텍스트가 접두 ·
   카드 = 그 `<p>` 의 `parentElement`, 그 안 `<p>` 자식들.
5. 판정 계산은 브라우저 밖 파이썬에서 했다(기대값 교차·5×5 행렬). 앱은 건드리지 않는다.

**마이크 권한 대화상자는 뜨지 않았다** — `/results/*` 는 `getUserMedia` 를 부르지 않는다.
`eval` 이 `undefined` 를 돌려준 회차가 0건이다.

## 5. DB 잔여물 — 3열 (§10)

이 회차는 **세션을 만들지 않았다** → teardown ①(세션 삭제)의 대상이 0건이고 `harness_runs` 회차를
열지 않았다. 그래서 셋째 열은 「해당 없음」이다(호출자 지시: DB 를 쓰지 마라).

| 표 | baseline (회차 전) | 회차 후 | teardown 후 |
|---|--:|--:|---|
| `learning_sessions` | 13 | 13 | 해당 없음 (생성 0건) |
| `analysis_jobs` | 49 | 49 | 해당 없음 |
| `utterances` | 120 | 120 | 해당 없음 |
| `error_patterns` | 9 | 9 | 해당 없음 |
| `session_plans` | 2 | 2 | 해당 없음 |
| `learner_notes` | 3 | 3 | 해당 없음 |
| `pronunciation_attempts` | 4 | 4 | 해당 없음 |
| `error_occurrences` | 24 | 24 | 해당 없음 |

`harness_pattern_baseline` drift = **0** (회차 후 직접 조회).
**보존 세션 6개 전부 기대 상태를 유지한다** (회차 후 결과 API 재조회):
`analyzing`/키부재 · `final`/1 · `partial_failure`/0 · `connection_failed`/키부재 ·
`no_utterances`/키부재 · `final`/2. 워커를 켜지 않았고 DB 에 쓰지 않았다.

⚠️ `session_plans` 2행 · `learner_notes` 3행은 §10 이 「세 시점 모두 1행」이라 적은 것과 다르다 —
**이 회차가 바꾼 것이 아니다**(회차 전·후가 같다). 그 서술이 낡았을 가능성을 §7 에 올린다.

## 6. 증거 파일 경로

브라우저 자동 저장 (액션 13건 · `.png`/`.html`/`.md`/`-console.txt` 각 1):
`/Users/redstar/Library/Caches/superpowers/browser/2026-09-09/session-1788920405956/`

| 번호 | 무엇 |
|---|---|
| `001-navigate`, `002-eval`, `003-eval` | C3b (`003-eval` 이 판정 반환값) |
| `004-navigate`, `005-eval` | C3f — A4-2 primary |
| `006-navigate`, `007-eval` | C3a `analyzing` |
| `008-navigate`, `009-eval` | C3c `partial_failure` — A4-1 대조 |
| `010-navigate`, `011-eval` | C3d `connection_failed` |
| `012-navigate`, `013-eval` | C3e `no_utterances` — A4-1 대조 |

⚠️ **`-console.txt` 는 여전히 빈 스텁이다** — `003-eval-console.txt` 를 재어 **58바이트**였다.
§10 이 적은 그대로이고 이 회차도 그것을 증거로 쓰지 않았다.

JSON 산출물 (⚠️ `.git/info/exclude:7` 로 무시됨 — 커밋되지 않는다):
`.harness/evidence/2026-09-09-task30-api-derived.json` (API 유도 전문) ·
`.harness/evidence/2026-09-09-task30-dom-observed.json` (DOM 관측 전문)

## 7. 절차 문서의 결함 — 발견만 하고 고치지 않았다 (호출자 판단 몫)

**D-1 · §5 A4-1 의 음성 대조가 둘 중 약한 쪽을 지목한다.**
§5 A4-1 행은 대조를 *"`corrections`가 빈 세션(`no_utterances`)에서 두 접두가 0개"* 로 적고,
§9 는 *"C3c 는 음성 대조로만 쓴다"* 로 적는다. **둘은 같은 강도가 아니다.**
`page.tsx:129` 의 `showCorrections` 가 `final`·`partial_failure` 만 통과시키므로
**`no_utterances`(C3e)에서는 교정 컨테이너가 아예 마운트되지 않는다** — 이 회차 관측:
C3e 의 `main` 은 `h1` + 상태 `<p>` 둘뿐이다. 즉 **C3e 의 0 은 `corrections.map` 을 한 번도
통과하지 않고 상태 게이트만으로 보장된다.** 반대로 C3c(`partial_failure`, N=0)는 컨테이너를
마운트하고 빈 배열 갈래(`표시할 교정이 없습니다.`)를 실제로 그린다.
→ **§5 가 이름 붙인 대조는 앱의 카드 경로에 대해 아무것도 배제하지 못한다.**
이 회차는 둘 다 재서 둘 다 0 이었으므로 판정이 흔들리지는 않았다. 다만 **§5 와 §9 가 서로 다른
세션을 지목하는 것을 어느 절도 기록하지 않았고**, 강도 차이도 적혀 있지 않다.

**D-2 · §10 의 증거 규약이 `eval` 반환 형식을 말하지 않아 증거가 조용히 사라진다.**
§10-1 은 *"`eval` 반환값에 DOM 자체를 실어 보낸다 — `outerHTML`·`innerHTML` 을 함께 담는다"* 라고만
적는다. 그대로 **객체를 반환하면 도구가 `Result: [object Object]` 로 접어 버린다**(이 회차 실측 —
`002-eval` 이 그것이다). 회차는 "규약대로 DOM 을 실어 보냈다"고 믿는데 **증거는 0 바이트**다.
반환값을 **`JSON.stringify` 한 문자열**로 만들어야 한다. 그리고 **top-level `await` 를 쓸 수 없다**
(`ReferenceError: await is not defined`) → 비동기 대기가 필요하면 async IIFE 로 감싸야 한다.
두 사실이 문서에 없어 이 회차가 두 번 헛돌았다.

**D-3 · §3 에 읽기 전용 회차의 분기가 없다.**
§3 은 조건 없이 *"회차를 연다"* 고 하고 그것은 `harness_runs` 에 **INSERT** 다. 그런데 이 회차처럼
`/results/<id>` 재방문만 하는 구성은 **세션을 0건 만들고**, 그러면 ①-a 스윕이 등록할 것이 없고
①의 삭제 범위도 공집합이라 **`run_id` 의 소비자가 없다.** 즉 순수 읽기 회차에서 §3 은 아무것도
보장하지 않는 DB 쓰기만 남긴다. 이 회차는 호출자의 명시 금지("DB 를 쓰지 마라")를 따라 회차를
열지 않았다 — **문서와 호출자 지시가 갈리는 자리이고 문서에 분기가 없다.**

**D-4 · §10 의 DB 3열 대상 표에 붙은 「`session_plans`·`learner_notes` 는 세 시점 모두 1행」이
현재 값과 다르다.** 이 회차 실측은 `session_plans` **2행** · `learner_notes` **3행** 이고
회차 전·후가 같다(이 회차가 바꾼 것이 아니다). 그 괄호 서술이 특정 회차의 값을 일반 규약처럼
적어 놓은 것으로 보인다 — 다음 회차가 그것을 기준선으로 읽으면 **정상 상태를 이상으로 오판한다.**

**D-5 (약함) · A3-1 의 「같은 요소」가 노드 동일성인지 선택자 동일성인지 명시되지 않았다.**
§5 A3-1 은 "요소를 **구조로** 지목한다"고 정하면서 음성 대조를 "**같은 요소**의 `textContent` 가
바뀐다"로 적는다. 전체 페이지 재방문에서는 DOM 노드가 매번 새로 생기므로 「같은 요소」는
선택자 동일성일 수밖에 없다. 회차가 이것을 구별하지 않으면 **재지도 않은 노드 동일성을 주장**할 수 있다.

**관찰 (결함 아님) · A3-1 의 ⓒ 하드코딩을 소스 파싱으로 대체할 수 있다.**
이 회차는 라벨을 손으로 옮기지 않고 `STATUS_LABEL` 블록을 정규식으로 파싱해 얻었다. 문구가 바뀌면
기대값이 함께 바뀌므로 「인용이 붙은 채로 썩는」 형태를 피한다. 문서를 고칠지는 호출자 몫이다.

## 8. 이 회차가 확인하지 못한 것

1. **A4-1 의 구조 하위 단정 둘은 무력화 관측이 없다.** 「카드 `<p>` 가 **정확히 3개**」와
   「셋째 `<p>` 가 **비어 있지 않다**」는 primary·C3f 합계 카드 3개에서 모두 성립했지만
   **3 이 아닌 카드나 빈 셋째 `<p>` 를 낸 페이지를 하나도 보지 못했다.** 계수 부분(N 등호)의
   판별력은 관측했고, 이 두 하위 단정은 **판별력 미확인**이다.
2. **A4-2 의 대조는 기대값 쪽 무력화다 — 앱 쪽 뒤바뀜을 실제로 만들어 보지는 않았다.**
   문서가 그것을 금지하므로(앱 소스 무변경) 정본 형태를 따랐다. 등호 검사에서 두 방향이
   대칭이라는 것은 **추론**이고 관측이 아니다. 그 사실을 그대로 적는다.
3. **소프트 내비게이션(노드 동일성) 미측정** — D-5.
4. **프론트 게이트(`npx tsc --noEmit` · `npx eslint app lib`)를 돌리지 않았다.** 문서 머리말은
   그것을 회차 **전에 호출자가** 확인하라고 정한다. 이 회차 브리프에 그 값이 없었고 내가 재지도
   않았다 → **미확인**이다.
5. **범위 밖 단정 전부 미평가**: A1-*·A2-*·A3-2·A5-* 는 이 회차에서 평가하지 않았다.
   `BLOCKED` 로도 적지 않는다 — 브리프가 셋만 지시했다.
6. **`pronunciation` 은 6건 모두 0행**이라 발음 카드 경로는 이 회차에서 한 번도 그려지지 않았다.
7. **결과 API 를 `GET` 으로 여러 번 호출한 것이 부수효과를 남기지 않는다는 것을 코드로 확인하지
   않았다.** 회차 전후 행 수가 8개 표 전부 동일한 것으로 **관측상** 배제했을 뿐이다.

---

_회차 종료. 앱 소스·설계서·계획서·원장·설정 파일 변경 0건. 백엔드 재기동 0회. 세션 생성 0건._
