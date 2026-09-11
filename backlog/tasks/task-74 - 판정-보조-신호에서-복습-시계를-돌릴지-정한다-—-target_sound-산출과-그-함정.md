---
id: TASK-74
title: '판정: 보조 신호에서 복습 시계를 돌릴지 정한다 — target_sound 산출과 그 함정'
status: Done
assignee: []
created_date: '2026-09-09 16:11'
updated_date: '2026-09-11 11:30'
labels: []
dependencies: []
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 결정 49 가 만든 후속임. 근거는 tests/harness/runs/2026-09-09-task67-tool-call-investigation.md 와 대장의 결정 49 임.

결정 49 가 발음 판정을 보조 신호로 축소했음. 그 결과 발음 신호는 기록되지만 복습 시계로 이어지지 않음 — note_transcript 가 outcome='unclear' + target_sound=None 만 내고 복습 SQL 은 target_sound 가 비지 않은 행만 봄.

⛔ 이것은 새로 발견한 것이 아니고 코드가 이미 적어 둔 사실임 — app/backend/app/services/review.py:207~216. 팀리드가 그 줄을 직접 읽어 확인했음.

⚠️ 그 주석이 함정도 함께 적어 뒀음. 보조 신호가 outcome='correct' + target_sound 를 내는 순간 ① 학습자가 다시 말하지 않았는데 복습 단계가 접힘 ② record_signal 이 refresh_review 를 부르지 않아(설계서 §5.5 가 두 진입점만 배선함) 즉시가 아니라 나중에 조용히 반영돼 진단이 어려움.

즉 「target_sound 를 채우자」로 바로 가면 그 둘을 밟음. 먼저 정할 것은 「보조 신호가 복습 단계를 전진시킬 자격이 있는가」임 — 한글 전사는 「학습자가 무엇을 틀렸는지」가 아니라 「ASR 이 언어 판별을 뒤집었다」는 관측이므로 소리를 지목하지 못함.

선택지 셋(초안 — 이 태스크가 판정함):
① 보조 신호는 기록만 하고 복습 시계는 tool 경로에만 걸림. 결정 49 아래에서는 복습이 발음에 대해 돌지 않는다는 뜻이고 그 사실을 문서에 명시함.
② 우리가 target_sound 를 산출함. 한글 전사문에서 소리를 추정하는 것은 발명값이 되므로 근거가 필요함.
③ signal_source 로 필터를 걸어 보조 신호를 단계 전진에서 배제하고, 별도의 「관측됨」 축으로만 셈. review.py 의 그 주석이 「필터를 지금 넣지 않는 이유: 설계가 정하지 않은 동작을 발명하지 않는다」로 남긴 자리임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 보조 신호가 복습 단계를 전진시킬 자격이 있는지 판정하고 근거를 남긴다 — 자격이 없다고 판정하는 경우도 기록한다
- [x] #2 판정에 따라 review.py:207~216 의 주석을 갱신한다 — 그 주석이 「다음 감지기를 만드는 태스크가 이 줄을 함께 판정한다」를 요구한다
- [x] #3 복습 시계가 발음에 대해 돌지 않는 상태를 유지한다면 그 사실을 설계서와 AC 문서에 명시한다 — 조용히 두지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 판정 재료 (2026-09-11 · 팀리드) — 보조 신호가 «세션당 몇 행» 을 만드는지가 이 판정에 걸린다.

TASK-96 이 확정한 것: 첫 발화가 한글로 전사되면 뒤따르는 «애매한» 발화도 한글로 전사될 수 있고(음소 치환판 5/6 · 명료한 발화는 0/7 로 앞 문맥을 이김) 갈리는 축은 둘째 발화의 명료도 하나다(픽스처 쌍 축은 p=1.0000 으로 구별되지 않음). 정본은 그 회차 기록이고 실행은 다른 세션이었다.

⇒ 그래서 scenarios-P §3.2 의 「보조 신호는 세션의 첫 마디부터 심하게 틀려야 발동함」이 조건으로는 여전히 참이지만 결과 범위가 넓어진다 — 첫 마디가 심하게 틀리면 그 뒤의 애매한 발화도 함께 걸리므로 «한 세션이 korean_transcript 행을 여럿 만들 수 있다».

⚠️ 내 P4·P5 관측은 세션당 발화 1건이라 행도 1건이었다(runs/2026-09-10-task82-{p4-p1,p5-p6}.md). 즉 「행 1개」는 그 회차 구성의 산물이고 상한이 아니다. 다중 턴 세션에서 몇 행까지 생기는지는 아직 재지 않았다.

