---
id: TASK-125
title: '결함: 두 tool 호출이 «모두 pending» 인 봉투에서 행이 둘 열리고 무너진 전사가 화면에 남는다'
status: To Do
assignee: []
created_date: '2026-09-12 01:09'
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
- [ ] #1 재현 조건을 코드로 확정한다 — 판정 UPDATE 가 돌지 않는 분기로 설명되므로 Nova 를 쓰지 않고 닫는다
- [ ] #2 한 코칭 사건이 행 하나가 되게 할지, 행 둘을 두고 화면에서 묶을지 정하고 근거를 적는다. ⛔ 표시로 덮지 않는다 — 복습 시계와 계획 프롬프트가 같은 값을 읽는다
- [ ] #3 test_two_pendings_leave_the_broken_target_form_on_the_older_row 의 단정을 의도적으로 뒤집고 그 위 주석을 함께 고친다 — 주석이 뒤집는 근거를 갖고 있다
- [ ] #4 화면을 직접 열어 카드가 하나인 것과 「시범 문장」 에 오발음이 없는 것을 확인한다 — seed_residual.py.txt 를 그대로 쓴다(새로 만들지 않는다)
<!-- AC:END -->
