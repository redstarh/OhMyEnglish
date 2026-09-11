# 회차 — `TASK-115`: `pq04` 를 대체한 `pq13` 으로 **/r/ 축**을 잰다

세션 `ohmyenglish-7f` 후속 · 2026-09-12 KST · 브랜치 `design/first-vertical-slice`

> **왜**: `pq04`(`I want to review the code with you.`)가 전용 모드 세션에서 코치를 **코딩 조수
> 역할로 끌어당겼고**(`I can't directly view or execute code…`) 발음 코칭이 0 이었다
> (`runs/2026-09-12-task114-mild-band-dedicated.md` §2.5). 그래서 **/r/ 축이 시험되지 못했다** —
> 실패 원인이 소리가 아니라 **문장 내용**이었기 때문이다.
>
> ⛔ **`pq04` 를 덮지 않았다** — PQ 정본과 `TASK-90` 회차가 그 ID 로 인용한다. 새 ID 로 만들었다.

---

## 0. ⛔ 상한과 해석 규칙

| 무엇 | 값 |
|---|---|
| 새 픽스처 | **`pq13`** `My blother will allive ealy tomollow molning.`(4.40s) → **`pq13a`** `My brother will arrive early tomorrow morning.`(4.08s) · 16kHz·16bit·mono |
| 문장 설계 | ⛔ **도구 지시로 읽히는 낱말을 피했다** — `code`·`review`·`debug`·`run`·`file` 계열 0개. 일상 문장이고 /r/ 이 네 자리(`brother`·`arrive`·`early`·`tomorrow`·`morning`)에 있다 |
| 스택 | 검증 전용 DB `ohmyenglish_pq13` · `:8012` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · 오늘의 소리 `r_as_l` |
| 상한 | **Nova 2세션** (오늘 누적 **133**) |

⚠️ **규율 어긋남을 적는다** — 상한 2회를 **명령줄에 적고** 돌렸고 이 기록으로 옮긴 것은 1회차
**뒤**다. 「돌리기 전에 기록에 적는다」의 순서를 지키지 못했다. 값이 바뀌지는 않았지만(2회를 넘기지
않았다) **그 사실을 남긴다.**

| 결과 | 읽는 법 |
|---|---|
| 코칭이 2회 같은 방향 | **원인이 문장 내용이었음이 확정된다** — 같은 소리·같은 도구·같은 모드에서 문장만 바꿔 갈렸다 |
| 코칭 0 | 문장이 아니라 **/r/ 자체**가 안 잡히는 것이므로 그것이 다음 물음이 된다 |

## 1. 결과 — **2/2 코칭. 원인은 문장이었다**

두 회차의 발화가 거의 같다:

```
사용자: my brother will arrive early tomorrow morning.
코치  : I noticed a small pronunciation issue with the "r" sound in "arrive."
        Let's focus on that. Try saying just the word "arrive" with a clear, slight
        trill or tap of the tongue against the roof of your mouth … Can you repeat that word for me?
```

⛔ **소리를 이름으로 지목하고 재발화를 요구했다** — 결정 51 기준의 코칭이다. 그리고 **혀 위치까지
말했다**(`tap of the tongue against the roof of your mouth`).

| 기록 | 값 |
|---|---|
| `pronunciation_attempts` | **2행**(세션당 1행) · `target_sound` 둘 다 **`r_as_l`** · `signal_source` 둘 다 `nova_tool` |
| `outcome` | 1행 `incorrect` · 1행 **`pending`** |

⚠️ **`pending` 이 그대로 저장된 것은 결함이 아니다** — `db/migrations/003_pronunciation_echo.sql:36`
의 CHECK 가 `pending` 을 값역에 넣었고, 같은 파일이 *"세션 종료 시 남은 pending"* 을 다루는 규약을
적었다. ⛔ 이 회차의 세션은 `--timeout` 으로 끝났고 **정상 종료가 아니라** 그 수렴 경로를 밟지
않았다. ⚠️ 그래서 이 값으로 「수렴이 안 된다」를 판정하지 **않는다.**

⚠️ **ASR 이 오철자를 완전히 복원했다** — 전사문이 두 회차 모두 `my brother will arrive early
tomorrow morning.` 이다(`blother`·`allive` 의 흔적 0). 그런데 코칭은 났다. Nova 가 오디오를 직접
듣는다는 PQ 정본 §5 의 주의가 여기서 한 번 더 확인됐다.

## 2. 판정

**`pq04` 의 실패 원인은 문장 내용이었다.** 같은 소리(`r_as_l`)·같은 도구(Qwen3-TTS Sohee·`en`)·같은
모드·같은 앱에서 **문장만 바꿨더니 2/2 로 코칭이 났다.**

⇒ **픽스처 설계에 규율 하나가 생긴다**: **문장이 모델을 다른 역할로 끌 수 있는 낱말을 담지 않는다.**
`review the code` 는 발음 오류를 담은 문장으로는 적절해 보이지만, 대화 상대가 그 내용에 반응하면
발음 축이 사라진다. ⛔ 이것은 「발음 오류를 하나만 담는다」와 **다른 축의 요구**이고 PQ 정본에 넣었다.

⚠️ **`pq04` 는 폐기하지 않는다** — 그 자체가 **「내용이 축을 가린다」의 실측 사례**이고 앞 회차가
그 ID 로 인용한다.

## 3. 정리

| 무엇 | 확인 |
|---|---|
| 백엔드 `:8012` | 종료 |
| 검증 전용 DB | `dropdb ohmyenglish_pq13` **exit 0** |
| 공유 dev DB | `learning_sessions` **17** · `pronunciation_attempts` **7** — 회차 앞 값과 같다 |

**Nova 2세션**(상한 2). Qwen3-TTS 생성 2건 — 로컬 모델이라 API 비용 0.
