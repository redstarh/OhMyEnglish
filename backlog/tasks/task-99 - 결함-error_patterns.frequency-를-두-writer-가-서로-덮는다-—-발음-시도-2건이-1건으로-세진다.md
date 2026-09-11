---
id: TASK-99
title: '결함: error_patterns.frequency 를 두 writer 가 서로 덮는다 — 발음 시도 2건이 1건으로 세진다'
status: Done
assignee: []
created_date: '2026-09-10 22:13'
updated_date: '2026-09-11 13:17'
labels: []
dependencies: []
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 TASK-94(P8) 회차가 실측했다. 정본은 tests/harness/runs/2026-09-11-task94-p8.md §4 다. 같은 컬럼에 writer 가 둘이다 — 발음 경로는 pronunciation_attempts 시도 수를 세고(pronunciation._RECOUNT_PATTERN_FROM_ATTEMPTS_SQL · 앵커 resolved_at) 문법 경로는 error_occurrences 행 수를 센다(analysis._RECOUNT_PATTERN_SQL · 앵커 utterances.created_at). 개수를 가른 조건(시도 2 대 occurrence 1)에서 문법 재계산이 frequency 를 2 에서 1 로 내리고 last_seen_at 을 과거로 옮기는 것을 독립 2회 재현했다. ⚠️ 도달성은 재지 않았다 — 프롬프트에 발음 키를 싣는 경로는 막혀 있고(analysis.load_existing_patterns 가 category <> UNJUDGEABLE_CATEGORY 로 제외 · G-8) 남은 것은 모델이 _PATTERN_KEY_RULES 규칙 2 를 어겨 pronunciation_ 접두 키를 지어내는 것이다. 앱 쪽 검증은 없고 _UPSERT_PATTERN_SQL 이 on conflict (user_id, pattern_key) 로 발음 행을 집으며 category 를 갱신하지 않는다. ⛔ 앱 코드 수정이라 구현 세션 몫이다. ⚠️ 부수: pronunciation.link_pattern 주석이 이 구멍의 근거로 「_EXISTING_PATTERNS_SQL 에 카테고리 필터가 없다」를 지목하는데 그 서술이 낡았다 — 필터가 있다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 도달성을 먼저 판정한다 — 모델이 pronunciation_ 접두 pattern_key 를 지어내는지 실물 분석 회차로 관측한다. 도달하지 않으면 잠재 결함으로 등급을 내리고 그 근거를 적는다
- [x] #2 고치는 층을 고르고 근거를 적는다 — 후보는 upsert 에서 발음 카테고리 행을 문법 경로가 집지 못하게 하는 것과 두 재계산이 카테고리로 갈리게 하는 것이다. ⛔ 새 추상화를 만들지 않는다
- [x] #3 last_seen_at 도 함께 다룬다 — frequency 만 고치면 앵커가 서로 다른 두 값이 같은 컬럼을 계속 덮는다
- [x] #4 pronunciation.link_pattern 의 낡은 주석을 정정한다 — _EXISTING_PATTERNS_SQL 에 카테고리 필터가 이미 있다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 AC#1 완료 — 도달성을 재고 «잠재 결함»으로 등급을 내렸음. 정본은 tests/harness/runs/2026-09-11-task99-reachability/ 임(README.md 가 판정 · observations.json 이 원자료).

방법: 실물 분석 18회(제품 팔 9 · 무력화 대조 팔 9). 두 팔의 차이는 프롬프트에 실린 패턴 수 8 대 9 이고 팔 B 에만 pronunciation_an_as_a 가 실렸음. 결과는 두 팔 모두 pron_category 0 · pron_prefix 0 · reused 0 임. DB 쓰기 0건(전후 스냅샷 동일).

⛔ 양성 대조로 둔 팔 B 도 0 이었으므로 판별력을 별도로 시험했음 — 같은 스크립트 --self-check 4/4 PASS. 그 시험이 밝힌 것 셋: ① 금지 카테고리 + pronunciation_intonation_<x> 조합은 앱이 «막지 않음»(accepted) ② 문법 카테고리 + pronunciation_ 접두 키는 AnalysisValidationError 로 그 발화의 분석 전체를 실패시킴 — frequency 덮어쓰기가 아니라 교정 유실임 ③ 기존 발음 키 재사용은 형식 검사를 받지 않아 그대로 upsert 까지 감.

⛔ 태스크 설명의 「앱 쪽 검증은 없고」를 정정함 — resolve_pattern_keys 가 upsert 앞에서 is_valid_new_pattern_key 로 ^{category}_ 를 강제함. 그것이 문법 카테고리 갈래를 막고 대신 다른 실패로 바꿈.

등급을 내린 근거 셋: ① 프롬프트 경로는 G-8 필터로 닫혀 있고 tests/integration/test_pipeline.py 가 그 제외를 지킴 ② 모델 발명 경로는 18회 0건이고 판별력이 확인됨 ③ 통과 가능한 유일한 조합이 만드는 키는 pronunciation_intonation_<x> 인데 기존 발음 행의 키는 pronunciation_<target_sound> 이고 DB 실측 값역(am_as_i_m · an_as_a · w_as_vw)에 intonation_ 으로 시작하는 것이 없어 충돌 대상 자체가 없음.

