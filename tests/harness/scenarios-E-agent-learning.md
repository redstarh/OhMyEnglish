# E·L계층 시나리오 — Agent가 학습 패턴을 분석하고 학습을 제시하는가

두 개의 서로 다른 질문을 다룬다. 하나는 **지금 구현돼 있고 검증됐다**. 다른 하나는
**스키마만 있고 코드가 없다.** 이 문서는 그 경계를 명시하고, 두 번째가 구현되면 바로 돌릴 수
있는 시나리오를 미리 확정해 둔다.

| 계층 | 질문 | 구현 상태 | 결과 |
|---|---|---|---|
| **E** | 반복 오류를 **패턴으로 인식·병합·순위화**하는가 | 구현됨 | E1·E2·E3 **PASS**(1차수), E4·E5·E6 **PASS**(2차수) |
| **L** | 그 패턴에 맞는 **학습(복습 과제·다음 복습일)을 제시**하는가 | **미구현 — 스키마만** | 미실행 (블로킹) |
| **M** | 저장된 패턴이 **다음 세션의 Agent 대화에 반영**되는가 | **미구현 — 경로 0건** | 4차수 M0로 부재를 실증 (아래 §M계층) |

> M계층은 캡틴 지시(2026-08-26)로 신설했다 — "학습 중 잘못된 대답과 오류를 이후 학습 패턴에
> Agent가 반영하는지 동작 검증". L계층(복습 스케줄링)과 다른 질문이다: L은 *과제를 만드는가*,
> M은 *대화가 달라지는가*다.

---

## 왜 오류를 주입해야 했나

스텁 픽스처(`app/audio_gateway/fixtures.py`)는 고정 3문장이고 `article` 오류 **하나**만 만든다.
그래서 종단에서는 다음을 밟을 수 없었다:

- **R1("패턴 상위 2개만 반환")** — 패턴이 1개뿐이라 상한이 발동하지 않는다. AC는 이 항목을
  "3개 이상 검출된 세션에서 테스트"라고 정했고 단위 테스트가 정본이었다.
- **카테고리 분산** — `verb_tense`·`preposition`·`word_order`·`verb_form`이 실제 Claude에서
  올바른 코드값으로 나오는지.
- **패턴 축적** — 세션을 넘나들며 같은 오류가 하나로 모이는지.

`inject_errors.py`가 `create_session` + `save_final_transcript`(앱 함수 그대로)로 임의 문장을
넣는다. **스텁 어댑터만 건너뛰고 나머지(전사문 저장 → 원자적 job 등록 → 워커 → 실제 Claude →
패턴 병합 → 결과 API)는 전부 실제 경로다.**

---

## E계층 — 구현됨, 검증 완료

### E1 · 카테고리 분산 <span>PASS</span>

주입 5문장 → **패턴 7개 · 카테고리 5종** · job 5/5 `done` (31.7초).

| 주입 문장 | 검출 |
|---|---|
| `Yesterday I go to the client meeting and present the project status.` | `verb_tense_past_simple_yesterday` (occ 2, high, 0.95) |
| `I will discuss about the deployment risk with my manager on next week.` | `preposition_extra_after_discuss` (medium, 0.95) · `preposition_extra_before_next_week` (medium, 0.93) |
| `I know not why the migration failed during the last release.` | `word_order_embedded_question` (high, 0.95) |
| `The team have finish the integration test already.` | `verb_form_present_perfect_participle` (medium, 0.95) · `word_order_adverb_already` (low, 0.50) |
| `I usually go to gym before the daily standup meeting.` | `article_missing_before_noun` (medium, 0.90) — **기존 패턴 재사용** |

**단정**

1. 카테고리가 전부 001 스키마 CHECK 안의 코드값이다 — 저장 전 거부(W7) 없이 통과.
2. 신규 `pattern_key`가 `{category}_{snake}` 형식이다 (§5.6).
3. 기존 key(`article_missing_before_noun`)는 **재사용**되고 새로 만들어지지 않는다.
4. severity가 한 값에 몰리지 않는다 — high 2 · medium 4 · low 1.

**비결정성 취급**: 실제 Claude 출력이므로 "이 문장에서 반드시 이 `pattern_key`가 나온다"고
단정하지 않는다. 단정하는 것은 **패턴이 3개 이상 생기는 것**, **카테고리가 CHECK 안에 드는 것**,
**기존 key가 재사용되는 것**이다.

