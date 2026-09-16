---
id: TASK-149
title: '갈라냄: 죽은 podman 경로를 가리키는 개발 도구 셋 (거짓 신호)'
status: Done
assignee: []
created_date: '2026-09-16 15:36'
updated_date: '2026-09-16 23:22'
labels: []
dependencies: []
ordinal: 210000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R5(도구 낡음) 리뷰 발견. dev DB 는 2026-08-31 부로 homebrew postgresql@17(:5432)로 이관됐는데 ① scripts/dev_db.sh 가 podman 컨테이너 ohmy-pg·:5433·postgres:16-alpine 을 그대로 갖고 있고(이 호스트에서 podman 소켓 연결 자체가 안 됨) ② scripts/smoke_analysis.py 의 실패 안내가 그 죽은 폴백으로 사람을 보내고 ③ tests/harness/README.md 의 「실행 전 필수」 명령 블록이 podman exec 를 복붙하게 둔다(같은 파일 주석은 스스로 낡았다고 적음). ⇒ 최악은 다른 호스트에서 podman 이 붙어 앱과 무관한 빈 DB 에 마이그레이션을 적용하고 그것을 「스모크 통과」로 보고하는 것이다. ⛔ 정리 회차에서 갈라낸 이유: 스크립트의 동작을 바꾸는 결정(폴백을 유지할지 지울지)이 필요하다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 podman 폴백을 지울지 homebrew 로 갈아탈지 사용자가 정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 처리 (2026-09-17 · 결정 123)

사용자가 판단을 팀리드에게 위임했고 「폴백을 지운다」로 정했음. 등재와 근거는
`docs/ops/captain-instruction-register.md` 의 결정 123 이 가짐.

**계측으로 확인한 전제 셋**:
- podman — 소켓 거부(`dial tcp 127.0.0.1:56914: connect: connection refused`) · 가상머신 LAST UP 2개월 전
- `:5432` — 살아 있음 · `server_version` 17.9 (Homebrew) · `schema_migrations` 23건
- `:5433` — LISTEN 0건

**고친 자리**:
1. `scripts/dev_db.sh` — homebrew `postgresql@17` 기준으로 다시 씀. `start`·`status` 만 두고
   `stop`·`reset` 은 `exit 2` 로 거부함(이 서버를 StockAgent·En-Coach 와 공유하므로 인스턴스 단위
   조작이 남의 앱을 멈춤). `status` 가 psql 경로·DSN·brew 상태·`server_version`·마이그레이션 건수를 냄.
2. `scripts/smoke_analysis.py` — 실패 안내의 podman 폴백 문장을 지우고 `dev_db.sh` 로 보냄.
3. `tests/harness/README.md` — `podman exec` 두 블록을 `psql_cli.py` 로 바꿈. 낡은 baseline SQL 은
   옮겨 적지 않고 `browser_leg.md` §8-0 을 가리킴(그 사본이 `next_review_at`·`mastery_score` 를
   빠뜨렸던 자리임).
4. `docs/ops/local-run.md` — 포트 표의 `:5433` 행과 폴백 절차 블록을 내림. 같은 블록의 낡은 기대값
   (`UTC|2`)도 함께 고침 — 지금 `learning_sessions` 는 그보다 많음.
5. 주석 문면 넷 — `scripts/db_utils.py` · `tests/harness/psql_cli.py` · `ws_session.py` ·
   `inject_errors.py` 가 「폴백으로 남아 있다」를 단정하고 있었음.

**직접 돌린 증거**:
- `dev_db.sh` 네 경로 — `status` exit 0(17.9 · 23건) · `start` exit 0(이미 떠 있음) ·
  `stop`·`reset` exit 2 · 인자 없음 exit 1
- README 에 새로 적은 `psql_cli` 명령을 무해한 변형(`select gen_random_uuid()`)으로 실행 —
  36바이트 · 개행 오염 0(`od -c` 로 확인)
- 게이트 — `pytest` 1278 passed · `ruff` exit 0 · `ruff format` exit 0 · `ty` exit 0

**범위 밖으로 갈라낸 것**: 절차 문서 둘(`2026-08-26-test-harness.html` ·
`docs/ops/shared-database-guide.md`)이 아직 `podman exec` 를 들고 있음 → `TASK-152`.
<!-- SECTION:NOTES:END -->
