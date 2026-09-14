# 회차 — `TASK-129`: **일반 세션**에서 계획의 복습 목록이 발음 키를 되풀이하는가

세션 `ohmyenglish-65` · 2026-09-14 23:49 KST 착수 · 태스크 `TASK-129` · 비용 승인 **결정 96**
· 범위 근거 `docs/design/2026-09-12-decision72-sound-as-candidate.md` §3(그 설계가 이 경로를
「범위 밖 · 측정 대상」으로 남겼음)

> ⛔ **앞 세 회차와 다른 것은 「모드」임.** `TASK-120` · `TASK-123` · `TASK-128` 은 전부 **발음 전용
> 모드**에서 쟀고 거기에는 계획 블록이 실리지 않음. 이 회차는 **모드를 주지 않는 일반 세션**이고
> 계획 블록이 실림 — `plan.py:320` 이 발음 due 패턴을 `target sound "키"` 로 이름 지어 내는 자리가
> 그 안에 있음.
>
> ⚠️ **이 회차는 앞 회차들을 대체하지 않음.** 그 셋이 「전용 모드에서 후보만 남겨도 되풀이한다」를
> 3회 연속 확정했고(`f_as_p` 3/3 ×3회차) 이 회차는 **일반 세션에서도 도는가**를 잼.

---

## 0. ⛔ 상한과 해석 규칙 — **돌리기 전에 적음**

### 스택 — 공유 자원을 건드리지 않음

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 **`ohmyenglish_t129`**(소유자 `ohmy`) · 마이그레이션 **024 까지** 적용 |
| ⚠️ dev 와의 차이 | dev DB 는 **023** 임(결정 93). 즉 이 회차의 스택은 `signal_source` 값역이 **넓음** |
| 백엔드 | **`:8023`** · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · `health=200` 확인 |
| 하네스 | `ws_session.py --wav pq13.wav,pq13a.wav --url ws://localhost:8023/ws/session --no-register` |
| ⛔ 모드 | **주지 않음** — `--mode` 를 비우면 일반 세션임(`ws_session.py` `--mode` 도움말) |
| 사용자 | 고정 시드 `00000000-…-0001` · `Asia/Seoul` · `A2` |
| 공유 자원 | 공유 dev DB(`ohmyenglish`) · `:8002` 를 **건드리지 않음.** 회차 전 기준선을 아래에 떴음 |

**dev DB 회차 전 기준선**(직접 조회): `learning_sessions=17` · `pronunciation_attempts=7` ·
`error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15`.

### ⛔ 하네스가 제품 규약을 우회한 개입 둘 — 숨기지 않고 적음

1. **`next_review_at` 을 SQL 로 당겼음.** `p8_inject_pronunciation.py inject --sound f_as_p` 가 만든
   패턴의 `next_review_at` 은 `now() + 1일`(`review.STAGE_DAYS[0]`)이라 **오늘 due 가 아님** — 계획의
   due 목록에 걸리지 않음. 그래서 검증 전용 DB 에서만
   `update error_patterns set next_review_at = now() - interval '1 hour'` 를 돌렸음.
   ⚠️ `review.py` 머리주석이 자기를 그 컬럼의 **유일한 writer** 로 못박았으므로 이것은 **하네스가 강제한
   값**이고 제품 경로가 만든 값이 아님. 되풀이 판정에는 개입하지 않음(계획에 실리게 하는 전건일 뿐임).
2. **`summarize_session` · `summarize_week` job 의 `available_at` 을 30일 뒤로 밀었음.** 세 job 이 같은
   시각에 pending 이라 `p5_worker_leg.py claim` 이 계획 job 을 집는다는 보장이 없음. 검증 전용 DB 라
   남의 job 이 없음.

### 비용 — 실제로 쓴 것

| 무엇 | 수 |
|---|--:|
| Claude 계획 호출 | **2회** — 1회는 계약 거부(후행 쉼표), 재시도 1회가 저장 성공 |
| Nova 세션 | **상한 4회**(판별 3 + 예비 1). ⛔ 중간에 늘리지 않음 |

