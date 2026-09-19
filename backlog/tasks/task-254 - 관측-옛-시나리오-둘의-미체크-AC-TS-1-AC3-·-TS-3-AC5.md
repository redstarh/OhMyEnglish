---
id: TASK-254
title: '관측: 옛 시나리오 둘의 미체크 AC (TS-1 AC#3 · TS-3 AC#5)'
status: In Progress
assignee: []
created_date: '2026-09-19 14:22'
updated_date: '2026-09-19 14:22'
labels: []
dependencies: []
ordinal: 318000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
이번 통합테스트가 세운 영역 18개는 전부 닫혔으나 2026-09-09 회차가 남긴 시나리오 둘이 열려 있음. 둘 다 비용 0(스텁·브라우저)으로 관측 가능함. TS-1 AC#3 — end_session 뒤 session_ended 가 도착하고 session_id 가 실려 옴. TS-3 AC#5 — 사용자가 학습자 언어의 안내를 보고 HTTP 상태 코드·API 라는 낱말이 화면에 노출되지 않음(D1). ⚠️ TS-3 AC#5 는 배치 B1 이 TS-22 AC#2 를 재면서 같은 성질을 이미 관측했음(화면이 「찾을 수 없습니다」 대 「열 수 없습니다」로 갈리고 상태 코드·영어 예외 누출 0건) — 다만 «다른 시나리오의 증거»이므로 이 AC 로 옮겨 쓰지 않고 다시 잼.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TS-1 AC#3 이 관측돼 그 시나리오가 닫힘
- [ ] #2 TS-3 AC#5 가 관측돼 그 시나리오가 닫힘
- [ ] #3 실패가 있으면 결함으로 등록됨
<!-- AC:END -->
