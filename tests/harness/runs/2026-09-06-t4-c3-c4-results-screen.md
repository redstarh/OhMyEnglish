# 회차 기록 — T4 C3 결과 화면 5상태 + C4 교정 카드 · `TASK-22` AC 4/4

- **일시** 2026-09-06 (UTC 14:36 ~ 14:45) · **회차** `.harness/browser_run_id.txt` = `cfa512f6-5a4f-4b1d-b09a-9fa14fa91d5f`
- **HEAD** `1157aa8` · 브랜치 `design/first-vertical-slice`
- **실물 모델 호출**: **`analyze_utterance` job 정확히 1건** (`us.anthropic.claude-opus-5` · `attempts=1` · `done`).
  캡틴 승인 범위(§9 상한 1회) 안이다. **`plan_next_session` job은 지워서 호출하지 않았다.**
- **판정** **`PASS`** — 실행체 게이트가 전건 통과. **첫 회차 48건 → 리뷰 반영 후 57건**(§5).
  ⛔ **A4-2의 기대값 교차 대조는 「판별력 미확인」이고 통과로 세지 않았다**(§10).
- **실행체** `tests/harness/c3_results_screen.py`(이 회차에 신설) · 원시 판독
  `.harness/evidence/c3-results-screen.json` · 스크린샷 6장

---

## 1. 직접 확인한 것

### 1-1. 5상태 — 요소 지목 + 등호 (A3-1)

상태 라벨은 `main`의 **첫 직계 `<p>`**다. 다섯 회차의 그 요소를 차례로 읽었다:

| 세션 | API `status` | 첫 직계 `<p>` | 원문/교정문 접두 `<p>` | 카드 `<div>` |
|---|---|---|--:|--:|
| C3a `210233be…` | `analyzing` | **`분석 중`** | 0 / 0 | 0 |
| C3b `6225ddaf…` | `final` | **`확정`** | **1 / 1** | **1** |
| C3c `b2f0d169…` | `partial_failure` | **`부분 실패`** | 0 / 0 | 0 |
| C3d `76d9ef31…` | `connection_failed` | **`연결 실패`** | 0 / 0 | 0 |
| C3e `d127dece…` | `no_utterances` | **`분석 대상 없음`** | 0 / 0 | 0 |
| 없는 uuid | (404) | **`결과 API가 404을 반환했습니다`** | 0 / 0 | 0 |

**A3-1의 음성 대조가 성립했다** — 같은 요소의 문구가 **다섯 상태에서 모두 달랐다**(게이트가 중복을
검사한다). 상수를 렌더하고 있으면 바뀌지 않는다.
**A3-2 상호 대조**: 없는 uuid에서 **상태 라벨 5개 전부 부재**(`labelsAnywhere == []`)이고,
정상 세션 5건에서 **404 문구가 부재**다(양방향).
**부분 실패 안내 문구**(`일부 발화는 분석하지 못했다 — 재시도되지 않습니다`)는 `partial_failure`에서만
있고 나머지 4상태에서 없다 — 게이트가 `status == "partial_failure"`와 등호로 잰다.

### 1-2. 교정 카드 (A4-1 · A4-2) — primary는 C3b 하나다

C3b의 결과 API(기대값의 출처, ⓑ):

```json
{"status":"final","partial_failure":false,"pronunciation":[],
 "corrections":[{"pattern_key":"article_missing_the_before_place_noun","category":"article",
   "original_span":"go to gym","correction":"go to the gym",
   "reason":"gym처럼 늘 다니는 장소를 말할 때는 앞에 the를 붙여 'go to the gym'이라고 합니다.",
   "target_form":"go to the + 장소 명사","occurrences":1}]}
```

화면에서 관측한 그 카드의 `outerHTML`(§10-1 — 제3자가 재확인할 수 있는 형태):

```html
<div style="border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 0.75rem 0;">
  <p style="margin: 0.25rem 0;"><strong>원문:</strong> go to gym</p>
  <p style="margin: 0.25rem 0;"><strong>교정문:</strong> go to the gym</p>
  <p style="margin: 0.25rem 0; color: var(--foreground-muted);">gym처럼 늘 다니는 장소를 말할 때는 앞에 the를 붙여 'go to the gym'이라고 합니다.</p>
</div>
```