⚠️ **`llm_calls` 로는 이 비용을 셀 수 없음** — `p5_worker_leg.py:395` 가 `usage_sink` 없이
클라이언트를 만들어 사용량을 적지 않음(실측 0행). **하네스의 한계이고 제품 결함이 아님**
(`claude_client.py:129` 이 `usage_sink` 를 주입 인자로 두고 실물 배선은 `ws.py`·`main.py` 에 있음).

### 픽스처와 심은 키의 대조 — 판별 장치

| 오디오 | 오디오의 오류 | 심은 키 | 맞는가 |
|---|---|---|---|
| `pq13` → `pq13a` | /r/→/l/ ×5 (`blother allive ealy tomollow molning`) | **`f_as_p`** | ⛔ **의도적으로 어긋냄** — 그 문장에 /f/ 가 한 자리도 없음 |

⛔ **`TASK-120` 이 만든 조건을 그대로 씀** — 오디오에 없는 소리를 심어야 「들은 것을 따라간 기록」과
「지시문의 키를 되풀이한 기록」이 갈림. `TASK-129` AC#2 가 요구하는 판별 방법이 이것임.

### 돌리기 전 프롬프트 실측 — 문면의 정본

두 프롬프트를 제품 로더로 재현해 이 디렉터리에 뒀음(`build_plan_prompt.py.txt` ·
`build_general_prompt.py.txt` · 산출 `prompt_plan.txt` · `prompt_general.txt`).

| 프롬프트 | 길이 | 키가 실린 자리 |
|---|--:|---|
| 계획 생성(Claude) | **5,079자** | 16행 `target sound "f_as_p"` (← `plan.py:320`) · 28행 발음 집계 `f_as_p` |
| 일반 세션(Nova) | **4,927자** | 32행 정적 예시 `such as th_as_s or f_as_p` · 37행 후보 목록 `f_as_p` · 46행 계획의 힌트 `model the /f/ word once` |

**저장된 계획**(`session_plans` 1행 · `source=agent`): 초점이 `pronunciation_f_as_p` 하나이고,
Claude 가 그 키에서 **맥락과 힌트까지 파생**시켰음 — 맥락 다섯이 `weekend food and Friday plans` ·
`phones and favourite apps` 처럼 **f 가 많은 주제**이고 힌트가 `/f/ word` 를 지목함.

### ⛔ 이 회차가 **가르지 못하는 것** — 먼저 적음

키가 모델에 닿는 경로가 **넷**이고 이 회차는 그중 하나만 떼어내지 못함.

1. `plan.py:320` 의 `target sound "f_as_p"` → 계획 초점 → 세션 프롬프트의 힌트·맥락
2. 후보 목록(`Sounds this learner has missed before`) — **`error_patterns` 에서 오므로 due 여부와
   무관하게** 실림. 즉 계획을 지워도 이 블록은 남음
3. 규칙 10 의 **정적 예시** `such as th_as_s or f_as_p` — 학습자 데이터와 무관하게 프롬프트에 박혀 있음
4. 계획 블록의 `Pronunciation is today's focus` 문면(결정 72 가 남긴 줄 · 키 이름은 없음)

⇒ **되풀이가 관측돼도 「`plan.py:320` 만 고치면 사라진다」로 읽지 않음.** 이 회차가 답하는 것은
**「일반 세션에서 그 고리가 도는가」**와 **「그것이 조건부 재사용의 정상 작동인가」**임.

### 팔과 상한

| 팔 | 회차 | 재는 것 | 기준선 |
|---|--:|---|---|
| **판별** | **3** | 기록된 `target_sound` 가 오디오에 **없는** 키 `f_as_p` 를 되풀이하는가 | 전용 모드에서 `f_as_p` **3/3 × 3회차** |

### ⛔ 해석 규칙 — 판정선을 먼저 정함

