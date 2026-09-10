---
id: TASK-100
title: '결함(HIGH): 계획 생성이 발음 초점을 골랐는데 JSON 파싱에서 거부된다 — 계획이 2026-09-08 이후 갱신되지 않는 이유 후보'
status: Done
assignee: []
created_date: '2026-09-10 22:16'
updated_date: '2026-09-10 23:55'
labels: []
dependencies: []
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-98 회차가 찾았음. 정본은 tests/harness/runs/2026-09-11-task98-production-prompt.md §8 임.

재현: cd app/backend && .venv/bin/python ../../tests/harness/p5_worker_leg.py claim --expect-session <plan_next_session job 이 있는 세션> (⛔ guard 와 앞선 job 밀기가 선행됨 — 그 절차는 회차 기록 §8 이 가짐)

실제 관측 (last_error 앞 200자 · 원문):
plan output rejected: plan response was not JSON: '{\n  "focus": [\n    {\n      "pattern_id": "99fc908f-e25c-4c19-86ed-a4720cf8eb2b",\n      "pattern_key": "pronunciation_an_as_a",\n      "target_form": "an_as_a"\n    },\n    {\n      "pattern_id": "70ad1279'

⛔ 두 가지가 동시에 드러났음.
1. 좋은 것 — 모델이 pronunciation_an_as_a 를 focus «첫 자리»에 골랐음. 즉 4563f15(발음이 복습 예정일에 걸리면 계획 초점 한 자리를 얻게 함 · TASK-81)가 «작동»함. 그 갈래가 성립함.
2. ⛔ 나쁜 것 — 그 응답이 models/plan.py:285 에서 「plan response was not JSON」으로 거부됨. 즉 모델이 옳은 내용을 냈는데 저장되지 않음. job 은 status=pending attempts=1 로 남고 재시도 백오프가 걸림.

⚠️ 원인 미확정. 후보 둘: ⑴ 응답이 잘렸음(에러가 앞 200자만 담아 원문 길이를 모름. 70ad1279 에서 끊긴 것으로 보임) ⑵ 파서가 찾는 JSON 후보 형태와 응답 형태가 어긋남(그 raise 가 for 루프 «밖»이라 후보를 모두 시도한 뒤임). ⛔ 어느 것도 배제하지 못했음.

⚠️ 왜 HIGH 인가: session_plans 의 최신 행이 2026-09-08 22:58 UTC 이고 그 뒤 plan_next_session job 이 pending 으로 8건 쌓여 있음. 이 결함이 그 정체의 원인이면 «계획이 갱신되지 않는 상태»가 이어짐 — 즉 발음이 초점을 얻는 기능(TASK-81)이 제품에서 한 번도 발휘되지 못함.

⛔ 이 회차가 고치지 않았음. DB 는 전건 복원했음(analysis_jobs drift 0).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 응답이 잘린 것인지 파서 불일치인지 가른다 — 원문 전체를 로그로 남기게 하고 길이를 잰다
- [x] #2 이 결함이 session_plans 정체(2026-09-08 이후 갱신 0)의 원인인지 확인한다 — pending 8건이 같은 사유로 실패하는지 본다
- [x] #3 고친 뒤 계획이 실제로 저장되고 그 계획으로 조립한 프롬프트에 소리 줄이 붙는지 확인한다 (grep -c "Sound to coach today" >= 1)
- [x] #4 ⛔ TASK-98 AC#4(21회 회차)가 이 결함에 막혀 있다 — 이것이 닫히기 전에 21회를 쓰지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 조사·계측 완료. ⛔ 원인은 «미확정**이고 그렇게 적는 것이 정확함 — 재현되지 않았음.

재현 시도 2회 (같은 세션 `24597f0f` · `build_plan_prompt` 로 같은 프롬프트를 조립 · 실물 Claude):
둘 다 «온전한 JSON»이었음. ① 읽기 전용 프로브 — 프롬프트 13,482자 · 응답 3,005자 · `json.loads` OK.
② 사본 DB 에서 제품 경로(`claim_next` → `process_plan`) — 계획이 저장됨. 즉 실패 관측은 TASK-98
회차의 1건뿐이고 «간헐적»임(실패 1 · 성공 2).

배제한 것 1건: 「예산 절단」이 사유였다면 `claude_client.extract_text` 가 `stop_reason=max_tokens`
를 먼저 잡아 다른 문구를 냈어야 함(그 경로는 계획도 같은 `analyze()` 를 씀). 남은 후보는
「온전한 JSON 뒤에 산문이 붙음(Extra data)」과 「JSON 내부 구문 오류」이고 «어느 쪽도 확정하지 못함».

AC#1 — 가름 수단을 코드에 넣었음. `models/plan.py` 의 거부 사유가 이제 원문 길이 · 파이썬 디코드
사유 · head · tail 을 담음(이전 판은 `raw[:200]` 만 담아 두 원인을 구별할 수 없었음). 잘림은
`Unterminated`·`Expecting`, 뒤에 붙은 산문은 `Extra data` 로 갈림 — 문구를 발명하지 않고 파이썬이
낸 것을 그대로 실음. 테스트 2건(`test_undecodable_response_reports_length_and_decode_reason` ·
`test_trailing_prose_is_reported_as_extra_data`)이 그것을 지킴. ⚠️ 파서가 받아들이는 형태는
넓히지 않았음 — 계측이지 관용이 아님.

AC#2 — ⛔ 이 결함은 정체의 원인이 «아님». 근거 둘: pending 15건 전부 `attempts=0`·`last_error` null
(실패 흔적 0건) · 떠 있는 백엔드의 환경이 `WORKER_ENABLED=false`(`ps -Eww` 로 직접 확인). 즉
아무도 그 job 을 집지 않았음. 실제 원인은 `TASK-104` 로 등록했음. 이 태스크의 HIGH 근거가 그
가설이었으므로 «그 근거는 철회됨» — 결함 자체는 실재함(관측 1건).

AC#3 — 사본 DB(`ohmyenglish_t100`, 012 적용 전 백업을 복원)에서 제품 경로로 확인했음:
`session_plans` 2행→3행 · job `status=done attempts=1 last_error=null` · 저장된 초점이
`[pronunciation_an_as_a, article_missing_before_noun]` · 제품 조립기 `build_system_prompt` 가 낸
세션 지시문 5,181자에 `- Sound to coach today: "an_as_a"` 가 «1건» 있음. 즉 TASK-81 의 기전이
계획 저장을 지나 세션 지시문까지 «닿음». ⛔ 공유 dev DB 는 건드리지 않았고(사본에서만 실행)
끝난 뒤 사본을 삭제하고 공유 DB 행 수 무변경을 확인했음(session_plans 2 · pending 15).

AC#4 — 21회를 쓰지 않았음. 이 태스크가 닫히므로 `TASK-98` AC#4 의 차단은 풀림 — 다만 그 회차는
`TASK-98` 의 몫이고 결정 49 유지 여부는 사용자 판단임.

⚠️ 범위 밖으로 남긴 것 1건: `models/analysis.py:223` 에 같은 형태(`raw[:200]`)가 그대로 있음.
분석 경로에서 같은 결함이 나면 같은 눈먼 자리가 재현됨 — 고치지 않았고 언급만 함.
<!-- SECTION:NOTES:END -->
