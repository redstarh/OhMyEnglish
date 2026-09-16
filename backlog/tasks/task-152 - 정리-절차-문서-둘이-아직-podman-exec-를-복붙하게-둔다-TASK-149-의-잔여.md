---
id: TASK-152
title: '정리: 절차 문서 둘이 아직 podman exec 를 복붙하게 둔다 (TASK-149 의 잔여)'
status: To Do
assignee: []
created_date: '2026-09-16 23:21'
labels: []
dependencies: []
ordinal: 213000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-149 가 개발 도구 셋(dev_db.sh · smoke_analysis.py · tests/harness/README.md)에서 죽은 podman 폴백을 지웠으나, 절차 문서 둘이 아직 그 명령을 들고 있다. ① docs/ops/2026-08-26-test-harness.html — podman 참조 10건이고 하네스 절차 정본이라 사람이 여기서 복붙한다(:5433 접속정보 · podman exec psql · podman ps 프리플라이트 · psql 이 없다는 낡은 서술). ② docs/ops/shared-database-guide.md — En-Coach 전달용 온보딩 문서인데 2.1 이 dev DB 를 podman 컨테이너로 소개하고 4.3 재현 SQL 과 6 확인 명령이 전부 podman exec 다. ⇒ 남의 앱 담당자가 이 문서를 따라가면 존재하지 않는 컨테이너로 간다. 참고: tests/harness/browser_leg.md:5 가 이 두 문서를 가리켜 위임 금지 근거로 삼으므로 고친 뒤 그 줄의 문면도 맞춘다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docs/ops/2026-08-26-test-harness.html 의 podman 참조가 homebrew :5432 경로로 바뀌었다 (grep 으로 0건 확인)
- [ ] #2 docs/ops/shared-database-guide.md 2.1 · 4.3 · 6 이 psql 절대경로 또는 psql_cli.py 로 바뀌었다
- [ ] #3 tests/harness/browser_leg.md:5 의 위임 금지 근거가 낡지 않게 정정됐다
<!-- AC:END -->
