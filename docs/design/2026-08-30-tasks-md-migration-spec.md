# 작업 지시 — `TASKS.md` → Backlog.md 마이그레이션

> **누가**: 이 리포에서 작업하는 세션(당신). **왜 당신인가**: 당신이 `TASKS.md`를 실시간으로 편집 중이라
> 다른 세션이 손대면 충돌한다. 분류는 캡틴이 확정했고 **실행만 남았다.**
>
> **분류 결정 근거·전체 원장**: `~/MyProject/DevInfra/TASKS.md` (Task 8)
> **도구 원칙·명령·함정**: `~/.claude/rules/task-management.md` — **먼저 읽을 것**
>
> 준비 상태: `backlog/` init 완료 · MCP 등록 완료(`.mcp.json`, **승인 대기 — 당신이 승인해야 붙는다**) ·
> `statuses` 4개 적용 완료(`To Do` / `In Progress` / `Awaiting Decision` / `Done`)

_작성: 2026-08-30_

---

## 착수 전 필수

1. **`.mcp.json`의 `backlog` MCP 서버를 승인한다.** 승인 전에는 툴이 안 붙는다.
2. `backlog task list`가 경고 없이 도는지 확인한다(현재 태스크 0건이 정상).
3. `TASKS.md`를 **커밋 가능한 상태로** 만든 뒤 시작한다. 반쯤 옮긴 상태를 남기지 않는다.

## 전체 구조 — 92행을 두 갈래로

측정 시점 `TASKS.md` 315줄 · 표 92행.

| 갈래 | 섹션 | 행 | 목적지 |
|---|---|--:|---|
| **태스크** | `A` `G` `E` `C` `D` | 55 | **`backlog/tasks/*.md`** |
| **비태스크** | `B` `F` `H` `관련 문서 지도` | 37 | 아래 §비태스크 |

판별 기준: **"이것을 누가 언제 끝내는가?"에 답이 없으면 태스크가 아니다.**

## 태스크 55행 — Backlog.md로

`A`(20) `G`(14) `E`(11) `C`(5) `D`(5). 헤더·구분선 행은 제외하고 실제 항목만 옮긴다.

- **상태 매핑**: `✅`→`Done` · `🔨`→`In Progress` · `⏭`→`To Do` · `⏸`→`Awaiting Decision` ·
  `⛔`은 **상태가 아니다** → `--dep`으로 선행 태스크를 건다.
- **"착수 전 필수" 열은 인수기준(AC)으로 옮긴다.** `--ac`는 **쉼표로 분리되지 않는다** — `--ac "a" --ac "b"`로 반복.
- **"커밋" 열의 해시는 설명(`-d`)에 남긴다.** 증거이므로 버리지 않는다.
- `A-1`~`A-4`, `G-8`처럼 **하위 절이 붙은 항목**은 그 내용을 해당 태스크의 설명·AC로 흡수한다.

```bash
backlog task create "<제목>" -d "<설명 + 커밋 해시>" --ac "<기준1>" --ac "<기준2>"
backlog task edit TASK-N -s "In Progress"
backlog task edit TASK-N --check-ac 1
```

⚠️ **`B-5`~`B-8`이 `G-4`~`G-7`을 가리킨다.** G는 태스크로 가고 B는 결정 문서로 가므로,
**결정 문서에서 새 태스크 ID로 다시 가리킨다.** 줄 번호로 가리키지 않는다.

## 비태스크 37행

### ① `B. 캡틴 결정` 12행 → `docs/design/2026-08-30-captain-decisions-phase1.md` (신설)

`B-1`~`B-10`, 전부 `종결`. 각 항목의 **결정 + 근거 + 해석을 그대로 보존**한다 — 요약하지 말 것.
이 문서가 존재하는 이유는 재논의 방지다. 특히 아래는 근거가 잘리면 다시 뒤집힌다.

- `B-1` 판정↔시범 상관키 → (b) 최신순 수용. `target_form` 술어를 **더하지 않는** 이유
- `B-9` `.claude/settings.json` → 커밋하지 마, **지우지도 마** (하네스 워크트리 금지가 이 파일에 의존)

각 결정 끝에 후속 태스크를 **새 태스크 ID**로 링크한다(`B-5`~`B-8` → `G-4`~`G-7`의 새 ID).

### ② `F. 전역 규약 정리` 11행 → **이 리포에서 삭제.** 조치 완료됨