게이트가 잰 것: 카드 `<div>` **1개** == API `corrections` 길이 · 그 카드의 `<p>` **정확히 3개** ·
라벨이 `['원문:', '교정문:', null]` · **셋째 줄이 비어 있지 않다** · 셋째 줄이 `corrections[0].reason`과
**정확히 같다**(A4-2) · **원문 줄도 `corrections[0].original_span`과 맞춘다**(카드끼리 뒤바뀜 검출).
⛔ **첫 판에 있던 sentinel 대조는 철회했다** — 등호가 이미 그것을 함의해 **독립 판별력이 0**이었다(§5).

⚠️ **이유 줄의 색이 `var(--foreground-muted)`다** — 원문·교정문보다 덜 강조한다는 그 파일의 주석과
일치한다. T3이 전사문에서 확인한 위계가 결과 화면에서도 같은 토큰으로 성립한다(눈으로도 봤다, §1-4).

**A4-1의 음성 대조**: `corrections`가 **빈** 세션(C3c, 0건)에서 두 접두가 **0개**다. 그 세션을
primary로 쓰지 않았다 — `0 == 0`은 카드 구현이 없어도 통과하기 때문이다(§5 A4-1의 ⚠️).

### 1-3. `corrections` 키는 상태에 따라 **없다** — 계약을 관측했다

`analyzing`·`connection_failed`·`no_utterances` 세 응답에 **`corrections` 키 자체가 없었다**(`null`도
아니다). `api/results.py:11~12`가 적은 계약 그대로다.
⛔ **첫 판은 그 키 부재를 조용히 0으로 읽었고 그것이 공허 통과를 만들었다** — 리뷰가 실증했다(§5).
지금은 **상태별로 키의 존재 자체를 단정한다**: `final`·`partial_failure`는 있어야 하고 나머지 셋은
없어야 한다.

### 1-4. 눈으로 본 것 — 스크린샷을 **내가 열어서 봤다**

| 파일 | 무엇이 보이는가 |
|---|---|
| `c3-final.png` | `학습 결과` / **`확정`**(굵게) / 카드 1개: `원문: go to gym` · `교정문: go to the gym` · 이유 줄이 **눈에 띄게 흐린 회색** |
| `c3-partial_failure.png` | **`부분 실패`** + 안내 문구 + `표시할 교정이 없습니다.` |
| `c3-missing.png` | **`결과 API가 404을 반환했습니다`**가 **danger 색(붉은)** 으로, 상태 라벨 없음 |
| `c3-analyzing.png` · `c3-connection_failed.png` · `c3-no_utterances.png` | 각 상태 라벨만 (교정 영역 없음) |

### 1-5. 5상태를 어떻게 만들었나 — 출처를 정직하게 가른다

`results.py`의 R2 다섯 규칙을 먼저 코드에서 확정한 뒤 각 조건을 만들었다.
**정본은 `browser_leg.md` §9 표다** — 여기서 재서술하지 않는다. 요지만: **C3a·C3d는 앱이 스스로 만든
상태**이고, **C3b·C3c·C3e는 앱이 만든 세션 위에 job 상태를 조성**한 것이다(규칙 2·4가 정의한 조건을
그대로 만든 것이고, 그 규칙의 실세계 원인도 그 docstring이 적어 둔 것이다).

⛔ **「5상태 관측」이라는 요약을 정확히 좁힌다** (2026-09-06 T4 검토 ③). 관측한 것은 **다섯 상태의
라벨과 안내 문구**이고, **교정 카드 렌더는 `final` 하나에서만** 봤다. `partial_failure`는 조성한 job에
occurrence가 없어 `corrections`가 **빈 배열**이므로 — 규칙 4가 약속하는 *"성공분(`done`) 교정은
포함한다"* 경로는 **미관측이다.** 즉 **"부분 실패 화면에서 교정 카드가 어떻게 보이는가"는 이 회차가
답하지 않는다.** §2에 그렇게 적었고 이 요약도 그 구별을 담는다.

