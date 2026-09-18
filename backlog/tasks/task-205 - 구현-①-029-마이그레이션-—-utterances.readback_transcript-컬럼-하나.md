---
id: TASK-205
title: '구현 ①: 029 마이그레이션 — utterances.readback_transcript 컬럼 하나'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:07'
labels: []
dependencies: []
ordinal: 266000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4. 낭독 전사문을 담을 자리. ⛔ 값역 CHECK 를 DROP → ADD 하지 않는 덧붙이는 형태다 — 새 job 종류도 새 표도 만들지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 029 가 utterances 에 readback_transcript text 컬럼 하나만 더한다
- [x] #2 기존 CHECK 를 건드리지 않는 것을 마이그레이션 본문으로 확인한다
- [x] #3 dev DB 적용 전 pg_dump -n ohmyenglish 로 백업한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18)

### AC#1 — 컬럼 하나만 더했음

`029_utterances_readback_transcript.sql`. `alter table utterances add column readback_transcript text`
하나와 CHECK 하나(`utterances_readback_only_for_shadowing`)임. 새 표·새 job 종류·새 `utterance_type`
값을 만들지 않았고 그 셋을 각각 왜 기각했는지 마이그레이션 머리말이 가짐.

### AC#2 — 기존 CHECK 를 하나도 건드리지 않았음

이 파일에 `drop constraint` 가 0건임 — `add column` 과 `add constraint` 둘뿐임.
⚠️ 새로 더한 CHECK 는 「없던 제약을 더하는」 것이고 `011`·`028` 처럼 기존 CHECK 를 DROP → ADD 하는
위험한 형태가 아님.

### AC#3 — 백업 뒤 적용하고 스키마를 직접 확인했음

백업: `pg_dump -d ohmyenglish -n ohmyenglish -f db/backups/2026-09-18-before-029.sql` ·
**exit 0** · **181,496 바이트** · `CREATE TABLE` **22** · `COPY ohmyenglish` **22**(일치).
⚠️ `-U ohmy` 를 붙이지 않음 — `H-BX` 계열이 적은 대로 그 롤은 `public` 의 남의 표에서 막힘.
⛔ 덤프에 학습 데이터가 담기므로 `.gitignore` 에 `db/backups/` 를 더했음(추적 대상이던 것을 확인하고).

적용: `./app/backend/.venv/bin/python scripts/migrate.py` · exit 0.
⛔ **exit 코드를 증거로 쓰지 않고 스키마를 조회했음** —
`schema_migrations` 에 `029_utterances_readback_transcript.sql` 있음 ·
컬럼 `readback_transcript` `text` `is_nullable=YES` 있음 · CHECK 이름 조회로 존재 확인.

### 판별력 — 가드가 실제로 막는 것을 반증 시험으로 봤음

낭독이 아닌 발화(`utterance_type='learning'`)에 `readback_transcript` 를 넣어 봤고
`CheckViolationError` 로 막혔음(*"violates check constraint
utterances_readback_only_for_shadowing"*). ⇒ 그 CHECK 가 무력한 장식이 아님.

### 게이트

`pytest` **1361 passed** · `ruff` 0 · `ty` 0 — 셋 다 exit 0. 컬럼이 nullable 이라 기존 INSERT 가
그대로 통과함.
<!-- SECTION:NOTES:END -->