섹션이 스스로 `범위: ~/.claude/** — 이 리포 밖`이라고 적어놨다. **이 리포에 있을 내용이 아니다.**

- **표 (a) 5행**(파일별 전→후 실측: `self-verification-gate.md` 132→46 등) → **버린다.**
  `~/.claude`의 git 이력이 이미 갖고 있다.
- **표 (b) 2행**(LSP 우선 원칙 유지 · `§2 [skip ci]` 유지 + 근거) → **이미 옮겼다.**
  `~/.claude/rules/code-development-principles.md` 꼬리에 "다시 삭제 후보로 올리지 말 것"으로 기록됨.

→ **당신이 할 일은 F절을 지우는 것뿐이다.**

### ③ `H. En-Coach와 DB 공유` 6행 → `docs/ops/`로 축약

`H-1`~`H-4` 전부 ✅. 철회안(`postgres_fdw`)은 본문이 밝힌 대로 이미
`docs/ops/shared-database-guide.md` §4-alt에 보존돼 있다 → **중복이므로 옮기지 않는다.**

**살릴 것은 `H-3`의 실측값 한 줄**: *"En-Coach가 실제로 붙었다 — `en_coach`에 `ec_*` 9개 +
자기 `schema_migrations`, 우리 `public`에 `ec_` 표 0개"*. 이 확인 사실을 `shared-database-guide.md`에
넣고 `TASKS.md`의 H절은 그 문서를 가리키는 한 줄로 줄인다(또는 삭제).

⚠️ **`H-2`가 가리키는 `docs/ops/shared-database-naming-rules.md`에 `en_coach` 역할의 평문 비밀번호가 있다**
(커밋 `7a5bfce`). 이 때문에 **이 리포의 GitHub 공개 push가 차단돼 있다**(`DevInfra/TASKS.md` Task 10-1).
H절을 손볼 때 같이 처리할지 캡틴에게 물어라 — 선택지는 비밀번호 회전 / 이 리포만 비공개 / 이력 재작성이다.

### ④ `관련 문서 지도` 8행 → 리포 루트 `README.md`

순수 인덱스 6행. `README.md`로 옮기고 **"무엇이 남았나 → 이 파일"** 행은
**"→ `backlog board` / `backlog task list`"** 로 고친다(원장이 파일에서 도구로 옮겨졌으므로).

## 마감 후 `TASKS.md`

**파일을 지우지 말고** 아래만 남긴다 — 다음 세션이 원장을 찾을 수 있어야 한다.

```markdown
# TASKS — 이 파일은 더 이상 원장이 아니다

태스크 원장은 **Backlog.md**다: `backlog task list` · `backlog board`
원칙·명령: `~/.claude/rules/task-management.md`

- 캡틴 결정 기록 → `docs/design/2026-08-30-captain-decisions-phase1.md`
- DB 공유 구성 → `docs/ops/shared-database-guide.md`
- 문서 지도 → `README.md`

이전 내용은 git 이력에 있다(마이그레이션 전 마지막 커밋 참조).
```

## 완료 판정 — 직접 돌려 확인한다

| # | 확인 | 명령 |
|--:|---|---|
| 1 | 태스크가 다 옮겨졌나 | `backlog task list \| grep -c TASK-` → **55행에서 나온 항목 수와 일치** |
| 2 | 상태가 4개로 매핑됐나 | `backlog board` — 네 열에 항목이 분포하고 `⛔`가 상태로 남지 않았나 |
| 3 | 선행 조건이 의존으로 갔나 | `grep -l 'dependencies:' backlog/tasks/*.md \| wc -l` → `⛔` 항목 수 이상 |
| 4 | 비태스크가 목적지에 있나 | `ls docs/design/2026-08-30-captain-decisions-phase1.md` · `grep -c '문서 지도\|어디' README.md` |
| 5 | F절이 지워졌나 | `grep -c '전역 규약 정리' TASKS.md` → **0** |
| 6 | 무회귀 | 테스트·lint·타입 검사 게이트를 직접 돌려 이전 실측값 유지/증가 |

**1번을 어림으로 세지 말 것.** 마이그레이션 전에 `A`·`G`·`E`·`C`·`D`의 실제 항목 수를 세어 적어두고 대조한다.

## 마감 시 원장 갱신

완료하면 `~/MyProject/DevInfra/TASKS.md`의 **Task 8을 `완료`로 바꾸고 증거를 적는다**(위 6개 확인 결과).
그 파일은 이 작업의 상태 정본이다.
