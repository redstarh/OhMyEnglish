# 회차 — `TASK-88` AC#4: 무너진 전사문이 **문법·표현 패턴을 만들지 않는지** 종단으로 본다

세션 `ohmyenglish-65` · 2026-09-15 KST · 방향 정본 **결정 94**(발음 기원 오류는 기록만 남기고 복습
과제를 만들지 않는다) · 설계 정본은 `TASK-88` 노트의 「확정된 구현 설계」다

> ⛔ **Nova 를 쓰지 않는다.** 재는 것은 **분석 경로**이고 그 입력(무너진 전사문)은 이미 실측돼 있다 —
> `tests/harness/scenarios-PQ-qwen-phoneme.md:22` 가 `p2m` 의 ASR 산출을 그대로 적어 두었다:
> `i finished the la porte en chaille de lesseps with my team.`(복원되지 않음).
> ⚠️ 오디오→ASR 단계는 이 태스크가 고친 자리가 아니므로 다시 돌리지 않는다 — 그 단계를 다시 돌리면
> **같은 입력을 비싸게 재생산**할 뿐이다.
>
> **비용**: Claude 분석 호출 **1회**(실물). Nova **0**.

---

## 0. ⛔ 해석 규칙 — 돌리기 전에 적는다

**스택**: 검증 전용 DB `ohmyenglish_t88`(마이그레이션 024) · `WORKER_ENABLED=false` ·
job 은 `p5_worker_leg.py claim` 으로 **1건만** 처리한다 · 공유 dev DB 와 `:8002`·`:3000` 을 건드리지
않는다.

| 결과 | 읽는 법 |
|---|---|
| `error_patterns` 에 **발음 카테고리가 아닌 행 0건** + `pronunciation_attempts` 에 `transcript_analysis` 행 **≥1** | **AC#4 충족** — 발음 기원 오류가 문법·표현으로 새지 않고 기록만 남았다 |
| `error_patterns` 에 문법·표현 행이 **생김** | ⛔ 결함 잔존 ⇒ AC#4 를 닫지 않고 원인을 **프롬프트(기원 표시)**와 **라우팅** 중 어디인지 가른다 |
| finding 이 **0건**(분석이 아무것도 못 찾음) | ⛔ **별 관측값이고 이 축을 시험하지 못한다** — 「고쳤다」로 읽지 않는다. 무너진 전사문이 분석기에 아무 재료도 주지 않은 것이므로 그 사실만 적는다 |
| `transcript_analysis` 행이 **0건**인데 `error_patterns` 도 0건 | 라우팅이 아니라 **기원 표시**가 안 붙은 것일 수 있다 ⇒ 원 응답을 읽어 가른다(판정 보류) |
| job 이 실패 | 환경 고장이므로 판정하지 않는다 |

⚠️ **복습 과제도 함께 센다** — 결정 94 가 「복습은 만들지 않는다」이므로 `review_tasks` 가 0건이어야
한다. 그것이 이 회차의 **반대 방향 단정**이다.

---

## 1. 결과 — §0 의 첫 행이 성립한다. **AC#4 충족**

Claude 분석 호출 **1회**(job `7f7d2fcc` · `status=done` · `attempts=1`).

| 표 | 실측 |
|---|---|
| `error_patterns` | **0행** — ⛔ 문법·표현 패턴이 **생기지 않았다**(이 태스크가 막으려던 것) |
| `error_occurrences` | **0행** |
| `pronunciation_attempts` | **1행** · `signal_source=transcript_analysis` · `outcome=incorrect` · `target_sound` **빈칸** |
| `review_tasks` | **0행** — 결정 94 의 「복습은 만들지 않는다」가 지켜졌다(반대 방향 단정) |

⇒ 발음 기원 오류가 **기록만 남고** 문법·표현으로 새지 않았으며 복습 과제도 만들지 않았다.
`target_sound` 가 빈 것이 그 기제의 열쇠다(`_UPSERT_PRONUNCIATION_PATTERN_SQL` 이 소리 이름을
요구하므로 패턴 행이 0행이 된다 — `TASK-88` 노트의 「무엇이 반증됐는가」가 그것을 이미 적었다).

⚠️ `llm_calls` 는 0행이다 — 하네스가 `usage_sink` 를 주입하지 않는다(제품 결함이 아니고 이 세션의
앞 회차가 같은 것을 적었다).

## 2. ⛔ 표에 없던 관측 하나 — **기록된 내용이 학습자에게 보일 모양이 아니다**

실린 값 둘:

```
target_form  : I finished the + 업무 산출물 명사 (report / presentation / draft)
spoken_form  : the la porte en chaille de lesseps
```

`target_form` 이 **문장이 아니라 한국어 주석이 붙은 빈칸 채우기 틀**이다. 그리고 결과 화면은
`signal_source === "nova_tool"` 이 아닌 행을 **「관찰된 신호」 갈래**로 렌더하며 그 갈래는
**`spoken_form` 을 아예 그리지 않는다**(`results/[sessionId]/page.tsx` 의 그 삼항). ⇒ 학습자는
자기가 말한 것을 못 보고 **틀만** 보게 된다.

⚠️ **이것은 코드를 읽어 얻은 판정이고 화면으로 관측하지 않았다** — 이 회차의 스택은 분석 경로만
세웠다(브라우저를 띄우지 않았다). 그래서 「그렇게 렌더된다」가 아니라 **「그 갈래로 간다」**까지만
단정한다.
⇒ **`TASK-88.1` 로 등록했다.** `TASK-97`(Nova tool 의 내용이 쓸 수 없다)과 **다른 경로**이므로 그쪽에
합치지 않았다 — 같은 증상 부류이지만 만드는 주체가 분석기다.

## 3. 정리 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| 검증 전용 DB | `dropdb ohmyenglish_t88` **exit 0** · 남은 DB 는 `ohmyenglish`·`_smoke`·`_test` 뿐 |
| 실물 사용 | Claude **1회** · Nova **0** |
| 공유 dev DB | 회차 전후가 **같다** — `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15` |
