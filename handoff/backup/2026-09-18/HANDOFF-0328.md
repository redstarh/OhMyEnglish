# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-18 01:42 KST**(같은 세션이 세 번째로 마감함) · 세션 `ohmyenglish-42` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-17/HANDOFF-1305.md` 에 있음**(그 앞 판들은 같은 폴더의
> `HANDOFF-1245.md`·`HANDOFF-0947.md`·`HANDOFF-0801.md`). 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 상태 정본은 원장(`backlog/`), 근거 정본은 **태스크 노트 · `tests/harness/runs/**` ·
> `docs/ops/captain-instruction-register.md` · `docs/ops/pitfalls.md`** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임**(사용자 지시 2026-09-17). 살아 있는 지시 셋: ⑴ 꼭 필요한 것 외에는
   묻지 않고 권고대로 감 ⑵ 개발이 끝나면 테스트를 필수로 돌림(게이트 수치로 대체하지 않음)
   ⑶ 짧게 핵심만 보고함. ⛔ **En-Coach 는 고치지 않음** — 관련 수정은 OhMyEnglish 가 흡수함.
2. ⛔⛔ **결정 124 는 반증됐음 — 「소리를 따옴표로 «따로» 인용하라」를 프롬프트에 다시 넣지 말 것.**
   실물 회차 7세션이 그것을 뒤집었음: 그 요구가 있으면 코치가 **오디오 오류가 아닌 낱말**을 집고
   tool 호출이 **2 → 1** 로 줄어 재발화 판정이 사라짐. 같은 날 앞 문면은 3/3 으로 제 오류를 집음
   (모델 변화가 아님). 정본은 `runs/2026-09-17-task154-dedicated-quote/README.md` 이고
   `nova.py` 규칙 9 위 주석과 `test_neither_prompt_asks_the_coach_to_quote_the_sound_on_its_own`
   이 그 금지를 지킴. ⇒ **결정 82 의 「이 축에서 프롬프트를 더 고치지 않는다」가 되살아났음.**
3. ⛔ **DB 배치**: 우리 표는 `public` 이 아니라 스키마 **`ohmyenglish`** 에 있음. 역할 `ohmy` 의
   `search_path` 가 `ohmyenglish, public` 이라 **비수식 이름이 정상 경로**임. `pg_dump` 는
   **`-n ohmyenglish`** 를 씀(`-n public` 은 호환 뷰 셋만 떠서 **데이터 0줄**). `public` 에는
   En-Coach 호환 뷰 셋만 남았고 `harness_*` 은 하나도 없음(`TASK-153`).
4. ⛔ **`information_schema` 조회에 `current_schema()` 를 반드시 건다** — `public` 에 동명 호환 뷰가
   있어 안 걸면 두 스키마 행이 섞이고 **뷰는 모든 컬럼을 nullable 로 보고함**(`H-BX`).
5. ⛔ **긴 문서는 절 단위로 나눠 쓰고 합침** · **커밋 메시지에 백틱 식별자를 넣을 때 `-m` 을 쓰지
   않음**(인용된 heredoc 을 씀).
6. ⚠️ **백엔드가 떠 있음**(pid **71188** · `:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub
   --log-level info` · 로그 `/tmp/omy-backend.log`). 소스를 고쳤으면 **재기동해야 함**(`--reload` 없음).
   ⚠️ **레벨은 `info`·`warning` 둘 다 됨**(`TASK-156` — P5 의 신원 확인이 로그 내용이 아니라
   **`lsof` 의 fd** 를 봄). `warning` 으로 내리면 「로그 0줄」을 근거로 쓰기 전에 그 채널이 오류를
   잡는지 먼저 증명해야 함.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | 게이트를 돌린 시점은 **`fc0cec8`** 이고 `origin` 과 **0/0** 이었음. ⛔ 자기 커밋 해시를 여기 적지 않는 이유는 반드시 낡기 때문임 — 새 세션 `HEAD` 가 한 커밋 뒤면 그것은 **이 handoff 뿐**임 |
