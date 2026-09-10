---
id: TASK-1
title: '신규 요구사항: 일일 오류 패턴 분석 Summary Table'
status: Done
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-10 23:44'
labels:
  - caps-req
dependencies: []
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 1. 매일의 오류 패턴 분석 내용을 별도 Summary Table에 기록한다. 지금은 error_patterns/error_occurrences에 누적만 되고 '그날 무엇을 분석했는지'를 담는 일일 단위 표가 없다. 근거: docs/design/2026-09-06-captain-response-to-status-report.md 항목 1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 요구사항을 Given/When/Then으로 상세화해 docs/PRD.md 또는 요구사항 문서에 반영
- [x] #2 일일 경계를 사용자 타임존으로 구하는 규약을 명시(current_date 금지)
- [x] #3 표 스키마(컬럼·키·보존기간)를 설계서에 반영하고 마이그레이션 번호를 지정
- [x] #4 읽는 화면 또는 소비자를 함께 정의(reader 0곳 재발 금지)
- [x] #5 마이그레이션 012 를 data-first §5 절차(백업 · 적용 전후 행 수 대조)로 적용하고 표 생성과 기존 행 수 무변을 직접 조회로 확인함
- [x] #6 저장 · 조회 · 화면이 같은 커밋으로 나가고 게이트(pytest · ruff · ty · tsc · eslint)를 통과함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 접근 B 로 확정(사용자 결정) — 새 표 `daily_error_summary` + 학습자 화면. 절차 정본은
`docs/ops/data-first-design-convention.md` 이고 6단계를 전부 지났음. 설계·근거·기각한 A/C 의 대가는
`docs/design/2026-09-11-daily-error-summary-design.md` 가 소유하고 요구사항은 `docs/PRD.md` §13 임.

⛔ 뒤집은 결정 1건을 명시했음: `2026-08-25-learning-coach-agent-design.md` §6.1 이 롤업 표를 기각했음.
그 근거(「결과가 같다」)가 이 표에는 성립하지 않는 자리 둘을 코드로 확인했음 — `_UPSERT_PATTERN_SQL`
이 `target_form` 을 최신값으로 갱신함 · `_DELETE_OCCURRENCES_SQL` 이 재분석에서 발생 행을 교체함.

실측 증거 (전부 이 세션에서 직접 돌림):
- 마이그레이션 012 적용 — 백업 `/tmp/ohmyenglish-public-before-012-20260911-083237.sql`(CREATE TABLE 18
  · COPY public 18) · `schema_migrations` 9행→10행 · 표 18→19 · 기존 행 수 차이 0건.
- 게이트 — pytest **915 passed**(17.05s · 신규 15건) · `ruff check` 안·밖 통과 · `ruff format --check`
  통과 · `ty` 통과 · 프론트 `tsc`·`eslint` exit 0(파이프 없이).
- 판별력 — 구현에 변이 3개(날짜를 UTC 로 그음 · 예시를 최신 발화로 · 정렬 오름차순)를 넣어 각각
  테스트가 잡는 것을 확인했고 복원 뒤 다시 통과했음.
- 앱 경로 화면 확인 — 검증 전용 DB(`ohmyenglish_uicheck`)와 별 포트(:8012·:3001)로 띄워 공유 스택을
  건드리지 않았음. 워커가 **실물 Claude** 로 분석해 오류 2건·패턴 1종을 남기고 요약 1행이
  `2026-09-11` 로 기록됐음. 결과 화면에서 「오늘 무엇을 틀렸는지」 절과 「오늘 2번 나왔어요」를
  **직접 봤음**(스크린샷 `003-navigate.png`). 0건으로 바꾸면 절 제목이 DOM 에서 사라지는 것도
  대조했음(AC13-5). 걷은 뒤 공유 dev DB 행 수 무변경을 확인했음.
- 새 함정 3건을 `docs/ops/pitfalls.md` 에 남겼음 — `H-BB`(pg_dump 가 `-U ohmy` 로 막힘) ·
  `H-BC`(두 번째 스택 띄우기) · `H-BD`(CDP 에서 `getUserMedia` 정지).

⚠️ 남은 미결 2건은 설계서 §9 가 소유함 — 오류 기록 삭제 시 스냅샷 처리 · 히스토리 화면(`TASK-3`).
⚠️ 관측 1건: 세션 교정 카드와 오늘 요약이 **같은 패턴의 다른 문장**을 보임(세션은 최신 발화 ·
요약은 그날 가장 이른 발화). 의도한 규칙이고 화면에서 어색하지 않았음.
<!-- SECTION:NOTES:END -->
