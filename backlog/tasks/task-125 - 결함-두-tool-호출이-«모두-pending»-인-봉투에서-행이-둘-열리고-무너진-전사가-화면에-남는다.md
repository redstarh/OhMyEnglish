---
id: TASK-125
title: '결함: 두 tool 호출이 «모두 pending» 인 봉투에서 행이 둘 열리고 무너진 전사가 화면에 남는다'
status: Done
assignee: []
created_date: '2026-09-12 01:09'
updated_date: '2026-09-14 00:32'
labels: []
dependencies: []
ordinal: 130000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 실측 · 눈 증거 있음. 정본: tests/harness/runs/2026-09-12-task103-target-form-storage.md §1-⑷ · 화면 캡처 screen_residual.png.

TASK-103 이 판정 UPDATE 에 target_form 을 더해 「pending → 판정」 봉투를 닫았다. ⛔ 그런데 관측된 봉투 하나는 두 호출이 «모두 pending» 이었다(12/12 · runs/2026-09-11-task97-tool-payload.md). 그 경로에서는 판정 UPDATE 가 «아예 돌지 않으므로» 고친 자리를 지나지 못한다.

실측한 결과 둘:
① 무너진 전사가 살아남는다 — resolve_dangling 이 두 행을 다 incorrect 로 수렴시키고, 오래된 행의 target_form 이 «I think Sri sings are ready for the demo.» 로 남는다. 그것이 결과 화면의 「시범 문장」 자리에 뜬다. 즉 「이렇게 말하세요」 자리에 학습자의 오발음이 뜬다 — 화면을 직접 열어 봤다.
② 한 코칭 사건에 카드가 «두 장» 뜬다. 학습자에게는 같은 일을 두 번 한 것처럼 보인다.

⛔ 둘 다 표시 문제가 아니라 «행이 둘 열린다» 는 저장 문제다 — TASK-103 AC#4 가 경고한 자리이므로 표시를 고쳐 덮지 않는다.
⚠️ 지금 거동은 테스트로 못박혀 있다 — tests/integration/test_pronunciation_service.py 의 test_two_pendings_leave_the_broken_target_form_on_the_older_row. 그 단정은 «여기까지만 고쳐졌다» 를 재는 것이고 이 태스크가 닫히면 «의도적으로 뒤집어야» 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 재현 조건을 코드로 확정한다 — 판정 UPDATE 가 돌지 않는 분기로 설명되므로 Nova 를 쓰지 않고 닫는다
- [x] #2 한 코칭 사건이 행 하나가 되게 할지, 행 둘을 두고 화면에서 묶을지 정하고 근거를 적는다. ⛔ 표시로 덮지 않는다 — 복습 시계와 계획 프롬프트가 같은 값을 읽는다
- [x] #3 test_two_pendings_leave_the_broken_target_form_on_the_older_row 의 단정을 의도적으로 뒤집고 그 위 주석을 함께 고친다 — 주석이 뒤집는 근거를 갖고 있다
- [x] #4 화면을 직접 열어 카드가 하나인 것과 「시범 문장」 에 오발음이 없는 것을 확인한다 — seed_residual.py.txt 를 그대로 쓴다(새로 만들지 않는다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4) — 회차 기록은 tests/harness/runs/2026-09-14-task125-fold-pending.md 임.

AC#1(재현을 코드로 확정) — Nova 를 쓰지 않고 닫았음. 재현은 「판정 UPDATE 가 돌지 않는 분기」로 설명되므로 record_attempt 를 두 번 pending 으로 부르는 것으로 충분했음.

AC#2(행 하나인가 둘인가) — ⛔ **행 하나로 접음**. 근거 둘: ① 규칙 10 이 한 코칭 사건을 「시범 + 재발화 판정」으로 짝지으므로 열린 pending 은 언제나 하나여야 하고 둘은 이상 상태임 ② 관측이 «나중 호출이 옳은 문장»을 싣는다고 말함(첫 호출이 무너진 전사) — 그것은 TASK-103 이 판정에 적용한 「나중 값이 target_form 을 덮는다」와 같은 규칙임. ⛔ 표시로 덮지 않은 이유는 복습 시계와 계획 프롬프트가 같은 행을 읽기 때문임. ⚠️ 대가를 코드 주석과 회차 §5 에 적었음 — 판정 없는 코칭이 두 번이면 복습 시계가 하나로 셈.

AC#3(단정 뒤집기) — 이름·단정·주석을 함께 고쳤음(test_a_second_pending_folds_into_the_open_row_with_the_later_target_form). 뒤집힌 경위를 그 주석이 갖게 했음.

AC#4(화면) — seed_residual.py.txt 를 그대로 돌렸고 같은 입력에서 결과가 갈렸음: 행 둘 → 행 하나 · 시범 문장이 오발음 → 옳은 문장. 화면과 API 를 직접 열어 봤음(카드 한 장 · pronunciation 배열 1건).

⚠️ 이웃 다섯이 깨졌고 전부 「내 변경이 옳아서」였음 — 넷은 setup 만 _legacy_pending 으로 우회(재는 축 유지 · DB 에는 두 pending 이 실재할 수 있음), 하나는 게이트웨이 대본이 바로 그 봉투라 행 수 단정을 고치고 나중 target_form 단정을 더했음.

게이트: pytest 1182 passed exit 0 · ruff 0 · format 정합 · ty 0.
정리: :3000·:8016 000 · dropdb exit 0 · dev DB 무변경(세션 17 · 시도 7 · 최대 022).
<!-- SECTION:NOTES:END -->
