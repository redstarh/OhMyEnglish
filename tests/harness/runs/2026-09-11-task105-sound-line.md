# 회차 — `TASK-105`: 소리 줄이 실린 제품 프롬프트로 21회 (결정 53)

세션 `ohmyenglish-7f` · 2026-09-11 · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-11-task105-sound-line/`

> **이 회차가 재는 것**: 계획이 발음 초점을 지정해 **소리 줄이 붙은** 제품 프롬프트에서
> ⑴ 발음 코칭이 일어나는가 ⑵ tool 이 오는가 ⑶ `target_sound` 가 실리는가.
> 판정은 `TASK-86` 이 갖고 이 회차는 **측정만** 한다(`TASK-93`·`95`·`98` 과 같은 분리).
>
> **왜 21회인가**: `runs/2026-09-11-task98-production-prompt.md` §5 가 계산했다 — 코칭 기준율
> 13%에서 `P(≥1회 코칭) ≥ 0.95` 에 필요한 회차가 21 이다. 팔당 4회는 0 이 나와도 아무것도
> 배제하지 못한다(4회 전부 0일 확률 0.564).

---

## 0. ⛔ 실물 호출 상한 — **먼저 적고 넘기지 않는다** (AC#5)

| 팔 | 프롬프트 | 회차 | wav |
|---|---|--:|---|
| **A(sound)** | 제품 조립 · 계획 실림 · **소리 줄 1건** | **21** | `p2m.wav` → `p2a.wav` |
| **B(base)** | 스파이크 전용 짧은 프롬프트 · 대조군 | **5** | 같음 |

**Nova 양방향 세션 상한 26회.** Claude 호출은 이 구간에 **0회**다(계획 재생성 1회는 §1 에서 이미
썼다). ⛔ **상한을 넘기지 않고, 중간에 늘리지 않는다** — 늘리려면 그 사실과 이유를 여기에 먼저 적는다.

대조군을 21회가 아니라 5회만 두는 이유: 대조군의 역할은 **판별력 확인**이고(`d50_judge.py` 1단계)
같은 픽스처에서 이미 `4/4`·`8/8` 로 확보돼 있다. 5회 전부 0이면 「환경이 바뀌었다」를 잡을 수 있고,
1:1 로 두면 비용이 두 배가 된다. ⚠️ **이 설계가 D98 의 1:1 교대와 다르다는 것을 여기에 적어 둔다** —
두 회차의 대조군 비율을 나란히 놓을 때 분모가 다르다.

## 1. 준비 — 계획 재생성(공유 dev DB) · 전부 직접 돌린 출력

**⛔ 공유 dev DB 에 쓴 것은 이 구간이 전부다.** 결정 53 이 승인한 범위이고 동료 세션
(`ohmyenglish-40`)에 착수를 알려 「진행 중 회차 없음」을 확인받았다.

| 단계 | 결과 |
|---|---|
| baseline drift(회차 전) | `harness_pattern_baseline` **0** · `harness_review_task_baseline` **0** (여섯 컬럼 스키마) |
| 표 스냅샷 | `baseline-{error_patterns,analysis_jobs,review_tasks,session_plans,learner_notes}.csv` (9 · 57 · 15 · 2 · 3행) |
| guard ① | ⚠️ 종류를 지목할 수단이 없어 `24597f0f` 의 **분석** job 이 당겨졌다 → `restore` 로 되돌렸고 스냅샷을 `p5-guard-01-analyze-restored.json` 으로 남겼다 |
| 도구 보강 | `p5_worker_leg.py guard` 에 **`--job-type`** 을 더했다(비보존 세션 넷 전부 분석 job 이 더 이르므로 종류 없이는 항상 분석이 당겨진다) |
| guard ② | `33447835` 의 `plan_next_session` 을 당겼다 — 스냅샷 `p5-guard.json` · 전역 최소 확인 통과 |
| claim | job `92a08f2c` `plan_next_session` → **`status=done attempts=1`** · `last_error` null |
| restore | `available_at` 을 원값(`2026-09-10T14:28:34.116633+00:00`)으로 되돌렸다 |
| 보존 세션 여섯 | `210233be` analyzing · `6225ddaf` final(1) · `76d9ef31` connection_failed · `b2f0d169` partial_failure(0) · `d127dece` no_utterances · `e0c5e580` final(2) — **전건 기대와 같다** |
| baseline drift(계획 처리 후) | **0 · 0** |
| 행 수 변화 | `session_plans` 2 → **3** · `learner_notes` 3 → **4** — 그 둘만 늘었다(의도한 변경). `error_patterns` 9 · `review_tasks` 15 · `analysis_jobs` 57 · `utterances` 128 · `users.current_level` A2 는 그대로 |

**저장된 계획**(`session_plans` 최신 행): 세션 `33447835` · `source=agent` ·
`created_at` **2026-09-11 00:08:24 UTC** · focus **`[pronunciation_an_as_a, article_missing_before_noun]`**
— 발음이 **첫 자리**다.

**조립한 제품 프롬프트**(`prompt_sound.txt` · 실행체 `build_prod_prompt.py.txt`):

| 인자 | 값(출처는 `api/ws.py:286~293` 의 로더) |
|---|---|
| `known_sounds` | `['an_as_a']` |
| `plan` | 있음 · `target_level=A2` · focus 위와 같음 |
| `questions` | **5건** |
| `scenario` | `'After work with a colleague'`(세션 `33447835`) |
| `drill_count` · `drill_turns_min` | 5 · 4 |
| 길이 | 제품 **5,223자** · AS4 **2,339자**(= `SYSTEM_PROMPT` 와 글자 그대로 같음 · 재확인) |
| 소리 줄 | **1건** — `- Sound to coach today: "an_as_a"` |

⚠️ **이 순간 `TASK-98` 이 측정한 제품 프롬프트 4,505자는 낡았다** — 모든 세션 시작이 새 계획을
읽으므로 그 회차의 팔 A' 는 **다시 재현되지 않는다.**

### 1.1 ⛔ 이 회차의 결과를 읽을 때의 경계 — 도착률이 좋아도 결정 50 의 ③ 은 열리지 않는다

세션 `ohmyenglish-40` 이 착수 직후 붙여 준 사실이다(교차 확인 요청 없음 — 그 세션의 회차 기록
`runs/2026-09-11-task97-tool-payload.md` 가 정본이다).

- tool 이 와도 **첫 호출의 `target_form` 이 학습자의 무너진 전사**다(6/6). 앱은 둘째 호출의 옳은
  문장을 **버린다** — 판정 UPDATE 에 그 필드가 없다(`TASK-103`).
- **사용자 결정 54 가 그 payload 질을 결정 50 의 ③ 기준에 넣었다.** 즉 ③(우회로 제거)은
  `TASK-103` 이 닫히기 전에 **열리지 않는다.**

⇒ ⛔ **이 회차의 도착률이 높게 나와도 「보조 신호를 걷어내자」로 읽지 않는다.** 이 회차가 답하는
질문은 「소리 줄이 코칭과 tool 도착을 바꾸는가」 하나다.

## 2. 회차 — 실행과 결과

실행체 `run_d105.sh`(회차 디렉터리) · 판정기는 `runs/2026-09-11-task93-d50-tool-rate/d50_judge.py`
를 **그대로** 썼다(`python3 <그 파일> D105 sound`). 판정 논리를 회차마다 복사하지 않는다.

| 팔 | 프롬프트 | 세션 | tool 도착 | `target_sound` 실림 |
|---|---|--:|--:|--:|
| **A(sound)** | 제품 조립 5,223자 · 소리 줄 1건 | **21** | **0/21** | **0/21** |
| **B(base)** | 스파이크 짧은 프롬프트 | **5** | **5/5** | 0/5(그 프롬프트는 요구하지 않는다) |

Fisher 양측 `p=0.0000`. 상한(§0) 26세션을 **정확히** 썼다.

**코칭 발화는 났다 — 21회 전부.** 그런데 **전부 문법 지시**였고 발음 코칭은 **0회**다. 21세션의
마지막 발화가 거의 같은 형태다(원문 그대로):

- `Use "an update" or "an action plan". For example: "I want to make an action plan."` (13회)
- `Use a short sentence with "a" or "an". For example: "I finished a report."` (3회)
- `Remember, we are focusing on using "a" or "an" before singular nouns.` (1회)

⛔ **「소리가 이렇게 났다 / 그 낱말만 다시 말해 보라」는 발화가 한 번도 없다.** `tool` 도 0이다.

## 3. ⛔ 판별력 — **이 수치는 질문에 답하지 못한다.** 픽스처에 목표 소리가 없다

⛔ **내가 설계를 틀렸고 그 사실을 먼저 적는다.** 계획이 지목한 소리는 `an_as_a` 인데
`scenarios-P-pronunciation.md:75~76` 이 정의한 픽스처의 오류는 **f→p · r→l · θ→s** 다:

```
p2a.wav  "I finished the report and shared the results with my team."   (정확)
p2m.wav  "I pinished the leport and shaled the lesults wis my team."    (f→p, r→l, θ→s)
```

**두 문장에 「an」이 아예 없다.** 즉 코칭할 목표 소리가 그 오디오에 존재하지 않으므로
**tool 0/21 은 프롬프트가 아니라 픽스처가 예측한 값**이다. 이것은 이 리포가 네 번 밟은
「결과를 이미 예측하는 조건에서 얻은 관측」과 **같은 형태**다(`H-AZ` 의 큰 규칙).

⚠️ **두 번째 교란도 있다** — 저장된 계획의 초점이 `[pronunciation_an_as_a,
article_missing_before_noun]` **둘**이고 둘이 같은 낱말(`an`)에서 만난다. 그래서 관측된 문법
지시가 ⑴ 모델이 소리 줄을 관사 지시로 읽은 것인지 ⑵ **둘째 초점을 그대로 따른 것**인지
**갈리지 않는다.**

**그래서 배제한 것과 배제하지 못한 것을 갈라 적는다.**

| | 판정 |
|---|---|
| 배제했다 | 「소리 줄이 프롬프트에 도달하지 않는다」 — 5,223자 안에 1건 있고 §1 이 실측했다 |
| 배제했다 | 「대조군에서도 tool 이 안 온다(환경 고장)」 — 팔 B 5/5 |
| ⛔ 배제하지 못했다 | 「소리 줄이 코칭·tool 도착을 바꾸는가」 — 목표 소리가 없는 오디오로는 원리적으로 잴 수 없다 |
| ⛔ 배제하지 못했다 | 「모델이 소리 키를 관사 지시로 읽는가」 — 둘째 초점이 같은 낱말을 요구해 교란된다 |

**시사(단정 아님)**: 소리 줄이 *"this is a pronunciation focus, not a grammar one"* 을 문장으로
말하는데도 21회 전부 문법 지시가 나왔다. `nova.py:195~196` 이 *"`an` 이 관사라서 소리 키가 관사
지시로 읽힌다"* 로 미리 지목한 형태와 같다. ⚠️ 그러나 위 교란 때문에 **원인으로 단정하지 않는다.**

**다음 회차의 조건 — 둘 중 하나를 만족해야 이 축을 잴 수 있다.**

1. **계획의 소리와 픽스처를 맞춘다** — DB 의 발음 패턴이 `pronunciation_an_as_a` **하나뿐**이므로
   (직접 조회: `frequency=2` · `next_review_at` 2026-09-04) 계획은 항상 그 소리를 고른다.
   그래서 **「an」을 「a」로 발음한 wav 를 만드는 것**이 필요하다(`gen_pq_fixtures.sh` · Qwen3 TTS).
2. **초점을 하나로 둔 팔을 만든다** — 문법 초점이 같은 낱말을 요구하지 않게 해야 교란이 사라진다.
   ⛔ 계획을 손으로 지어내는 것은 「제품이 보내는 것」이 아니게 되므로, 그 팔은 **하네스 팔로
   이름 붙이고** 제품 팔과 섞지 않는다.

## 4. 회차 뒤 DB — 무변경 확인

| 표 | 값 |
|---|---|
| `error_patterns` · `review_tasks` · `analysis_jobs` · `learning_sessions` · `pronunciation_attempts` | 9 · 15 · 57 · 17 · 7 — **회차 전과 같다** |
| `session_plans` · `learner_notes` | 3 · 4 — §1 의 계획 재생성으로 늘어난 그대로다(회차가 더 늘리지 않았다) |
| baseline drift | `harness_pattern_baseline` **0** · `harness_review_task_baseline` **0** |

⇒ **스파이크 팔은 DB 에 쓰지 않는다**(세션을 만들지 않는다). 이 회차가 공유 DB 에 남긴 변경은
§1 의 계획 1건과 노트 1건뿐이다.