| 2 | 다음 한 걸음 | ⛔ **원장이 완전히 닫혔음 — 열린 태스크가 0건임**(`To Do` 0 · `In Progress` 0 · `Awaiting Decision` 0). ⇒ **다음 걸음은 사용자의 방향 지시뿐임.** 지시를 받으면 태스크로 등록하고 착수함 |
| 3 | 게이트 | **일곱 다 exit 0** — 수집 **1294** · `pytest` **1294 passed** · `ruff` 0 · `ruff format` **273 files** · `ty` 0 · `tsc` 0 · `eslint` 0 |
| 4 | 착수 전 필수 | 전체 **217** · 완료 **217** · 열린 것 **0** · **미충족 AC 0건**. ⇒ 착수 전 조건이 없음 |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q --collect-only && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint .
```

## ① 이 세션이 한 것 — 원장을 비웠음

닫은 것: `TASK-153`·`116.5`·`154`·`155`·`156`·`122`. 근거는 각 태스크 노트가 가짐
(`backlog task view <ID> --plain`) — 여기 옮겨 적지 않음.

⛔ **이 세션의 값은 넣은 것보다 «되돌린 것» 에 있음.** 결정 124 를 이행했다가 실물 회차가 반증해
두 프롬프트에서 걷었음. 그 판정을 만든 것은 **회차 중간에 더한 짝 대조 팔** 하나임 — 그것이 없으면
「모델이 바뀐 듯하다」로 잘못 닫았음(상한을 4 → 7 세션으로 늘렸고 그 사실을 회차에 적었음).

## ② 지금 상태 — 새로 생긴 계약

- **하네스 기준선 표**: `ohmyenglish` 스키마 · 소유자 `ohmy` · 9행·15행. 파일 사본 둘이
  `runs/2026-09-17-*-baseline*.tsv` 임. ⛔ §8-0 의 SQL 을 **비수식으로** 씀(`public.` 을 붙이면 없음).
- **P5 프리플라이트**: 로그 신원을 `lsof -nP -p <pid> -Fn` 의 열린 fd 로 세움(`realpath` 도 함께 봄 —
  macOS 의 `/tmp` 가 심볼릭 링크임).
- **프롬프트**: 두 프롬프트의 규칙 9 가 **결정 124 이전 문면**임. 바이트 게이트가 `prompt_dedicated_v4`
  를 가리키고 초록임 — 그것이 「되돌렸다」의 기계 증거임.
- **계획 파서**: `parse_plan` 이 `PlanOutput` 검증 «전에» **이름이 빈 키 중 값도 빈 것**만 걷음
  (`TASK-122`). ⛔ 그 관용을 넓히지 말 것 — 이름이 있는 모르는 키와, 이름이 비어도 값이 있는 키는
  **여전히 거부**하고 그 두 경계를 단정이 지킴.
- **함정 신설**: `H-BZ`(프롬프트 회차를 tool 도착만으로 검수하면 「무엇을 코칭하는가」가 조용히 깨짐).
  `H-BT` 는 원인이 사라져 `-T 'harness_*'` 우회를 ⟨보관⟩ 으로 내렸음.

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(루트에서 돌리면 기본 규칙셋으로 떨어져 「0건」이
   나옴 · `H-BN`). 부분 실행은 `-o asyncio_mode=auto`. 툴 호출 사이에 cwd 가 남으므로 절대 경로를 씀.
2. ⛔ **한글 주석을 쓴 직후 `ruff check` 를 한 번 돌림** — `E501` 은 문자 수가 아니라 표시 폭이라
   한글이 2열임(`H-BW`). 이 세션이 그 자리에서 반복해서 걸렸음.
3. ⛔ **종료 코드를 판정에 쓸 때 파이프를 걸지 않음** — `> /tmp/out 2>&1; echo $?`(`H-AZ`).
   그리고 zsh 는 변수에 담은 명령을 쪼개지 않고, **함수 호출을 `$(...)` 에 중첩하면 파싱이 깨짐**.
4. ⚠️ **실물 Nova 회차는 전용 검증 DB 에서 돌림** — `createdb` → `scripts/migrate.py` →
   `p8_inject_pronunciation.py inject` → 백엔드를 **다른 포트**(`:8014`)에 `VOICE_ADAPTER=nova` 로.
   끝나고 `dropdb` 하고 **공유 dev DB 표를 다시 읽어** 무변경을 대조함.
5. ⚠️ **불변 지표(이 세션 마지막 실측)**: dev `learning_sessions` **17** · `utterances` **128** ·
   `error_patterns` **9** · `review_tasks` **15** · `analysis_jobs` **57** ·
   `pronunciation_attempts` **7** · `schema_migrations` **24** · `harness_runs` **28** ·
   `harness_sessions` **100**.
6. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄(`H-BE`·`H-BR`).

⚠️ **나머지 일반 함정은 여기에 옮겨 적지 않음** — 정본은 `docs/ops/pitfalls.md` 임.

## ④ 열린 태스크 — **0건**

원장이 완전히 닫혔음(전체 217 · 완료 217). ⛔ **다음 세션의 첫 행동은 태스크를 고르는 것이 아니라
사용자의 방향을 받는 것임.** 지시를 받으면 `rules/session-handoff.md` 3항대로 **계획 직후 전체를
원장에 등록**하고 착수함.

⚠️ **원장이 비었다는 것이 「할 일이 없다」는 뜻은 아님** — 이 세션이 남긴 열린 축 하나를 적어 둠:
문장 전체만 인용한 코치 발화는 어긋남 검사가 여전히 판정하지 못함(세션 2/59). 검사 쪽은 이득이
구조적으로 0 이고 프롬프트 쪽은 반증됐으므로, 남은 후보는 **오디오를 듣는 판정**이고 설계서 §6 이
범위 밖에 뒀음. 그것을 열려면 사용자 결정이 필요함 — 그래서 태스크로 등록하지 않았음.

## ④-1 이 세션이 남긴 산출물 하나 (git 추적 대상 아님)

`.harness/reports/feature-and-usage.html` — 구현된 기능과 사용 방법을 한 장으로 정리한 보고서임
(사용자 요청 2026-09-18). 기능은 코드에서 확인해 파일 경로를 함께 적었고 **미구현 항목도 따로**
두었음. ⚠️ **기능 판정의 정본이 아님** — 정본은 `docs/PRD.md`·`docs/design/`·이 파일임. 그 보고서는
`fc0cec8` 시점의 사본이라 코드가 바뀌면 낡음. 다시 필요하면 그 시점 코드로 다시 만듦.

## ⑤ 착수 전 반드시 읽을 것

- **결정 124 와 그 반증 절**(지시 대장) — 위 「먼저 챙길 것」 2번의 근거. 그것을 읽지 않고 프롬프트
  문면을 만지면 반증된 변경을 되살림.
- **`runs/2026-09-17-task154-dedicated-quote/README.md` §7** — 이 세션이 배운 것 둘.
- **함정 `H-BZ`·`H-BT`·`H-BX`·`H-BW`** — 앞 둘은 이 세션이 세우거나 고쳤음.
- ⚠️ **가장 값 있는 관찰**: 게이트가 초록이고 tool 이 4/4 로 와도 **제품이 나빠질 수 있음.**
  깨진 축은 「무엇을 코칭하는가」와 「몇 번 보고하는가」였고 그 둘은 판정선에 없었음.
