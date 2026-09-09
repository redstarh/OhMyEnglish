# 회차 기록 — 앱 프롬프트에서 발음 tool 이 불리지 않는 원인 조사 (TASK-67)

> **판정: 원인 둘을 확정하고 후보 둘을 배제했음. 그러나 프롬프트 수정으로는 닫히지 않음** —
> 다섯 가지 문구로 고쳐도 tool 이 오지 않았고, 작동하는 유일한 수단(`toolChoice`)은 **음성 발화를
> 없앰.** 그래서 구조 결정이 필요하고 `TASK-67` 을 `Awaiting Decision` 으로 둠.
>
> 모든 팔을 **같은 픽스처(`p1k.wav`)** 로 이 세션에서 **내가 직접** 돌렸음. 남의 관측을 A/B 의 한
> 쪽으로 쓰지 않았음 — 기준선도 내가 다시 재현했음.
>
> ⛔ **`toolConfiguration` 은 모든 팔에서 같음**(`--tool-choice` 팔만 예외이고 그것이 잰 변수임).
> 스파이크의 `_tool_configuration()` 이 `app_prompt` 와 무관하게 앱 상수를 싣는 것을 코드로 확인했음
> — 즉 프롬프트 팔들 사이의 차이는 **시스템 프롬프트 글자뿐**임.

## 1. 팔 열 개 — 무엇을 바꿨고 무엇이 왔는가

| 팔 | 시스템 프롬프트 | `toolChoice` | `toolUse` | 발화 |
|---|---|---|--:|---|
| **양성 대조** | 스파이크 전용 (317자) | 없음 | **1** | 코칭(문장 되읽기 + 재발화 요청) |
| 기준선 | 앱 `SYSTEM_PROMPT` (2,339자) | 없음 | 0 | `I'm sorry, I didn't catch that.` |
| H1 | 앱 + 규칙 10 앞에 `You MUST` (**+9자**) | 없음 | 0 | 코칭 |
| H2 | 앱 − 규칙 1~7 (1,394자) | 없음 | 0 | 코칭 + **소리 지목**(`th`) |
| H3 | 앱, 규칙 10 을 즉시·단일 호출로 (−35자) | 없음 | 0 | 코칭 |
| **H4** | **양성 대조 + 규칙 9 게이트 문장만** (+198자) | 없음 | 0 (**n=2**) | **문법으로 라우팅** |
| **H5** | **양성 대조, tool 문장만 앱 규칙 10 으로** | 없음 | 0 | `I didn't catch that clearly.` |
| 수정 후보 | 앱, 규칙 9·10 둘 재작성 (+51자) | 없음 | 0 | **발음 문제 없다고 판정** |
| **기제 탐침** | **앱 그대로 (한 글자도 안 바꿈)** | `tool` | **1** | **없음** (`audioOutput` 0) |
| 기제 탐침 | **앱 그대로** | `auto` | 0 | 코칭 |

실행 11회(H4 만 2회). 원자료는 `.harness/evidence/P-tooluse-*-p1k-<UTC>.json` 에 팔별로 따로
있음 — `TASK-68` 이 파일명을 회차마다 다르게 바꿔서 서로 덮지 않음.

## 2. 확정된 원인 둘 — 양성 대조를 기준으로 단일 변수로 잼

⛔ **뺄셈이 아니라 덧셈으로 확정했음.** 앱 프롬프트에서 절을 빼는 방식(H1·H2·H3)은 셋 다 0건이라
무엇이 원인인지 가르지 못했음. **작동하는 프롬프트에 앱 요소를 하나만 더하는** 방향으로 바꾸자
곧바로 갈렸음.

**C1 — 규칙 9 의 게이트가 심한 발음을 문법으로 라우팅한다** (H4 · n=2).
양성 대조에 *"Grammar first. On most turns, correct grammar and leave pronunciation alone. Take up
pronunciation only when a sound is so far off … never for a mild accent."* 를 **한 문장만** 더하니
`toolUse` 가 1 → 0 이 됐고, 발화가 *"Let's make sure the grammar is correct."* 로 바뀌었음.
두 회차의 발화 문구가 **동일**해서 동전 던지기가 아님. 즉 모델이 발음 분기에 아예 들어가지 않음.

**C2 — 규칙 10 의 지시 형태가 호출을 막는다** (H5).
양성 대조에서 tool 문장 하나만 앱 규칙 10 으로 바꾸니 0건이 됐음. ⛔ **원인이 「강제력 낱말」이
아님** — H1 이 `You MUST` 를 더해도 0건이었음. 작동하는 형태는
*"Then you MUST call the … tool to report **what you heard**."* 이고, 앱 형태는 *"Call … **twice**:
once with outcome pending … and again … once you have heard the learner repeat it."* 임. H2 의 발화가
그 차이를 스스로 증언함 — *"I'll wait to hear your repetition before confirming your pronunciation."*
로 **명시적으로 미뤘음.**

