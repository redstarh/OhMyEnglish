# OhMyEnglish

개인의 반복 오류를 기억해 말하기 중심으로 재훈련하는 영어 학습 Agent임. 목표는 일상 회화에서
출발해 IT 프로젝트 리딩과 프로젝트 보고 영어까지 넓히는 것임.

## 여기서 시작함

**`open docs/overview.html`** — 구현된 기능 · 화면 · 뒷단 파이프라인 · 실행 방법 · 문서 지도를
한 장에 담은 진입점임. 이 문서는 색인만 두고, 내용은 그쪽이 소유함.

```bash
open docs/overview.html          # 개요서 (진입점)
open docs/storyboard.html        # 화면 흐름 스토리보드
```

실행 절차와 포트 함정의 정본은 [`docs/ops/local-run.md`](docs/ops/local-run.md) 임.

## 프로젝트 구조

```text
OhMyEnglish/
├── app/                 # 애플리케이션 코드 (frontend · backend)
├── assets/              # 디자인·음성·콘텐츠 자산
├── backlog/             # 작업 원장 (Backlog.md — 태스크 하나 = 파일 하나)
├── db/migrations/       # DB 마이그레이션
├── docs/                # 제품·설계·운영 문서 (진입점은 overview.html)
├── handoff/             # 세션 인계 (지금 어디까지 왔나)
├── infra/               # 배포·관측성 설정
├── scripts/             # 개발·보고 보조 스크립트
└── tests/               # unit · integration · e2e · harness (회차 증거는 harness/runs)
```

## 정본 셋 — 값이 어긋나면 이쪽이 맞음

| 무엇 | 어디 |
|---|---|
| 무엇을 만들어야 하나 | [`docs/PRD.md`](docs/PRD.md) — 요구 정본 v1.6 (개정 이력은 §12) |
| 무엇이 남았나 · 무엇이 끝났나 | 작업 원장 — `backlog task list --plain` |
| 지금 어디까지 왔나 · 다음 한 걸음 | [`handoff/HANDOFF.md`](handoff/HANDOFF.md) (매 세션 새로 씀 · 이전 판은 `handoff/backup/`) |
| 실제로 밟아 본 함정 | [`docs/ops/pitfalls.md`](docs/ops/pitfalls.md) |
| 왜 이렇게 설계했나 | [`docs/design/`](docs/design/) — 결정과 근거의 정본 |

문서 층별 지도(요구 · 설계 · 운영 · 진행)는 **개요서 §7** 이 소유함 — 두 곳에 적으면 한쪽이
조용히 낡으므로 여기서 복제하지 않음.

## 폐기 문서

현행 정본이 아니지만 승인된 설계서가 줄 단위로 인용해 지우지 않음. 규약과 보관 목록은
[`docs/backup/superseded/README.md`](docs/backup/superseded/README.md) 가 소유하고, 이관한 판은
날짜별 폴더에 있음 — 가장 최근은
[`docs/backup/2026-09-20-superseded/`](docs/backup/2026-09-20-superseded/README.md) 임
(현황 보고 스냅샷 · 결정 대기 목록 · 어긋남 점검 · 진행 요약 넷).
