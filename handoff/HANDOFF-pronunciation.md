# Handoff — 발음 축 · 세션 `ohmyenglish-7f`

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. **짧게 씀** — 판정 근거를 옮기지 않고
> **태스크 조회와 회차 기록을 가리킴**(`backlog task view <ID> --plain`).
>
> **이전 판**: `handoff/archive/HANDOFF-pronunciation-2026-09-11-0920.md`(그 앞은 `…-0857` · `…-0320`).
> ⛔ **다른 갈래의 handoff 를 건드리지 않았음** — `HANDOFF-test-harness.md`(세션 `ohmyenglish-40`) ·
> `HANDOFF-implementation.md` · `HANDOFF-audit.md` 는 그쪽 소유임.

최종 갱신 **2026-09-11 09:36 KST** · 브랜치 `design/first-vertical-slice`

---

## ① 이번 세션이 한 것

사용자 지시 둘 — 「handoff 를 읽고 4지표를 대조한 뒤 `TASK-1` 의 접근을 골라 이어가라」 →
「결정이 필요한 것만 Slack 으로 보내고 계속 진행하라(자리 비움)」.

**닫은 태스크 넷**: `TASK-1`(일일 오류 요약 표 012 + 학습자 화면) · `TASK-100`(계획 거부 사유가
원인을 말하게 함) · `TASK-98`(AC#4 판정) · `TASK-105`(소리 줄 팔 21회).
**등록한 태스크 셋**: `TASK-104`(정체의 실제 원인) · `TASK-105`(닫음) · `TASK-106`(픽스처).
**받은 결정 하나**: 사용자가 `TASK-1` 을 **접근 B** 로 확정.
**동료 세션(`ohmyenglish-40`)과 교차 확인 셋**: 진행 중 회차 없음 · `WORKER_ENABLED=false` ·
`--job-type` 변경 검토(그쪽이 docstring 에 「결함 3」으로 올려 커밋했음).

⛔ **판정 다섯만 옮김.**

1. **`session_plans` 정체의 원인은 JSON 거부 결함이 아님** — pending 15건이 전부 `attempts=0`·
   `last_error` null 이고 백엔드가 `WORKER_ENABLED=false` 로 떠 있음. `TASK-104` 가 소유함.
2. **그 결함은 간헐적이고 원인 미확정임**(실패 1 · 성공 2). 예산 절단은 배제했음.
3. **`TASK-81` 기전이 세션 지시문까지 닿음** — 공유 DB 에서 계획을 다시 생성하니 초점 첫 자리가
   `pronunciation_an_as_a` 이고 제품 지시문 **5,223자**에 소리 줄이 **1건** 붙음.
4. **`TASK-98` AC#4 = 구별되지 않음** — 두 팔이 같은 분기에 있어 축이 경로에 닿지 않음.
5. ⛔ **`TASK-105` 21회도 질문에 답하지 못함** — tool **0/21**(대조군 5/5)인데 **픽스처에 목표
   소리가 없음**(`p2m` 의 오류는 f→p·r→l·θ→s 이고 두 문장에 «an» 이 없음). 코칭은 21회 전부
   났으나 **전부 문법 지시**였음. 선행은 `TASK-106` 임.

**관측 정본**: `runs/2026-09-11-task105-sound-line.md` §2·§3(측정과 판별력) ·
`runs/2026-09-11-task98-production-prompt.md` §9 · 태스크 노트 `TASK-1`·`TASK-100`.
**새 함정 넷**: `H-BB`·`H-BC`·`H-BD`·`H-BE`.
**실물 호출**: Nova **27세션**(팔 A 21 · 팔 B 5 · 상한 26 안 + 준비 확인 0) · Claude **6회**
(계획 프로브 1 · 계획 저장 2 · 분석 3).

## ② 다음 한 걸음 — **`TASK-106`**(목표 소리가 든 픽스처 · 지금 `To Do`)

`backlog task view TASK-106 --plain` 이 근거와 인수기준 넷을 가짐. 요지는 하나임 —
**계획이 고르는 소리는 `an_as_a` 하나뿐**(DB 의 발음 패턴이 그것뿐임)이므로 **「an」을 「a」로
발음한 wav** 를 만들어야 이 축을 잴 수 있음.

⚠️ **다시 재기 전에 배제된 것 둘을 다시 재지 않음**: 소리 줄이 프롬프트에 도달함 · 대조군 정상(5/5).

**대안 후보 둘**(둘 다 `To Do`): `TASK-104`(pending 15건 소화 — 비용과 시점을 먼저 적어야 함) ·
`TASK-2`·`TASK-3`(신규 요구사항 갈래).

## ③ 착수 전 필수

1. ⛔ **픽스처와 계획의 소리가 맞는지 «먼저» 확인함** — 이 세션이 그 확인을 빠뜨려 21회를 썼음.
   `scenarios-P-pronunciation.md:75~76` 이 픽스처 문장의 정본임.
2. ⛔ **초점이 둘이면 교란됨** — `pronunciation_an_as_a` 와 `article_missing_before_noun` 이 같은
   낱말에서 만남. 하네스 팔로 초점을 하나로 두려면 그 팔을 제품 팔과 섞지 않고 이름을 갈라 붙임.
3. ⛔ **결정 54 가 payload 질을 결정 50 의 ③ 기준에 넣었음** — tool 도착률이 좋아져도 ③ 은
   `TASK-103` 이 닫히기 전에 열리지 않음.
4. ⛔ **워커 구간은 `p5_worker_leg.py` 를 쓰고 `--job-type` 을 «항상» 줌**(그 도구 docstring 의
   결함 3). 스냅샷은 회차 디렉터리에 두고 `restore` 로 되돌림.
5. ⚠️ **게이트는 `app/backend` cwd 에서만 판정함**(`H-A`). `tests`·`scripts` 는 그 cwd 에서 경로를
   지정해 따로 돌림(`H-L`). 파이프 뒤 `$?` 를 판정에 쓰지 않음(`H-AZ`).
6. ⚠️ **`git add <디렉터리>/` 를 쓰지 않음**(`H-BE` · 이 세션이 밟았음) — 파일을 열거함.
7. ⚠️ **공유 DB 백업은 `-U ohmy` 로 막힘**(`H-BB`) — `pg_dump -d ohmyenglish -n public` 으로 뜸.
   `harness_*_baseline` 조회도 `ohmy` 롤로는 막힘(같은 원인).
8. ⚠️ **CDP 에서 마이크가 열리지 않음**(`H-BD`) — 화면만 볼 때는 서비스 함수로 전사문을 남김.

그 밖의 실측 함정은 `docs/ops/pitfalls.md` 가 소유함 — 여기에 복제하지 않음.

## ④ 인계 지표 — **직접 돌려** 얻고 대조함

| # | 지표 | 이 마감 시점 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`30336bc` 이상**(등호를 요구하지 않음 — 동료 세션이 커밋·푸시함). `origin` 보다 **1 앞섬** |
| 2 | 다음 걸음 | **`TASK-106`**(`To Do`). `backlog task view TASK-106 --plain` 을 먼저 돌림 |
| 3 | 게이트 | `pytest` **917 passed**(15.70s) · `ruff check` 안·밖 **exit 0** · `format --check` **exit 0** · `ty` **All checks passed** · 프론트 `tsc`·`eslint` **exit 0**(파이프 없이) |
| 4 | 착수 전 필수 | **8개**(위 ③). `TASK-106` 의 `dependencies` **0건** · 미충족 AC **4건**(전부 미체크) |

⚠️ **format 의 「N files」는 `.md` 를 세므로 지표로 적지 않음**(`H-AR`).
⚠️ **DB**(공유 dev · 이 세션 마감 시점): `error_patterns` **9** · `review_tasks` **15** ·
`session_plans` **3**(2026-09-11 00:08 UTC 가 최신 · 초점 첫 자리가 발음) · `learner_notes` **4** ·
`analysis_jobs` **57**(pending 14) · `learning_sessions` **17** · `utterances` **128** ·
`pronunciation_attempts` **7** · `daily_error_summary` **0** · 표 **19개**(012 적용).
⛔ **baseline drift 0·0** · 보존 세션 여섯 전건 기대와 같음.
⚠️ **이 세션이 공유 DB 에 남긴 변경은 둘뿐임** — 계획 1행 · 노트 1행(결정 53 범위).
⚠️ **미커밋에 내 것은 0건**임 — `runs/2026-09-10-*` 셋과 `handoff/archive/…` 백업만 남음.

## ⑤ 이 세션이 얻은 규율 — **판별력을 「돌리기 전에」 확인함**

⛔ **21회를 쓰고 나서 픽스처에 목표 소리가 없다는 것을 알았음.** 「내가 직접 돌렸다」가 아니라
**「이 관측이 무엇을 배제할 수 있는가」**를 먼저 물었어야 함 — 이 리포가 다섯 번째로 밟은 형태임.
`TASK-100` 에서 얻은 같은 규율의 다른 얼굴: 거부 사유가 `raw[:200]` 만 담아 **두 원인을 구별할 수
없었음**. 고친 것은 결함이 아니라 그 눈먼 자리임.
⚠️ **`attempts=0` 을 「한 번도 시도되지 않았음」으로 단정하지 않았음** — 하네스 복원으로도 그 값이
만들어짐. 그래서 `WORKER_ENABLED=false` 를 `ps` 로 직접 확인해 두 번째 근거를 세웠음.