**실물 호출을 1건으로 묶은 방법**: 스텁 세션은 묶음이 3개라 `analyze_utterance` job이 **3건** 생기고
`plan_next_session`까지 합쳐 **4건**이 된다(직접 확인). 그래서 ① **발화 seq 4·6을 삭제**해 묶음을 하나만
남기고(job은 cascade로 사라진다) ② **`plan_next_session` job을 삭제**한 뒤 ③ 워커를 켰다.
⚠️ **job을 지우는 것으로는 안 된다** — `flush_ended_sessions`가 **job 없는 묶음을 다시 등록**한다.
**발화를 지워야** 묶음 자체가 없어진다. 켜기 직전 DB 전체의 `pending` job은 **1건**이었다(직접 확인).

### 1-6. DB 3열 (§10 ⛔)

`WINDOW_START` = `2026-09-06 14:36:36.185766+00`

| 표 | baseline | 회차 후 | teardown 후 |
|---|--:|--:|--:|
| `learning_sessions` | 7 | 12 | **12** ← 5건 보존 |
| `analysis_jobs` | 34 | 45 | **45** ← 보존 세션의 job |
| `utterances` | 92 | 114 | **114** ← 보존 세션의 발화 |
| `error_patterns` | 7 | 8 | **8** ← 보존 세션의 교정 근거 |
| `error_occurrences` | 17 | 18 | **18** |
| `session_plans` (보존) | 1 | 1 | **1** |
| `learner_notes` (보존) | 1 | 1 | **1** |
| baseline 패턴 drift | 0 | 0 | **0** |

⚠️ **이 회차는 teardown이 「원복」이 아니다 — 그것이 §9의 의도다.** 5개 세션과 그 파생 행을 남겨
다음 회차의 재실행 비용을 0으로 만든다. teardown 실행: ①-a `INSERT 0 5` · ① `DELETE 0`(창 안 5건이 전부
보존 대상) · ② `UPDATE 0` · ③ `DELETE 0`(새 패턴은 occurrence가 있어 남는다).

⛔ **§8-④의 첫 대조가 이 회차에서 성립하지 않았고, 그것이 절차의 결함이었다** — 「패턴 수 == baseline
행 수」는 보존 세션이 새 패턴을 만들면 깨진다. **§8-④에 그 정정을 박고**, §8-0의 규칙대로 **baseline을
다시 떠 새 파일로 남겼다**: `runs/2026-09-06-pattern-baseline-v2.tsv`(**8행**). 이전 사본(7행)도 추적된
채로 둔다. 재스냅샷 후 그 대조는 등호로 돌아온다(직접 확인: 8 == 8).

### 1-7. 프로세스 복원

백엔드는 받은 상태(`VOICE_ADAPTER=stub` · **`WORKER_ENABLED=false`**)로 돌려놨다.
⚠️ **워커를 끈 것이 C3e의 전제다** — 켜면 `flush_ended_sessions`가 지운 job을 되살려
`no_utterances`가 `analyzing`으로 바뀐다. **다음 회차가 워커를 켜면 C3e가 깨진다.**
`app/backend/.env`는 열지도 고치지도 않았다(모드는 환경변수로만).

---

## 2. 직접 확인하지 **못한** 것 — 통과로 적지 않는다

- ⛔ **A4-2의 기대값 교차 대조는 평가할 수 없었다 → 판별력 미확인.** 교정 **2건 이상**인 세션이 없다.
  **그리고 스텁 픽스처로는 원리적으로 어렵다**: 오류가 있는 두 문장(`go to gym`·`go to office`)이 같은
  패턴으로 묶이고 R1이 패턴 단위로 그룹하므로 교정이 1건이 된다. 늘리려면 **서로 다른 오류 종류**의
  표본이 필요하고 그것은 **실물 호출을 더 쓴다** → 캡틴 결정 사안으로 §9·§11-9에 남겼다.
- **발음 카드(C5·A5-1·A5-2)는 이 회차의 범위가 아니다.** 다섯 세션 모두 `pronunciation`이 **0건**이라
  그 화면 영역은 렌더되지 않았다(게이트가 그것을 단정하지 않는다 — 재지 않은 것을 통과로 세지 않는다).
- **`partial_failure`에서 `done` 교정이 실리는 경로는 재지 않았다.** C3c의 `done` job 2건은 조성한
  것이라 occurrence가 없어 `corrections`가 0이다. 규칙 4의 "성공분 교정은 포함한다"는 **미관측**이다.