⛔ 이 판정에 미치는 것: 「보조 신호에서 복습 시계를 돌릴지」를 정할 때 그 신호가 만드는 행이 세션당 여러 개일 수 있음을 전제해야 한다. 그 행들은 pattern_id·target_sound 가 둘 다 NULL 이므로(P4 회차에서 직접 확인) 여러 개가 생겨도 복습 시계를 걸 재료는 여전히 없다 — 즉 「재료가 없다」는 판정은 행 수와 무관하게 유지되고, 바뀌는 것은 「무해한가」의 계산이다(행이 쌓이면 pronunciation_attempts 가 실제 시도 수를 과장할 수 있다).

⚠️ §3.2 원문 문단에는 「이 문단의 고정됨은 아래에서 기울임으로 좁혀졌음」 표시만 붙였고 문단을 다시 쓰지 않았다 — 그 조건 서술 자체는 참이고, 두 서술이 나란히 있을 때 위를 먼저 읽고 오독하는 것만 막았다.

2026-09-11 판정 재료 — 코드를 직접 읽어 확정했음(테스트 하네스 갈래). ⛔ 판정 자체는 사용자 몫이라 여기서 결론을 쓰지 않았음.

사실 A — 보조 신호의 유일한 생산자가 `target_sound` 를 주지 않음. `note_transcript`(`services/pronunciation.py`)가 `record_signal` 을 부를 때 넘기는 것은 `target_form=KOREAN_TRANSCRIPT_TARGET_FORM` · `outcome='unclear'` · `signal_source='korean_transcript'` · `spoken_form=transcript` 넷이고 `target_sound` 는 기본값 `None` 으로 남음.

사실 B — 보조 신호 행은 `pattern_id` 도 NULL 임. `record_signal` 은 `_insert_attempt` 만 부르고 `link_pattern` 도 `refresh_review` 도 부르지 않음. 그 둘을 부르는 것은 `record_attempt` 와 `resolve_dangling` 두 경로뿐임. 즉 복습 시계를 걸 재료가 두 컬럼 모두 없음 — P4 회차 관측(`runs/2026-09-10-task82-p4-p1.md`)과 코드가 일치함.

사실 C — 두 번째 생산자는 예정 자체가 없음. `agent_reprompt` 는 「만들지 않는다」가 캡틴 결정(2026-08-28)이고 `TASK-24` 가 2026-09-09 실측으로 「뒤집지 않음」을 판정해 Done 임(근거: 사각 3턴 전부에서 agent 가 되묻지 않아 감지할 문구가 없음). 즉 `review.py` 주석이 걱정한 「다음 감지기」는 계획에 없음. ⚠️ 그 주석이 지목한 소유자가 `TASK-24` 인데 그 태스크는 Done 이라 이 줄의 소유가 이 태스크로 넘어와 있음 — AC#2 가 그 자리를 고치는 일임.

사실 D — 타입 잠금은 절반만 막음. `AssistOutcome = Literal["correct", "unclear"]` 라 `incorrect` 는 값역에 없지만 `correct` 는 허용됨. 그러므로 새 생산자가 `outcome='correct'` + `target_sound` 를 주면 단계가 접히는 경로는 구조적으로 여전히 열려 있음. 지금 닫혀 있는 근거는 전부 호출자 쪽 관례이고 `_PRONUNCIATION_HISTORY_SQL` 자체에는 방어가 0임.

사실 E — 행이 여러 개 쌓여도 오염되는 소비 경로가 없음. 세 소비 경로가 전부 NULL 을 거름. ① 복습: `_PRONUNCIATION_HISTORY_SQL` 이 `btrim(a.target_sound) = p.sound` 로 이으므로 NULL 행이 빠짐. ② 계획: `plan_input._PRONUNCIATION_SQL` 이 `a.target_sound is not null` 을 걺. ③ 빈도: `_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL` 이 `where pattern_id = $1` 로 세므로 `pattern_id` NULL 행이 빠짐. 남는 자리는 결과 화면의 시도 목록 하나이고 프론트가 `signal_source === 'nova_tool'` 로 갈라 렌더함(`app/results/[sessionId]/page.tsx`). ⇒ 노트 앞부분의 「행이 쌓이면 시도 수를 과장할 수 있다」는 «표의 행 수» 에만 해당하고 시도 수를 읽는 경로에는 해당하지 않음.

