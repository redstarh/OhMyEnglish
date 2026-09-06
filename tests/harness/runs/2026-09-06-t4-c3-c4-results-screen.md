# 회차 기록 — T4 C3 결과 화면 5상태 + C4 교정 카드 · `TASK-22` AC 4/4

- **일시** 2026-09-06 (UTC 14:36 ~ 14:45) · **회차** `.harness/browser_run_id.txt` = `cfa512f6-5a4f-4b1d-b09a-9fa14fa91d5f`
- **HEAD** `1157aa8` · 브랜치 `design/first-vertical-slice`
- **실물 모델 호출**: **`analyze_utterance` job 정확히 1건** (`us.anthropic.claude-opus-5` · `attempts=1` · `done`).
  캡틴 승인 범위(§9 상한 1회) 안이다. **`plan_next_session` job은 지워서 호출하지 않았다.**
- **판정** **`PASS`** — 실행체 게이트가 **단정 48건**을 검사해 전건 통과.
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
**정확히 같다**(A4-2) · sentinel 변형과 같지 않다 · **원문 줄도 `corrections[0].original_span`과 맞춘다**
(카드끼리 뒤바뀜 검출).

⚠️ **이유 줄의 색이 `var(--foreground-muted)`다** — 원문·교정문보다 덜 강조한다는 그 파일의 주석과
일치한다. T3이 전사문에서 확인한 위계가 결과 화면에서도 같은 토큰으로 성립한다(눈으로도 봤다, §1-4).

**A4-1의 음성 대조**: `corrections`가 **빈** 세션(C3c, 0건)에서 두 접두가 **0개**다. 그 세션을
primary로 쓰지 않았다 — `0 == 0`은 카드 구현이 없어도 통과하기 때문이다(§5 A4-1의 ⚠️).

### 1-3. `corrections` 키는 상태에 따라 **없다** — 계약을 관측했다

`analyzing`·`connection_failed`·`no_utterances` 세 응답에 **`corrections` 키 자체가 없었다**(`null`도
아니다). `api/results.py:11~12`가 적은 계약 그대로다. 게이트는 `payload.get("corrections", [])`로 읽어
**키 부재를 0으로** 다룬다.

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
