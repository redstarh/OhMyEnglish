# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-17 08:01 KST** · 세션 `ohmyenglish-43` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-17/HANDOFF-0801.md` 에 있음**(그 앞 판들은 같은 폴더의
> 날짜별 하위에 있음). 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 상태 정본은 원장(`backlog/`), 근거 정본은 **태스크 노트 · `tests/harness/runs/**` ·
> `docs/ops/captain-instruction-register.md` · `docs/design/2026-09-16-codebase-cleanup-plan.md`** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. **역할은 기본값(통합 테스트)에서 출발함.** 이 세션은 사용자가 구현을 지시할 때마다 그 범위만
   구현했음(결정 121·122). ⛔ **새 세션은 다시 기본값에서 출발하고 열려 있는지 확인함.**
2. ⚠️ **살아 있는 사용자 지시 둘**: ⑴ *"테스트 진행은 니가 권고안 대로 나에게 뭍지 말고 진행해"*
   ⑵ *"짧게 핵심만 보고해 … 각 항목당 두줄 요약"*. 설계·제품 판단은 그대로 물음.
3. ⛔ **긴 문서는 절 단위로 나눠 쓰고 합침** (사용자 지시 2026-09-16) — 한 번의 `Write` 로 통째로
   만들지 않음.
4. ⛔ **커밋 메시지에 코드 식별자를 넣을 때 `-m` 을 쓰지 않음** — 백틱이 셸 명령 치환으로 읽혀
   식별자가 사라짐(이 세션에서 밟았고 `--amend` 로 고쳤음). 인용된 heredoc(`<<'EOF'`)을 씀.
5. ⚠️ **학습 추천 job 만 `us.openai.gpt-5.6-terra` 로 돌고 bearer 키로 붙음**(결정 121). 키가 없는
   환경에서는 그 job 이 `RuntimeError` 로 즉시 실패함. 나머지 job 넷은 Opus 5 · SigV4 임.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | 게이트를 돌린 시점은 **`c4bdb1c`** 이고 `origin` 과 **0/0** 이었음. ⚠️ 새 세션 `HEAD` 는 그보다 **한 커밋 뒤**임 — 그 커밋은 **이 handoff 와 원장뿐이고 코드가 아니므로** 게이트 수치가 같으면 실질 일치임. ⛔ 자기 커밋 해시를 여기 적지 않는 이유는 반드시 낡기 때문임 |
| 2 | 다음 한 걸음 | **`TASK-148`** — `api/ws.py` 의 도메인 정책 쪼개기. 방향은 확정됨(결정 122) 이고 그 태스크 노트가 착수 순서 ③→①→④→② 를 가짐 |
| 3 | 게이트 | **일곱 다 초록** — 수집 **1278** · `pytest` **1278 passed** · `ruff` exit 0 · `ruff format` exit 0 · `ty` exit 0 · `tsc` exit 0 · `eslint` exit 0 · 문면 정본 검사 **13 passed** |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **8건**(전부 `To Do` · In Progress **0** · 전체 **212** · 완료 **204**) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q --collect-only && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . && ./.venv/bin/ruff format --check . && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint .
```

## ① 이 세션이 한 것 — 결함 하나, 모델 교체, 정리 회차

**결함 둘을 확정하고 고쳤음**: `TASK-140`(자정을 넘겨 정지 중인 세션의 녹음이 지워짐 — 결정 119) ·
`TASK-78.1`(51세션에서 입력 0인 우회로 제거 — 결정 120).
**모델을 옮겼음**: `TASK-141` 측정 → 결정 121 → `TASK-142` 구현(추천 job 만 terra · bearer 경로) ·
`TASK-143` 그림자 평가(analysis 도 문턱 셋 충족 · 전환은 미결).
**정리 회차 `TASK-144`**: 리뷰 다섯 갈래 · 적용 넷 · 갈라냄 여섯. 정본은
`docs/design/2026-09-16-codebase-cleanup-plan.md` §8~§12 임.
**결정 122 로 갈라낸 것 중 셋을 닫았음**: `TASK-145`(안 쓰는 헬퍼 삭제) · `TASK-146`(타임존 SQL
정본화) · `TASK-150`(DB CHECK 대조 단정 넷 + 이름 정정).

## ② 지금 상태 — 새로 생긴 계약 셋

- **모델**: 추천만 terra(bearer HTTPS) · 나머지 넷 Opus 5(SigV4 boto3). 계열 판정은
  `is_openai_model` 하나이고 본문·텍스트·usage 세 자리가 그것으로 갈림.
- **값역 정본 둘**: `LIVE_SESSION_STATUSES`(살아 있는 세션 상태 — 녹음 층도 이것을 읽음) ·
  `services/user_timezone.timezone_of`(타임존 조회와 널 검사).
- **린트**: 규칙군 여섯을 켰고(`BLE`·`DTZ`·`PTH`·`SLF`·`S310`·`N803`) **앱 트리에만** 적용됨 —
  `tests`·`scripts` 는 `per-file-ignores` 로 뺐음(그 트리의 위반 다수가 «일부러 그렇게 쓴 것»임).

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest` 는 `app/backend` 에서 인자 없이 돌림.** 부분 실행은 `-o asyncio_mode=auto` 를 붙임.
   툴 호출 사이에 cwd 가 남으므로 **절대 경로**를 씀(이 세션에서 `cd` 가 두 번 실패했음).
