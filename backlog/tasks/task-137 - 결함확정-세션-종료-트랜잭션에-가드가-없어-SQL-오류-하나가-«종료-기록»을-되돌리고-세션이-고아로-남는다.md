---
id: TASK-137
title: '결함(확정): 세션 종료 트랜잭션에 가드가 없어 SQL 오류 하나가 «종료 기록»을 되돌리고 세션이 고아로 남는다'
status: Done
assignee: []
created_date: '2026-09-13 23:29'
updated_date: '2026-09-14 00:18'
labels: []
dependencies: []
ordinal: 159000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
발음 축(ohmyenglish-d9)이 두 팔로 갈라 재서 확정한 관측임(2026-09-14 · 검증 전용 DB ohmyenglish_v020 + :8014 + stub). 팔 A: sound_check 컬럼이 있으면 세션이 completed 로 닫히고 ended_at 이 서며 예외 0건. 팔 B: 그 컬럼을 drop 해 019 상태를 재현하면 UndefinedColumnError 가 나고 ⛔ 세션이 active · ended_at null 로 남음. 기전: check_recorded_sounds 가 end_session·resolve_dangling 과 «같은 트랜잭션»에 있고 그 블록에 try 가 없어 예외가 종료 기록까지 되돌림. ⚠️ dev 피해는 0건임 — 그 창에 mode='pronunciation' 세션이 0건이었고 지금 active 도 0건임. ⚠️ I-4 리퍼가 그 고아를 닫는지는 «재지 않았음»(발음 축이 추측으로 적지 않았음). ⛔ 판단은 개발 세션 몫이라고 넘겨 왔음 — 즉 이 태스크는 「종료 기록을 무엇으로부터 보호하는가」를 정하는 것임. 020 이 적용됐으므로 그 컬럼의 직접 위험은 해소됐고 남은 것은 구조적 취약성임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 종료 기록이 «부가 조회» 실패로 되돌아가지 않는 것을 단정으로 못박는다 — 무력화(그 조회를 일부러 실패시킴)로 red 를 먼저 본다
- [x] #2 부가 조회 셋 가운데 어느 것이 종료 기록과 같은 트랜잭션에 있어야 하는지 가른다 — 전부 감싸면 「기록은 됐는데 판정이 없다」가 조용해질 수 있으므로 근거를 적는다
- [x] #3 I-4 리퍼가 그 고아를 실제로 닫는지 확인한다 — 발음 축이 재지 않은 자리이고 추측으로 닫지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — check_recorded_sounds 를 일부러 터뜨리니 RuntimeError 가 올라가 종료 기록이 남지 않았음(단정 실패). 그 red 가 발음 축이 팔 B 로 재현한 것과 같은 기전임.

AC#2(어디까지 감싸는가) — ⛔ 감싸는 범위를 «한 줄»로 좁혔음. end_session 과 resolve_dangling 은 트랜잭션 안에 그대로 뒀음: 남은 pending 이 수렴되지 않으면 「세션은 끝났는데 대답 기다림이 영원히 남은」 행이 생기고 그것이 학습 계산에 섞임(그 함수의 근거) — 즉 종료 «상태»의 일부임. 반면 check_recorded_sounds 는 결정 82 의 «표시»이고 그 실패는 되돌릴 수 있음(복습 큐가 그 행을 유지할 뿐이고 다음 세션 종료가 다시 표시함). ⚠️ 셋을 함께 감쌌으면 「기록은 됐는데 상태가 수렴되지 않았다」가 조용해졌을 것임.

AC#3(I-4 리퍼) — ⚠️ 리퍼 SQL 과 기존 단정을 읽어 확인했고 «새로 돌리지는 않았음». 결론: 리퍼는 그 고아를 닫지만 **failed 로** 닫음(tests/unit/test_sessions.py 의 단정이 그 값을 고정함). 조건이 coalesce(max(utterances.created_at), started_at) < now() - 60s 이므로 마지막 발화 60초 뒤에 걷힘. ⇒ 이 결함의 잔재는 「영구 미종료」가 아니라 **종료 상태의 오기록**임 — 정상 종료한 세션이 failed 로 남음. 발음 축이 「재지 않았다」고 남긴 자리를 그렇게 메웠음.

⚠️ 로그를 warning 으로 찍음(H-Z) — 문서가 지정한 실행 명령에서 INFO 는 보이지 않으므로 그것이 표시 누락의 유일한 신호임.

게이트: pytest 1182 passed exit 0 · ruff 0 · format 0 · ty 0.
<!-- SECTION:NOTES:END -->