- **폴링 종료(terminal이면 멈춘다)는 재지 않았다.** `analyzing`은 2초마다 계속 폴링하는데 그 정지
  조건을 이 회차의 게이트가 검사하지 않는다.
- **실물 Nova(음성) 경로는 이 회차와 무관하다** — 세션은 `stub`/`stub_unresponsive`로 만들었다.

---

## 3. 이 회차가 새로 알아낸 것

1. **`analysis_jobs.session_id`는 `analyze_utterance`에 채워지지 않는다** — 그 job은 `utterance_id`로만
   걸리고 `session_id`는 `plan_next_session` 같은 세션 단위 job에 쓰인다. `j.session_id = <세션>`으로
   조인하면 **analyze job이 0건으로 보인다**(실제로 그렇게 보고 "job 0건"이라 읽었다가 다시 셌다).
   → **세션의 analyze job은 `utterances`를 거쳐 센다.**
2. **`flush_ended_sessions`가 지운 job을 되살린다** — 워커가 켜져 있는 동안 job만 지우면 원상복구된다.
   상태를 조성할 때는 **발화**를 지워 묶음을 없애야 한다(§1-5).
3. **스텁 세션 1회는 실물 호출 4건짜리다**(`analyze_utterance` 3 + `plan_next_session` 1). "세션 1회"를
   "호출 1회"로 읽으면 4배가 된다 — **묶음 수를 먼저 세라.**

---

## 4. 이 회차가 신설한 자산

`tests/harness/c3_results_screen.py` — §5 C3·C4의 실행체. `Cdp`·`find_target`을
`c2_render_hierarchy.py`에서 **재사용**한다(같은 CDP :9222. 새 수단 0개).
⭐ **처음부터 `check_screen`·`check_missing` 게이트를 넣었다** — T3의 첫 판이 리뷰에서 뚫린 이유가
「값을 인쇄만 하고 판정하지 않았다」였고 그것을 되풀이하지 않기 위해서다. 어긋나면 **비영 종료**하고,
**BLOCKED(표본 조건 실패)와 「판별력 미확인」을 FAIL과 따로 출력한다** — 미확인은 PASS로 세지 않는다.

**절차 문서에 박은 것**: §9 보존 표(5개 + `corrections` 수 + 만든 방법) · §8-④ 첫 대조 정정 ·
§8-0 baseline 사본 참조를 v2로 · §11-8·10 **닫힘** · §11-9는 **답을 확정하고 캡틴 결정으로** 남김.

---

## 5. 리뷰 반영 — 차단 4건 + 내 테스트가 잡은 1건

**리뷰 결론: `CHANGES REQUESTED`**(CRITICAL·HIGH 없음). 리뷰어가 저장된 판독값에 `check_screen`·
`check_missing`을 **직접 다시 돌려** 48건 산식(`analyzing 6 · final 14 · 나머지 6·6·6 · missing 4`
= 42 + A3-1 대조 1 + 상호대조 5)을 재현했고 내 수치와 일치했다. 차단 4건을 **전부 재현한 뒤** 고쳤다.

