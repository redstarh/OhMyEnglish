---
id: TASK-34
title: 프론트 계약에 기계적 방어를 둔다 — 「결과 화면에 숫자를 렌더하지 않는다」 자동 게이트
status: Done
assignee: []
created_date: '2026-09-07 16:34'
updated_date: '2026-09-09 14:09'
labels: []
dependencies: []
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Batch C 리뷰가 LOW(NOTE) 로 올렸다: app/frontend/app/results/[sessionId]/page.tsx 의 「드릴 두 수를 화면에 렌더하지 않는다」 계약을 지키는 자동 게이트가 없다. tests/harness/c3_results_screen.py 는 directPCount 를 측정만 하고 단정하지 않아 새 <p> 한 줄을 모른다. 캡틴 결정 10(미달의 주어는 학습자가 아니라 대화 모델 — 학습자가 손쓸 수 없는 수를 자기 점수로 읽게 하지 않는다)과 결정 18 이 걸린 계약인데 사람의 주의에만 의존한다. 팀리드가 코드로 '숫자가 DOM 에 닿을 수 없음'을 확인했으나 그것은 지금 코드에 대한 확인이고 회귀 방어가 아니다. 브리프 테스트 목록에 프론트 항목을 넣지 않은 것도 팀리드 쪽 누락이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 결과 화면에 드릴 두 수(exchanges_observed·exchanges_expected)가 렌더되지 않는 것을 기계적으로 단정한다 — 무력화(일부러 숫자를 렌더) 에서 실제로 FAIL 하는 것을 관측해 판별력을 증명한다
- [x] #2 미달일 때만 문장이 그려지고 달성 세션에는 아무것도 그려지지 않는 것을 함께 단정한다 (달성 문장도 점수판이 된다)
- [x] #3 c3_results_screen.py 의 directPCount 를 측정에서 단정으로 올릴지, 별도 프론트 테스트로 둘지 정하고 근거를 남긴다 — 하네스는 브라우저 회차 규약(browser_leg.md)의 소유물이라 함부로 고치지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 계약을 사람의 주의에서 게이트로 옮겼음. `browser_leg.md` 에 `A3-3` 으로 정식 등록했음.

AC3 판단 — `c3_results_screen.py` 에 순수 함수(`check_drill_contract`)로 두고 `test_c3_gates.py` 가 무력화로 지킴. 근거 셋:
① 별도 프론트 테스트를 만들지 않았음 — 이 리포에 JS 테스트 러너가 없음. `app/frontend/package.json` 의 스크립트는 dev·build·start·lint 넷이고 devDependencies 에 jest·vitest·jsdom 이 0건임(직접 읽어 확인). 러너와 jsdom 을 새로 들이는 것은 단정 하나가 요구하는 비용을 넘음.
② `directPCount` 를 등호로 올리지 않았음 — 그 수는 계약이 아니라 구현의 부산물이라 정당한 `<p>` 하나만 늘어도 깨짐. `TASK-55` 가 출구 링크를 넣을 때 실제로 늘었음. 계약이 말하는 것은 개수가 아니라 무엇이 그려지는가임.
③ 계약은 렌더된 출력에 걸리고 그것을 관측하는 것은 브라우저 다리뿐임. 판정을 순수 함수로 빼면 픽스처로 브라우저 없이 회귀를 잡음 — `TASK-64` 가 같은 이유로 A3-1 을 뺐고 그 형태를 따랐음.

AC1 — 「그 두 수가 없다」로 재지 않았음. 문자열로 찾으면 양쪽으로 틀림: 교정문에 우연히 든 수가 오탐이 되고, `아홉`·`2회` 같은 다른 표기로 새면 못 잡음. 재는 것은 「API 가 준 학습자 문구에 없던 숫자가 화면에 있는가」임 — 화면 소유 상수에 숫자가 하나도 없음(직접 확인). 그래서 드릴 두 수뿐 아니라 `occurrences` 같은 다른 누출까지 막음. ⛔ `target_form` 은 허용 목록에 넣지 않았음(렌더되지 않는 필드를 허용하면 그 필드에만 있는 숫자가 새도 통과함). ⛔ `bodyText` 가 아니라 `main` 만 읽음(`next dev` 주입 스크립트에 숫자가 섞여 항상 FAIL 임).

판별력을 실물에서 관측했음 — 임시로 `<p>{observed} / {expected}</p>` 를 넣고 회차를 돌려 FAIL 을 받았음: `[final_two] 화면에 API 가 주지 않은 숫자가 있다 — ['2', '20']` (단정 94건 중 어긋남 1건). 되돌린 뒤 94건 전건 통과임. 되돌림을 두 가지로 확인했음 — `grep TASK34_MUTATION_TEMP` 0건 · `git diff --stat` 이 그 파일에 아무것도 내지 않음.

AC2 — 「미달일 때만 그린다」를 biconditional 로 재므로 달성 세션에 문장이 있으면 FAIL 임. ⚠️ 실물 표본이 미달 하나(`final_two` = 2/20)뿐이라 달성 갈래는 회차에서 미확인으로 내고 통과로 세지 않음 — 그 갈래는 게이트의 무력화가 지킴(`test_shortfall_notice_on_a_met_session_is_caught`).

⛔ 오탐 대조를 함께 넣었음 — API 가 준 교정문의 숫자(`2026년`)는 FAIL 을 내지 않음. 이것이 없으면 이 단정은 「숫자가 하나도 없다」와 구별되지 않아 교정문에 연도가 든 세션에서 잡음 생성기가 됨.

본문을 고치고 그것을 설명하는 문장을 함께 고쳤음: `browser_leg.md` §5 표에 `A3-3` 추가 · 같은 문서의 「단정 18건」과 유도 방식 분류에서 **개수를 없앴음**(`A3-3` 을 더하자 그 수가 실제로 낡았음 — 세지 않는 서술로 바꾸는 것이 유일하게 통한 해법임) · `test_c3_gates.py` 모듈 docstring 에서 픽스처 파일 이름을 뺐음(같은 세션 안에서 두 번 낡았음).

게이트: pytest 884 passed · ruff check exit 0 · format unformatted 0 · ty check exit 0 · 게이트 밖 ruff 0건 · format unformatted 0 · 프론트 tsc·eslint exit 0. 877 → 884 는 이 태스크가 넣은 판별력 7건임.
회차 기록은 tests/harness/runs/2026-09-09-task34-drill-number-contract.md 임.
<!-- SECTION:NOTES:END -->
