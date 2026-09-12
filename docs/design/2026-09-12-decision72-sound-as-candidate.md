# 결정 72 구현 설계 — 오늘의 소리를 «이름으로» 주지 않고 «후보»로 내려받는다

세션 `ohmyenglish-19` · 2026-09-12 KST · 결정 정본은 `docs/ops/captain-instruction-register.md`
(**결정 72**) · 태스크는 `TASK-128`

> **왜 설계서를 따로 쓰는가**: 이 변경이 세 파일(`nova.py`·`api/ws.py`·`audio_gateway/factory.py`)의
> 조립 계약을 건드리고 **실물 회차를 요구**한다. 즉흥으로 고치면 어느 계약이 왜 바뀌었는지가 커밋
> 메시지에만 남는다.

---

## 1. 좋은 소식 — **후보 기제가 이미 있다**

처음 예상보다 변경이 작다. `build_system_prompt` 이 이미 「후보」 형태의 블록을 만든다
(`nova.py:483-492`):

```
Sounds this learner has missed before:
th_as_s, f_as_p
If one of them is off again, reuse that exact key as target_sound instead of
inventing a new one — repeat offenders must group under one key.
```

⛔ **이 블록은 고리의 구동부가 아니다.** 조건이 *"If one of them is off again"* — **실제로 어긋났을
때만** 재사용하라는 것이므로 모델이 없는 오류를 발명할 이유가 없다. 결정 72 가 말하는 「후보로만
내려받는다」가 **정확히 이 모양**이다.

고리를 구동한 것은 **단수 지목**이다 — `_SOUND_INSTRUCTION` 의 `- Sound to coach today: "{sound}"`.
실측이 세 판에서 같았다(강제판·조건판·제거판 전부 계획 키를 되풀이했다).

## 2. 바꾸는 것 — 세 자리

| # | 자리 | 무엇 | 왜 |
|--:|---|---|---|
| **C1** | `nova._SOUND_INSTRUCTION` | `{sound}` **단수 지목을 없앤다.** 줄 자체는 남긴다 | 결정 56(질문 목록보다 앞)과 결정 75(규칙 9·4 대체)가 그 줄에 살아 있다 — ⛔ 줄을 지우면 그 둘이 함께 죽는다 |
| **C2** | `nova.build_pronunciation_prompt` | 인자를 `sound: str` → **`known_sounds: Sequence[str]`** 로 바꾸고, 전용 프롬프트에도 **후보 블록**을 싣는다 | 전용 모드에는 지금 후보가 **하나도** 없다(팩토리가 놓친 소리 목록을 뺀다). 단수 지목만 빼면 코치가 아무 재료 없이 시작한다 |
| **C3** | `api/ws.py` + `audio_gateway/factory.py` | 모드 판정을 「소리 키가 오면」 → **「`?mode=pronunciation` 이면」** 으로 바꾼다. `_pronunciation_sound_or_none` 는 **삭제하지 않고** 역할을 바꾼다(초점 후보를 목록에 **더하는** 것) | 결정 72 가 전용 모드의 뜻을 「오늘의 소리」에서 **「발음만 다룬다」**로 바꿨다. 소리가 없으면 모드가 안 열리는 지금 규약이 그 뜻과 어긋난다 |

⛔ **C1 의 문면 초안** — 실측 전에는 초안일 뿐이다:

```
- Pronunciation is today's focus: the learner's problem is how words sound, not which
  word to pick. When a sound is off in what you actually hear, take it up on that turn
  instead of the Grammar first rule 9, and spend the one correction you make that turn
  on this sound rather than on grammar. Stop and have them say just that word again.
  This outranks the question list and the sentence-shape target below: pause the current
  question, coach the sound, then come back to the question you paused. Rule 10 still
  applies unchanged: call the report_pronunciation_coaching tool twice — once with
  outcome "pending" right after you model it, and again with the judgement once you have
  heard the repeat.
```

⚠️ `{grammar_first}` 칸은 **그대로 둔다**(결정 71) — 전용 모드는 빈 문자열.

## 3. ⛔ 범위 밖으로 두는 것 하나 — 그리고 그 이유

`plan.py:319-321` 이 due 패턴을 계획 블록에 실을 때 발음이면 `target sound "키"` 로 **키를 이름으로**
낸다. 이것도 프롬프트에 키를 넣는 **둘째 경로**다.

⛔ **이번에 건드리지 않는다.** 그 줄은 **모든 카테고리**의 복습 목록을 만드는 공용 기제이고
(`pattern_id` 를 함께 실어야 하는 계약이 리뷰 Critical-1 로 걸려 있다), 발음만 빼면 「복습 예정인데
계획에 안 실린 패턴」이 생겨 다른 결함을 만든다. **그리고 그 경로는 전용 모드에 존재하지 않는다**
(계획 블록을 싣지 않으므로). ⇒ 일반 세션에서 그 경로가 되풀이를 일으키는지는 **측정 대상**이고 새
태스크로 남긴다.

## 4. 검증 — 회차 설계의 골격

⛔ **상한과 해석 규칙은 그 회차 기록의 §0 이 소유한다** — 여기서 정하지 않는다. 팔 둘만 못박는다:

| 팔 | 조건 | 재는 것 | 기준선 |
|---|---|---|---|
| **회귀** | `pq06`→`pq12` · 후보 `th_as_s` | 코칭이 유지되는가 | ARM-A **4/4** |
| **판별** | `pq13`→`pq13a` · 후보 **`f_as_p`**(오디오에 없음) | 기록된 `target_sound` 가 **`f_as_p` 가 아닌 것**이 되는가 | 지금까지 **`f_as_p` 3/3 ×2회차** |

⛔ **판별 팔의 성공 조건이 이전과 «반대»다.** 지금까지는 「계획 키가 실린다」가 결함이었고, 이제는
**「계획 키가 실리지 않는다」가 성공**이다. 그 소리가 오디오에 없으므로 코치는 실제로 들은 소리
(/r/ 계열)를 골라야 하고 기록도 그것을 따라야 한다.
⚠️ **후보 목록에 `f_as_p` 를 그대로 둔다** — 후보 기제가 「없는 소리를 발명하지 않는다」를 지키는지
함께 재기 때문이다. 후보에서 빼면 그 판별력이 사라진다.

## 5. 감수한 대가 — 결정이 명시한 것을 여기 옮겨 적지 않는다

⛔ 대가 둘(간격 반복이 느슨해짐 · 전용 모드의 뜻이 바뀜)의 정본은 **결정 72 항목**이다.
여기서 재서술하면 한쪽이 낡는다.

⚠️ **다만 구현이 만드는 대가 하나를 더 적는다**: `build_pronunciation_prompt` 의 인자가 바뀌므로
`test_nova.py` 의 **바이트 게이트가 깨지고** 그 게이트가 가리키는 회차가 네 번째로 바뀐다.
그 이력은 게이트 독스트링이 갖는다 — 판을 세 개까지 적어 뒀고 네 번째를 더한다.