### E2 · R1 상위 2개 — 종단 최초 검증 <span>PASS</span>

E1 세션(패턴 7개)의 결과 API가 **정확히 2개**를 반환했다. 정렬도 계약 그대로다:

| 순위 | pattern_key | severity | confidence | occurrences |
|---|---|---|--:|--:|
| 1 | `verb_tense_past_simple_yesterday` | high | 0.95 | 2 |
| 2 | `word_order_embedded_question` | high | 0.95 | 1 |

severity ordinal(high=high) → confidence desc(0.95=0.95) → occurrence desc(**2 > 1**)로
tie가 풀렸다. **화면에도 카드가 정확히 2개** 렌더됐다
(`runs/2026-08-26-run-1/E2-top2-cards.png`).

이 시나리오에서 **F-2(`target_form` 불일치)**가 드러났다 — 1위 카드의 원문/교정문은
occurrence 1(`Yesterday I go` → `Yesterday I went`)인데 `target_form`은 `and presented`다.
상세는 `runs/2026-08-26-run-1.md` F-2.

### E3 · 학습 패턴 축적 <span>PASS</span>

같은 `article` 오류를 서로 다른 3문장(`go to office` · `go to gym` · `go to airport`)에
주입했다.

- `error_patterns` 행 증가 **0** — 세 문장이 한 패턴으로 병합.
- `frequency` 누적: baseline 1 → E1 후 3 → E3 후 **6** (세션 3개에 걸쳐).
- 부수 검출: `verb_form_third_person_s`(`She go` → `She goes`),
  `verb_tense_future_tomorrow`.

**이것이 제품의 핵심 주장("개인의 반복 오류를 기억한다")의 종단 증거다** — 문장이 달라도,
세션이 달라도 하나의 패턴으로 모이고 빈도가 쌓인다.

### E4 · 추가 제안 (미실행)

| # | 시나리오 | 목적 |
|---|---|---|
| E4 | `voice_command` 타입 발화를 섞어 주입 | W6 — 명령 발화가 분석에서 제외되는지 종단 확인 (`utterance_type='voice_command'`로 저장하면 job이 안 생겨야 한다) |
| E5 | 오류 없는 문장만 5개 주입 | 전체 occurrence 0 → 결과 화면이 `확정` + "표시할 교정이 없습니다"인지 |
| E6 | 같은 문장을 두 번 주입 | 발화 단위 replace 멱등성이 종단에서도 유지되는지(`frequency` 부풀지 않음) |

---

## L계층 — 미구현. 시나리오만 확정한다

### 실측한 구현 상태 (2026-08-26)

| 자산 | 상태 |
|---|---|
| `error_patterns.next_review_at` | 컬럼 존재, **설정 0건** — 앱 코드에 참조 없음 |
| `error_patterns.mastery_score` | 컬럼 존재, **전부 0** — 앱 코드에 참조 없음 |
| `error_patterns.self_difficulty` | 컬럼 존재, 미사용 |
| `review_tasks` 테이블 | 존재, **0행** — 앱 코드에 참조 없음 |
| `analysis_jobs.job_type='summarize_session'` | CHECK에만 있고 등록 코드 없음 (`services/analysis.py:345` 주석이 명시) |
| 프론트엔드 복습·추천 UI | 없음 |
| 음성 명령 `show review` | `docs/agent-system-prompt.md:33`에 정의, 구현 없음 |

즉 **"오류에 맞는 학습을 제시"에 해당하는 코드는 하나도 없다.** 현재 사용자가 받는 가장 가까운
것은 교정 카드의 `교정문`과 `한 줄 이유`, 그리고 API에만 있는 `target_form`(F-2 대상)이다.

이는 설계상 이월이 맞다(AC §"Phase 1에서 쓰지 않는 것" — 복습 스케줄링은 3단계).
다만 아래는 **아직 미충족인 문서화된 요구**다:

- `tests/README.md` 필수 케이스 **4번** — "1·3·7일 복습 일정이 중복 없이 생성되는가"
- `docs/first-4-weeks.md` — "상위 2개 문법 패턴을 1·3일 간격으로 복습",
  "다음 복습일과 짧은 준비 과제를 확인한다", "약점 집중: 다음 복습 예정 오류 중 하나를 즉시 연습"

### 구현되면 돌릴 시나리오

