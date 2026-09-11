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

## 2. 회차 — 실행과 결과

(회차 실행 뒤 채운다)

## 3. 판정 재료

(회차 실행 뒤 채운다 — 판정 자체는 `TASK-86` 이 갖는다)
