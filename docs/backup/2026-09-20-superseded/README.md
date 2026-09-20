# 2026-09-20 이관 — 스냅샷·조사 기록 4건

여기 있는 문서는 **현행 정본이 아니다.** 만들어진 시점의 판정과 조사를 담고 있고 그 뒤 정본이
움직였다. 값이 현행과 다르면 **정본이 맞다.**

규약은 `docs/backup/superseded/README.md` 가 소유한다 — 요지는 셋이다:
**① 파일 내용을 수정하지 않는다**(인용이 `file:line` 형태다) **② 폐기 사실은 이 README 에만 적는다**
**③ 참조하는 쪽은 경로만 갱신한다**(줄 번호는 그대로 유효하다).

## 왜 지금 옮겼나

사용자 지시(2026-09-20 · 「구현된 기능과 사용 방법을 개요서로 정리하고 기존 문서는 backup 으로
옮겨 정리해」)로 **최상위 `docs/` 를 진입점 한 장과 정본만 남기도록** 정리했다. 최상위에 스냅샷이
함께 있으면 다음 세션이 어느 것이 현행인지 **파일명 날짜로 추측**하게 된다 — 이 리포가 실제로 겪은
실패 모드이고 `docs/ops/status-report-convention.md` 가 같은 이유를 적어 두었다.

## 보관 목록

| 파일 | 만든 날 | 무엇 | 왜 폐기 | 대체 |
|---|---|---|---|---|
| `status-report-2026-09-06.html` | 2026-09-06 | 요구사항 47건 판정(완료 22 · 부분 16 · 미완료 9) · 미결정 7건 · 아키텍처 한 장 | 2주가 지나며 원장이 크게 움직였다 — 그 보고 뒤에 **태스크 295건이 새로 생겼다**(직접 셌음: `created_date` 가 2026-09-07 이후인 파일 295건 · 그 앞은 31건 · 2026-09-20 기준 `Done` 325). 판정 다수가 낡았다. 스냅샷은 사후 편집하지 않는 문서이므로 새 판으로 대체하는 것이 규약이다 | 기능과 사용법: `docs/overview.html` · 상태: 작업 원장(`backlog task list --plain`) · 요구사항별 판정: `docs/requirements-tracking.html` |
| `decisions-pending-2026-09-08.html` | 2026-09-08 | 그 시점의 사용자 결정 대기 목록(타이밍 2건 등) | 그 대기들이 결정됐다 — 결정의 정본은 `docs/ops/captain-instruction-register.md` 이고 그 대장이 그 뒤로도 계속 늘었다. 대기 목록을 최상위에 두면 이미 닫힌 질문을 다음 세션이 다시 연다 | `docs/ops/captain-instruction-register.md` · 지금 대기 중인 결정은 원장의 `Awaiting Decision` 상태가 답한다 |
| `consistency-audit-2026-09-04.md` | 2026-09-04 | 추천 학습 루틴 기능의 네 층(요구·설계·조각1·코드)이 어긋난 자리 점검 — 「조각 2」가 아직 없던 시점 | 그 「조각 2」(판단·적용)가 만들어졌고 계획 생성·복습 사다리·초점 적용이 종단으로 동작한다. 점검이 가리킨 미충족 요구 4건도 그 뒤 태스크로 처리됐다 | 설계: `docs/design/2026-08-25-learning-coach-agent-design.md` · 현재 동작: `docs/overview.html` §1·§3 |
| `2026-09-09-progress-summary.html` | 2026-09-09 | 그 시점의 진행 요약 스냅샷 | 같은 이유로 낡았다. ⚠️ **이 파일을 가리키는 곳이 리포 안에 0곳이었다**(이관 전 직접 셌음) — 이미 아무도 읽지 않는 상태였다 | `docs/overview.html` · 작업 원장 |

## 인용처 — 무엇을 갱신했고 무엇을 남겼나

**갱신한 것**: `README.md`(색인) · `docs/requirements-tracking.html`(살아 있는 추적표) ·
`docs/design/2026-09-04-learning-coach-slice2-plan.md` ·
`docs/design/2026-08-25-learning-coach-agent-design.md` — 경로만 바꿨다.

**남긴 것과 이유**:

| 인용하는 곳 | 왜 남겼나 |
|---|---|
| `backlog/tasks/task-40`·`task-44`·`task-48` 의 노트 | 원장 노트는 **그때의 기록**이다. 사후에 경로를 고치면 그 태스크가 무엇을 보고 판정했는지가 흐려진다 |
| `docs/design/2026-09-06-captain-response-to-status-report.md` · `docs/design/2026-09-06-gap-investigation.md` | 둘 다 그 보고를 **대상으로** 쓴 문서다 — 제목과 본문이 그 판을 가리키는 것이 정확하다 |
| `docs/design/2026-09-08-tasks-md-archive.md` | `TASKS.md` 원문을 옮긴 보관 문서다(스냅샷) |
| `docs/backup/2026-09-05-superseded/README.md` · `docs/backup/2026-09-06-superseded/README.md` | 보관소 안의 문서는 고치지 않는다(규약 ①). 두 폴더의 계보는 이 README 가 이어받는다 |

## ⚠️ 이 판을 계속 읽을 값이 남아 있는 자리

`status-report-2026-09-06.html` 의 **아키텍처 한 장**과 **미결정 7건의 서술**은 그 시점의 판단을
가장 짧게 담고 있다. 지금 아키텍처는 `docs/overview.html` §3 이 대체하지만, 「그때 무엇을 끊긴
자리로 봤는가」를 확인하려면 이 파일을 본다.

`consistency-audit-2026-09-04.md` 의 값은 **점검 방법**이다 — 네 층을 나란히 놓고 어긋난 곳을 세는
형태이고, 같은 점검을 다시 할 때 그 틀을 그대로 쓸 수 있다.