전제: E1·E3로 패턴 7개 이상과 `frequency` 편차가 이미 만들어져 있다 — L계층은 **그 상태 위에서**
돈다. 새로 주입할 필요가 없다.

| # | 시나리오 | 단정 |
|---|---|---|
| **L1** | 분석 완료 후 상위 패턴에 복습 일정이 생긴다 | R1이 고른 상위 2개 패턴에 `next_review_at`이 설정된다. **1일 뒤**(1단계)여야 한다 |
| **L2** | 1·3·7일 3단계가 중복 없이 생성된다 | `review_tasks`에 같은 `(pattern_id, review_stage)`가 두 번 생기지 않는다 — 001의 `unique (pattern_id, review_stage)`가 가드다. 재분석·재시도 후에도 행 수가 늘지 않는다(멱등) |
| **L3** | 복습 과제가 패턴 종류에 맞는 형태로 나온다 | `review_tasks.task_type`이 `rephrase`/`role_play`/`shadowing` 중 패턴 카테고리에 적합한 값. 예: `pronunciation_intonation` → `shadowing`. **적합성 판정 기준을 설계 시점에 문서로 확정해야 한다** — 없으면 이 시나리오는 판정 불가다 |
| **L4** | 제시된 연습 목표가 표시된 교정과 같은 문장이다 | **F-2의 회귀 테스트.** `target_form`(또는 후속 필드)이 카드의 `원문`/`교정문`과 같은 occurrence에서 나온다 |
| **L5** | 복습일이 지나면 그 패턴이 우선 제시된다 | `next_review_at`을 과거로 세팅(실시간 대기 금지 — AC W4·W5와 같은 방식) → 다음 세션/화면이 그 패턴을 먼저 낸다 |
| **L6** | 숙련도가 오르면 복습 간격이 늘거나 제시가 멈춘다 | `mastery_score` 갱신 규칙이 확정된 뒤에만 판정 가능. **현재는 갱신 주체가 없다** |
| **L7** | 세션 총평이 생성된다 | `summarize_session` job이 세션 종료 시 등록되고 terminal에 도달한다. 총평 문구가 상위 패턴을 언급한다 |
| **L8** | 화면에 다음 복습일과 준비 과제가 보인다 | 결과 화면 또는 별도 화면에 렌더. **다크모드 대비도 함께 본다**(F-1 재발 방지) |

### L계층 착수 전에 캡틴이 정해야 하는 것

시나리오를 확정했지만 **아래가 미결이면 L3·L6은 판정 불가**다. 구현 전에 결정이 필요하다.

1. **복습 간격의 기준 시각** — 마지막 발생 시각(`last_seen_at`)인가, 분석 완료 시각인가,
   세션 종료 시각인가. 1·3·7일을 어디서부터 세는지가 정해져야 L1·L5를 단정할 수 있다.
2. **`task_type` 선택 규칙** — 카테고리→과제유형 매핑표. 없으면 "적합한가"를 판정할 수 없다.
3. **`mastery_score` 갱신 규칙** — 무엇이 점수를 올리고 내리는가, 만점의 의미는 무엇인가.
4. **복습 대상 선정 범위** — 세션마다 상위 2개인가, 전체 패턴 풀에서 복습일이 지난 것 전부인가.
5. ~~**`target_form`의 의미**(F-2와 직결)~~ → **결정됨(2026-08-26): 패턴 수준 일반형**(선택지 B).
   프롬프트가 일반형을 요구하도록 고쳐졌고 3차수 Q1에서 검증됐다(커밋 `3bde54f`).

---

## M계층 — 오류가 이후 학습에 반영되는가 (Agent 적응)

### 실측한 구현 상태 (2026-08-26, 코드 직접 확인)

"오류 → 이후 학습"은 **두 개의 링크**다. 하나는 있고 하나는 없다.

| 링크 | 내용 | 상태 | 근거 |
|:--:|---|---|---|
| **저장** | 발화의 오류가 `error_patterns`에 누적·병합되고 `frequency`가 오른다 | ✅ **구현·검증됨** | E1·E3·E6 PASS, 3차수 N5에서 실음성으로도 확인 |
| **활용** | 누적된 패턴이 **다음 세션의 대화 내용을 바꾼다** | ❌ **경로 0건** | 아래 |

활용 링크가 없다는 증거 3개:

