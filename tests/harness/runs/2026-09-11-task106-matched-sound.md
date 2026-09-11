# 회차 — `TASK-106`: 소리 키를 픽스처의 실제 오류에 맞춘 **하네스 팔**

세션 `ohmyenglish-7f` · 2026-09-11 · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-11-task106-matched-sound/`

> **왜 이 회차가 있는가**: `TASK-105` 가 21회를 돌렸으나 계획이 지목한 소리(`an_as_a`)가 픽스처
> 오디오에 **없어서** tool 0/21 이 프롬프트가 아니라 픽스처로 예측됐다
> (`runs/2026-09-11-task105-sound-line.md` §3). 여기서는 **소리 키를 오디오의 실제 오류에 맞춘다.**
>
> ⛔ **이 팔은 제품 팔이 아니다.** 개발 DB 의 발음 패턴은 `pronunciation_an_as_a` 하나뿐이라
> 제품 계획은 그 소리만 고른다. 이 회차가 답하는 것은 **기전 질문 하나**다 —
> 「소리 줄의 소리가 오디오의 오류와 맞으면 발음 코칭과 tool 이 오는가」.

---

## 0. ⛔ 상한과 **해석 규칙** — 돌리기 전에 적는다

| 팔 | 프롬프트 | 회차 | wav |
|---|---|--:|---|
| **A2(hsound)** | 하네스 조립 5,232자 · 소리 줄 `th_as_s` | **8** | `p2m.wav` → `p2a.wav` |
| **B(base)** | 스파이크 짧은 프롬프트 · 대조군 | **2** | 같음 |

**Nova 세션 상한 10회.** ⛔ 중간에 늘리지 않는다.

**해석 규칙 — 무엇을 배제할 수 있는지 먼저 못박는다.**

| 결과 | 읽는 법 |
|---|---|
| tool 이 **여러 회** 온다 | 기전이 성립한다 — 「소리가 맞아야 코칭이 난다」가 `TASK-105` 의 0/21 을 설명한다 |
| tool **0/8** | ⛔ **「소리 줄이 무효」로 단정하지 않는다.** 코칭 기준율 13% 가정에서 `P(0 in 8)=0.33` 이므로 낮은 비율을 배제하지 못한다. 다만 **높은 비율(≥ 40%)은 배제된다**(`P(0 in 8 | 0.4)=0.017`) |
| 대조군 tool 0/2 | 환경 고장이므로 **판정하지 않는다**(판별력 없음) |

⚠️ **코칭 발생과 tool 도착을 갈라 센다** — `TASK-105` 에서 코칭 발화는 21회 전부 났는데 전부 문법
지시였다. 「코칭이 났다」로 뭉개면 그 구별이 사라진다.

## 1. 준비 — 바꾼 변수는 **하나**다

실행체 `build_hsound_prompt.py.txt`(회차 디렉터리). 저장된 제품 계획을 읽어 **발음 초점의 소리
키만** 교체하고 나머지 인자는 제품 로더 값을 그대로 쓴다.

| 인자 | `TASK-105` 팔 A(제품) | 이 팔 A2(하네스) |
|---|---|---|
| `known_sounds` | `['an_as_a']` | `['an_as_a', 'th_as_s']` (오늘의 소리를 목록에도 넣음) |
| focus | `[pronunciation_an_as_a, article_missing_before_noun]` | `[pronunciation_th_as_s, article_missing_before_noun]` |
| `questions` · `scenario` · `target_level` | 5건 · `'After work with a colleague'` · A2 | **같음** |
| 프롬프트 길이 | 5,223자 | **5,232자** |
| 소리 줄 | `"an_as_a"` 1건 | `"th_as_s"` 1건 |

**픽스처의 실제 오류**(`scenarios-P-pronunciation.md:75~76`):

```
p2a.wav  "I finished the report and shared the results with my team."   (정확)
p2m.wav  "I pinished the leport and shaled the lesults wis my team."    (f→p, r→l, θ→s)
```

⇒ `th_as_s` 는 `with` → `wis` 로 **오디오에 실재한다.** `an_as_a` 는 그 문장에 아예 없었다.

⚠️ **남는 교란 하나를 적어 둔다** — 문법 초점(`article_missing_before_noun`)이 그대로 있다.
`TASK-105` 에서는 그것이 소리 키와 **같은 낱말**에서 만났지만 여기서는 다른 낱말이므로 교란이
약해진다. 그래도 **모델이 문법 쪽을 고를 자유는 남는다.**

## 2. 회차 — 실행과 결과

(회차 실행 뒤 채운다)

## 3. 판정 재료

(회차 실행 뒤 채운다 — 판정은 `TASK-86` 이 갖는다)