| 결과 | 읽는 법 |
|---|---|
| `f_as_p` 가 **2/3 이상** | **일반 세션에서도 되풀이가 남.** 오디오에 /f/ 가 없으므로 후보 블록의 조건절(*"If one of them is off again"*)이 참일 수 없음 ⇒ **조건부 재사용이 아니라 구멍임**(AC#2 가름) |
| `f_as_p` 가 **아닌 키**가 **2/3 이상** | 일반 세션 경로에서는 되풀이가 나지 않음 ⇒ `plan.py:320` 을 고칠 근거가 이 관측에는 없음(AC#3 는 「고치지 않음」쪽) |
| 발음 코칭이 **0/3** | ⛔ **별 관측값이고 이 축을 시험하지 못함.** 일반 세션에서 발음 코칭이 밀려나는 것은 `TASK-81` 의 축임 — 「고쳤다」로 읽지 않음 |
| tool 이 **0/3** (코칭은 났으나 기록이 없음) | 기록 경로가 열리지 않은 것 ⇒ 되풀이를 판정하지 않음. `TASK-97`·`TASK-116` 축의 재료로 남김 |
| 갈림(1:1:1 꼴) | ⛔ 표본 3 으로 비율을 말하지 않음 — **방향 없음**으로 적음 |
| 세션이 `session_failed` | 환경 고장이므로 판정하지 않음 |

⚠️ **코칭 발생과 tool 도착을 갈라 셈**(결정 51).
⚠️ **발화로 지목한 소리를 원문으로 인용해 적음** — `target_sound` 값만 보면 어긋남이 보이지 않음
(`TASK-128` B1 이 그 함정의 실측임: 발화와 기록이 **함께** 틀렸음).
⛔ **미리 적은 이 표에 결과를 억지로 끼워 넣지 않음** — 표에 없는 모양이 나오면 새 행으로 적음.

---

## 1. 결과 — **일반 세션에서도 되풀이가 났고(3/3), 결정 82 의 검사는 한 건도 표시하지 못했음**

**Nova 4세션을 썼음**(상한 4). **죽은 회차 1** — `T129-B1` 은 내가 `--timeout` 기본값 30초로 돌려
코칭 왕복이 프레임에 담기지 않았음(앞 회차 러너는 120 을 씀). ⛔ **상한을 늘리지 않고 예비 1회를
그것에 썼음.** 판별 팔은 `T129-B2`·`B3`·`B4` 셋임.

### 판별 팔 — `pq13`→`pq13a`(/r/→/l/ ×5) · 계획이 고른 키 **`f_as_p`** · 일반 세션 3회

| 세션 | 코칭 | tool | 기록된 `target_sound` | `target_form` | 코치가 지목한 것(발화 원문) | `sound_check` |
|---|:--:|:--:|---|---|---|---|
| B2 `51c81e86` | 남 | 1 | **`f_as_p`** | `early` | *Sorry, I need to hear that word again. Can you say "early" one more time for me?* | (빈칸) |
| B3 `485c8f42` | 남 | 1 | **`f_as_p`** | `early` | *I see. Your brother is arriving early tomorrow morning.* | (빈칸) |
| B4 `5117f28e` | 남 | 1 | **`f_as_p`** | `early` | *Sorry, I need to hear that word again. Can you say "early" one more time for me?* | (빈칸) |

**기록은 3/3 으로 계획이 고른 키였음.** §0 의 「`f_as_p` 를 2/3 이상」 행이 성립함.
⛔ **그 오디오에 /f/ 가 한 자리도 없으므로 후보 블록의 조건절(*"If one of them is off again"*)이
참일 수 없음** ⇒ 조건부 재사용의 정상 작동이 아니라 **구멍임**(AC#2 의 가름).
⚠️ **코치가 지목한 것은 `early`** 이고 그것은 /r/ 낱말임 — 즉 **코칭은 들은 것을 따라갔고 기록만
키를 따라갔음.** `target_form` 도 `early` 로 옳게 실렸음. 어긋난 것은 `target_sound` 한 칸임.

### ⛔ 표에 없던 모양 둘 — 새 행으로 적음

**① 결정 82 의 어긋남 검사가 이 경로에서 한 건도 표시하지 못했음.** `sound_check` 가 세 행 모두
비어 있음. 추론으로 두지 않고 `sound_check_verdict(코치 발화, 'f_as_p')` 를 실제 발화로 직접 돌려
**세 세션 모두 `None`** 을 얻었음(`results.txt` 마지막 절). 사유는 계약 그대로임 — **코치가 소리를
인용하지 않았음**(낱말 `early` 만 말함). `pronunciation.check_recorded_sounds` 는 「어긋남을 증명할
수 있을 때만」 표시하므로 비워 두고 지나감.
⇒ **`review.py:197` 의 조건(`sound_check is null or <> 'mismatched'`)에 그대로 걸려 복습 시계가
전진했음**: `error_patterns.frequency=4` · `next_review_at=2026-09-15` · `review_tasks` 4행(최신
`pending` · 앞의 셋은 `abandoned`). ⛔ **즉 `TASK-116.1` 이 이행한 방어가 일반 세션에서는 무력함** —
전용 모드 회차(`TASK-128` ARM-B)에서 코치가 *"the 'er' sound"* 처럼 **소리를 인용했기 때문에** 그
방어가 발화할 수 있었던 것임. 일반 세션의 코치는 소리를 인용하지 않음(3/3).

**② ASR 이 오류 오디오를 정답 문장으로 전사했음.** `pq13` 의 다섯 오류
(`blother allive ealy tomollow molning`)가 전사문에서 전부 사라져 네 세션 모두
*"my brother will arrive early tomorrow morning."* 으로 왔음(`prompt`·프레임 실측).
⇒ **이 회차의 코칭은 오디오의 오류를 듣고 난 것이 아님** — 들을 근거가 전사문에 없는데도 코치가
`early` 를 붙잡았고, 그 이유로 남는 것은 프롬프트가 준 재료(계획의 `/f/ word` 힌트 · f 가 많은 맥락
다섯 · 후보 목록)뿐임. ⛔ **기전을 단정하지 않음** — 표본 3 이고 오디오 판정 없이는 「코치가 실제로
무엇을 들었는가」를 이 회차가 가르지 못함(`TASK-116.1` AC#4 가 적어 둔 맹점과 같은 자리임).

### 비용과 정리

| 무엇 | 실측 |
|---|---|
| Nova 세션 | **4**(판별 3 + 죽은 1) · `session_failed` 0건 |
| Claude 계획 호출 | **2**(계약 거부 1 · 성공 1) |
| `llm_calls` | **0행** — 하네스가 `usage_sink` 를 주입하지 않음(제품 결함 아님) |
| 정리 | 백엔드 `:8023` 종료(리스너 0) · `dropdb ohmyenglish_t129` 완료 · DB 목록에 `ohmyenglish`·`_smoke`·`_test` 만 남음 |
| dev DB 무오염 | 회차 전후가 **같음** — `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15` |

### AC 판정

- **AC#1(센다)** — 충족. 되풀이 **3/3**.
- **AC#2(가른다)** — 충족. 오디오에 없는 소리를 심어 판별했고 **조건부 재사용이 아니라 구멍**임.
- **AC#3(그 줄을 고칠지 정한다)** — ⛔ **이 회차는 「`plan.py:320` 만 고치면 사라진다」를 지지하지
  않음.** §0 이 미리 적은 대로 키가 닿는 경로가 넷이고, 그중 **후보 목록은 `error_patterns` 에서
  오므로 계획을 지워도 남음.** 그리고 이 회차가 새로 관측한 것은 **방어(결정 82)가 이 경로에서
  발화하지 못한다**는 것이라, 고칠 자리의 후보가 「계획 줄」보다 넓어졌음. ⇒ **제품 판단으로 올림.**