사실 F — 결정 54 가 같은 축의 원칙을 이미 정했음. 그 결정 ①이 「도착률만으로 우회로를 걷어내지 않는다 — 걷어내면 기록은 생기고 그 기록이 틀린 구간이 생기고, 그 기록으로 복습 시계가 엉뚱한 소리에 걸린다」임(`docs/ops/captain-instruction-register.md`). 한글 전사는 「ASR 이 언어 판별을 뒤집었다」는 관측이라 소리를 지목하지 못하므로 선택지 ②(우리가 `target_sound` 를 산출)는 그 원칙과 정면으로 부딪힘.

⇒ 사실 A~F 로 좁혀진 것: 선택지 ②는 결정 54 ①에 걸려 사실상 닫힘. 남는 것은 ①(현 동작을 문서로 명문화)과 ③(`signal_source` 필터로 쿼리의 불변으로 집행)이고 그 둘은 배타적이지 않음 — ③이 ①의 집행판임. 갈리는 축은 「설계서 §3.2 가 정하지 않은 필터를 지금 넣는 것이 발명인가」 하나임.

2026-09-11 판정 완료 — 사용자가 선택지 ③(필터로 집행 + 명문화)을 골랐음. 정본은 캡틴 지시 대장 결정 59 임.

한 것 넷.

1. AC#1 — 판정과 근거. 「보조 신호는 복습 단계를 전진시킬 자격이 없다」로 정했고 근거 둘을 남겼음: 한글 전사가 소리를 지목하지 못하는 것(관측의 성질)과 결정 54 ①이 같은 축에서 이미 금지한 것(틀린 기록으로 시계가 엉뚱한 소리에 걸린다). 선택지 ②는 그 결정에 걸려 닫혔음.

2. AC#2 — `services/review.py` 의 그 주석을 판정 결과로 다시 썼음. 이전 판이 적어 둔 「필터를 지금 넣지 않는 이유」가 뒤집힌 사실을 명시했고, 그 주석이 지목했던 소유자 `TASK-24` 가 이미 Done 이라 지목이 낡았던 것도 함께 해소했음. 허용 목록(`= 'nova_tool'`)으로 쓴 이유와 relapse 쪽에 걸려도 가리는 것이 없는 이유를 그 자리에 남겼음.

3. AC#3 — 설계서와 AC 문서 두 곳에 명시했음. `docs/design/2026-09-08-pronunciation-review-cycle-design.md` §3.2 에 「네 번째 규칙」으로 넣고, `docs/PRD.md` §10.4 의 AC 목록 뒤에 경계 문단을 넣었음. ⛔ 새 AC 번호를 만들지 않았음 — 이 판정은 요구를 늘리는 것이 아니라 R10-4 의 「판정을 대체하지 않는다」를 복습 주기까지 확장한 것임. R10-4 의 기록 요구와 AC10-3 은 줄이지 않았음.

4. TDD 로 했음. RED 를 먼저 봤음 — `tests/unit/test_pronunciation_review.py::test_an_assist_signal_does_not_advance_the_stage` 가 `assert 2 == 1` 로 실패했음(보조 신호 행이 단계를 2로 올렸음). 필터 한 줄을 넣고 GREEN 을 확인했음.

⛔ 판별력을 지키려고 한 것 하나: 이 테스트는 `record_signal` 을 부르지 않고 행을 직접 넣음. 그 함수를 쓰면 지금의 도달 불가 때문에 필터를 지워도 통과해 판별력이 0이 됨. 형제 테스트(`test_a_correct_attempt_without_a_pattern_id_still_advances_the_stage`)가 같은 회차에서 통과한 것이 양성 대조임.

게이트 (2026-09-11 · `app/backend` cwd 에서 직접 돌림): pytest 940 passed(13.41s) · `ruff check .` exit 0 · unformatted 0 · `ty` exit 0 · 프론트 `tsc`·`eslint` exit 0. ⚠️ 게이트 밖 `ruff check ../../tests ../../scripts` 만 exit 1 이고 그 1건은 `tests/unit/test_plan.py:412` E501 로 동료 세션(`ohmyenglish-7f`)이 지금 만지는 파일임 — 내 두 파일만 따로 돌려 exit 0 을 확인하고 그쪽에 넘겼음.

⚠️ 이 판정이 «닫지 않은» 것 하나: `refresh_review` 의 패턴 조회(`_FIND_SOUND_PATTERN_SQL`)에는 필터를 넣지 않았음. 보조 신호 행으로 재계산이 «발화» 되는 것은 여전히 가능하지만 그 재계산은 이력 쿼리가 그 행을 배제하므로 값이 바뀌지 않는 no-op 임. 그리고 `record_signal` 이 `refresh_review` 를 부르지 않아 제품 경로에서는 발화 자체가 없음. 필터를 한 곳에만 둔 것은 사용자가 고른 안의 범위임.
<!-- SECTION:NOTES:END -->
