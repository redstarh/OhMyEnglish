---
id: TASK-39
title: '설정: botocore 재시도 정책 설정 (Phase 2 운영 관찰 대상)'
status: To Do
assignee: []
created_date: '2026-09-07 17:50'
updated_date: '2026-09-12 01:30'
labels: []
dependencies: []
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. botocore 재시도 미설정 상태라 스로틀 시 중복 과금 위험이 있다. Phase 2 운영 관찰 시점에 설정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 botocore 재시도 정책(최대 재시도·backoff)을 설정한다
- [ ] #2 스로틀 재현 또는 관찰로 중복 과금이 사라지는지 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 (TASK-60 AC#3 에서 넘어옴). 실측 botocore 1.43.78 기본값: connect_timeout 60 · read_timeout 60 · retries None(= legacy 모드 기본이라 스로틀에 재시도가 «이미» 일어남). ⚠️ TASK-60 노트가 인용한 「기본 10분」은 이 리포의 값이 아님 — 참고 프로젝트 수치이고 여기서는 60초임. 그 문장을 그대로 옮기지 않음.

⛔ 이 태스크가 알아야 할 새 사실: 재시도가 SDK «안에서» 나므로 방금 만든 llm_calls 는 재시도분을 못 봄 — invoke_model 이 한 번 돌아오고 그 응답의 usage 만 적힘. 즉 중복 과금이 나도 이 표에는 1건으로 보임. ⇒ AC#2(중복 과금이 사라지는지 확인)를 이 표로 잴 수 없음. 재는 방법을 그 AC 설계에서 먼저 정해야 함(후보: botocore 이벤트 훅으로 시도 수를 세거나, retries 를 명시 설정해 max_attempts 를 알고 있는 값으로 고정).

2026-09-12 세션 ohmyenglish-f4. 정본 회차 기록은 tests/harness/runs/2026-09-12-task39-retry-policy.md 임.

AC#1 닫음: config.bedrock_boto_config() 가 standard 모드 · total_max_attempts=2 · connect_timeout=10 · read_timeout=120 을 명시함. 불변식 테스트 3건(전송 상한 · 읽기 여유 · 배선)을 두고 뮤테이션 셋으로 판별력을 확인했음 — config= 를 안 넘김 · 키를 max_attempts 로 바꿈 · read_timeout 을 60 으로 내림, 셋 다 실패로 잡혔음.

⛔ 실측으로 확정한 함정: max_attempts 키는 실제 전송 수와 «1 어긋남» (1→2회 · 2→3회 · 3→4회). total_max_attempts=N 은 정확히 N회임. request-created·before-send·needs-retry 를 함께 세어 여분 전송이 서명까지 새로 한 온전한 시도임을 확인했음 — 즉 max_attempts 로 적으면 청구 횟수를 하나 적게 세게 됨.

실측 수치: 정책 전(botocore 1.43.78 legacy 기본) 전송 5회 → 제품 정책 2회. 최대 청구 횟수가 job 재시도(MAX_ATTEMPTS=5)와 곱해져 5×5=25 → 2×5=10 으로 내려감.

read_timeout 을 «늘린» 근거: 계획 크기 호출(14,538자 · 입력 6,174 토큰)의 실제 소요가 30.27초·18.25초였음. 기본 60초는 그 최대의 2배뿐이고 넘으면 botocore 가 같은 호출을 다시 보냄 — 그것이 중복 과금의 기전임. ⚠️ 이 태스크 설명이 인용한 참고 프로젝트의 「10분 → 8초」와 방향이 반대이고 이유가 다름(그쪽은 종료 지연). 대가는 인터프리터 종료 시 스레드가 최대 120초 붙잡을 수 있는 것이고 lifespan 대기는 WORKER_SHUTDOWN_TIMEOUT=15 가 끊음.

⛔ AC#2 는 닫지 않음. 회차 기록 §0 이 미리 정한 대로 스로틀을 재현하지 않았음 — 잰 것은 기전과 상한이고 「중복 과금이 사라졌다」는 관측이 아님. 재시도 1회는 의도적으로 남김(스로틀에서 계획 job 을 살리는 값). 이 AC 는 태스크 제목대로 «운영 관찰» 항목으로 남김. ⚠️ llm_calls 로는 못 봄(SDK 안의 재전송은 1건으로 보임) — 운영에서 세려면 before-send 계수기를 붙여야 하고 그 형태는 이 회차의 실행체가 보여 줌.

게이트: pytest 987 passed(12.66s) · ruff check 0 · format --check 38 files · 게이트 밖 ruff 0 · ty 0. ⚠️ 게이트 밖 format --check 에서 내 파일 둘이 걸렸고 고쳤음 — 앞 마감 게이트에서 그 항목을 빠뜨렸던 것임(남은 1건은 동료 세션 파일).
<!-- SECTION:NOTES:END -->
