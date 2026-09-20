---
id: TASK-263
title: '결함: 재시도 뒤 성공한 job 이 낡은 last_error 를 들고 done 이 된다'
status: Done
assignee: []
created_date: '2026-09-20 21:55'
updated_date: '2026-09-20 21:58'
labels: []
dependencies: []
ordinal: 327000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
handoff §3-3 이 원장 밖에 적어 둔 결함. complete() 가 status 만 done 으로 올리고 last_error 를 지우지 않아, 재시도 끝에 성공한 job 이 이전 시도의 실패 문면을 들고 done 으로 남는다. 화면 판정은 job 상태로만 하므로 사용자에게 새지는 않으나, 진단하는 사람이 done 인 job 의 실패 문면을 현재 사유로 오독한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 재시도 뒤 complete 된 job 의 last_error 가 null 임을 단정하는 단위 테스트가 있고, 고치기 전에 그 테스트가 실패하는 것을 직접 관측한다
- [x] #2 complete() 가 status 와 함께 last_error 를 지우고, last_error 는 현재 상태의 사유만 담는다는 계약을 docstring 이 적는다
- [x] #3 백엔드 게이트 넷이 exit 0 이다 (pytest · ruff check · ruff format --check · ty check)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
실측 증거 (2026-09-21 · 기준 1077417).

- AC#1 — 고치기 전 실행에서 새 테스트만 실패하는 것을 직접 봤음: `assert 'bedrock timeout' is None` · `1 failed, 1428 deselected`. 전체 회차에서 이 한 건만 실패했으므로 이 테스트가 그 계약의 유일한 방어라는 것도 같이 측정됐음.
- AC#2 — `app/backend/app/services/jobs.py` 의 `complete()` 가 `status = 'done', last_error = null` 로 바뀜. 반대쪽(`failed` 는 문면을 보존함)은 `test_failure_at_attempt_limit_marks_failed_and_is_never_reclaimed` 가 이미 지키고 있음.
- AC#3 — 백엔드 게이트 넷 exit 0: pytest 1429 passed · ruff check 0 · ruff format --check 331 files · ty 0.

추가 변경 없음으로 판정한 자리 하나. `complete()` 는 `locked_by`·`locked_at` 도 지우지 않아 `fail_or_retry` 와 어긋나지만, 제품 코드에서 그 두 값을 읽는 자리가 0곳임(grep: app·scripts 전체에서 `jobs.py` 밖 일치 0건 · 나머지는 테스트가 lease 를 빼앗는 픽스처임). reaper·claim 둘 다 `status` 로만 고르므로 done 행의 남은 lease 값은 동작에 닿지 않음. 근거 없이 넓히지 않았음.
<!-- SECTION:NOTES:END -->
