# TASK-99 AC#1 회차 — 도달성을 재고 **잠재 결함으로 등급을 내렸음**

> 소유 `TASK-99` AC#1. 세션 `ohmyenglish-40`(테스트 하네스 갈래) · 2026-09-11 · 브랜치
> `design/first-vertical-slice`. 분석 모델은 `us.anthropic.claude-opus-5` 다(`Settings.claude_model_id`).
>
> ⛔ **판정 요지 세 줄.**
>
> 1. **얻은 것**: 실물 분석 18회에서 `pronunciation_` 접두 `pattern_key` **0건** ·
>    금지 카테고리 `pronunciation_intonation` **0건** · 발음 키 재사용 **0건**이고,
>    그 0 을 읽을 수 있게 하는 **판별력 시험을 4/4 로 통과**했음.
> 2. ⛔ **잃은 것**: 양성 대조로 둔 **팔 B 도 0** 이었음 — 그래서 이 회차는 「G-8 필터가
>    없으면 재사용이 일어난다」를 **입증하지 못했음.** 표본 9의 상한 안에서만 참임.
> 3. ⛔ **등급을 내리면서 남는 것 둘**: 앱이 `category='pronunciation_intonation'` +
>    `pronunciation_intonation_<x>` 조합을 **막지 않음**(판별력 시험 c1 이 `accepted`).
>    그리고 접두를 헷갈린 조합은 `frequency` 문제가 아니라 **그 발화의 분석 전체 실패**임(c2).

---

## 1. 무엇을 재려 했나

`TASK-99` 는 `error_patterns.frequency` 를 두 writer 가 서로 덮는 것을 실측한 태스크다
(개수를 가른 조건에서 2 → 1 · `last_seen_at` 이 과거로 이동 · 독립 2회 재현). **덮기가
일어나려면 문법 경로가 발음 행의 `pattern_key` 를 집어야 한다.** 그 도달성이 이 회차의 대상이다.

경로는 둘뿐이다.

| 경로 | 무엇 | 상태 |
|---|---|---|
| ① 프롬프트에 실려 재사용 | 발음 키가 문법 프롬프트에 들어가 모델이 그대로 재사용 | **닫혀 있음** — `load_existing_patterns` 가 `UNJUDGEABLE_CATEGORY` 를 제외함(G-8) |
| ② 모델이 지어냄 | 모델이 `pronunciation_` 접두 키를 스스로 만듦 | 이 회차가 잼 |

⛔ **① 에는 회귀 보호가 이미 있음** — `tests/integration/test_pipeline.py` 가 발음 카테고리 행을
넣고 `load_existing_patterns` 가 그것을 빼는지 재는 테스트를 가진다. 즉 ① 은 조용히 되돌아오지 않는다.

## 2. ② 의 문턱은 코드가 정해 둠 — 관측 전에 읽었음

`resolve_pattern_keys` 가 upsert **앞에서** 신규 키에 `is_valid_new_pattern_key` 를 걸어
`^{category}_[a-z0-9_]+$` 를 강제한다. 그래서 조합마다 결과가 갈린다.

| 모델이 낸 것 | 앱의 처리 | 뜻 |
|---|---|---|
| 문법 카테고리 + `pronunciation_…` 키 | `AnalysisValidationError` | **그 발화의 분석 전체가 실패**한다 — 덮기가 아니라 교정 유실이다 |
| `pronunciation_intonation` + `pronunciation_intonation_<x>` | **통과한다** | 문법 경로가 발음 카테고리 행을 만든다 |
| 기존 발음 키를 **재사용** | **통과한다**(재사용은 형식 검사를 받지 않는다) | 정확히 덮기 경로다. 단 ① 이 그 키를 프롬프트에서 뺀다 |

⛔ **태스크 설명의 「앱 쪽 검증은 없고」는 이 지점에서 부정확하다** — 검증이 하나 있고, 그것이
문법 카테고리 갈래를 막는다(대신 다른 실패로 바꾼다).

⚠️ **정확 충돌 조건**: 통과하는 조합이 만드는 키는 `pronunciation_intonation_<x>` 이고 기존 발음
행의 키는 `pronunciation_<target_sound>` 다. 둘이 같아지려면 `target_sound` 가 `intonation_<x>`
여야 한다. **DB 실측 `target_sound` 값역은 `am_as_i_m` · `an_as_a` · `w_as_vw` 셋이고 해당이 없다.**

## 3. 방법 — 두 팔과 판별력 시험

| 팔 | 프롬프트에 실린 패턴 | 무엇을 재나 |
|---|---|---|
| A 제품 | **8건** (발음 행 없음) | 제품 그대로에서 모델이 지어내는가 |
| B 무력화 대조 | **9건** (`pronunciation_an_as_a \| pronunciation_intonation` 포함) | 필터가 없으면 재사용하는가 |

전사문 9개는 **발음을 유발하려고** 고른 것이다 — 발음을 말로 꺼내는 것(`my pronunciation is very
bad` · `accent is strong` · `r and l sound`)과 음소 혼동이 전사문에 흔적을 남긴 것
(`sink`/`think` · `rice`/`lice`)이고, `t8` 은 팔 B 의 재사용을 노려 `an` 자리에 `a` 를 두었다.
`t9` 는 발음과 무관한 순수 문법 대조군이다.

