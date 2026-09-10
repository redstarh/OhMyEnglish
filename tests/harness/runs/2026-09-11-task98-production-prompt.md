# TASK-98 회차 — 제품 프롬프트를 조립해 쟀고 **한 갈래는 해석 불가로 판정함**

> 소유 `TASK-98`. ⛔ **판정 요지 두 줄.**
>
> 1. **얻은 것**: AS4 프롬프트가 `SYSTEM_PROMPT` 와 **글자 그대로 같음**을 실증했고(AC#2), 제품
>    프롬프트를 **앱과 같은 함수·같은 인자**로 조립하는 방법을 확정했다.
> 2. ⛔ **잃은 것**: 그 프롬프트로 돌린 8회는 **해석 불가**다 — 그 갈래에는 소리 줄이 없어
>    규칙 9·11 이 온전히 살아 있고 **그 둘이 이미 0을 예측한다.** 세션 `ohmyenglish-40` 이 지적했다.
>
> ⚠️ 파일명은 KST(2026-09-11)이고 원자료 시각은 **UTC**(2026-09-10 21:5x)다.

---

## 1. ⛔ AC#2 실증 — 이것이 이 회차의 가장 단단한 산출물이다

```
build_system_prompt((), None, [], None, drill_count=5, drill_turns_min=4) == SYSTEM_PROMPT  →  True
둘 다 2339자
```

⛔ **`TASK-67` 정정의 함의가 코드로 확인됐다** — 스파이크의 `--app-prompt` 팔은 **계획·무대·초점·질문이
없는 세션(AS4)의 실제 앱 프롬프트와 글자 그대로 같다.** 그 위에 세운 `TASK-93`·`TASK-95` 의 0/8 이
근거를 갖는다.

## 2. 제품 프롬프트 조립 — 인자를 손으로 지어내지 않았다

`api/ws.py:286~293` 이 제품 경로이고 그 로더를 그대로 불렀다(`build_prod_prompt.py.txt` 사본).

| 인자 | 값 | 출처 |
|---|---|---|
| `known_sounds` | `['an_as_a']` | `_load_known_sounds_or_empty(pool)` |
| `plan` | `A2` · focus `article_missing_before_noun`·`business_expression_verb_noun_collocation` · `5~8 words` | `_load_prepared_plan_or_none(pool).instruction` |
| `questions` | 5건 | 같은 것의 `.questions` |
| `scenario` | `'After work with a colleague'` | `_load_scenario_or_none(pool, sid)` · `sid`=`e0c5e580…` |
| `drill_count`·`drill_turns_min` | 5 · 4 | `settings` |

**제품 프롬프트 4505자**(AS4 2339 + 2166). 붙은 것: 놓친 소리 목록 · 무대 · 계획 · 질문 5개.
전문 사본은 `runs/2026-09-11-task98-production-prompt/prompt_production.txt` 다.

⛔ **`grep -c "Sound to coach today"` = 0** — 계획 `focus` 에 발음 패턴이 없어 **소리 줄이 붙지 않았다.**

## 3. ⛔ 그래서 이 8회는 **해석 불가**다 — 네 번째 같은 기전

| 팔 | 프롬프트 | tool 도착 |
|---|---|--:|
| **B** 대조군 | 스파이크 짧은 프롬프트 | **4/4** |
| **A'** 측정 | 제품 프롬프트(계획 실림 · **소리 줄 없음**) | **0/4** |

Fisher 양측 `p=0.0286`. **그런데 이 값을 「제품 프롬프트가 tool 을 막는다」의 근거로 쓸 수 없다.**

⛔ **기전 (`nova.py` 를 직접 읽어 확인했다)**:

> `:339~340` — 대체 범위가 이 줄이 있는 세션으로 한정된다 — 계획이 발음 초점을 지정하지 않으면 줄이
> 아예 없고 규칙 9·11 이 그대로다.
> `:335~337` — 남은 층이 이 두 규칙이며 **겹치지 않는 두 경로**로 막는다 — 규칙 9 는 문법 교정이
> **없는** 턴에서도, 규칙 11 은 **있는** 턴에서 상호배제로.

⇒ **소리 줄이 없는 갈래는 규칙 9·11 이 온전히 살아 있고 그 둘이 tool 0 을 이미 예측한다.** 즉 픽스처가
아니라 **분기 자체가 결과를 예측한다** — `pq*` 구간에서 결정 52 가 0을 예측한 것과 **같은 형태의
순환**이다.

⚠️ **내가 반대로 생각했던 것을 적어 둔다**: 「규칙 9 는 심한 발음(`p2m`)에서는 코칭을 허용하므로 0 이
예측값이 아니다」로 읽었다. ⛔ **코드 주석이 그것을 반증한다** — 규칙 9 가 막는 경로는 문턱이 아니라
`Grammar first` 이고 **문법 교정이 없는 턴에서도** 막는다. `TASK-75` 회차가 그것을 실측했다.

## 4. ⛔ 「DB 에 계획이 없어 ⑶ 을 못 잰다」도 틀렸다 — 계획이 **낡은** 것이다

세션 `ohmyenglish-40` 이 직접 조회해 확정했다.

| 사실 | 값 |
|---|---|
| 최신 `session_plans` | `created_at` **2026-09-08 22:58 UTC** · focus 둘 다 문법·표현 |
| 발음에 초점 한 자리를 준 커밋 | `4563f15` **2026-09-09 23:35 UTC** (`TASK-81`) |
| 발음 패턴 `pronunciation_an_as_a` | `next_review_at` **2026-09-04** — 이미 지났다(허용 집합에 있다) |

⇒ 그 계획은 **`4563f15` 이전 프롬프트가 만든 것**이다. ⛔ **지금 코드로 계획을 다시 생성하면 소리 줄이
붙은 갈래가 「제품 데이터」로 성립한다** — 손으로 지어낼 필요가 없다. 그것이 `TASK-81` AC#4 이고
선행 `TASK-75` 가 `Done` 이라 의존이 풀렸다.

## 5. ⛔ 다음 회차의 예산 — 사용자 결정 앞에 멈춘다

발음 코칭 기준율이 **13%**(대체 판 누적 15회에 2건 · `runs/2026-09-10-task75-rule9-rule11-replacement.md`
§8.5)이므로 세션 `ohmyenglish-40` 이 이 턴에 계산한 값:

```
P(4회 전부 코칭 0) = 0.564
P(8회 전부 코칭 0) = 0.318
P(≥1회 코칭) ≥ 0.95 에 필요한 회차 = 21
```

⛔ **즉 팔당 4회는 0 이 나와도 아무것도 배제하지 못한다.** 그리고 계획 재생성은 **공유 학습 데이터에
행을 더하고 워커 기동을 요구**하며, 그 순간부터 이 회차가 측정한 제품 프롬프트 4505자가 **낡는다**
(모든 세션 시작이 새 계획을 읽는다).

⇒ ⛔ **회차 예산(21회 규모)과 워커·DB 쓰기가 함께 걸리므로 사용자 결정을 받는다.** 이 회차는 여기서
멈추고 `TASK-98` 을 `In Progress` 로 남긴다 — **AC#4 는 미충족이다.**

## 6. 하지 않은 것

워커 미기동 · DB **SELECT 만**(계획 재생성 안 함) · 소스 미수정 · `--tool-choice` 미사용 ·
보존 세션 불가침. 실물 Nova 왕복 8회(이 세션 누적 **50회**).

## 7. 재현

```bash
cd app/backend
.venv/bin/python <회차 디렉터리>/build_prod_prompt.py.txt   # 프롬프트 조립 + AC#2 실증
<회차 디렉터리>/run_d98.sh 4                                # 팔 A' 와 팔 B 교대
python3 tests/harness/runs/2026-09-11-task93-d50-tool-rate/d50_judge.py D98 prod   # 판정
```

⚠️ `build_prod_prompt.py.txt` 는 **확장자를 `.txt` 로 두었다** — `tests/` 아래 `.py` 는 `ty`·`ruff`
게이트 대상인데 이 스크립트는 `app/backend` cwd 에서만 import 가 풀린다(`H-AV`).

---

## 8. 계획 재생성 시도 — ⛔ **소리 줄 갈래는 성립하는데 계획이 저장되지 않는다** (결정 53 실행)

사용자 결정(결정 53)대로 워커 구간을 열어 **내 세션 `33447835` 의 `plan_next_session` job 하나만**
처리했다. 실물 Claude 호출 1건.

### 8.1 ⛔ 절차에서 배운 것 — `guard` 의 범위가 부족하다

`p5_worker_leg.py guard` 는 **보존 세션 job 만** 비켜 둔다. 그런데 `claim_next` 는 `available_at` 이
가장 이른 **모든** pending job 을 집으므로 **비보존 세션의 job 이 먼저 집힌다.**

⛔ **실제로 첫 시도에서 `24597f0f` 의 `analyze_utterance` job 이 집혔다.** `--expect-session` 이
**처리는 거부**했지만 **claim 자체는 일어나** `status=running` · `attempts=1` · `locked_at`·`locked_by` 가
커밋됐다. **즉 그 방어는 처리를 막고 오염은 막지 못한다.**

**복원**: baseline 스냅샷의 원값으로 되돌려 `analysis_jobs` **drift 0** 을 확인했다.

⛔ **그래서 순서를 바로잡았다**: `guard`(보존) → **내 job 을 제외한 claim 가능 pending 을 밀고 별도
스냅샷** → `claim` → 그 스냅샷 복원 → `restore`. ⚠️ **`guard` 를 나중에 돌리면 안 된다** — 내가 이미
민 값을 `guard` 가 「원값」으로 기록해 `restore` 가 거짓 복원을 한다.

### 8.2 ⛔ 결과 — 두 가지가 동시에 드러났다

```
plan output rejected: plan response was not JSON: '{\n  "focus": [\n    {\n
  "pattern_id": "99fc908f-e25c-4c19-86ed-a4720cf8eb2b",\n
  "pattern_key": "pronunciation_an_as_a",\n      "target_form": "an_as_a"\n    },\n
  {\n      "pattern_id": "70ad1279'
```

1. ⛔ **좋은 것 — 소리 줄 갈래가 성립한다.** 모델이 `pronunciation_an_as_a` 를 **focus 첫 자리에**
   골랐다. 즉 `4563f15`(발음이 복습 예정일에 걸리면 계획 초점 한 자리를 얻게 함 · `TASK-81`)가
   **작동한다.** 세션 `ohmyenglish-40` 이 「값싼 확인에 이 한 칸을 먼저 넣으라」고 한 그 항목이
   **통과했다.**
2. ⛔ **나쁜 것 — 그 응답이 `models/plan.py:285` 에서 거부됐다.** 모델이 옳은 내용을 냈는데
   **저장되지 않는다.** job 은 `pending`·`attempts=1` 로 남고 재시도 백오프가 걸린다.

⚠️ **원인 미확정.** 후보 둘: ⑴ 응답이 잘렸다(에러가 앞 200자만 담아 원문 길이를 모른다 — `70ad1279`
에서 끊긴 것으로 보인다) ⑵ 파서가 찾는 JSON 후보 형태와 응답 형태가 어긋난다(그 `raise` 가 for 루프
**밖**이라 후보를 모두 시도한 뒤다). ⛔ **어느 것도 배제하지 못했다.**

⇒ **`TASK-100` 으로 등록했다(HIGH).** ⛔ **그 결함이 닫히기 전에 21회를 쓰지 않는다** — 계획이
저장되지 않으므로 소리 줄이 붙은 프롬프트를 만들 수 없다. `TASK-98` AC#4 가 그것에 막혔다.

⚠️ **함께 드러난 정황**: `session_plans` 최신 행이 **2026-09-08 22:58 UTC** 이고 그 뒤
`plan_next_session` job 이 **pending 8건** 쌓여 있다. 이 결함이 그 정체의 원인이면 **`TASK-81` 의
기능이 제품에서 한 번도 발휘되지 못한 것**이다. ⛔ **표본 1건이라 단정하지 않는다** — `TASK-100`
AC#2 가 그것을 확인한다.

### 8.3 DB 는 전건 복원했다

| 표 | 회차 전 | 회차 후 |
|---|--:|--:|
| `analysis_jobs` | 57 | 57 · ⛔ **drift 0**(baseline 과 문자 단위 일치) |
| `error_patterns` | 9 | 9 |
| `review_tasks` | 15 | 15 |
| `session_plans` | 2 | **2** — ⛔ 계획이 생성되지 않았다 |

복원한 것 넷: 오염된 job `9c4d00b7`(`status`·`attempts`·`lock`) · 내가 민 pending 7건의
`available_at` · `guard` 스냅샷(`restore`) · 내 job 의 `attempts`·`last_error`·`available_at`
(재시도 백오프로 밀린 것).

⛔ **보존 세션 여섯은 `verify` 로 회차 전 상태를 찍어 두었다** — `210233be` analyzing ·
`6225ddaf` final(corrections=1) · `76d9ef31` connection_failed · `b2f0d169` partial_failure(0) ·
`d127dece` no_utterances · `e0c5e580` final(2).