⛔ 등급을 내리면서 남긴 것 넷 (AC#2 를 정할 때 이것을 읽어야 함): ① 표본은 팔당 9회이고 「절대 안 낸다」가 아님 ② ⛔ 팔 B 가 발화하지 않았으므로 G-8 필터의 «필요성»은 입증되지 않았음 — 이 회차를 「필터를 지워도 된다」의 근거로 인용하면 안 됨 ③ ErrorFinding.category 가 UNJUDGEABLE_CATEGORY 를 값역에 갖고 금지가 프롬프트 문구뿐이라, 모델이 한 번 쓰면 문법 경로가 발음 카테고리 행을 만듦 — R10-3 위반이고 뒤에 Nova 가 그 소리를 내면 공유 행이 됨(한 발 남았음) ④ AnalysisValidationError 갈래에 pronunciation_ 접두 전용 회귀 테스트가 없음.

AC#4 완료 — services/pronunciation.py 의 낡은 서술 세 곳을 정정했음. 셋 다 「_EXISTING_PATTERNS_SQL 에 카테고리 필터가 없다」를 근거로 삼고 있었는데 G-8 이 그 필터를 넣은 뒤라 낡았음. 자리는 _KNOWN_SOUNDS_SQL 위 주석 · link_pattern docstring · refresh_review docstring 임. ⚠️ 줄 번호 참조(analysis.py:188)를 이름 참조로 바꿨음(기록의 규율 2).

게이트 (app/backend cwd 에서 직접 돌림): pytest 940 passed(12.13s) · ruff check 안·밖 exit 0 · unformatted 0 · ty All checks passed. ⚠️ ty 가 tests/harness/runs/** 까지 본다는 것을 실측했음 — Settings() 에 # ty: ignore[missing-argument] 를 붙이는 것이 이 리포의 확립된 관용임(spike_nova_protocol.py · scripts/smoke_analysis.py 가 같은 주석을 씀).

⇒ 남은 AC#2·#3 은 앱 코드 수정이라 이 갈래가 단독으로 정하지 않음. 등급이 잠재로 내려갔으므로 «고칠지 자체»가 판단 대상이 됐음.

2026-09-11 AC#2·#3 완료 — 사용자가 「finding 하나만 버린다」를 골랐음(선택지 셋 중 ①). 나머지 둘은 「그 발화를 전부 실패시킨다」와 「고치지 않고 가드만 둔다」였음.

AC#2 — 고친 층과 근거. resolve_pattern_keys 안에서 category == UNJUDGEABLE_CATEGORY 인 finding 을 버리고 경고 로그를 남김. ⛔ 자리가 신규 키 형식 검사 «앞»이어야 함 — 뒤에 두면 그 finding 의 키가 규격 밖일 때 버려지지 않고 AnalysisValidationError 가 나서 그 발화의 교정 전체가 날아감. 그 순서를 고정하는 테스트를 따로 뒀음(test_a_dropped_unjudgeable_finding_does_not_fail_the_utterance).

⛔ 새 추상화를 만들지 않았음(AC#2 의 금지 조항). 버리기를 이미 attempts 미매치 키를 버리는 같은 함수 안에 뒀고 상수도 같은 모듈의 UNJUDGEABLE_CATEGORY 를 그대로 씀. 모델 계층에 넣지 않은 이유는 그 상수가 services 에 있어 models 가 services 를 import 하는 역전이 생기기 때문임.

근거 — 왜 실패가 아니라 버리기인가. 같은 함수가 이미 비대칭을 정해 뒀고 그 주석이 「성질이 다른 두 실패를 같은 강도로 다루면 저가치 필드 하나가 그 발화의 교정 전체를 태운다」임. 버릴 대상은 우리가 프롬프트로 «내지 말라고 지시한» 산출이라 값어치 판단 근거가 이미 프롬프트에 있음. 그 세 강도를 docstring 표로 남겼음.

AC#3 — last_seen_at 을 함께 다뤘음. ⛔ 별도 수정을 넣지 않았고 대신 «도달 불가가 됐음»을 확정했음: 발음 행의 pattern_key 는 pronunciation_ + target_sound 이고, 신규 키는 ^{category}_ 를 강제받으며 허용 카테고리 6개 중 그 접두를 만들 수 있는 것이 없음. 재사용 키는 G-8 필터가 발음 행을 목록에서 빼므로 나올 수 없음. ⇒ 문법 경로가 발음 행을 집을 수 없어 frequency 와 last_seen_at 이 둘 다 단일 writer 가 됨(앵커가 발화 시각과 resolved_at 으로 갈리는 문제 자체가 사라짐).

그 근거를 지키는 가드를 넣었음 — test_no_promptable_category_can_produce_a_pronunciation_pattern_key. 판별력 단정을 테스트 «안»에 뒀음(가짜 카테고리 pronunciation_stress 를 넣으면 잡히는 것을 먼저 단정함) — 0건만 단정하면 그 0 을 통과로 읽을 수 없음. 깨지는 유일한 길은 ErrorCategory 에 pronunciation_ 로 시작하는 새 카테고리를 프롬프트 허용 집합에 더하는 것이고 그때 이 테스트가 먼저 실패함.

게이트 (app/backend cwd 에서 직접 돌림): pytest 943 passed(12.82s · 이 태스크가 3건을 더했음) · ruff check 안·밖 exit 0 · unformatted 0 · ty All checks passed · 프론트 tsc·eslint exit 0.

⚠️ 미이행 하나 — 캡틴 지시 대장의 «결정 62» 항목을 아직 붙이지 않았음. 이유는 동료 세션이 결정 61 을 미커밋으로 열어 두어 같은 파일을 지금 담으면 남의 판이 내 커밋에 섞이기 때문임. 코드 주석과 테스트 주석에는 이미 «결정 62» 로 번호를 박아 뒀으므로 그 번호로 붙여야 함. 동료가 커밋하는 즉시 붙임.

2026-09-11 미이행 해소 — 대장의 결정 62 항목을 1a52397 로 붙였음. 동료 세션이 결정 61 을 f0c550d 로 커밋한 뒤에 넣어 두 판이 한 워킹 카피에 섞이는 것을 피했음. ⇒ 이 태스크에 남은 미이행이 0건임.
<!-- SECTION:NOTES:END -->
