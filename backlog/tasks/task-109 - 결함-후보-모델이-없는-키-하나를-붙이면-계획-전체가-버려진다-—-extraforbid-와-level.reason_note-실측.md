---
id: TASK-109
title: '결함 후보: 모델이 없는 키 하나를 붙이면 계획 전체가 버려진다 — extra=forbid 와 level.reason_note 실측'
status: Done
assignee: []
created_date: '2026-09-11 11:35'
updated_date: '2026-09-11 22:48'
labels: []
dependencies: []
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 세션 ohmyenglish-7f 후속이 이 턴에 직접 관측했다. 같은 재료로 계획을 생성한 첫 호출에서 모델이 level.reason_note: null 을 붙였고 PlanOutput 계열의 extra='forbid' 가 계획 전체를 거부했다(실측 사유: 'level.reason_note Extra inputs are not permitted'). 프롬프트는 이미 'Do not add any key that is not listed above — one unknown key makes the whole response invalid' 를 말하고 있는데도 났다 — 즉 문구로 막는 방식이 실패하는 것을 관측했다. ⚠️ 값이 null 이었다는 것이 중요하다: 내용이 없는 키 하나 때문에 유효한 초점·질문·수준 판정이 통째로 버려지고 job 은 'plan contract violated' 로 실패한다. ⛔ 원장에 올리는 것은 관측이고 처방이 아니다 — 미지의 키를 무시할지, null 인 것만 떨어낼지, 지금처럼 전부 거부할지는 계약 결정이라 이 태스크가 근거를 세워 정한다. 근거 정본: runs/2026-09-11-task86-sound-shaped-questions.md §1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 실패율을 먼저 센다 — 같은 프롬프트로 몇 회 중 몇 건이 없는 키로 거부되는지 실측한다(1회 관측을 비율로 읽지 않는다)
- [x] #2 계약을 유지할지 완화할지 정하고 근거를 적는다 — 완화하면 무엇을 잃는지(모르는 키가 조용히 통과하는 것) 함께 적는다
- [x] #3 ⛔ 사후 처리로 키를 지우는 방식을 쓸 때는 지운 사실을 job 사유나 로그에 남긴다 — 조용히 삼키면 프롬프트가 잘못 유도되고 있다는 신호를 잃는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 동료 세션 ohmyenglish-40 이 전달한 선례 — 이 태스크의 처방 후보를 좁힌다. 정본은 그쪽 회차 tests/harness/runs/2026-09-11-task99-reachability/ 이고 커밋 7c85f3b 다.

① 같은 실패 모양이 분석 경로에도 있다 — resolve_pattern_keys 가 신규 pattern_key 에 ^{category}_ 를 강제하므로 모델이 접두를 헷갈리면 AnalysisValidationError 로 «그 발화의 교정 전체» 가 버려진다. 즉 「모델이 규격 밖 키를 내면 산출 전체가 버려진다」가 계획 경로와 분석 경로 양쪽에 있다.

② ⛔ 그런데 같은 모듈에 비대칭 선례가 이미 있다 — attempts 의 미매치 키는 예외로 올리지 않고 «버린다». 근거 주석이 「저가치 필드 하나가 그 발화의 교정 전체를 태우면 안 된다」다. 이 태스크의 AC#2(계약을 유지할지 완화할지)는 그 선례를 먼저 읽고 정한다 — 새 방침을 발명하는 것이 아니라 이 리포에 이미 있는 방침을 어디까지 적용하는가의 문제다.

⚠️ 다만 선례를 그대로 옮기지 않는다: attempts 는 «저가치 필드» 라는 판단이 붙어 있었고, 계획 쪽에서 버릴 대상은 «모르는 키» 라 값어치를 판단할 근거가 없다. 그 차이를 AC#2 에서 적는다.

2026-09-12 KST **결정 65 로 닫음**(사용자가 위임한 결정 — 「추가 결정사항은 너의 권고 안으로 진행해」). 정본은 docs/ops/captain-instruction-register.md 의 결정 65 임.

AC#1(실패율) — 두 세션이 각각 관측했고 **키 이름이 달랐음**: 내 관측 (계획 생성 2회 중 1회) · 동료 세션 ohmyenglish-40 관측 (4회 중 1회 · 커밋 6b14adf). ⇒ 대략 6회에 2건이고 ⛔ **특정 키의 문제가 아니라 모델이 없는 키를 만드는 «성향»** 임. 그 좁힘이 동료 세션의 관측에서 왔음.

AC#2(계약 유지/완화) — **유지**로 정했음. 근거 셋: ① 모르는 키를 조용히 버리면 프롬프트가 잘못 유도되고 있다는 신호를 잃음(그 신호가 위 표를 만들었음) ② **재시도가 흡수함** — 동료 세션 실측에서 1회차 거부가 2회차에 성공해 계획 행이 생겼음 ③ 키 이름이 매번 다르므로 「그 키를 스키마에 더한다」로는 애초에 닫히지 않음.

⇒ **심각도를 다시 읽었음**: 「계획이 안 생긴다」가 아니라 **「늦게 생기고 재시도 예산을 먹는다」** 임.

AC#3(사후 처리 시 기록) — 사후 처리를 **쓰지 않기로** 정했으므로 그 조건은 발동하지 않음. 그리고 지금도 사유가 남음 — services/plan.py:512 가 report_failure(… f'plan contract violated: {exc}') 로 **없는 키 이름을 그대로** last_error 에 넣음(직접 확인함).

⛔ 다시 열 조건: **재시도 예산이 소진돼 계획이 없는 세션이 관측되면** 결정 65 를 뒤집고 완화안을 다시 봄. 선례는 결정 62(분석 경로에서 finding 하나만 버림)임.

⚠️ 위 AC#1 문장에서 키 이름 둘이 빠졌음 — 노트를 붙일 때 셸이 백틱을 명령 치환으로 먹었음(zsh · 이중 인용 안의 백틱). 값을 여기 다시 적음: 내 관측은 level.reason_note (값 null) 이고 동료 세션 관측은 level.reason_en 임. 그 둘이 다른 것이 이 태스크의 핵심 좁힘임.

⛔ 도구 함정 하나로 남김: backlog task edit --append-notes 에 이중 인용을 쓰면 백틱이 치환됨. 단일 인용을 쓰거나 백틱을 쓰지 않음.
<!-- SECTION:NOTES:END -->
