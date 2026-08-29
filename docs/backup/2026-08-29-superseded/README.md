# 폐기 스냅샷 — 2026-08-29 이관

여기 있는 3개 파일은 **2026-08-25 상태 보고 세트**(Part 1·2·3)다. 서로 상대 링크로 묶여 있어
**함께** 옮겼다 — 한 개만 옮기면 나머지의 "← Part 1" 링크가 깨진다.

대체 문서: **`docs/status-report-2026-08-29.html`** (요구사항 · 스토리보드 플로우 · 아키텍처 · 미결정)

## 규약 (`../superseded/README.md`와 동일)

1. **파일 내용을 수정하지 않는다.** 스냅샷을 사후 편집하면 "그때 무엇을 보고 판정했는지"가 흐려진다.
2. 폐기 사실·대체 문서는 이 README에만 적는다.

## 보관 목록

| 파일 | 무엇 | 왜 폐기 |
|---|---|---|
| `status-report-2026-08-25.html` | Part 1 — 요구사항 · 스토리보드 (요구사항 **v1.0** 기준) | 요구사항이 **v1.1**로 개정되며 §10 발음 시범·§11 추천 루틴이 신설됐다. 머리말이 "Phase 1 개발·검증 완료"라고 적고 있으나 그 뒤 **완료 선언 기준 6항목**이 세워졌고(`docs/design/2026-08-25-first-slice-acceptance-criteria.md:147`) 아직 미충족이다 — 그대로 읽으면 상태를 오인한다 |
| `status-report-2026-08-25-architecture.html` | Part 2 — 시스템 구성 · 비동기 분석 큐 · 개발 상황 · 블로커 | 아키텍처의 뼈대(모델 분리·PostgreSQL 큐)는 유효하나 **발음 경로가 없다** — `pronunciation_attempts`(003~005)와 Nova tool 경로가 그 뒤에 들어왔다. "블로커와 다음 단계"는 전부 지나간 내용이다 |
| `status-report-2026-08-25-learning-agent.html` | Part 3 — 학습 코치 Agent 설계 시각화 (§11) | 같은 내용의 **설계 정본이 별도로 승격**됐다: `docs/design/2026-08-25-learning-coach-agent-design.md`. 이 HTML은 그 시점의 보기 좋은 사본이라 두 곳이 갈라질 위험이 있다 |

## ⚠️ 대체 문서가 **덮지 못하는** 내용

새 문서(`status-report-2026-08-29.html`)는 **현재 상태 한 장**이라 아래는 담지 않았다.
필요하면 여기가 아니라 **정본**을 봐라 — 이 스냅샷은 근거가 아니라 기록이다.

| 내용 | 정본은 어디 |
|---|---|
| §11 Agent의 3계층 입력 · 지시문 가변부 · 만성 약점 판정 · 수준 적응 | `docs/design/2026-08-25-learning-coach-agent-design.md` |
| 비동기 분석 큐를 PostgreSQL로 고른 근거(원자성 요구) | `docs/design/2026-08-24-first-vertical-slice-design.md` §5 |
| v1.0 요구사항 원문 | `docs/backup/v1.0/PRD.md` · `docs/backup/v1.0/requirements-summary.md` |
| 화면별 시안 | `docs/storyboard.html` (**현행 유지** — 폐기하지 않았다) |

## 같은 이름이 두 곳에 있다 (혼동 주의)

`../status-report-2026-08-25.html`과 `../status-report-2026-08-25-architecture.html`은
**더 이른 개정판**이다(2026-08-25). 이 폴더의 같은 이름 파일은 그것을 2026-08-26에 고친
**나중 개정판**이다. 둘 다 남긴 이유는 위 규약 1 — 스냅샷을 덮어쓰지 않는다.
