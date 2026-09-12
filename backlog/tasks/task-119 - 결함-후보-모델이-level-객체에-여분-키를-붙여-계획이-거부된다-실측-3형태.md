---
id: TASK-119
title: '결함 후보: 모델이 level 객체에 여분 키를 붙여 계획이 거부된다 (실측 3형태)'
status: Done
assignee: []
created_date: '2026-09-12 00:00'
updated_date: '2026-09-12 00:09'
labels: []
dependencies: []
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 관측. 정본은 runs/2026-09-12-task108-deepest-marker.md §2 임. TASK-108 회차에서 Claude 4회 중 2회가 여분·기형 키로 걸렸음 — 팔A 는 무인용 키 reason: "" (JSON 문법 위반이라 후보 탐색 전부 실패), 팔B-1 은 level 안 빈 키 "": "" (extra_forbidden). ⚠️ 생산 경로에도 같은 부류가 있음 — 공유 dev DB 의 analysis_jobs 에 2026-09-10 07:49 UTC 계획 job 이 level.reason_en 여분 키로 거부됐고 attempts=2 로 재시도해 통과했음(직접 조회). 앞 회차 주석에도 level.reason_note: null 이 있음. ⇒ 세 형태가 전부 level 객체에 붙었으므로 _OUTPUT_SPEC 의 level 불릿이 여분 키를 유발한다는 가설이 섬. ⛔ extra=forbid 를 푸는 쪽으로 가지 않음 — 지어낸 키가 조용히 저장되는 것을 막는 가드임(parse_plan docstring). ⚠️ 대가는 재시도 1회이고 attempts 상한을 넘기면 계획이 아예 안 생김 — TASK-104 의 pending 간극에 기여하는 후보임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 재현률을 먼저 센다 — 같은 재료로 회차 수를 정해 놓고 돌려 몇 회에 여분·기형 키가 나오는지 센다. ⛔ 표본 4의 2회를 50%로 읽지 않는다
- [x] #2 기전을 가른다 — _OUTPUT_SPEC 의 level 불릿이 reason 을 요구하는 방식이 여분 키를 부르는지, 아니면 모델의 형식 오류인지
- [x] #3 고칠 자리를 정한다 — 프롬프트 문면인지 재시도 정책인지. ⛔ PlanOutput 의 extra=forbid 를 풀지 않는다
- [x] #4 TASK-104 의 pending 간극에 이 사유가 얼마나 기여하는지 analysis_jobs.last_error 로 대조한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4. 정본 회차 기록은 tests/harness/runs/2026-09-12-task119-extra-keys.md 임.

AC#1 재현률: 1단계 5회에서 여분키 2건(level.reason_note: null · level.reason_en: 영어 번역). 누적 9회에 4건이고 넷이 전부 level.reason 다음 자리임. 생산 경로 1건까지 다섯임. ⛔ 표본 5의 비율을 발생률로 단정하지 않음.

AC#2 기전: ⛔ 전역 금지 문장이 이미 있고 지켜지지 않았음 — plan.py:274 'Do not add any key that is not listed above'. 즉 문장이 없어서 생긴 결함이 아님. ⚠️ 동기는 단정하지 않음 — 「영어를 담고 싶어서」로는 reason_note: null 과 빈 키를 설명하지 못함. 확정된 것은 자리임.

AC#3 고칠 자리: _OUTPUT_SPEC 의 - level: 불릿에 국소 문장. ⛔ extra=forbid 를 풀지 않고 전역 문장을 강화하지 않고 재시도로 덮지 않음(근거는 회차 기록 §3). 구현은 TASK-121.

AC#4 TASK-104 대조: pending 4건이 전부 attempts=0 이라 이 부류의 기여는 0건임. 물린 대가는 재시도 1회(done 6건 중 1건)임. ⚠️ last_error 는 덮어써지므로 이 숫자는 하한임.
<!-- SECTION:NOTES:END -->
