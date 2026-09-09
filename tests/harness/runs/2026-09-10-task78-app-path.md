# TASK-78 AC#1 — 앱 경로에서는 tool 이 오지 않는다. **계획 블록이 발음 코칭을 밀어낸다**

> ⛔ **이 회차가 「앱 프롬프트」의 뜻을 고친다.** 지금까지 나와 동료 세션이 「앱 프롬프트」라 부른
> `--app-prompt` 는 **기반 프롬프트만** 싣는 팔이었다(스파이크 주석이 그렇게 적어 뒀다).
> **앱이 실제로 보내는 것은 거기에 계획·무대가 붙은 4,545자다.** 그 차이가 결과를 뒤집는다.
>
> 원자료: `.harness/evidence/task78/fullprompt-{1,2,3}.json` · 브라우저 레그 회차 2건
> (세션 `18e64d1d`·`ad61c8ea` — teardown 완료) · 조립 프롬프트 전문 `/tmp/app-full-prompt.txt`

---

## 1. 환경 — 이 턴에 직접 재서 얻음

| 항목 | 값 |
|---|---|
| 백엔드 | 재기동해 `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` (pid 42692 · `/health` `{"status":"ok"}`) |
| 재기동 전 기준선 | `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false` (pid 52228 · `ps eww` 로 프로세스에서 읽음) |
| 복원 | 같은 명령으로 되돌렸다 (pid 58241 · 어댑터·워커 재확인) |
| ⛔ 워커 | **켜지 않았다**(`H-AT`). 그래서 **AC#3(복습 시계 종단)은 이 회차에서 닫지 못한다** |
| 브라우저 | CDP. `getUserMedia` 를 합성 스트림으로 대체. `AudioContext.sampleRate` = **48000** ← 이중 리샘플 경로가 실재함이 확인됐다(단 `TASK-65` 가 그것을 원인에서 배제했다) |
| 클릭 | CDP 실제 입력. `eval` 안의 `element.click()` 은 user activation 을 만들지 않는다(1차수 `H-1`) |

## 2. 앱 경로 실측 — 2회 모두 코칭 없음 · tool 0

`p2a` → 무음 1.6초 → `p2k` 를 한 세션에 흘렸다(스파이크의 다중 턴 팔과 같은 순서).

| 회차 | 세션 | 사용자 전사문 | agent |
|---|---|---|---|
| 1 | `18e64d1d` | `i finished the report and shared the results with my team.` **×2** | `Great job sharing the report with your team! Let's practice a sentence about your weekend plans.` |
| 2 | `ad61c8ea` | 같음 **×2** | `Great job sharing the results with your team! Let's practice a sentence about your weekend plans.` |

- **전사문이 둘 다 영어로 복원됐다** — `TASK-65` 의 기전(세션 첫 발화가 ASR 언어를 고정한다)이
  앱 경로에서 재현됐다.
- **발음 코칭이 0건이다.** agent 가 곧바로 **주말 계획**으로 넘어갔다.
- `pronunciation_attempts` **델타 0**.

## 3. 왜 넘어갔는가 — 계획이 초점을 문법에 고정한다

앱이 세션에 싣는 계획을 조회했다(`GET /api/sessions/next-plan`):

> *"짧은 문장에서 a/an을 자주 빼먹고 \"plan the action plan\"처럼 말했기 때문에, 오늘은 a/an과
> make/prepare + an + 계획 명사를 함께 연습해요."*

그리고 **앱이 어댑터에 실제로 넘기는 지시문을 같은 코드로 재조립했다**
(`build_system_prompt` 를 `factory.py:63` 과 같은 재료로 호출. `known_sounds=['an_as_a']` ·
`plan` 있음 · `questions` 5 · `scenario` 있음 → **4,545자**). 그 안의 계획 블록:

```
Today's plan:
- Focus on: article_missing_before_noun (a/an + 단수 명사),
            business_expression_verb_noun_collocation (make / prepare + an + 계획 명사)
- Situations to use today: weekend plans small talk, planning a short trip, …
- Hint timing for today …: wait for one full attempt, then give a short hint if the
  article or the verb is missing
```

⛔ **초점·무대·힌트 시점이 전부 문법을 가리킨다.** 규칙 9 가 이미 *"Grammar first"* 인데 계획이
그 방향을 한 번 더 못박는다.

## 4. 통제 대조 — 계획을 실으면 스파이크에서도 tool 이 0이 된다

위 4,545자 전문을 `--prompt-file` 로 스파이크에 실어 **같은 오디오**로 3회 돌렸다.

