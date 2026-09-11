# OhMyEnglish

개인의 반복 오류를 기억해 말하기 중심으로 재훈련하는 영어 학습 Agent입니다. 목표는 일상 회화에서 출발해 IT 프로젝트 리딩과 AWS Engage Manager 대상 프로젝트 보고까지 확장하는 것입니다.

## 시작하기

스토리보드는 별도 설치 없이 `open docs/storyboard.html`로 열 수 있습니다.

## 프로젝트 구조

```text
OhMyEnglish/
├── app/                 # application code (frontend, backend)
├── assets/              # 디자인, 음성, 콘텐츠 자산
├── db/migrations/       # DB 마이그레이션
├── docs/                # 제품·설계 문서와 스토리보드
├── infra/               # 배포·관측성 설정
├── scripts/             # 개발 보조 스크립트
└── tests/               # unit, integration, e2e 테스트
```

## 핵심 문서

- [PRD](docs/PRD.md) — **요구사항 정본 v1.4** (§13 v1.2 · §14 v1.3 · §15 v1.4 가 뒤에 붙었다)
- [**요구사항-구현 추적 체크리스트**](docs/requirements-tracking.html) — 요구사항 ID 별 판정과 근거.
  ⛔ **위 현황 보고와 성질이 다르다**: 그쪽은 고치지 않는 스냅샷이고 이쪽은 **갱신되는 살아 있는
  추적표**다. ⚠️ **갱신은 사람이 한다** — 구현이 판정을 바꾸는 커밋에서 함께 고친다(그 문서의 「갱신 규약」)
- [핵심 요구사항 요약](docs/requirements-summary.md) — 학습자 관점 요약, PRD와 같은 버전
- [데이터베이스 스키마](docs/database-schema.md)
- [Agent 시스템 프롬프트](docs/agent-system-prompt.md)
- [첫 4주 학습 플로우](docs/first-4-weeks.md)
- [Nova Sonic + Claude 목표 아키텍처](docs/nova-sonic-claude-architecture.md)
- [UI 스토리보드](docs/storyboard.html)
- [**현황 보고 (2026-09-06)**](docs/status-report-2026-09-06.html) — 요구사항 47건 판정(완료 22 · 부분 16 · 미완료 9) · 미결정 7건 · 아키텍처(단순) 한 장. **스냅샷이고 정본이 아니다** — 값이 다르면 **원장**(`backlog task list --plain`)이 맞다. 이전 판은 `docs/backup/2026-09-06-superseded/`
  - **형식 규약**: [docs/ops/status-report-convention.md](docs/ops/status-report-convention.md) — 다음 보고는 **이 형식으로만** 쓴다(절 순서 · 판정 어휘 4개 · 근거 규칙 · 색 검증)
  - **템플릿**: [docs/templates/status-report-template.html](docs/templates/status-report-template.html) — 복사해서 `{{…}}`를 채운다
  - 이전 판(2026-08-29 등 4건)은 [`docs/backup/2026-09-05-superseded/`](docs/backup/2026-09-05-superseded/README.md)
- Handoff — ⛔ **`handoff/HANDOFF.md` 는 없다.** 갈래별로 갈렸다:
  [`handoff/HANDOFF-test-harness.md`](handoff/HANDOFF-test-harness.md) ·
  [`handoff/HANDOFF-pronunciation.md`](handoff/HANDOFF-pronunciation.md) ·
  [`handoff/HANDOFF-implementation.md`](handoff/HANDOFF-implementation.md) ·
  [`handoff/HANDOFF-audit.md`](handoff/HANDOFF-audit.md). 이전 판은 `handoff/archive/`.
  ⚠️ **자기 갈래만 읽는다** — 인계 원칙은 `~/.claude/rules/session-handoff.md` 가 소유한다

### 폐기 문서

현행 정본이 아니지만 승인된 설계서가 줄 단위로 인용해 지우지 않는다 —
규약과 보관 목록은 [docs/backup/superseded/README.md](docs/backup/superseded/README.md).

## 관련 문서 지도

> `TASKS.md`의 「관련 문서 지도」절을 원장 마이그레이션(`TASK-28`)으로 이관했다.

| 무엇을 알고 싶은가 | 어디 |
|---|---|
| 무엇이 남았나 / 무엇을 놓쳤나 | `backlog board` · `backlog task list --plain` (원장은 Backlog.md — `~/.claude/rules/task-management.md`) |
| 지금 어디까지 왔나 / 다음 한 걸음 | `handoff/HANDOFF-*.md` (짧게 유지) |
| 실측된 함정 (반복하지 말 것) | `docs/ops/pitfalls.md` |
| 왜 이렇게 설계했나 | `docs/design/**` — 결정과 근거의 정본 |
| 끝난 일의 기록 · `TASKS.md`의 내용은 어디 갔나 | `TASKS.md`에는 **절 제목 + 포인터만** 남았다(인용이 끊기지 않게) → 원문은 `docs/design/2026-09-08-tasks-md-archive.md` |
| 무엇을 만들어야 하나 | `docs/PRD.md` (v1.1) · `docs/requirements-summary.md` |
| 어떻게 돌리나 | `handoff/HANDOFF.md` §로컬 실행 방법 |