| # | 무엇 | 내가 재현한 결과 · 고친 것 |
|---|---|---|
| **①** | **`corrections` 키 부재를 0으로 읽는 것이 공허 통과를 만든다** | **재현했다**: `final`에서 그 키를 지우고 화면도 0장이라 넣으니 `checked` **14 → 6** · `fails=[]` **통과**. A4-1·A4-2 전체가 조용히 사라지는데 FAIL이 아니다. 지금은 `primaries`가 BLOCKED로 막지만 **§11-9가 요구하는 「교정 2건 이상 세션 추가」가 그 마스크를 벗긴다.** → **상태별로 키 존재 자체를 단정**하도록 고쳤다(고친 뒤 같은 입력이 이름 있는 어긋남을 낸다) |
| **②** | **sentinel 대조의 독립 판별력이 0이다** | **재현했다**: 그것을 반증하는 유일한 입력에서 어긋남이 **2건**(등호가 함께 잡는다). 카드마다 `checked`를 1씩 부풀리는 줄이었다 → **지우고 회귀 방지 테스트를 박았다.** `browser_leg.md` §5 A4-2 대조 ①도 **철회**했다(문서와 코드를 함께) |
| **③** | **A3-1 음성 대조가 세션 1건이면 항진명제** | **재현했다**: `len(set(x)) != len(x)`는 원소 1개면 절대 참이 되지 않는다 → **2건 미만이면 「미평가」로 갈라 낸다**(C2의 `check_cross`와 같은 형태). 실측: `--session final=…` 하나만 주면 `A3-1 음성 대조 미평가`가 뜬다 |
| **④** | **`READ_JS`가 `location.href`를 담고도 아무도 단정하지 않는다** | **사실이다**(grep: `url:`은 `READ_JS`에만 있고 판정에 없다). `Page.navigate` 직후 폴링이 **이전 문서**를 읽을 수 있고 같은 status 세션 둘이면 스테일 판독이 조용히 통과한다 — **C2 MEDIUM-1과 같은 형태**(측정만 하고 게이트 안 함). → `dom["url"]`이 그 세션 id로 끝나는지 단정한다 |
| **⑤** | **내가 쓴 테스트가 실행체 결함을 하나 더 잡았다** | 화면 카드가 API보다 많으면 `payload["corrections"][i]`가 **`IndexError` 트레이스백**으로 죽어 **이름 있는 FAIL과 나머지 어긋남을 함께 잃었다**(카드 초과는 앱이 낼 수 있는 결함이다). → **경계 가드**를 넣어 `A4-1: 카드[i]가 API 범위를 넘는다`로 낸다 |

### 게이트 테스트 신설 — `tests/harness/test_c3_gates.py` (**24 passed**)

입력은 **실물 판독값**(`runs/2026-09-06-t4-c3-dom-read.json`)이고 그 위에 **한 필드씩** 변이를 얹는다.
변이 **18종** + 없는-세션 변이 **4종** + sentinel 회귀 방지 + green. ⚠️ **이 파일도 게이트 안이다**
(`pyproject.toml:33`). 그래서 `H-AA`는 적용되지 않는다.
⚠️ **추적 증거 사본이 테스트 픽스처를 겸한다**(리뷰 LOW) — 그 파일은 **회차 기록이 소유**하고 테스트는
읽기만 한다. 회차가 갱신돼 red가 나면 **픽스처를 맞추지 말고 게이트가 옳은지 먼저 본다.**

### 반영 후 종단 재확인

- 5세션 회차: **`판정 (단정 57건 검사) · PASS · exit 0`**(48 → 57: 상태별 키 존재 5 + url 5 − sentinel 1).
- 단일 세션 회차: **`A3-1 음성 대조 미평가`** + A4-1·A4-2 미확인 3건, `20건 전건 통과`.
- **DB 변화 0** — 결과 화면 재방문은 세션을 만들지 않는다(`learning_sessions` 12 불변).
- 게이트 테스트 전체: `test_c2_gates` + `test_c3_gates` = **71 passed**.

### 리뷰가 남긴 조건 하나 — 여기서 답한다

리뷰어가 §8-④ 정정을 **"§8의 취지를 훼손하지 않는다"**로 판정하면서 조건을 달았다: *"v2가 v1 공유
7행에 대해 **drift 0인 시점에** 떴어야 한다 — 그 한 줄이 기록에 있는지는 내가 확인하지 않았다."*
→ **있다. 그리고 그 턴에 직접 돌렸다**: 재스냅샷 직전 출력이 `drift(재스냅샷 전): 0`이었고, v2 파일의
머리주석에도 뜬 시각(`2026-09-06T14:44:52Z`)과 v1 대비 증가분의 이유가 적혀 있다.
§8이 지키는 것이 **비트 동일성이 아니라 캡틴 데이터 불파괴**이고 그 장치가 **baseline 행에 대한 drift
대조**라는 판정에 동의한다 — 그래서 개수 등호를 푼 것이다.

### ⚠️ 도구 사실 하나 (다음 세션이 시간 낭비하지 않게)

**`ruff`의 `line-length`는 문자 수가 아니라 표시 폭이다** — 동아시아 문자를 **2**로 센다. 한글 주석을
`len(line) <= 100`으로 맞춰도 `E501`이 난다(이 회차에서 두 번 밟았다). 재려면
`sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line)`을 쓴다.