| 팔 | 프롬프트 | 회차 | 코칭 | `toolUse` |
|---|---|--:|:--:|--:|
| 기존 (`--app-prompt`) | **기반 프롬프트만** | 11 | **3회** | **3회** (이벤트 4건) |
| **신규 (`--prompt-file`)** | **앱이 실제로 보내는 조립 프롬프트** | 3 | **0회** | **0** |
| 앱 경로 (브라우저) | 같은 조립 프롬프트 | 2 | **0회** | **0** |

⛔ **그리고 발화가 앱 경로와 거의 글자까지 같다**:
`Great job sharing the report with your team. Now, let's practice a sentence about your weekend plans.`
→ 브라우저 회차 1의 발화와 대조하면 문장 구조가 일치한다. **즉 이 팔이 앱을 충실히 재현한다.**

**따라서 원인은 계획 블록이다.** 변수를 하나만 바꿨고(기반 → 조립) 결과가 뒤집혔다.

## 5. 이것이 「단순화」 판단을 어떻게 바꾸는가

**tool 배선은 여전히 문제가 아니다** — `runs/2026-09-10-task78-coaching-implies-tool.md` 의
「코칭 ⟺ tool」(**11/11 회차**)은 그대로 참이고 `target_sound` 도 **이벤트 6건 전부**에 실렸다.
⚠️ **처음 이 줄이 「15/15」·「5/5」로 적었고 틀렸다** — 회차 수와 이벤트 수를 섞었다. 원자료를
기계로 다시 세어 고쳤고 그 경위는 판별 회차 기록 §2 머리에 있다.

⛔ **그러나 지금 앱 설정에서는 코칭 자체가 일어나지 않는다.** 우회로를 걷어내고 tool 에만
의존하면, **의존하는 그 신호를 앱 자신의 프롬프트가 막고 있다.**

**즉 단순화의 전제가 하나 늘었다**: 계획 블록이 발음에 자리를 내주어야 한다. 지금 계획은
초점 둘을 **문법으로만** 채운다. 방법 후보(⚠️ **어느 것도 시험하지 않았다**):

1. 발음 패턴이 복습 예정일에 걸리면 **계획의 초점에 그것을 싣는다** — `load_known_sounds` 가
   이미 소리 목록을 싣지만(`api/ws.py`) **초점(`Focus on:`)에는 들어가지 않는다.**
2. 계획과 무관하게 **심한 발음은 우선한다**를 규칙에 넣는다 — 규칙 9 의 `Grammar first` 와
   경합하므로 문구 설계가 필요하다.
3. 발음 전용 세션 모드를 둔다.

⚠️ **1이 가장 값어치 있어 보인다** — 계획 파이프라인이 이미 발음 패턴을 알고 있고
(`known_sounds=['an_as_a']` 가 실렸다) 초점에만 안 넣는다. 그러나 **재지 않았다.**

## 6. 이 회차가 고치는 서술

⛔ **`--app-prompt` 라는 이름이 오해를 만들었다.** 그 팔은 앱 프롬프트가 아니라 **기반 프롬프트**다.
`TASK-67`·결정 49·내 앞선 회차 기록이 전부 그것을 「앱 프롬프트」로 불렀다 — **그 서술들이
가리키는 것은 앱이 보내는 지시문이 아니다.** 스파이크 주석은 그 사실을 적어 뒀으나
(*"`build_system_prompt` 를 쓰지 않고 기반 프롬프트만 가져온다"*) 결론 문장이 그것을 반영하지 않았다.

## 7. 정리 대조 — 기준선과 정확히 일치

| 표 | 기준선 | 정리 후 |
|---|--:|--:|
| `learning_sessions` | 13 | **13** |
| `utterances` | 120 | **120** |
| `pronunciation_attempts` | 4 | **4** |
| `error_patterns` | 9 | **9** |
| `error_occurrences` | 24 | **24** |
| `review_tasks` | 15 | **15** |
| `analysis_jobs` | 49 | **49** |

시각창(`started_at > 2026-09-09 22:08:46+00`)으로 잡아 세션 2건·발화 6건·job 을 지웠다.
⚠️ **`analysis_jobs` 는 내가 명시로 지운 것이 2건인데 3건이 줄었다** — 나머지 1건은 발화·세션
삭제의 cascade 로 빠졌다. **최종 수치가 기준선과 같은 것이 판정 근거다.**
**보존 세션 여섯 전건 생존 확인**(`210233be`·`6225ddaf`·`b2f0d169`·`76d9ef31`·`d127dece`·`e0c5e580`).
