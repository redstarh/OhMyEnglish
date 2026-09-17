---
id: TASK-153
title: '정리: 하네스 기준선 표 둘이 redstar 소유라 ohmy 가 읽지도 지우지도 못한다'
status: Done
assignee: []
created_date: '2026-09-17 00:38'
updated_date: '2026-09-17 01:13'
labels: []
dependencies: []
ordinal: 214000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-41 이관 중에 발견. public 에 harness_pattern_baseline · harness_review_task_baseline 이 남았고 소유자가 redstar 다(다른 세션이 superuser psql 로 만들었다). 결과 셋: ① ohmy 로 pg_dump -n public 을 뜨면 permission denied for table harness_pattern_baseline 으로 죽는다(실측 — 백업을 redstar 로 떠야 했다) ② 하네스가 psql_cli(=ohmy)로 그 표를 drop/create 하려 하면 소유자가 아니라 막힌다 ③ 026 이 소유자로 걸러 옮기므로(R5) public 이 완전히 비지 않았다. ⛔ 그 표를 함부로 지우지 않는다 — browser_leg.md §8-0 이 「앞 회차 teardown 이 죽었으면 그 표가 원값의 유일한 사본」이라 무조건 drop 을 금지했다. 먼저 내용이 유효한 기준선인지 판정하고, 유효하면 소유자만 ohmy 로 바꾸고(alter table owner to) 아니면 지운 뒤 다음 회차가 다시 뜨게 한다. 소유자 변경은 superuser(redstar) 가 필요하다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 두 표의 내용이 살아 있는 기준선인지 판정한다 (앞 회차 teardown 이 끝났는지)
- [x] #2 ohmy 소유로 바꾸거나 지운 뒤, ohmy 로 pg_dump -n public 이 exit 0 인 것을 보인다
- [x] #3 하네스가 그 표를 ohmy 로 drop/create 할 수 있는 것을 보인다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실행 (2026-09-17 · 전부 이 세션에서 직접 돌린 출력)

**AC#1 — 살아 있는 기준선이었다.** `browser_leg.md` §8-0 의 drift 쿼리 둘을 `redstar` 로 돌려
`error_patterns` 4컬럼 대조 **0** · `review_tasks` 3컬럼 대조 **0**. 행수도 정확히 같았다
(baseline 9 = live 9 · baseline 15 = live 15) 그리고 id 집합 차이가 양방향 **0**
(only_in_baseline 0 · only_in_live 0). 컬럼도 2026-09-11 재스냅샷 이후의 여섯/일곱 컬럼 형태였다.
⇒ 앞 회차 teardown 이 끝난 상태다 → **지우지 않고 소유자를 옮기는 쪽**을 골랐다(태스크 서술의 분기).

**먼저 파일 사본을 떴다** (DB 표 하나에 진실을 걸지 않는 규약 · 옮기기 «전»에):
`tests/harness/runs/2026-09-17-pattern-baseline-v3.tsv`(9행) ·
`tests/harness/runs/2026-09-17-review-task-baseline.tsv`(15행). ⚠️ `review_tasks` 는 그때까지
**파일 사본이 아예 없었다** — DB 표 하나가 유일한 사본이었다. 그 공백을 이 태스크가 메웠다.

**AC#2 — `ohmy` 로 `pg_dump -n public` 이 exit 0 이다.**
`alter table public.harness_pattern_baseline owner to ohmy` · 같은 것을
`harness_review_task_baseline` 에(superuser `redstar` 로). 그 직후 `ohmy` 로 select 가 9 · 15 로 통했고
`pg_dump -n public` 이 **exit 0**(그 전에는 `permission denied for table harness_pattern_baseline`).
⛔ 종료코드를 **파이프 없이** 읽었다 — `H-BT` 가 적어 둔 대로 `| head` 를 걸면 `$?` 가 `head` 것이라
실패가 `exit=0` 으로 보인다(이 세션에서 처음 그렇게 읽었고 다시 쟀다).

**AC#3 — 하네스가 `ohmy` 로 drop/create 할 수 있다.** §8-0 의 SQL 블록을 **글자 그대로**(비수식)
`ohmy` 로 돌렸다. `begin/commit` 으로 묶어 실패 시 원값이 남게 했다 → exit 0.
결과: 두 표가 **`ohmyenglish` 스키마 · 소유자 `ohmy`** 로 다시 생겼다(비수식 `create` 는
`search_path` 앞자리에 만든다 — 026 이 `ohmyenglish, public` 으로 고정했다). 행수 9 · 15 ·
비수식 drift 쿼리 둘 다 **0**.

**값이 안 바뀐 것을 대조했다** — 재생성 결과를 위 파일 사본 둘과 `diff` 해 **차이 0**
(pattern 9행 정순 대조 · review_task 15행은 pattern_key+stage 에 동순위가 셋 있어 정렬 대조).

**최종 상태**: `public` 에는 En-Coach 호환 뷰 셋만 남았다(`error_patterns`·`error_occurrences`·
`pronunciation_attempts` · 전부 `ohmy` 소유). `pg_dump -n ohmyenglish` 는 exit 0 이고 `CREATE TABLE`
**21개** · `COPY ohmyenglish.harness*` **4개**(runs·sessions·기준선 둘). En-Coach 는 그대로 읽는다
(`set role en_coach` → 9 · 24 · 7 — 026 이 적은 값과 같다).

## 문서 — 낡을 자리 둘을 그 자리에서 고쳤다

- `tests/harness/browser_leg.md` §8-0: 두 표가 이제 `ohmyenglish` 에 있고 `ohmy` 소유임을 인용 블록으로
  박았다. ⛔ **「`public.` 을 붙이지 마라」와 「하네스 SQL 을 superuser 로 돌리지 마라」를 함께 적었다** —
  후자가 이 결함의 «원인» 이다(앞 회차를 superuser `psql` 로 돌린 세션이 그 표를 만들었다).
  그리고 파일 사본 지목을 v2(8행) 하나에서 v3(9행)+review-task(15행) 둘로 갱신했다.
- `docs/ops/pitfalls.md` `H-BT`: **원인이 사라졌음을 그 자리에 적고 `-T 'harness_*'` 우회를
  ⟨보관⟩ 으로 내렸다.** 지우지 않은 이유는 그때의 경위가 그 안에만 있기 때문이다.
  ⛔ **기전은 살아 있다** — 공유 스키마에 다른 소유자의 표가 하나 생기면 `pg_dump` 가 그 스키마
  전체에서 막힌다. 그래서 대응을 「우회」에서 **「그런 표를 만들지 않는다」**로 바꿨다.
- ⚠️ **`db/migrations/023` 머리주석의 `-T 'harness_*'` 는 고치지 않았다** — 이미 적용된
  마이그레이션의 이력이고, 지금의 백업 범위는 **026 머리주석**이 정본으로 갖는다(`-n ohmyenglish`).
  `docs/design/2026-09-14-weekly-report-plan.md` 의 같은 언급도 같은 이유로 그대로 둔다.
<!-- SECTION:NOTES:END -->
