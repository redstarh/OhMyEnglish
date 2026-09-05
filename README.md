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

- [PRD](docs/PRD.md) — **요구사항 정본 v1.1**
- [핵심 요구사항 요약](docs/requirements-summary.md) — 학습자 관점 요약, PRD와 같은 버전
- [데이터베이스 스키마](docs/database-schema.md)
- [Agent 시스템 프롬프트](docs/agent-system-prompt.md)
- [첫 4주 학습 플로우](docs/first-4-weeks.md)
- [Nova Sonic + Claude 목표 아키텍처](docs/nova-sonic-claude-architecture.md)
- [UI 스토리보드](docs/storyboard.html)
- [**현황 보고 (2026-09-06)**](docs/status-report-2026-09-06.html) — 요구사항 47건 판정(완료 22 · 부분 16 · 미완료 9) · 미결정 7건 · 아키텍처(단순) 한 장. **스냅샷이고 정본이 아니다** — 값이 다르면 `TASKS.md`가 맞다. 이전 판은 `docs/backup/2026-09-06-superseded/`
  - **형식 규약**: [docs/ops/status-report-convention.md](docs/ops/status-report-convention.md) — 다음 보고는 **이 형식으로만** 쓴다(절 순서 · 판정 어휘 4개 · 근거 규칙 · 색 검증)
  - **템플릿**: [docs/templates/status-report-template.html](docs/templates/status-report-template.html) — 복사해서 `{{…}}`를 채운다
  - 이전 판(2026-08-29 등 4건)은 [`docs/backup/2026-09-05-superseded/`](docs/backup/2026-09-05-superseded/README.md)
- [Handoff](handoff/HANDOFF.md)

### 폐기 문서

현행 정본이 아니지만 승인된 설계서가 줄 단위로 인용해 지우지 않는다 —
규약과 보관 목록은 [docs/backup/superseded/README.md](docs/backup/superseded/README.md).
