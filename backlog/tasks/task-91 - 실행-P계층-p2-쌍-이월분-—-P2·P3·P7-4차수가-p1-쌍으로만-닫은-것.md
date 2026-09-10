---
id: TASK-91
title: '실행: P계층 p2 쌍 이월분 — P2·P3·P7 (4차수가 p1 쌍으로만 닫은 것)'
status: In Progress
assignee: []
created_date: '2026-09-10 13:59'
updated_date: '2026-09-10 14:11'
labels: []
dependencies: []
ordinal: 94000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-37(5차수)이 P8 과 p2 쌍을 이월분으로 남겼고 TASK-82 가 P1·P4·P5·P6 만 닫았다. 남은 것은 P2·P3·P7 의 p2 쌍이다. ⚠️ N계층은 이월분이 아니다 — 5차수가 N6·N7·N8·N11·N12·N13 을 전부 PASS 로 닫았고(runs/2026-09-09-run-5.md:16) N9·N10 은 태스크 설명이 일부러 뺀 것이다. handoff 이전 판이 「N계층도 열려 있다」고 적었던 것은 낡은 서술이었다.

⛔ P2 는 이번 회차가 이미 재료를 가졌다 — TASK-82 P6 세션의 p2m 전사문이 i finished the la porte en chaille de lesseps with my team. 이고 p2a 전사문은 i finished the report and shared the results with my team. 이다. 즉 문자 단위로 동일하지 않다. 4차수가 p1 쌍에서 얻은 「전사문이 동일하다 → 앱은 발음 오류를 인지하지 못한다」가 p2 쌍에서는 성립하지 않는다. 정본은 runs/2026-09-10-task82-p5-p6.md §4-1 이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 P2: p2a 와 p2m 의 전사문을 문자 단위로 대조해 판정한다. 이번 회차 재료로 충분한지 먼저 판단하고 부족하면 세션을 새로 만든다. ⛔ 4차수의 p1 쌍 결론을 뒤집는 것이 아니라 쌍에 따라 갈린다는 것을 적는다
- [x] #2 P3: p2m 에 대해 agent 가 발음을 지목하는지 관측한다. ⛔ 발음 코칭 기저율이 앱 경로에서 0/n 이고 원인이 미확정이므로 한 회차의 0건을 신호로 쓰지 않는다
- [ ] #3 P7: p2a 세션과 p2m 세션의 결과 화면을 대조한다. ⛔ 스크린샷 2장이 바이트 동일이면 판정 불가다 — 4차수가 그 함정에 걸렸다(세션 식별자가 보이는 캡처를 받는다)
- [ ] #4 회차 전에 browser_leg.md §8-0 의 새 절차대로 error_patterns 의 next_review_at·mastery_score 와 review_tasks 를 파일로 뜬다 — 분석 워커를 지나가면 복습 시계가 움직인다(H-AY)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
착수·부분 완료 2026-09-10 (ohmyenglish-40). 실물 호출 0회 · DB 쓰기 0건. 정본은 tests/harness/runs/2026-09-10-task91-p2-p3-p7.md 임.

기존 원자료로 판정한 근거: TASK-82 두 회차의 p2a·p2m 세션이 같은 조건이었음 — 둘 다 앱 경로 · 해당 픽스처를 세션의 첫 발화로 단독 · sampleRate 16000(원자료에서 직접 확인). P2·P3 이 요구하는 대조가 그 조건에서 성립함.

AC#1 (P2) 충족 — 판정: p1 쌍의 결론이 p2 쌍에서 성립하지 않음. 전사문이 동일하지 않으므로(공통 접두 「i finished the 」 · 공통 접미 「 with my team.」 · 가운데가 report and shared the results 대 la porte en chaille de lesseps) P2 의 조건문이 거짓임. ⛔ 4차수를 뒤집지 않음 — 쌍에 따라 갈림. 두 쌍의 실패 모드가 다름: p1 은 발음 오류가 전사문에서 소실돼 볼 것이 없고, p2 는 전사문을 파괴해 볼 재료는 있으나 그것을 발음으로 읽지 않음. 후자가 TASK-82 P6 의 FAIL 이고 TASK-84 판정이 그것을 받았음.

AC#2 (P3) 충족 — 판정: 발음 지목 0건(기대대로). agent 발화 둘에 발음·소리·억양 낱말이 0건이고 되말하게 하지도 않았음. ⛔ 새 현상 하나: p2m 세션에서 agent 가 무너진 전사문을 「메웠음」 — 전사문은 la porte en chaille de lesseps 인데 agent 는 finishing a project 라고 말했고 project 는 전사문에 없는 낱말임. 그리고 사후 분석기는 같은 자리를 report 로 메웠음. 두 층이 서로 다른 낱말로 메웠으므로 둘 다 추측이고 일치하지도 않음. ⚠️ 환각으로 단정하지 않음 — 인과를 재지 않았고 표본 1건임. 관련 판정 소유자는 TASK-88 임.

AC#3 (P7) 미충족 — 판정 불가. 두 결과 화면 캡처가 md5 동일(305746073160ed91671eb9918e61a69c)이고 4차수가 걸린 함정과 같은 형태이나, 이번에는 「같은 캡처」가 아니라는 판별력이 있음(같은 드라이버가 낸 P4-results.png 는 다름 — 발음 절과 관찰된 신호가 있음). ⛔ 그래도 닫히지 않는 이유가 더 큼 — 두 캡처가 둘 다 「분석 중」임(팀리드가 이미지를 직접 열어 확인: 학습 결과 / 분석 중 / 링크 뿐이고 교정 0건). 분석 전에는 두 화면이 같은 것이 자명하므로 그것을 PASS 로 읽으면 아무것도 배제하지 못하는 대조가 됨. 특히 p2m 세션은 그 뒤 분석 job 이 처리돼 final + 교정 1건이 됐으므로 최종 화면은 두 세션이 다름. 닫으려면 분석 job 을 처리한 뒤 캡처해야 하고 그 세션들은 teardown 됐으므로 새 세션 2건 + 분석 2회가 필요함 — 실물 호출이 들어 이 회차에서 쓰지 않았음.

AC#4 미충족(해당 없음으로 처리하지 않고 미체크로 둠) — 이 회차는 분석 워커를 지나가지 않아 그 절차를 실행할 자리가 없었음. ⛔ 체크하면 「했다」가 되어 거짓이므로 체크하지 않음. P7 을 닫는 회차가 워커를 지나가므로 그때 이 AC 가 실제로 필요해짐.
<!-- SECTION:NOTES:END -->
