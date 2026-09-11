# 회차 기록 — `TASK-81` AC#4 앱 경로. **판정: 조건 미성립. 계획에 발음 초점이 없음**

> ⛔ **AC#4 를 체크하지 않음.** 「앱 경로에서 코칭이 나는가」를 재려 했으나 **잴 조건이 성립하지
> 않았음** — 실행 중 최신 계획이 2026-09-08 것이고 초점이 문법 둘이라 `TASK-81` 층②의 소리 줄과
> `TASK-75` 의 규칙 9·4 대체가 **애초에 프롬프트에 실리지 않음.**
>
> ⚠️ **「코칭이 오지 않는다」가 아니라 「잴 기회가 없었다」임** — `TASK-86` 리마인더 8회가 빠진 것과
> 같은 형태이고, 그 회차 기록(`2026-09-10-task75-rule9-rule11-replacement.md` §10)이 그 구별을
> 이미 적어 뒀음.
>
> **부수 산출 둘이 이 회차의 실질임**: 우회로가 3/3 작동함(§5) · 그 행에 복습 재료가 없음(§6).

---

## 1. 환경 — 이 턴에 직접 재서 얻음

| 항목 | 값 |
|---|---|
| 회차 구간 | 2026-09-10 16:48:33 ~ 16:57 KST (`WINDOW_START` = `2026-09-10 07:48:33.70918+00`) |
| HEAD | `b6b3b7d` |
| 백엔드 | pid **25563** · 기동 **16:27:44 KST** · **`VOICE_ADAPTER=nova`** · `WORKER_ENABLED=false` · `/health` 200 |
| 프론트 | pid 37650 `:3000` · 최신 코드(번들에 `awaiting_analysis` 있음) |
| CDP | `:9222` `Chrome/152.0.7977.65` |
| 워커 | ⛔ **켜지 않았음.** `claim_one` 을 부르지 않았음 |
| 실행체 | `tests/harness/p_app_path.py` (`instrument.js` sha256 `cbc19fb6…` · 44,552B) |
| 픽스처 | `p2k.wav` (3.792s · 16000Hz — 관측 JSON 의 `bufferSampleRate` 로 확인. 리샘플 0회) |
| 회차 수 | **3** (지시는 8회였으나 §3 의 조건 미성립을 확인해 중단하고 알렸음) |

**baseline DRIFT**: 착수 전 **0** · 종료 시 **0**(`harness_pattern_baseline` 9행 대조). 패턴 값을
건드리지 않았음.

## 2. 회차별 관측 — 3회가 같은 방향

| # | `session_id` | 전사문 | agent 발화 | 발음 코칭 | `recv.pronunciation` |
|--:|---|---|---|:--:|--:|
| 1 | `24597f0f-22db-452e-94ab-842d8a10f6eb` | `마이티니시트더리포트엔쉬어드더리절치위드마이팀` | *"I see you mentioned a meeting sheet report. Let's start with a simple weekend plan. … Try to say: I want to make a plan. Remember to use a or an before a singular noun."* | **없음** | **0** |
| 2 | `f8ebc78b-9e76-4f1c-979a-75c7a31dd561` | `아이피니시프트리포트엔씨어드리절치위드마이팀` | *"I see you mentioned a report with your team. … Could you say: I need to prepare an agenda."* | **없음** | **0** |
| 3 | `d727f79d-ffc4-4bf0-a37a-f7551f0f9f25` | `아이티니시트 더리포트 엔쉐어드 더리절치우이드 마이팀` | *"I see you mentioned a report and sharing research. Let's start with a simple weekend plan. … Try to say: I want to make a plan. or I want to make a new plan."* | **없음** | **0** |

**학습자 축 판정 기준**은 `runs/2026-09-10-task81-pronunciation-focus.md` §7 이 소유함 — 발화가
어긋난 소리를 다루는가. 3회 모두 소리를 지목하지 않고 관사·콜로케이션 드릴로 갔음.

⚠️ **한글 전사가 3/3 임.** `p2k` 를 첫 발화로 주면 ASR 이 한글로 전사함 — `TASK-65` 기전과
`runs/2026-09-10-task82-p4-p1.md` 의 관측이 앱 경로에서 다시 재현됐음. 표기는 회차마다 다름.

## 3. ⛔ 조건 미성립의 근거 — 계획을 직접 조회했음

`session_plans` 는 **2행뿐이고 최신이 2026-09-08 22:58** 임. 그 행의 `instruction.focus` 가 문법 둘임.

