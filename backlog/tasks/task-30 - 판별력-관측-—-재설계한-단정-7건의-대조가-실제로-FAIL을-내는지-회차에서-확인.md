---
id: TASK-30
title: 판별력 관측 — 재설계한 단정 7건의 대조가 실제로 FAIL을 내는지 회차에서 확인
status: Done
assignee: []
created_date: '2026-09-06 02:43'
updated_date: '2026-09-09 08:40'
labels:
  - caps-req
dependencies:
  - TASK-19
  - TASK-21
  - TASK-22
  - TASK-37
priority: high
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-29 가 7건을 재설계했으나 판별력을 '설계'했을 뿐 '관측'하지 않았다. 대조가 무력화에서 실제로 FAIL 을 내는지는 브라우저 회차에서만 관측된다 — TASK-29 안에서는 순환한다(회차가 재설계를 전제한다). 정본은 tests/harness/browser_leg.md 의 재설계 상자와 §5 표이고, 리뷰 근거는 docs/design/2026-09-06-review-outcomes.md §4 가 소유한다. 관측 전에는 이 7건을 PASS 로 보고하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A1-4 의 when 인자 대조가 실제로 판별력을 갖는지 확인 — 세 값이 전부 같으면 FAIL 이 나는가
- [x] #2 A1-5 의 sentinel 변형 대조가 FAIL 을 내는지 확인
- [x] #3 A1-7 의 무음 스트림 대조가 audio 계수 0 을 내는지 확인 — 못 내면 판별력 미확인으로 기록한다
- [x] #4 A3-1 의 상태별 세션 재방문에서 같은 요소의 문구가 바뀌는지 확인
- [x] #5 A4-1 의 primary 세션이 corrections 를 비우지 않음을 확인하고 빈 세션 대조가 0 개를 내는지 확인
- [x] #6 A4-2 의 기대값 교차 대조가 FAIL 을 내는지 확인 — 교정 2건 이상 세션이 필요하다. 1건뿐이면 판별력 미확인으로 기록한다
- [x] #7 A5-1 의 순차 주입에서 같은 요소의 문구가 매번 바뀌는지 확인
- [x] #8 관측 결과를 회차 기록에 남기고 미확인으로 남은 건을 browser_leg.md 상자에 정확한 개수로 갱신한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 착수 — 회차를 셋으로 나눈다 (실물 호출 0회).

프리플라이트(메인이 직접 확인): 백엔드 :8002 pid 55492 · 프로세스 환경에 WORKER_ENABLED=false 실재(ps eww) · VOICE_ADAPTER=nova · 프론트 :3000 HTTP 200 · 보존 세션 6개 전부 기대 상태 유지(결과 API).

⛔ 어댑터 규약 때문에 한 회차로 8건을 못 닫는다(browser_leg.md:119-127 — 한 회차는 어댑터 모드 하나만 판정하고 재기동은 호출자 몫이다).

- 회차 1 (어댑터 무관 · /results 재방문): AC#4 A3-1 · AC#5 A4-1 · AC#6 A4-2 → frontend-verifier 에 위임했다. 기대값은 메인이 API·소스에서 직접 유도해 /tmp/omy-expect.json 과 프롬프트에 실었다. A4-1 primary=C3b(N=1) · 음성대조 C3c(N=0)·C3e(키 부재). A4-2 primary=C3f(N=2 · reason 51자·63자로 둘 다 비지 않아 BLOCKED 조건이 아니다 — 오래 막혔던 항목이 이번에 평가 가능해졌다).
- 회차 2 (VOICE_ADAPTER=stub 재기동): AC#1 A1-4 · AC#2 A1-5 · AC#3 A1-7
- 회차 3 (VOICE_ADAPTER=stub_unresponsive · 주입 창 browser_leg.md:405): AC#7 A5-1

재기동 시 ⛔ WORKER_ENABLED=false 를 반드시 넣는다(config.py:63 기본값 True · .env 에 그 키가 없다 — 직접 확인). 기동 명령 정본은 browser_leg.md:160-162.
복구: .env 에 VOICE_ADAPTER 가 없고 코드 기본값이 stub 이므로(config.py:68) 재기동하면 nova 가 아니라 stub 이 된다. 회차가 끝나면 VOICE_ADAPTER=nova 로 명시해 원래 상태로 되돌린다.

AC#8(기록·개수 갱신)은 세 회차가 끝난 뒤 마지막에 한다.

회차 1 완료 (2026-09-09 · 어댑터 무관 · 실물 호출 0회 · 재기동 0회).