2. ⛔ **종료 코드에 파이프를 걸지 않음**(`H-AZ`) — 이 세션에서 또 한 번 밟을 뻔했음.
3. ⛔ **`ruff check --select X` 는 프로젝트 규칙을 «대체»함**(새 함정 `H-BV`) — 규칙을 더해 보려면
   `--extend-select` 를 씀. 그리고 규칙을 켤 때 **`tests`·`scripts` 트리도 함께 재야 함**(A1 의 실수).
4. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.
5. ⚠️ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop.
   불변 지표(이 세션 실측): 새 DB `schema_migrations` **23** · 공유 dev DB `learning_sessions` **17**
   · `session_plans` **6**.
6. ⚠️ **명령 경로를 실물로 태우려면** 브라우저 없이 `ws_session.py --wav <픽스처>` 로 됨 —
   `:8013`·`:8014` 로 두 번 돌렸음. Nova 는 오디오 간격 55초를 넘기면 스트림을 끊음(`H-BF`).

## ④ 열린 태스크 8건

| 태스크 | 상태 |
|---|---|
| **`TASK-148`** | **다음 걸음.** 방향 확정(결정 122) · 착수 순서는 그 노트가 가짐 |
| **`TASK-41`** | 방향 확정(결정 122 — 「구현이 끝났다」) · 착수 전 확인 셋이 노트에 있음 |
| `TASK-147` | `review.py` 배치화 — 성능이고 사용자 결정 대기 |
| `TASK-149` | 죽은 podman 경로 셋 — ⛔ **팀리드 권고로는 이것이 가장 급함**(검사 도구가 거짓 신호) |
| `TASK-151` | `tests` 트리 누적 줄 길이 위반 17건 — 남의 문장이라 그 갈래가 하는 것이 맞음 |
| `TASK-39`·`TASK-41` 외 | `TASK-116.5`(문장 인용 구멍 2/59 파킹) · `TASK-122`(LOW · 네 세션이 보류) |

## ⑤ 착수 전 반드시 읽을 것

- **결정 119~122** — 값역 정본 공유 · 우회로 제거 · 모델 교체와 그 대가 · 갈라낸 다섯의 방향.
- **`docs/design/2026-09-16-codebase-cleanup-plan.md` §10~§12** — 절차가 무엇에서 성립했고
  무엇을 보태야 했는지, 갈라낸 여섯의 이유.
- ⚠️ **가장 값 있는 산출물이 코드가 아니라 단정이었음** — 정리에서 변이를 걸어 보니 `cancelled`
  단계를 밟는 테스트가 0건이었고, 그 구멍은 학습 발화 하나를 오류 분석에서 빼앗았음.
