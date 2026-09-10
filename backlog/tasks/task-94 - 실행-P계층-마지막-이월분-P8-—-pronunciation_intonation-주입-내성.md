---
id: TASK-94
title: '실행: P계층 마지막 이월분 P8 — pronunciation_intonation 주입 내성'
status: To Do
assignee: []
created_date: '2026-09-10 17:27'
updated_date: '2026-09-10 17:35'
labels: []
dependencies: []
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
4차수부터 미실행으로 남은 유일한 P 항목이다. scenarios-P §4 의 P8 단정: inject_errors.py 로 pronunciation_intonation 카테고리를 «직접» 주입해 저장·조회·렌더가 깨지지 않는지 본다. 저장 경로 자체는 카테고리를 차별하지 않아야 한다. ⛔ 실물 Nova 호출이 필요하지 않다 — 주입이므로 비용이 낮고 값어치가 높다. 지금 이 카테고리는 error_patterns CHECK 에 허용돼 있고(직접 확인) pronunciation_an_as_a 행이 실재하지만, 그 행은 pronunciation_attempts 에서 frequency 를 세므로 error_occurrences 가 0행이다(H-AX) — 주입 경로가 그 비대칭을 어떻게 다루는지가 이 시나리오의 핵심이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 inject_errors.py 로 pronunciation_intonation 패턴을 주입하고 error_patterns·error_occurrences 에 무엇이 생기는지 기록한다 — frequency 를 어느 writer 가 세는지 함께 확인한다
- [ ] #2 결과 API 와 결과 화면이 그 카테고리를 깨지지 않고 렌더하는지 확인한다 — 스크린샷을 직접 열어 본다
- [ ] #3 복습 과제가 생기는지 본다. 생기면 shadowing 매핑 의도(scenarios-E L3)와 실제가 갈리는지 적는다
- [ ] #4 회차 전에 browser_leg.md §8-0 절차대로 스냅샷을 뜨고 teardown 후 어긋난 행 0 을 확인한다 — 주입도 DB 쓰기다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 착수 전 알아 둘 것 (2026-09-11) — 이 태스크 파일이 외부에서 한 번 변경됐다가 되돌려졌음.

다른 세션(ohmyenglish-7f)이 자기 새 태스크 ID 를 짐작해 -s "In Progress" 를 돌렸는데 실제 자기 것은 TASK-95 였고 이 태스크 상태가 To Do → In Progress 로 바뀌었음. 그 세션이 스스로 알리고 git diff 로 되돌렸음.

팀리드가 커밋 5e0772f 판과 git diff 로 직접 대조했음 — status To Do · AC 4건 전부 미체크 · 설명·AC 문면 차이 0 임. 즉 원래대로임.

⚠️ 유일한 잔여는 updated_date 줄이 «추가»된 것임(원래는 태스크 생성 후 수정이 없어 그 키가 아예 없었음). 그 세션은 「원래 값 17:32 로 복구 불가」로 적었으나 정확히는 «그 줄을 지우면 커밋 판과 글자 그대로 같아짐» 이므로 복구 가능함. ⛔ 지우지 않았음 — 도구가 다음 편집에 다시 넣을 값이고 판정에 쓰이지 않음(상태·AC·의존이 정본임). 즉 「복구 가능하나 무의미해서 두었다」임.

⛔ 이 사고에서 얻은 절차: 남의 세션이 내 태스크를 건드렸는지 감지하는 수단은 git diff <내 마지막 커밋> -- <태스크 파일> 임. 그 diff 가 비면 안전하고, 그 대조가 「알려 줬으니 믿는다」보다 강함. 같은 리포에 여러 세션이 태스크를 만들면 번호가 사이에 끼어들므로 backlog task create 의 반환 ID 를 읽지 않고 짐작하지 않음.
<!-- SECTION:NOTES:END -->
