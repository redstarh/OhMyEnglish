---
id: TASK-149
title: '갈라냄: 죽은 podman 경로를 가리키는 개발 도구 셋 (거짓 신호)'
status: To Do
assignee: []
created_date: '2026-09-16 15:36'
labels: []
dependencies: []
ordinal: 210000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R5(도구 낡음) 리뷰 발견. dev DB 는 2026-08-31 부로 homebrew postgresql@17(:5432)로 이관됐는데 ① scripts/dev_db.sh 가 podman 컨테이너 ohmy-pg·:5433·postgres:16-alpine 을 그대로 갖고 있고(이 호스트에서 podman 소켓 연결 자체가 안 됨) ② scripts/smoke_analysis.py 의 실패 안내가 그 죽은 폴백으로 사람을 보내고 ③ tests/harness/README.md 의 「실행 전 필수」 명령 블록이 podman exec 를 복붙하게 둔다(같은 파일 주석은 스스로 낡았다고 적음). ⇒ 최악은 다른 호스트에서 podman 이 붙어 앱과 무관한 빈 DB 에 마이그레이션을 적용하고 그것을 「스모크 통과」로 보고하는 것이다. ⛔ 정리 회차에서 갈라낸 이유: 스크립트의 동작을 바꾸는 결정(폴백을 유지할지 지울지)이 필요하다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 podman 폴백을 지울지 homebrew 로 갈아탈지 사용자가 정한다
<!-- AC:END -->
