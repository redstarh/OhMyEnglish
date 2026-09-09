---
id: TASK-62
title: '신규 기능: 세션 총평 생성 (summarize_session) — 컬럼과 job type 은 이미 있다'
status: To Do
assignee: []
created_date: '2026-09-09 13:11'
labels: []
dependencies: []
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
learning_sessions.summary 컬럼과 analysis_jobs.job_type 의 summarize_session 값이 이미 있고 설계서가 「summary(세션 총평)는 summarize_session 과 함께 다음 슬라이스에서 채워진다」고 지정했다. 아직 구현이 없다. ⛔ 요구사항인데 원장에 태스크가 없었다 — 2026-09-09 사용자 질문에서 발견했다.

참고: realtime-meeting 이 같은 부류를 구현했고 그 방식이 배울 만하다 — 세션 종료 시 자동 생성 · 템플릿 지정 가능 · 구획 5개 · ⛔ 재생성 시 원자 교체(부분 실패로 반쯤 덮이지 않게) · 동시 재생성에 409. ⚠️ 우리는 회의록이 아니라 학습 총평이라 형식은 다르지만 「생성·재생성」 구조 문제는 같다. 근거는 docs/design/2026-09-09-realtime-meeting-fit-gap.md 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 summary 를 무엇으로 채울지 정한다 — 학습 총평의 구획을 요구사항에서 유도하고 발명하지 않는다
- [ ] #2 ⛔ summary 컬럼의 소유권을 지킨다 — 설계서 §2.3 이 그 컬럼을 다른 용도로 쓰려던 시도를 H-2 로 기각했다. 그 판단을 뒤집지 않는다
- [ ] #3 재생성이 원자적이게 만든다 — 부분 실패로 반쯤 덮이지 않고 동시 요청이 충돌로 드러난다
- [ ] #4 TASK-60 과 함께 토큰 사용량을 기록한다 — 총평 생성도 돈이 나가는 호출이다
<!-- AC:END -->