1. **세션 시나리오가 고정이다.** `app/backend/app/services/sessions.py:29` —
   `(select id from learning_scenarios order by created_at, id limit 1)`. 학습자 이력과
   무관하게 **항상 시드된 첫 행**이 붙는다. 같은 파일 docstring이 "첫 슬라이스에는 추천
   로직이 없다(YAGNI)"고 명시한다.
2. **Nova 지시문이 정적 문자열이다.** `app/backend/app/audio_gateway/nova.py:77`의
   `SYSTEM_PROMPT`는 학습자 프로필을 **하드코딩**했고 과거 오류가 주입되는 인자가 없다.
   `port.py:84`의 `async def start(self) -> None:` — **지시문 파라미터가 없다.**
3. **복습 자산이 죽어 있다.** `next_review_at`·`mastery_score`·`review_tasks`·
   `summarize_session` 전부 앱 참조 0건(위 L계층 표).

즉 **오류를 기억은 하지만 그 기억을 쓰지 않는다.** 이는 설계상 이월이며(3단계 학습 코치
Agent — `docs/design/2026-08-25-learning-coach-agent-design.md`, 검토 전 초안) 결함이 아니다.
다만 캡틴이 요구한 "동작 검증"의 답은 **"현재 반영되지 않는다"**이고, 아래로 그 사실을
증거와 함께 고정한다.

### 4차수에 실제로 돌리는 시나리오

| # | 시나리오 | 단정 | 판정 방식 |
|---|---|---|:--:|
| **M0** | **반영 부재 실증** — `inject_errors.py --scenario E1`로 패턴 7개를 쌓은 뒤 **새 세션**을 열어 `p1a.wav`(또는 `u1.wav`)를 주입한다 | ① 새 세션의 `scenario_id`가 **이전 세션과 동일**하다(고정 첫 행) ② agent 첫 발화가 축적된 패턴을 **언급하지 않는다** ③ `review_tasks` 0행 유지 ④ `next_review_at` 전부 null 유지 | 지금 실행 가능 |
| **M1** | 같은 오류를 2세션 연속 만든다 (`u1`→새 세션→`u2`, 같은 `article` 패턴) | `frequency`가 2로 오른다(저장 링크 ✅). 그런데 두 번째 세션의 agent 대화는 첫 세션과 **구별되지 않는다**(활용 링크 ❌) — 두 세션의 agent 발화를 나란히 기록해 대조 증거로 남긴다 | 지금 실행 가능 |
| **M2** | `frequency` 상위 패턴이 다음 세션에서 먼저 다뤄지는가 | **구현 후 판정.** 지금은 M0-①로 부재만 확인 | 미구현 |
| **M3** | 교정을 성공적으로 재발화하면 그 패턴의 우선순위가 내려가는가 | **구현 후 판정.** `mastery_score` 갱신 규칙(위 미결 3번)이 선행 | 미구현 |
| **M4** | 세션 종료 시 다음 세션 계획이 만들어지는가 | **구현 후 판정.** 설계서 §4의 `session_plans` — 사용자 대기 경로에 Claude 호출 0개가 요구사항이므로 **앞선 세션 종료 시** 생성돼야 한다 | 미구현 |
| **M5** | 계획 생성이 실패해도 다음 세션이 열리는가 | **구현 후 판정.** 계획 없으면 고정 시나리오로 폴백해야 한다(Failure lens) | 미구현 |

**M0·M1은 "없음"을 증거로 고정하는 것이 목적이다.** 통합테스트 시 이 두 건이 PASS로
뒤집히면 그때 활용 링크가 붙었다는 뜻이다 — 회귀 기준선으로 쓴다.

### M계층 착수 전 캡틴 결정 (L계층 5건과 별도)

1. **반영의 단위** — 다음 세션의 *시나리오 선택*을 바꾸는가, *Nova 지시문*에 약점을 주입하는가,
   둘 다인가. 지시문 주입은 `port.start()` 시그니처 변경이 필요하다(AC가 허용한 확장).
2. **반영 시점** — 세션 시작 시 계산(대기 발생)인가, 앞선 세션 종료 시 미리 계산(설계서 §4)인가.
3. **"반영됐다"의 판정 기준** — agent가 약점 패턴을 명시적으로 언급해야 하는가, 해당 문형을
   쓰게 유도하기만 해도 되는가. 후자면 자동 판정이 어렵다.
