# Handoff — 계획 프롬프트·시나리오·총평 갈래 · 세션 `ohmyenglish-f4`

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 짧게 씀 — 판정 근거를 옮기지 않고
> 태스크 조회와 설계서를 가리킴(`backlog task view <ID> --plain`).
>
> 이전 판은 `handoff/archive/HANDOFF-plan-prompt-2026-09-14-0800.md` 임(그 앞은 `…-0740.md`).
> ⛔ 다른 갈래의 handoff 를 건드리지 않았음 — `HANDOFF-pronunciation.md` 는 발음 축 소유임.

최종 갱신 2026-09-14 · 브랜치 `design/first-vertical-slice` · **작업 진행 중**(마감이 아님)

---

## ① 이 세션이 한 것

**받은 사용자 결정 다섯**(정본은 `docs/ops/captain-instruction-register.md`): **88**(시드의 시간 창은
실측 · PRD 하한 미달은 알려진 격차) · **89**(`TASK-62` 범위 넷을 뒤늦게 등재) · **90**(클립 오디오:
리포 추적 · 최소 화면까지 · 컬럼 하나 + WAV + 새 엔드포인트 · `has_audio`) · 그리고 그 뒤 셋
(dev DB 시드 동기화 승인 · 발음 축 답을 기다린다 · 다음은 `TASK-26`).

**닫은 태스크 열**: `TASK-66` 과 `66.1`~`66.8` · `TASK-135`.
⇒ **합성 쉐도잉 클립 오디오가 스키마부터 화면까지 끝났음.** 022 · 설정 키
`shadowing_clip_audio_root` · `assets/clips/…201.wav`(추적) · `services/clip_audio.py` ·
`api/shadowing.py` · payload 의 `has_audio` · `app/ShadowingPanel.tsx`.

**만든 문서**: 설계서 `2026-09-14-shadowing-clip-audio-design.md` · 계획서 `…-plan.md` ·
회차 `tests/harness/runs/2026-09-14-task66-clip-audio.md` · 함정 `H-BS`.

## ② 다음 한 걸음 — `TASK-26`(주간 리포트)

사용자가 골랐음. **AC#1 은 이미 닫혀 있음**(결정 58 — 주 경계는 월요일 시작). 남은 셋이 판정을
요구함: AC#2(표에 적재할지 조회 시 계산할지) · AC#3(경계를 `users.timezone` 으로 · ⛔ `current_date`
금지) · AC#4(마이그레이션 번호 발급 — 착수 턴에 `ls db/migrations/` 로 다시 봄. 002·008 은 영구 결번).
⇒ 새 기능이라 `brainstorming` → `writing-plans` 를 태움.

⛔ **막힌 것 하나**: `TASK-66.9`(dev DB 에 020·021·022 적용)가 `Awaiting Decision` 임. 발음 축
(`ohmyenglish-d9`)에 020 이 적용 가능한 상태인지 물어 뒀고 **답을 기다리는 중임** — 답이 오면
사용자에게 올림. ⛔ 답 전에 아무것도 적용하지 않음.

## ③ 착수 전 필수 — 9개

1. ⛔ 태스크를 새로 열기 전에 **결정 대장과 원장을 함께** `grep` 함.
2. ⛔ **부분 실행에 `-c pyproject.toml`**(`H-AJ`) · 게이트는 **cwd `app/backend`**(`H-A`·`H-BN`) ·
   **`ty` 는 절대경로** `/Users/redstar/.local/bin/ty`.
3. ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 **전** `git diff --cached --name-only` · push **전**
   `git log --oneline origin/<브랜치>..HEAD`(`H-BO`) · **공유 파일은 고친 턴에 커밋**(`H-BR`).
4. ⛔ **무력화 시험의 되돌림이 안 돌 수 있음**(`H-BS` · 이 세션이 등록) — 같은 자리수 치환을 같은
   초에 되돌리면 `.pyc` 가 유효로 판정돼 옛 바이트코드가 돎. `diff -q` 는 그것을 통과시킴.
5. ⛔ **`pytest` 를 돌리기 전에 발음 축(`ohmyenglish-d9`)에 알림**(`H-X`).
6. ⚠️ 마이그레이션 파일 최대는 **`022`** 이고 **dev DB 는 `019`** 임 — 020·021·022 셋이 미적용이고
   `migrate.py` 는 미적용분을 **전부** 적용하므로 022 만 가려낼 수 없음(`TASK-66.9`).
7. ⚠️ **dev DB 의 시드가 낡았음** — `clip_end_sec` 이 `16.64` 인데 리포 상수는 `17.36` 임.
   022 적용과 함께 재시드가 필요함.
8. ⛔ **검증 전용 스택 규약**: DB 소유자를 **`ohmy`** 로 · `WORKER_ENABLED=false`(`H-AT`) ·
   끝나면 죽이고 drop 한 뒤 **dev DB 무오염을 조회로 확인**. 브라우저 레그는 **전용 Chrome** 을
   `--use-fake-device-for-media-stream` 로 띄움(`H-BD` · 이 세션이 다시 썼음).
9. ⛔ **`db_pool` 픽스처는 아무것도 정리하지 않음** — 심은 행을 스스로 지움.

## ④ 인계 지표 — 이 시점에 직접 돌려 얻음

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`e9a392f`** — 이 handoff 를 담은 커밋이 그 뒤임. 미커밋 0건 · origin 과 동기 |
| 2 | 다음 걸음 | **`TASK-26`**(주간 리포트) · `Awaiting Decision` **1건**(`TASK-66.9`) |
| 3 | 게이트 | 여섯 전부 exit 0 — `pytest` **1152 passed** · `ruff check` · `ruff format` **217 files** · `ty` · 프런트 `tsc` · `eslint` |
| 4 | 착수 전 필수 | 9개(③) · 원장 To Do **8** · In Progress **7**(전부 발음 축) · Awaiting Decision **1** · Done **141**(frontmatter 를 직접 센 출력) |

## ⑤ 이 세션이 얻은 규율

- ⛔ **되돌림이 red 로 남으면 「내 되돌림이 틀렸다」로 읽기 전에 «소스와 실행 대상이 같은가»를 봄**
  (`H-BS`). `grep -c` 로 소스에 변이 문자열이 0인지 세고, 그때도 red 면 캐시임.
- ⛔ **TTS 는 회차마다 같은 길이를 내지 않음** — 같은 전사문·같은 화자에서 16.64초와 17.36초가
  나왔음. 그래서 시간 창은 「그 파일의 길이」이고 단정이 **파일에서 다시 읽어** 대조함.
- ⛔ **조사의 결론은 「무엇이 없는가」의 «범위»까지 적어야 함** — 「엔드포인트가 0곳」이라 적었는데
  화면 자체가 0이었고, 그 차이가 AC 의 크기를 바꿔 범위 질문을 다시 만들었음.
- ⛔ **설정값을 기본값으로 두고 「적용됐는가」를 잴 수 없음** — 항등원(1.0배·1회)이면 적용 여부가
  관측에 나타나지 않음. 회차에서 1.5배·2회로 주고 쟀음.
- ⛔ **브라우저 회차가 단위·통합이 못 보는 부류를 잡음** — 오디오 주소가 상대 경로라 프런트 포트로
  가고 있었음. 프런트 테스트가 0이고 백엔드 단정은 자기 포트로 직접 부르므로 어느 쪽도 못 봄.
- ⚠️ **결정을 받은 턴에 대장에 적음** — `TASK-135` 가 그것을 어긴 자리를 뒤늦게 메운 태스크였음.
