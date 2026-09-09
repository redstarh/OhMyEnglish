---
id: TASK-30
title: 판별력 관측 — 재설계한 단정 7건의 대조가 실제로 FAIL을 내는지 회차에서 확인
status: In Progress
assignee: []
created_date: '2026-09-06 02:43'
updated_date: '2026-09-09 04:50'
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
- [ ] #1 A1-4 의 when 인자 대조가 실제로 판별력을 갖는지 확인 — 세 값이 전부 같으면 FAIL 이 나는가
- [ ] #2 A1-5 의 sentinel 변형 대조가 FAIL 을 내는지 확인
- [ ] #3 A1-7 의 무음 스트림 대조가 audio 계수 0 을 내는지 확인 — 못 내면 판별력 미확인으로 기록한다
- [x] #4 A3-1 의 상태별 세션 재방문에서 같은 요소의 문구가 바뀌는지 확인
- [x] #5 A4-1 의 primary 세션이 corrections 를 비우지 않음을 확인하고 빈 세션 대조가 0 개를 내는지 확인
- [x] #6 A4-2 의 기대값 교차 대조가 FAIL 을 내는지 확인 — 교정 2건 이상 세션이 필요하다. 1건뿐이면 판별력 미확인으로 기록한다
- [ ] #7 A5-1 의 순차 주입에서 같은 요소의 문구가 매번 바뀌는지 확인
- [ ] #8 관측 결과를 회차 기록에 남기고 미확인으로 남은 건을 browser_leg.md 상자에 정확한 개수로 갱신한다
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
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행에 TASK-37 을 더했다(기존 TASK-19·21·22 는 보존). 이 태스크 설명이 「대조가 실제로 FAIL 을 내는지는 브라우저 회차에서만 관측된다」고 적는데 그 회차를 소유한 태스크가 TASK-37 이다(AC#2 가 B1~B4 재확인과 라이트·다크 5상태를 담는다). 회차를 따로 도는 대신 5차수 안에서 관측한다.
---
<!-- COMMENTS:END -->