```json
{"focus": [{"pattern_key": "article_missing_before_noun", "target_form": "a/an + 단수 명사"},
           {"pattern_key": "business_expression_verb_noun_collocation",
            "target_form": "make / prepare + an + 계획 명사"}],
 "hint_timing": "wait for one full attempt, then give a short hint if the article or the verb is missing",
 "sentence_length": "one short single-clause sentence, about 5 to 8 words"}
```

`GET /api/sessions/next-plan` 의 `reason` 도 발음을 말하지 않음 — *"짧은 문장에서 a/an을 자주
빼먹고 \"plan the action plan\"처럼 말했기 때문에, 오늘은 a/an과 make/prepare + an + 계획 명사를
함께 연습해요."*

⛔ **그래서 세션 지시문에 `Sound to coach today:` 줄이 실리지 않음.** `TASK-81` 층②가 그 줄을
만드는 조건이 「계획이 발음 초점을 지정함」이고(`ae5e832`), `TASK-75` 의 규칙 9·4 대체 문장은 **그
줄에 붙어 있음**(`runs/2026-09-10-task75-…md` §2 — *"대체를 계획 블록의 소리 줄이 말하므로 범위가
그 줄이 있는 세션으로 한정된다"*). **두 수정이 모두 비활성인 조건임.**

⚠️ **agent 가 계획을 정확히 실행했음** — 3회의 발화가 `weekend plans small talk` 문맥과
`make/prepare + an + 계획 명사` 를 그대로 씀. 즉 프롬프트 전달 경로는 정상이고 **계획 내용이 낡은
것**임.

**새 계획이 만들어지지 않는 이유**: `plan_next_session` job 이 `pending` 에 머물고 워커가 꺼져 있음.
⛔ 이 회차는 그것을 처리하지 않았음(`claim_one` 금지).

## 4. 그래서 AC#4 를 어떻게 두는가

⛔ **AC#4 를 체크하지 않고 `TASK-81` 을 `In Progress` 로 둠.** 판정은 **「조건 미성립」**이고
「코칭 없음」이 아님. 두 표현의 차이가 다음 회차의 설계를 가름.

**AC#4 를 닫으려면 선행 조건 하나가 더 있음**: 발음 초점이 실린 계획. 그 계획을 만드는 경로는
`plan_next_session` job 처리이고, **내 세션 3건이 자기 job 을 각각 pending 으로 만들었음**(보존 세션
것이 아님). `p5_worker_leg.py` 의 `guard` 가 보존 job 을 비켜 두면 내 것만 집힘 — **승인 사안임.**

## 5. 부수 산출 ① — 우회로가 3/3 으로 작동함

`pronunciation_attempts` 가 **4 → 7**(+3, 회차당 1건). 세 행이 전부 내 세션 것이고 값이 동일함.

| 열 | 값 (3행 모두) |
|---|---|
| `target_form` | `(전사문이 한국어로 인식되었습니다)` |
| `outcome` | `unclear` |
| `target_sound` | **빈값** |
| `pattern_id` | **NULL** |

`services/pronunciation.py:268 note_transcript` → `record_signal` → `_insert_attempt` 경로임.
`recv.pronunciation` 이 0 이므로 **tool 없이 생긴 행임.**

⛔ **결정 50 순서 ③(우회로 제거)을 막는 근거가 실측으로 하나 더 늘었음.** 지금 걷어내면 앱 경로에서
발음 관련 기록이 **0** 이 됨 — 이 회차의 3건이 그 유일한 산출이었음.

## 6. 부수 산출 ② — ⛔ 그 행은 복습 시계를 돌리지 못함

`review_tasks` **17 → 17**(불변) · `error_patterns` **10 → 10**(불변) · baseline DRIFT **0**.

이유는 코드에 있음: `link_pattern` 이 `outcome = 'incorrect'` 로 거르므로(`pronunciation.py:499-504`
주석) `unclear` 는 패턴에 연결되지 않고, `refresh_review` 에 넘길 `pattern_id` 도 없음.

**같은 표에 대조가 나란히 있음** — tool 경로로 만들어진 기존 행임.

| 행 | 경로 | `outcome` | `target_sound` | `pattern_id` | 그 패턴의 `next_review_at` |
|---|---|---|---|---|---|
| `a817b206` (2026-09-03) | tool | `incorrect` | `an_as_a` | `99fc908f…` | **`2026-09-04 13:51:26+00`** |
| 이 회차 3건 | 보조 신호 | `unclear` | **빈값** | **NULL** | — |

⛔ **`TASK-74`(보조 신호에서 복습 시계를 돌릴지)가 지목한 「재료가 없다」의 실측 재현임.**
그리고 `2026-09-10-worker-cost-judgment.md` §1 이 적은 단정 범위(**tool 이 판정 호출까지 와야
종단이 성립함**)의 **실증**임 — 워커와 무관하게 `outcome` 이 갈림을 결정함.

## 7. 표 건수 — 회차 시작 전 대비

| 표 | 착수 전 | 종료 시 | 델타 | 무엇이 만들었나 |
|---|--:|--:|--:|---|
| `learning_sessions` | 13 | **16** | +3 | 내 세션 3건 |
| `utterances` | 120 | **126** | +6 | 회차당 2건(user 1 · agent 1) |
| `analysis_jobs` | 49 | **55** | +6 | 회차당 2건(`analyze_utterance` 1 · `plan_next_session` 1) |
| `pronunciation_attempts` | 4 | **7** | +3 | §5 |
| `error_patterns` | 10 | 10 | 0 | — |
| `error_occurrences` | 24 | 24 | 0 | — |
| `review_tasks` | 17 | 17 | 0 | — |
| `session_plans` | 2 | 2 | 0 | 새 계획 없음(§3) |

⚠️ **`2026-09-10-worker-cost-judgment.md` §2 의 계산이 이 회차로 낡았음.** 그 문서는 스윕이 걷을
대상을 `d127dece` 3건으로 셌는데, 지금 내 세션 3건이 `analyze_utterance` job 을 각각 **이미 갖고
있으므로** 스윕 대상은 아님. 다만 **`claim_one` 이 집을 pending 은 늘었음** — `plan_next_session`
4 → **7**(내 것 3 추가) · `analyze_utterance` pending 3 → **6**. `p5_worker_leg.py` 의 `guard` 가
비켜 둘 목록이 그만큼 늘었음.

## 8. ⛔ teardown 을 보류함 — 판단을 올림

**내 세션 3건을 지우지 않았음.** 근거 셋임.

1. **그 3건이 `TASK-74` 의 유일한 앱 경로 재현본임**(§6). 지우면 같은 상태를 다시 만드는 데 앱 경로
   세션 3회가 다시 들고, 그때 계획이 바뀌어 있으면 **같은 조건이 재현되지 않음.**
2. **오염이 없음.** baseline DRIFT 0 · `error_patterns`·`review_tasks`·`occurrences` 불변 · 보존 세션
   6건 무손상. 늘어난 것은 내 세션 계열뿐임.
3. **지우는 것은 되돌릴 수 없고 남기는 것은 되돌릴 수 있음.**

**teardown 대상 id (지울 때 이것을 씀 — 시각창 단독으로 지우지 않음)**:

```
24597f0f-22db-452e-94ab-842d8a10f6eb
f8ebc78b-9e76-4f1c-979a-75c7a31dd561
d727f79d-ffc4-4bf0-a37a-f7551f0f9f25
```

관측 JSON 3건(`run-01.json`·`run-02.json`·`run-03.json`)이 각 세션의 `walk.startedSessionId` 를
갖고 있음 — 그것이 삭제 대상의 정본임(`p_app_path.py` docstring 규약).

## 9. 정리 대조

- 워커 **켜지 않았음** · `claim_one` **부르지 않았음** · `WORKER_ENABLED` 손대지 않았음
- 보존 세션(`210233be`·`d127dece`·`b2f0d169`·`76d9ef31`·`6225ddaf`·`e0c5e580`)에 대한
  UPDATE·DELETE **0건**
- 앱 코드 변경 **0건** · 원장 변경 **0건** · 백엔드 재기동 **0회**
- `.harness/browser_run_id.txt` 를 `9f21b483-bb71-41c8-ad1c-96d6a8aca99d` 로 갱신하고 이전 값
  (`6454e5c1-…`)을 `prev-browser-run-id.txt` 에 보관했음.
  ⚠️ **`p_app_path.py` 는 `harness_sessions` 에 등록하지 않아 run_id 를 쓰지 않음** —
  등록 주체는 `ws_session.py`·`inject_errors.py` 뿐임. teardown 근거는 관측 JSON 임
- Nova 실물 호출 **3회**(회차당 1세션) · 실물 Claude 호출 **0회**(분석 job 이 pending 에 머묾)
- 브라우저 탭은 `p_app_path.py` 가 매 회차 `Page.navigate` 로 재사용함 — 내가 띄운 Chrome 이 아니라
  닫지 않았음
