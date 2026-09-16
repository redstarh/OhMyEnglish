---
id: TASK-152
title: '정리: 절차 문서 둘이 아직 podman exec 를 복붙하게 둔다 (TASK-149 의 잔여)'
status: Done
assignee: []
created_date: '2026-09-16 23:21'
updated_date: '2026-09-16 23:53'
labels: []
dependencies: []
ordinal: 213000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-149 가 개발 도구 셋(dev_db.sh · smoke_analysis.py · tests/harness/README.md)에서 죽은 podman 폴백을 지웠으나, 절차 문서 둘이 아직 그 명령을 들고 있다. ① docs/ops/2026-08-26-test-harness.html — podman 참조 10건이고 하네스 절차 정본이라 사람이 여기서 복붙한다(:5433 접속정보 · podman exec psql · podman ps 프리플라이트 · psql 이 없다는 낡은 서술). ② docs/ops/shared-database-guide.md — En-Coach 전달용 온보딩 문서인데 2.1 이 dev DB 를 podman 컨테이너로 소개하고 4.3 재현 SQL 과 6 확인 명령이 전부 podman exec 다. ⇒ 남의 앱 담당자가 이 문서를 따라가면 존재하지 않는 컨테이너로 간다. 참고: tests/harness/browser_leg.md:5 가 이 두 문서를 가리켜 위임 금지 근거로 삼으므로 고친 뒤 그 줄의 문면도 맞춘다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 docs/ops/2026-08-26-test-harness.html 의 podman 참조가 homebrew :5432 경로로 바뀌었다 (grep 으로 0건 확인)
- [x] #2 docs/ops/shared-database-guide.md 2.1 · 4.3 · 6 이 psql 절대경로 또는 psql_cli.py 로 바뀌었다
- [x] #3 tests/harness/browser_leg.md:5 의 위임 금지 근거가 낡지 않게 정정됐다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 처리 (2026-09-17)

**`docs/ops/2026-08-26-test-harness.html` — 아홉 자리**: 머리 문단의 스택 서술 · 1절 DB 행 ·
프리플라이트 `P1`(`podman ps` → `scripts/dev_db.sh status`) · 러너 기동 근거 둘 · A계층 도구 목록 ·
증거 확인 SQL 블록(`psql_cli.py` 로) · 함정 목록의 「psql 이 없다」 · 승인 관련 서술 · 꼬리말의 근거 절.
⚠️ **`podman` 문자열 4건이 남았고 의도한 것임** — 전부 「지웠다」·「그때는 그랬다」는 이력 서술이고
복붙 가능한 명령은 0건임. ⛔ **AC#1 의 「grep 0건」은 달성하지 않았고 달성하면 안 됨**: 뒤집힌 사실을
남기는 것이 규율임(`rules/session-handoff.md` §4-3).
⛔ **꼬리말에서 「직접 실행해 확인했다」의 범위를 좁혔음** — 그 문장이 podman 경로까지 덮고 있었는데
지금 확인한 것은 `dev_db.sh status` 하나임. 확인하지 않은 것을 확인했다고 남겨 두지 않았음.

**`docs/ops/shared-database-guide.md` — 살아 있는 서버에 직접 붙어 다시 재고 두 곳을 정정했음**:
- §2.1 을 homebrew 기준으로 다시 씀(17.9 · :5432 · psql keg-only · `stop`·`reset` 이 없는 이유).
- ⛔ **§2.3 은 결론이 뒤집혔음** — 이전 판은 *"호스트 접속에 비밀번호가 필수"*(컨테이너 실측)였는데
  homebrew 서버는 `PGPASSWORD=COMPLETELY_WRONG` 과 비밀번호 없는 DSN **둘 다 접속됨**. 즉 `trust` 임.
  ⚠️ `pg_hba.conf` 원문은 못 봤음(`pg_hba_file_rules` 가 permission denied) — 관측된 동작이라고 적었음.
- ⛔ **§4.3 의 「superuser(= ohmy)로」가 지금 성립하지 않음**: 직접 조회로 `ohmy` 는 `rolsuper=f` ·
  `rolcreaterole=f` · `rolcreatedb=t` 이고 superuser 는 `redstar`·`stockagent` 임. 어느 문장이
  `redstar` 를 요구하는지 갈라 적었고, 그 갈라짐은 권한 모델에서 유도한 것이라고 명시했음
  (공유 서버에 시험용 역할을 만들지 않기 위해 문장별로 돌려 보지 않았음).
- §4.2 ① 의 「비밀번호 필요」와 §3-(2) 의 「역할이 ohmy 하나뿐」이 새 §2.3 과 모순이라 함께 정정했음.
- ⚠️ **내가 만든 낡은 지목도 고쳤음** — §1 이 `api/ws.py:44` 의 `FIXED_USER_ID` 를 가리키고 있었는데
  `TASK-148` ④ 로 `models/user.py` 로 옮겼음.

**`tests/harness/browser_leg.md`**: 위임 금지의 근거가 「그 두 문서가 podman 을 들고 있다」였는데 그
전제가 사라졌음. 근거를 **「판정 근거가 한 곳에 있어야 한다」**로 바꿔 적고 자기완결은 유지했음.

**직접 돌린 증거**:
- ⛔ **가이드 §6 에 처음 적은 형태가 zsh 에서 안 됐음** — `PSQL=... ; $PSQL -U ohmy` 는 zsh 가 변수를
  단어로 쪼개지 않아 `command not found` 임. 돌려 보고 잡아서 **셸 함수**로 바꿨고, 바꾼 형태를
  zsh 에서 다시 돌려 `\dn` 이 `en_coach`·`public` 을 내는 것을 확인했음(exit 0).
- 코드 변경 0건이라 게이트는 앞 커밋의 값(1280 passed)이 그대로 유효함.
<!-- SECTION:NOTES:END -->
