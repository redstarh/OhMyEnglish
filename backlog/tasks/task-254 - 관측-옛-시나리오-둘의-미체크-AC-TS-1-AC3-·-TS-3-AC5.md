---
id: TASK-254
title: '관측: 옛 시나리오 둘의 미체크 AC (TS-1 AC#3 · TS-3 AC#5)'
status: Done
assignee: []
created_date: '2026-09-19 14:22'
updated_date: '2026-09-19 14:47'
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
- [x] #1 TS-1 AC#3 이 관측돼 그 시나리오가 닫힘
- [x] #2 TS-3 AC#5 가 관측돼 그 시나리오가 닫힘
- [x] #3 실패가 있으면 결함으로 등록됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 (2026-09-19 · 회차 B10). TS-1 AC#3 · TS-3 AC#5 둘 다 관측돼 두 시나리오가 Done 임(TS-3 은 AC#6 까지 여섯 전부). 결함 등록 0건. 증거를 직접 열어 확인했음 — TS-1 은 팔 둘이 종료 «원인» 을 갈랐음: 팔 A 는 end_session 을 0.6초에 보내 스크립트 3건 가운데 1건만 소진된 상태(adapter_exhausted=false · remaining=2)에서 session_ended 를 받았고, 팔 B 는 소진(exhausted=true · remaining=0)으로 받았음. 그 대조가 없으면 「어댑터가 스스로 닫혔다」와 「내 명령이 닫았다」를 가를 수 없었음(앞 회차가 실제로 그 함정에 걸렸음). TS-3 은 화면 문구가 「그 학습 결과를 찾을 수 없습니다.」 로 한국어이고 상태 코드·API 낱말 노출 0건임.
<!-- SECTION:NOTES:END -->
