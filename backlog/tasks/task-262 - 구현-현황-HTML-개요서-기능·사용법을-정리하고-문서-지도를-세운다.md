---
id: TASK-262
title: '구현 현황 HTML 개요서: 기능·사용법을 정리하고 문서 지도를 세운다'
status: Done
assignee: []
created_date: '2026-09-20 00:36'
updated_date: '2026-09-20 00:53'
labels: []
dependencies: []
ordinal: 326000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시(2026-09-20). ⑴ 지금까지 «완료된» 기준으로 구현된 기능과 사용 방법을 HTML 한 장으로 요약함 ⑵ 그 문서와 거기서 가리키는 문서만으로 전체를 파악할 수 있게 관련 문서를 최신화함 ⑶ 낡아 대체된 문서는 backup 으로 옮겨 정리함. ⛔ 옮기기 전에 인용을 세어야 함 — 코드 주석과 다른 설계서가 경로로 그 문서들을 가리키고 있어 조용히 끊어짐.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 HTML 개요서가 구현된 기능과 실행 방법을 담고 링크가 전건 실재함(기계 검사)
- [x] #2 문서 지도가 층별로(요구·설계·운영·회차) 정리되고 각 문서의 역할이 한 줄로 적힘
- [x] #3 대체된 문서만 backup 으로 옮기고 그것을 가리키던 인용을 함께 고침 — 옮기기 전 인용 수를 셈
- [x] #4 README 가 개요서를 가리켜 진입점이 하나로 모임
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
처리 결과 (2026-09-20 · 이 세션이 직접 돌렸음). ⑴ 개요서 docs/overview.html 신설 — 기능 요약 16행 · 화면 여섯과 진입 여덟 · 파이프라인 7단계와 job 다섯 · 데이터 묶음과 시각 규약 · 실행 순서와 환경 변수 · 게이트 다섯과 회차 도구 여섯 · 문서 지도 4층 · 아직 없는 것 다섯. 표 14개 · 링크 57개. AC#1 기계 검사: scripts/check_doc_links.py 신설 — 링크·경로 표기 86건 전건 실재. ⛔ 판별력을 직접 쟀음(일부러 없는 경로를 넣은 사본에서 검사가 실패하는 것을 확인). HTML 태그 짝과 표 구조(머리행·본문행)·차례 앵커도 렌더된 DOM 으로 확인했고 브라우저로 직접 열어 눈으로 봤음. ⚠️ 짧은 모듈 이름(plan.py 같은 지시어)은 검사 밖에 둠 — 넣으면 소음이 되어 진짜 낡은 경로를 가림. ⑵ AC#3 이관 4건: status-report-2026-09-06.html · decisions-pending-2026-09-08.html · consistency-audit-2026-09-04.md · ops/2026-09-09-progress-summary.html → docs/backup/2026-09-20-superseded/. 옮기기 전에 인용을 세었고(각 0~6곳) 살아 있는 문서 넷의 경로만 갱신했음(README · requirements-tracking.html · 설계서 둘). ⛔ 설계서 둘은 «경로 치환뿐»임을 기계로 증명했음(git show 와 치환 결과를 대조). 원장 노트와 그 보고를 대상으로 쓴 문서 둘, 보관소 안 README 는 규약대로 남겼음. ⑶ AC#4 README 를 진입점으로 줄였음 — 문서 지도는 개요서 §7 이 소유하고 README 는 복제하지 않음. 낡은 서술 셋을 고쳤음(PRD v1.4→v1.6 · handoff 가 없다는 서술 · 옮긴 현황 보고). ⑷ 추적표에 「범위 상태」 절을 더했음 — 그 표가 v1.4 까지만 덮는다는 사실과 v1.5·v1.6 이 요구 «철회·한정» 개정이라 판정을 뒤집지 않는다는 것을 적었음. 검사가 그 표의 낡은 경로 하나를 실제로 잡았음.
<!-- SECTION:NOTES:END -->
