---
id: TASK-161
title: '기획안·설계서: 영상 학습 갈래 설계를 확정하고 구현 태스크로 분해한다'
status: Done
assignee: []
created_date: '2026-09-17 16:54'
updated_date: '2026-09-17 17:18'
labels: []
dependencies:
  - TASK-160
ordinal: 222000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토리보드를 근거로 설계서를 쓰고, 그 설계서의 항목을 구현 태스크로 원장에 전부 등록한다. PRD 5 의 비범위 경계를 옮기는 결정을 문서에 명시한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 설계서를 docs/design/ 에 썼다 (데이터 모델·API·화면·오류 처리·테스트)
- [x] #2 PRD 범위 확장 결정을 근거와 함께 기록했다
- [x] #3 구현 태스크를 원장에 전부 등록했다
- [x] #4 단순 대안 1개를 함께 검토해 적었다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 산출물

- `docs/design/2026-09-18-video-learning-storyboard.md` — 228줄 (`TASK-160`)
- `docs/design/2026-09-18-video-learning-design.md` — **434줄** (이 태스크)
- `docs/ops/captain-instruction-register.md` — 2026-09-18 지시 절 · **결정 125·126** 등재

## ⚠️ AC#2 의 문구를 이행 결과가 정정함

AC#2 는 「PRD 범위 확장 결정을 근거와 함께 기록했다」로 적혀 있었으나 **조사가 그 전제를 뒤집었음.**
`PRD.md` §10 이 *"외부 영상은 메타데이터·링크만 보관하고 사용자가 선택한 콘텐츠만 과제로 사용한다"* 로
이 갈래를 **이미 요구**하므로 범위를 넓히는 결정이 아님.
⇒ 기록한 것은 **「확장이 아니다」라는 판정과 그 근거**이고 그것이 결정 125 임. AC 의 취지(범위 판정을
근거와 함께 남기는 것)는 이행됨.

## 설계가 확정한 것 — 스토리보드의 질문 다섯에 대한 답

| 질문 | 답 | 되돌리는 비용 |
|---|---|---|
| 1 영상을 지울 때 문장도 지우나 | **문장을 남김** (`on delete set null`) | cascade 로 바꾸는 마이그레이션 한 줄. 반대 방향은 불가하므로 보수적인 쪽을 골랐음 |
| 2 30일 보관 제한 | `metadata_fetched_at` + 서버가 `stale` 계산 · 갱신은 `POST` 가 겸함 | 엔드포인트를 늘리지 않았음 |
| 3 `level` | 서버가 `users.current_level` 을 읽어 채움 | 화면에 선택지를 더하면 됨 |
| 4 구간 정밀도 | 소수 둘째 자리 · **서버가** 반올림 | 선례(시드 행)를 따랐음 |
| 5 `ADDITIONAL_LEARNING` | 원소에 `href?` 를 더함 · 렌더 조건을 좁힘 | `업무 역할극` 빈 칸이 휩쓸리지 않음 |

## ⛔ 심플하게 유지한 결과 — 새로 쓰는 코드가 적음

| 안 만드는 것 | 근거 |
|---|---|
| 새 세션 모드 | 지시문이 달라지지 않음 — 판정 기준의 선례가 `2026-09-12-additional-learning-entry-design.md` §2 임 |
| 백엔드 HTTP 클라이언트 의존성 | oEmbed 가 CORS 를 허용해 브라우저가 직접 부름(실측) |
| 새 job 종류 | oEmbed 는 1회·짧은 호출이라 동기로 충분함 |
| `thumbnail_url` 컬럼 | videoId 에서 조립함(실측 200 · 없는 id 404) |
| `user_id` 컬럼 | `shadowing_items`·`learning_scenarios` 가 둘 다 없음 |
| 검색 · 낱말 사전 · 쓰기 퀴즈 · 이중 자막 · 난이도 계산 · 재생 속도 UI · 재생목록 · 딕테이션 채점 | 스토리보드 §6 이 각각의 근거를 가짐 |

## 단순 대안 검토 (AC#4)

**「새 표를 만들지 않고 `shadowing_items` 만 쓴다」** 를 검토하고 기각했음(설계서 §9).
⛔ 기각의 결정적 이유는 **문장을 담기 전에는 영상이 목록에 없는 것**임 — 사용자 지시가 「영상을
수집해서」이므로 영상 자체가 자산이고, 담아 두고 나중에 공부하는 동작이 이 갈래의 핵심임.
⇒ 다만 그 대안의 교훈을 채택해 **영상 표의 컬럼을 최소로** 뒀음(썸네일 조립 · `user_id` 없음).

## 구현 태스크 여덟 (AC#3)

`TASK-162`(027 마이그레이션) · `TASK-163`(URL 파싱 · 독립) · `TASK-164`(서비스) ·
`TASK-165`(API) · `TASK-166`(쉐도잉 배선) · `TASK-167`(프론트 부품) · `TASK-168`(프론트 화면) ·
`TASK-169`(simplify + Test Agent 통합 테스트).

의존을 걸었고 `--ready` 가 `TASK-162`·`TASK-163` 둘을 착수 가능으로 계산함(직접 확인).
<!-- SECTION:NOTES:END -->
