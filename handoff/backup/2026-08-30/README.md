# 폐기 handoff — 2026-08-30 단일화

캡틴 지시로 **handoff를 하나로 합쳤다.** 이제 살아 있는 연속성 문서는 `handoff/HANDOFF.md`
하나이고, 갈래별 4개는 여기 보관한다.

## 규약

1. **파일 내용을 수정하지 않는다.** 스냅샷을 사후 편집하면 "그때 무엇을 보고 판정했는지"가
   흐려진다(`docs/backup/superseded/README.md`가 세운 규약과 같다).
2. 여기 있는 내용을 근거로 쓰지 마라 — **정본을 봐라.** 아래 표가 어디로 갔는지 알려준다.

## 무엇이 어디로 갔나

합치면서 **버린 것은 없다.** 세션이 바뀌어도 유효한 내용은 각 정본으로 옮겼고, 지나간
경과만 여기 남았다.

| 폐기 파일 | 담고 있던 것 | 지금 정본 |
|---|---|---|
| `HANDOFF.md` (310줄) | 로컬 실행 방법 · 포트 함정 · 게이트 · `.env` 우선순위 | **`docs/ops/local-run.md`** (신설, 이관) |
| | 캡틴 게이트 3건 | `TASKS.md` B-5·B-6·B-7 → **전건 결정됨**, 작업은 G-4·G-5·G-6 |
| | 4차수 범위·기록 규약 | `tests/harness/runs/ROUNDS.md` |
| | 발음 교정 4차수 실측(핵심 발견) | `docs/PRD.md` §10.1 · 설계서 §2(스파이크 결과) |
| | 구현 중 확정된 주요 판단 | `TASKS.md` B절 "이전에 결정된 것" · `docs/design/**` |
| `HANDOFF-v1.1-implementation.md` (121줄) | §10 진행 상태 · 다음 한 걸음 · 발음 서비스 계약 | **`handoff/HANDOFF.md`** (흡수) · 상태는 `TASKS.md` A절 |
| `HANDOFF-test-harness.md` (274줄) | 차수 상태 · 5차수 묶음 P/M/①②③④ · 차수 시작 절차 | `tests/harness/runs/ROUNDS.md`(차수·5차수 범위) · `tests/harness/README.md`(실행 전 필수·정리) |
| | O-1 관측(agent 전사문 선행 개행) · 음성 픽스처 상주 배치 | **`TASKS.md` E절**로 이관 |
| | `tests/harness/**` ruff 6건 | `TASKS.md` E절 · `ROUNDS.md` 5차수 행 |
| `HANDOFF-fix-session.md` (58줄) | 3차수 "고치는 쪽" 인계 — 그 왕복은 끝났다 | 경과는 `tests/harness/runs/2026-08-26-run-3.md`(차수 기록) |

## 뒤늦게 합류한 파일 — 2026-09-01

| 폐기 파일 | 무엇 | 왜 여기로 |
|---|---|---|
| `handoff-to-fix-session-round3.md` (12k) | 3차수에 **테스트 세션 → 수정 세션**으로 보낸 지시서 | 원래 `tests/harness/`에 있었다. 그 왕복은 3차수에 끝났고 O-1 등 잔여 관측은 **2026-08-30에 `TASKS.md` E절로 이관**됐는데 파일만 제자리에 남아 있었다. 캡틴 지시(2026-09-01 "이전 handoff와 최종본이 아닌 것은 backup 폴더로")로 옮겼다 |

**갱신한 참조 1건**: `tests/harness/runs/2026-08-26-run-3.md:5`의 상대 링크를 이 폴더로 돌렸다.
규약 3(경로만 갱신)에 따라 **문장은 건드리지 않았다.**
**갱신하지 않은 참조 1건**: 같은 폴더의 `HANDOFF-fix-session.md:5`가 옛 경로를 산문으로 적고 있다 —
그 파일은 스냅샷이라 사후 편집하지 않는다(규약 1). 이 절이 그 사실을 대신 기록한다.

## 참조 갱신 결과

옮기면서 깨진 경로를 고쳤다 — **경로만** 고치고 줄 번호는 건드리지 않았다.

| 고친 파일 | 어떻게 |
|---|---|
| `TASKS.md` A절·D절 | 연속성 포인터 → `handoff/HANDOFF.md` |
| `app/backend/app/audio_gateway/nova.py` | 폐기된 handoff §3.1 인용 → `TASKS.md` A-3 (같은 표를 갖고 있다) |
| `docs/design/2026-08-27-pronunciation-echo-{design,plan}.md` | 연속성 정본 → `handoff/HANDOFF.md`. 계획 `:1286`의 "handoff §6 트랜잭션 항목" → `TASKS.md` A-1 |
| `tests/harness/scenarios-P-pronunciation.md` | N5 주입 스크립트 참조 → 이 폴더의 `HANDOFF-test-harness.md` §5 (그 스크립트는 여기밖에 없다) |

**고치지 않은 것 2건** — 둘 다 **스냅샷**이라 규약 1을 적용했다:
`tests/harness/runs/2026-08-26-run-3.md`(차수 기록) · `handoff-to-fix-session-round3.md`(같은 폴더 — 2026-09-01 이동)
(3차수 인계 원본). 그때의 경로를 그대로 두는 것이 "그 시점의 기록"이다.
