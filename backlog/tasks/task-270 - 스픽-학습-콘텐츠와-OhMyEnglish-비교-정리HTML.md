---
id: TASK-270
title: 스픽 학습 콘텐츠와 OhMyEnglish 비교 정리(HTML)
status: Done
assignee: []
created_date: '2026-09-26 02:31'
updated_date: '2026-09-26 02:56'
labels: []
dependencies: []
ordinal: 334000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-268 조사 문서를 OhMyEnglish 의 실제 학습 콘텐츠와 비교해 HTML 로 정리함
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 비교 문서 MD·HTML 이 docs/research 에 있음
- [x] #2 OhMyEnglish 쪽 주장마다 코드·문서 근거 경로가 있음
- [x] #3 내가 HTML 을 직접 열어 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
산출물 작성 완료함(docs/research/2026-09-26-speak-vs-ohmyenglish.md 247줄, .html 305줄). 근거 상태(구현됨/설계서만/부재) 표기와 파일 경로+기호 인용 방식으로 8축 비교와 격차 목록을 담음. 브라우저 도구(mcp__plugin_superpowers-chrome_chrome__use_browser)로 HTML 을 직접 열어 렌더링·본문 순서·인코딩을 확인함(스크린샷·eval·markdown 추출 대조) — 다만 AC#3 은 «내가»의 최종 확인 주체가 이 작업을 지시한 사용자일 수 있어 체크를 비워 둠. 지시에 따라 커밋은 하지 않음 — 두 파일이 커밋되지 않은 채로 남아 있음.

사용자 지시(2026-09-26)로 스픽 회사 일반 내용을 빼고 학습 관점만 남김 · 3-1 의 계정·로그인 항목도 학습 밖이라 뺌. 내가 코드와 대조한 수치: STAGE_DAYS (1,3,7) · WINDOW 10/NEW_PER_WINDOW 3 · CefrLevel 6단계 · SEED_SCENARIOS 30건(9·9·6·3·3). 헤드리스 Chrome 렌더링으로 표·배지를 직접 확인함.
<!-- SECTION:NOTES:END -->