⛔ **판별력 시험을 따로 두었다** — 팔 B 까지 0 이 나와서 **검출기가 볼 수 있는지를 증명하지
않으면 이 회차 전체를 읽을 수 없기** 때문이다. Bedrock·DB 를 쓰지 않는 무력화 대조 4건이다.

## 4. 결과

```
A_product_filtered:   n=9  pron_category=0  pron_prefix=0  reused=0  rejected=0
B_control_unfiltered: n=9  pron_category=0  pron_prefix=0  reused=0  rejected=0
snapshot_unchanged=True
```

판별력 시험 (같은 스크립트 `--self-check`):

```
PASS c1_forbidden_category_new_key   got=(1, 1, False, False)  resolve=accepted
PASS c2_grammar_category_pron_prefix got=(0, 1, False, True)   resolve=AnalysisValidationError
PASS c3_reuses_existing_pron_key     got=(1, 1, True,  False)  resolve=accepted
PASS c4_negative_control_clean       got=(0, 0, False, False)  resolve=accepted
self-check failures=0
```

findings 총 **32건**의 카테고리 분포: `verb_form` 13 · `verb_tense` 12 · `article` 6 ·
`business_expression` 1. **발음 카테고리는 0이다.**

⛔ **가장 값어치 있는 단서는 팔 B 의 `t8` 이다** — 프롬프트에 `pronunciation_an_as_a` 가 실려
있고 전사문이 정확히 그 오류(`a amazing`)인데, 모델은 그것을 **무시하고 새 문법 키
`article_a_vs_an_before_vowel` 를 만들었다.** 즉 모델은 an/a 오류를 문법으로 분류한다.

⚠️ **DB 에 쓰기가 0건이다** — 전후 스냅샷이 같다(`snapshot_unchanged=True`). 이 회차는
`resolve_pattern_keys` 까지만 부르고 저장 단계를 부르지 않는다.

## 5. 판정 — 잠재 결함으로 내림 (AC#1)

**근거 셋.**

1. 경로 ① 은 필터로 닫혀 있고 **회귀 테스트가 그것을 지킨다.**
2. 경로 ② 는 실물 18회에서 0건이고, 그 0 은 **판별력 4/4 로 뒷받침된다.**
3. 통과 가능한 유일한 조합이 만드는 키와 기존 발음 행의 키가 **지금 값역에서는 겹칠 수 없다.**

## 6. ⛔ 이 회차가 «말하지 않는» 것 — 등급을 내리면서 함께 남기는 것

1. **표본 상한.** 팔당 9회다. 「모델이 절대 안 낸다」가 아니라 「가장 불리하게 고른 9회에서
   나지 않았다」가 관측된 것이다.
2. ⛔ **팔 B 가 발화하지 않았으므로 G-8 필터의 «필요성»은 입증되지 않았다.** 그 필터를
   지워도 이 표본에서는 재사용이 0이었다. **필터를 지우자는 근거로 이 회차를 인용하면 안 된다** —
   이 회차는 필요성에 대해 음성 결과이고, 필터의 값은 「모델이 한 번이라도 재사용하면 데이터가
   손상된다」는 비대칭에 있다.
3. **남은 위험 둘이 열려 있다.**
   - 앱이 `pronunciation_intonation` 카테고리를 **값역에 갖고**(`ErrorFinding.category`)
     금지는 프롬프트 문구뿐이다. 모델이 한 번 쓰면 문법 경로가 **발음 카테고리 행을 만든다** —
     R10-3(전사문 경로는 발음을 판정하지 않는다)에 어긋나고, 뒤에 Nova 가 그 소리를 내면
     **두 writer 공유 행**이 된다. 지금 충돌 대상이 없다는 것은 **한 발 남았다**는 뜻이다.
   - 접두를 헷갈린 조합은 그 발화의 **분석 전체를 실패**시킨다. 관측 0건이지만 경로는 열려 있다.
4. **`AnalysisValidationError` 갈래에는 전용 회귀 테스트가 없다.** `test_analysis.py` 가 재는 것은
   형식 위반 일반(`missing_article_before_gym`)이고 `pronunciation_` 접두 사례는 아니다.

⚠️ **같은 실패 «모양»이 계획 경로에도 있다** — 동료 세션(`ohmyenglish-7f`)이 같은 날
`TASK-109`(모델이 없는 키를 붙여 계획 전체가 버려진다)를 등록했다. 즉 「모델이 규격 밖 키를 내면
그 산출 전체가 버려진다」는 이 리포의 **반복되는 형태**이고, 분석 경로의 그 갈래(위 3번 둘째)가
관측 0건이라는 것이 「일어나지 않는다」를 뜻하지 않는다는 근거가 하나 더 생겼다.

## 7. 재현

```bash
cd app/backend
.venv/bin/python ../../tests/harness/runs/2026-09-11-task99-reachability/reach_probe.py --self-check   # 판별력 · 무료
.venv/bin/python ../../tests/harness/runs/2026-09-11-task99-reachability/reach_probe.py                # 실물 18회 · Bedrock
```

원자료는 `observations.json` 이다 — 팔별 프롬프트 패턴 목록 · 응답 전문 · 전후 스냅샷을 담는다.
⚠️ **`app/backend` cwd 에서만 import 가 풀린다**(`H-AV`).