판정 — A3-1 PASS(판별력 있음: 5×5 라벨 교차에서 비대각 어긋남 20/20 · 같은 선택자가 다섯 상태에서 서로 다른 다섯 값) · A4-1 PASS(계수 부분 · 대조 두 페이지에서 0≠1 2/2) · A4-2 PASS(맞바꾼 기대값에서 2/2 어긋남).

⛔ 호출자가 A4-2 를 독립 재현했다(규약: 보고를 그대로 믿지 않는다). 자동 저장된 015-eval.html 을 파싱하고 결과 API 를 다시 호출해 비교했다 — 손 전사 0. 본 단정 어긋남 0/2 · 맞바꾼 기대 2/2 FAIL. 검증자보다 한 단계 더: 카드 귀속을 original_span 등호로 확인해 순서 가정을 배제했다. 스크립트는 /tmp/omy_a42_verify.py.

무변경 증거: 보존 세션 6개 전부 기대 상태 유지 · baseline drift 0 · 백엔드 pid 55492 동일 · 세션 생성 0건.

⚠️ 판별력 미확인 2건(새로 발견) — A4-1 의 구조 하위 단정 둘: 「카드 <p> 정확히 3개」·「셋째가 비어 있지 않다」. 카드 3개에서 성립했으나 3이 아닌 카드나 빈 셋째를 낸 페이지를 보지 못했다. 계수 부분만 관측됐다. A4-2 의 대조는 기대값 쪽 무력화이고 앱 쪽 뒤바뀜은 만들지 않았다(문서가 금지) — 두 방향 대칭은 추론이다.

절차 문서 결함 5건이 보고됐고 3건을 고쳤다(전부 호출자가 코드·브라우저로 직접 재확인한 뒤):
1. §5 A4-1 의 음성 대조가 약한 쪽을 지목했다 — page.tsx:129 showCorrections 가 final·partial_failure 만 통과시켜 no_utterances 에서는 교정 컨테이너가 마운트조차 안 된다. C3c 가 강한 대조다. §9 는 처음부터 C3c 를 지목했고 이 행만 어긋나 있었다.
2. §10 에 eval 반환 형식 규약이 없어 증거가 조용히 사라진다 — 객체를 반환하면 Result: [object Object] 로 접힌다(호출자가 일부러 넣어 재현). top-level await 도 막힌다(직접 얻은 오류는 SyntaxError: await is only valid in async functions… 이고 검증자가 적은 ReferenceError 와 문자열이 다르다).
4. §10 의 「session_plans·learner_notes 는 세 시점 모두 1행」이 낡았다 — 실측 2행·3행. 세지 않는 서술로 바꿨다(정상을 이상으로 오판하거나 1행으로 복원하려 드는 것이 위험이다).
고치지 않은 2건: §3 에 읽기 전용 회차 분기가 없다(회차 2·3 은 세션을 만들므로 해당 없음) · A3-1 의 「같은 요소」가 노드 동일성인지 선택자 동일성인지 미명시(약함).

§11-9 를 닫았다 — A4-2 표본 유무가 「없다」에서 「있다」로 바뀌었다. ⛔ C3f 를 지우면 되살아난다는 경고를 함께 넣었다.

⛔ 다음 세션이 잊지 말 것: 판별력 재설계 상자의 「미확인으로 남을 수 있는 것 2건」은 아직 안 고쳤다. A1-7 이 회차 2 에서 판정되므로 그때 한 번에 고친다(두 번 고치지 않는다). 그 자리에 A4-1 구조 하위 2건도 함께 넣어야 한다.

⛔ 회차 2 유실 (2026-09-09) — H-AO 재발. 다시 돌려야 한다.

위임한 검증자가 「Now let me write the run record」 시점에 API 오류로 죽었다. 즉 관측은 끝내고
산출물만 잃었다 — pitfalls H-AO 가 적은 그 형태다.

⚠️ 무결성은 지켜졌다(호출자가 직접 확인): 보존 세션 6개 전부 기대 상태 · 8개 표 수치가 baseline 과
전부 동일(learning_sessions 13 · analysis_jobs 49 · utterances 120 · error_patterns 9 ·
session_plans 2 · learner_notes 3 · pronunciation_attempts 4 · error_occurrences 24) · drift 0 ·
harness_sessions 에 run_id 6454e5c1 로 C1 세션 3건이 등록돼 teardown 감사 기록이 남았다.
즉 검증자가 회차를 정상 수행하고 teardown 까지 끝냈다.

