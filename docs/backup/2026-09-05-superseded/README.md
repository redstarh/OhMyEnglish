# 2026-09-05 이관 — 보고 스냅샷 4건

여기 있는 문서는 **전부 스냅샷이다.** 만들어진 시점의 판정을 담고 있고, 그 뒤 정본이 움직였다.
값이 현행과 다르면 **정본이 맞다.**

규약은 `docs/backup/superseded/README.md`가 소유한다 — 요지는 셋이다:
**① 파일 내용을 수정하지 않는다**(인용이 `file:line` 형태다) **② 폐기 사실은 이 README에만 적는다**
**③ 참조하는 쪽은 경로만 갱신한다.**

## 왜 지금 옮겼나

`docs/status-report-2026-09-05.html`(현행 보고)이 이 넷의 역할을 한 장으로 대체했다.
넷 다 `docs/` 최상위에 남아 있으면 다음 세션이 **어느 것이 현행인지** 파일명 날짜로 추측하게 된다 —
이 리포에서 실제로 겪은 실패 모드다(스냅샷을 정본으로 오인).

## 보관 목록

| 파일 | 만든 날 | 무엇 | 왜 폐기 | 대체 |
|---|---|---|---|---|
| `status-report-2026-08-29.html` | 2026-08-29 | 그 시점의 전체 상태 보고 | 슬라이스 1·2가 그 뒤에 관통했다. 요구사항 판정이 전부 낡았다 | `docs/status-report-2026-09-05.html` |
| `remaining-work-2026-08-31.html` | 2026-08-31 | 남은 작업 목록 | §10 Task 7·8 완료 · I절 전건 종결 · 슬라이스 1 완료 · 슬라이스 2 S2-1~S2-7로 대부분 소진됐다 | 현행 보고 + `TASKS.md`(상태의 정본) |
| `consistency-audit-2026-09-01.html` | 2026-09-01 | 5개 층 일관성 점검(D-1~D-6) | **D-5·D-6이 2026-09-03에 해소됐다**(근거는 `TASKS.md` C절에 남아 있다). 후속 점검이 `docs/consistency-audit-2026-09-04.md`다 | `docs/consistency-audit-2026-09-04.md` |
| `i1-status-2026-09-03.html` | 2026-09-03 | I-1(조각 발화 오탐) 완료 보고, 공유용 | **I절 미결 0건**이다. 실물 마이크 2회로 확증까지 끝났다 | `TASKS.md` I절 + `tests/harness/runs/2026-09-03-mic-2.md` |

## 경로만 갱신한 참조

| 참조하는 문서 | 무엇을 가리켰나 |
|---|---|
| `README.md` | `status-report-2026-08-29.html` (문서 색인) |
| `TASKS.md` | `consistency-audit-2026-09-01.html` (D-5·D-6 판정 근거) |
| `handoff/HANDOFF.md` | `consistency-audit-2026-09-01.html` · `i1-status-2026-09-03.html` (찾는 것 표) |

`remaining-work-2026-08-31.html`은 이관 전 참조가 **0건**이었다(`grep -rIl` 확인).

---

## 함께 제거한 것 — 2일 이상 지났고 참조가 0건이었다 (2026-09-05)

캡틴 지시로 보관소를 정리했다. **판정 기준은 둘을 함께 만족하는 것**이다:
**① mtime이 2일 이상 지났다 ② `grep -rIl`로 보관소 밖 참조가 0건이다.**
전부 git 추적 파일이라 바이트는 이력에 남는다(`git show <커밋>:<경로>`).

| 제거한 파일 | mtime | 참조 |
|---|---|:--:|
| `docs/backup/status-report-2026-08-25.html` | 2026-08-25 | 0 |
| `docs/backup/status-report-2026-08-25-architecture.html` | 2026-08-25 | 0 |
| `docs/backup/2026-08-29-superseded/status-report-2026-08-25.html` | 2026-08-26 | 0 |
| `docs/backup/2026-08-29-superseded/status-report-2026-08-25-architecture.html` | 2026-08-26 | 0 |
| `docs/backup/2026-08-29-superseded/status-report-2026-08-25-learning-agent.html` | 2026-08-25 | 0 |
| `handoff/backup/2026-08-30/HANDOFF-v1.1-implementation.md` | 2026-08-29 | 0 |

**제거하지 않은 것과 그 이유** — 오래됐지만 참조가 살아 있다:

| 남긴 것 | 누가 읽는가 |
|---|---|
| `docs/backup/v1.0/**` (PRD·요구사항 v1.0) | 승인된 설계서들이 v1.0 줄을 요구 근거로 인용한다 |
| `docs/backup/superseded/voice-architecture.md` | 설계서 3곳이 `:41`·`:42-43`·`:63`을 인용한다(그 README의 표) |
| `handoff/backup/2026-08-30/HANDOFF-test-harness.md` | `tests/harness/scenarios-P-pronunciation.md`가 §5 브라우저 주입 스크립트를 재사용한다 |
| `handoff/backup/2026-08-30/handoff-to-fix-session-round3.md` | `tests/harness/runs/2026-08-26-run-3.md`가 3차수 지시서로 인용한다 |
| `handoff/backup/2026-08-30/HANDOFF.md`·`HANDOFF-fix-session.md` | 현행 handoff가 "이전 판"으로 가리킨다 |
| 각 폴더의 `README.md` | **보관 규약과 이관 근거의 소유자다.** 지우면 "왜 폐기했나"가 사라진다 |

⚠️ `docs/backup/2026-08-29-superseded/README.md`는 **남겼지만 그것이 서술하는 3개 파일은 제거됐다.**
그 README는 이제 "무엇이 왜 폐기됐는지"의 기록으로만 쓴다 — 파일을 찾으려면 git 이력을 본다.
