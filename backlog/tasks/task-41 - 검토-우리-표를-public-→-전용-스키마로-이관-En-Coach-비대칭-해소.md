---
id: TASK-41
title: '검토: 우리 표를 public → 전용 스키마로 이관 (En-Coach 비대칭 해소)'
status: To Do
assignee: []
created_date: '2026-09-07 17:51'
updated_date: '2026-09-16 23:01'
labels: []
dependencies: []
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. En-Coach는 전용 스키마(en_coach)를 쓰는데 우리 표는 public에 있어 비대칭이다 — 남의 search_path 폴백이 우리 표로 떨어질 수 있다. 우리 SQL이 전부 한정자 없이 쓰여 있어 범위가 커서 미뤄 왔다. 근거: docs/ops/shared-database-naming-rules.md §5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 전용 스키마 이관의 영향 범위(한정자 없는 SQL 전수)를 조사한다
- [ ] #2 이관 여부와 시점을 캡틴 결정으로 확정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## AC#2 답 (2026-09-17 · 결정 122)

사용자가 「모든 구현이 끝났다고 봐」로 정했음 — 결정 31 이 「모든 구현이 끝난 뒤」로 미뤄 둔 자리가
이것으로 열렸음. 착수하지 않았으므로 상태를 To Do 로 되돌림.

⚠️ 착수 전에 확인할 것 셋(팀리드 메모): ⑴ 이 DB 인스턴스는 StockAgent 와 공유하므로 인스턴스 단위
조작을 하지 않음 ⑵ search_path 를 바꾸면 하네스 드라이버와 scripts/ 가 함께 영향을 받음 —
그 목록을 먼저 뽑음 ⑶ 마이그레이션 번호는 실측 최대(025) 다음이고 002·008 은 영구 결번임.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:56
---
캡틴 결정 31(2026-09-08): 「En-Coach DB 사용중이니, 모든 작업이 마무리되고 나중에 이관할지 결정해」 — 010·011 을 public 에 그대로 추가한다. ⚠️ 받아들이는 비용: 표를 더할수록 이관 범위가 커지고 우리 SQL 이 전부 한정자 없이 쓰여 있어 그 비용은 선형이 아니다. 모든 구현이 끝난 뒤 다시 올린다.
---
<!-- COMMENTS:END -->