잃은 값: A1-4 의 when 배열 · A1-5 의 6줄 textContent · A1-7 의 sent.audio/end_session 계수와
무음 대조 결과. AC#1·#2·#3 은 미체크로 둔다.

⛔ 순서를 바꾼다 — 위임을 다시 하지 않고 C1 실행체를 만든 뒤 돌린다. 근거: 위임이 두 번 중 한 번
죽었고(H-AO), C1 은 단정이 9건으로 가장 많아 유실 비용이 크고, 실행체가 있으면 유실이 구조적으로
불가능해진다. TASK-49 가 C5 에서 같은 판단을 이미 내렸다.

새 순서: ① stub_unresponsive 재기동 → TASK-49 AC#2·#3 실행 검증 = TASK-30 AC#7(A5-1) 을 함께 닫음
(재기동 1회로 둘을 처리한다) ② 그 뒤 C1 실행체 신설 → AC#1·#2·#3 ③ AC#8.

⛔ 위임 대상 재지정 (2026-09-09 · TASK-53). frontend-verifier 정의가 제거됐고 대체 에이전트로 갈아 끼우지 않았다 — 실행체로 옮겼다.

AC#4·#5·#6(A3-1·A4-1·A4-2)은 회차 1 에서 그 에이전트로 이미 닫혔고 그 기록은 그 시점 사실이므로 고치지 않는다. 남은 AC#1·#2·#3(A1-4·A1-5·A1-7)은 TASK-52 의 C1 실행체(tests/harness/c1_session_walkthrough.py)로 호출자가 직접 돌린다. AC#7(A5-1)은 TASK-49 의 C5 실행체로 이미 닫았다.

근거: 위임이 두 번 중 한 번 죽었다(회차 2 · H-AO). 실행체는 판정이 순수 함수라 게이트가 브라우저 없이 판별력을 고정하고(test_c1_gates 15 passed · test_c5_gates 11 passed) 관측이 파일로 떨어져 유실이 구조적으로 불가능하다. 판정 정본은 docs/ops/review-and-decision-protocol.md 의 그 절이다.

⚠️ app-test-agent 는 사용자 여정 검증에 쓰고 하네스 단정 판정에는 쓰지 않는다 — 둘은 겹치지 않는다.

2026-09-09 완료 — 판별력 7건 전부 관측. 회차 기록 넷이 값을 갖는다.

A3-1·A4-1·A4-2 → runs/2026-09-09-task30-discrimination-c3c4.md (회차 1 · 위임)
A5-1 → …-c5-a51.md (TASK-49 의 C5 실행체 · 호출자 직접)
A1-4·A1-5 → …-c1-tone.md (VOICE_ADAPTER=stub · TASK-52 의 C1 실행체)
A1-7 → …-a17.md (VOICE_ADAPTER=stub_unresponsive)

⛔ 미결 둘이 닫혔다: §11-4(A1-7 대체 대조가 세션 관통에서 성립 — 톤 313 / 무음 0 이고 sent.audio 는
313=313 으로 같다) · §11-9(A4-2 표본이 실물 세션 C3f 로 생겼고 맞바꾼 기대값에서 2/2 어긋남).

⛔ 새로 드러난 미확인 2건을 재설계 상자에 적었다 — A4-1 의 구조 하위 단정 둘(카드 <p> 3개 · 셋째가
비어 있지 않다)은 계수 부분만 관측됐다. 3 이 아닌 카드를 낸 페이지를 보지 못했고 스텁으로는 만들 수
없다. A4-2 의 대조가 기대값 쪽 무력화라는 한계도 함께 적었다.

⚠️ 판별력이 이제 게이트로 옮겨졌다 — 실행체 셋이 판정을 순수 함수로 분리해 test_c1_gates(15) ·
test_c3_gates · test_c5_gates(11) 가 브라우저 없이 변이를 잡는다. 재설계가 퇴화하면 회차를 열기 전에
죽으므로 이 태스크와 같은 관측을 다시 열 필요가 없다.

게이트 넷 전부 직접 확인: pytest 869 passed · 게이트 밖 ruff·format exit 0 · ty exit 0 (H-AV 대로).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행에 TASK-37 을 더했다(기존 TASK-19·21·22 는 보존). 이 태스크 설명이 「대조가 실제로 FAIL 을 내는지는 브라우저 회차에서만 관측된다」고 적는데 그 회차를 소유한 태스크가 TASK-37 이다(AC#2 가 B1~B4 재확인과 라이트·다크 5상태를 담는다). 회차를 따로 도는 대신 5차수 안에서 관측한다.
---
<!-- COMMENTS:END -->