## 3. 배제한 후보 둘

| 후보 | 판정 | 근거 |
|---|---|---|
| ④ 모델의 tool 우선순위·미지원 | ⛔ **배제** | 같은 픽스처·같은 `toolConfiguration` 으로 양성 대조가 `toolUse` 를 냈고, 기제 탐침은 **앱 프롬프트 그대로** 냈음 |
| ③ 규칙 2(one question, then stop)와의 경합 | ⛔ **필요조건 아님** | H4·H5 는 규칙 2 가 **없는** 프롬프트에서 실패를 재현했음 |
| ② 규칙 11(one-per-turn)과의 경합 | ⛔ **필요조건 아님** | 같은 이유 — H4·H5 에 규칙 11 이 없음. ⚠️ **충분조건인지는 재지 않았음** |
| ① 규칙 10 의 강제력 | ⚠️ **부분 확정** | 낱말(`MUST`)만으로는 아니고(H1 반증) **문장 형태**가 원인임(H5 확정) |

## 4. AC2 의 답 — 소리 지목 미이행과 tool 미호출은 **따로 움직인다**

- **H2**: 게이트가 있는데도 모델이 **소리를 지목했고**(*"focus on the 'th' sound in 'three'"*)
  재발화를 요청했음. 그런데 **tool 은 0건**임.
- **H4**: 게이트를 더하자 **소리 지목도 tool 도 없음** — 발음 분기에 들어가지 않았음.

즉 소리 지목은 **C1(게이트 통과 여부)** 에 걸리고 tool 은 **C2(규칙 10 의 형태)** 에 걸림.
**같은 원인이 아니고, 관측으로 갈랐음.**

## 5. AC4 의 답 — `target_sound` 누락의 원인은 프롬프트가 아니라 호출의 부재였다

`PRONUNCIATION_TOOL_SCHEMA_JSON` 의 `required` 는 **`["target_form", "outcome"]`** 이고
`target_sound` 는 **필수가 아님**(`app/backend/app/models/pronunciation.py`). 그래서 규칙 10 의
*"Always include target_sound"* 는 산문만으로 버텨야 함.

⛔ **그런데 강제 호출 팔의 payload 가 그것을 실었음**:
`{"target_sound":"th_as_s","target_form":"I think I found three very useful videos.","outcome":"pending"}`.
**앱 프롬프트를 한 글자도 바꾸지 않은 팔임.** 즉 이전에 관측된 `target_sound` 누락 4회는
**스파이크 프롬프트가 그것을 요구하지 않았기 때문**이고, 앱 프롬프트는 호출이 일어나면 실제로 채움.
⚠️ **`nova.py` 의 `_pronunciation_tool_configuration()` docstring 이 예측했던 것이 맞았음** — 그
예측이 이제 관측으로 확인됐음.

⚠️ **그것이 `services/pronunciation.py` 의 SQL 조건을 통과한다는 뜻은 아직 아님** — 그 조건은
`length(btrim(coalesce(target_sound,''))) > 0` 이고, 실물 앱 경로 세션에서 이 payload 가 저장되는
것까지는 이 회차가 보지 않았음.

## 6. 왜 프롬프트 수정으로 닫지 않았는가 — 구조 결정이 필요하다

C1·C2 를 둘 다 고친 **수정 후보**도 0건이었고, 그 회차의 모델은 오히려 *"That was a clear and
natural sentence."* 로 **발음에 문제가 없다고 판정**했음. 즉 게이트를 느슨하게 쓰면 분기 진입이
더 줄어듦. 문구 다섯 가지가 전부 실패했으므로 이 스킬의 규약대로 **더 고치지 않고 구조를 의심함.**

**기제는 있고, 대가가 있음.** `toolChoice: {"tool": {"name": …}}` 를 `promptStart` 에 실으면
Nova 가 **거부하지 않고** 앱 프롬프트 그대로 `toolUse` 를 냄. ⛔ 그런데 같은 회차에서
**`audioOutput` 이 0이고 코칭 발화가 사라졌음** — 강제하면 말을 하지 않음.
`auto` 는 생략과 같아서 발화는 있고 tool 은 없음.

**즉 지금 구조(프롬프트 하나·프롬프트당 `toolChoice` 하나)에서는 턴마다 둘 중 하나만 얻음.**
말하기 코치에게 발화를 잃는 것은 받아들일 수 없으므로 선택은 프롬프트 문구가 아니라 구조임 —
그 선택은 사람이 함.
