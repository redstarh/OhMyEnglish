---
id: TASK-73
title: W/R/G AC 테스트에 뮤테이션 KILL 확인을 붙인다 (결정 48 의 등가 증거)
status: Done
assignee: []
created_date: '2026-09-09 14:39'
updated_date: '2026-09-10 01:09'
labels: []
dependencies: []
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 결정 48 이 만든 작업임. 근거는 docs/design/2026-09-09-phase1-completion-audit.md §4 와 대장의 결정 48 임.

결정 48 이 red→green 의 등가 증거로 뮤테이션 KILL 확인을 인정했음(면제가 아님 — 증거의 형태만 바꿈). 그 기준으로 실제 상태를 재서 얻은 결론은 「기록된 KILL 확인이 사실상 0건」임.

직접 센 것 (grep: 뮤테이션·mutation·KILL·revert-재현·무력화):
- tests/unit/test_utterances.py (W1·W3·W6) — 0건
- tests/unit/test_jobs.py (W3·W4·W5) — 0건
- tests/unit/test_claude_schema.py (W7) — 0건
- tests/unit/test_analysis.py (W2) — 1건인데 SURVIVED 기록임(제거 뮤테이션이 전체 스위트를 통과한다는 사실을 근거와 함께 적은 주석)
- tests/unit/test_results.py (R1~R3) — 1건인데 무력화 둘이 통과한다는 기록임
- tests/integration/test_pipeline.py (W1 후반·W2·W3) — 3건 전부 SURVIVED 기록임
- tests/integration/test_worker.py (W1) — 1건인데 테스트 이름(does_not_kill_the_loop)임
- tests/integration/test_gateway.py (G1~G4) — 4건 중 셋이 테스트 이름(does_not_kill_the_session 류)이고 하나만 실제 뮤테이션 기록인데 그것은 S2-10(슬라이스 2) 범위임
- tests/integration/test_ws.py (G4) — 1건인데 뮤테이션 추론 주석임

⛔ SURVIVED 기록을 KILL 로 세지 않음 — 그것은 반대 방향의 사실임. 다만 그 주석들은 근거와 함께 남긴 것이라 지우지 않고, 「왜 이 자리는 뮤테이션으로 잴 수 없는가」의 근거로 그대로 씀.

⚠️ 개수를 세는 서술로 AC 를 쓰지 않음 — 대상은 AC 항목(W1~W7 · R1~R3 · G1~G4)이고 파일은 그 항목을 담는 자리일 뿐임.

이 태스크가 닫히면 AC 문서 「선언 자리」 표의 항목 4 를 충족으로 올리고, 그 뒤 TASK-70 만 남으면 Phase 1 완료를 선언할 수 있음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 W1~W7 각 항목의 테스트에 뮤테이션 KILL 확인을 붙이고 어떤 변이를 어떻게 걸었는지 기록한다
- [x] #2 R1~R3 각 항목에 같은 것을 한다
- [x] #3 G1~G4 각 항목에 같은 것을 한다
- [x] #4 뮤테이션이 SURVIVED 하는 자리는 KILL 로 위장하지 않고 그 사실과 이유를 남긴다 — 기존 SURVIVED 주석을 지우지 않는다
- [x] #5 붙인 뒤 게이트 넷을 다시 재고 AC 문서 「선언 자리」 표의 항목 4 를 갱신한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 착수 전 범위 메모.

⛔ 뮤테이션 대상은 테스트가 아니라 AC 항목임. 해당 파일 아홉에 든 `def test_` 를 세 보면 200건을 넘음(2026-09-09 실측 — 이 수는 테스트가 늘면 낡으므로 기준으로 쓰지 않음). 그것을 하나씩 뮤테이션하면 이 태스크는 끝나지 않고, AC 가 요구하는 것도 그것이 아님.

AC 항목은 열넷임 — W1~W7 · R1~R3 · G1~G4. 각 항목마다 **그 항목을 담는 단정 하나**를 골라 무력화하고 FAIL 을 관측하면 됨.

2026-09-10 — 항목별 대상 단정을 실제 줄로 확정했음(소스를 건드리지 않고 읽기만 했음):
- W1 ✅ **완료** — TASK-76 에서 두 변이로 확인했음. ① flush 묶음 정렬 뒤집기(`order by ... sequence_no` → `desc`) → FAIL 2건(test_merge_sql_keeps_its_explicit_ordering · test_agent_speech_between_finals_splits_the_run_in_two) ② 회복 스윕이 failed 세션을 건너뛰게(ENDED_SESSION_STATUSES 를 completed 만) → FAIL 2건(test_sweep_covers_sessions_closed_as_failed · test_worker_reaps_an_orphan_session_and_then_recovers_its_run). 둘 다 되돌렸고 git diff 로 확인했음.
- W2 integration/test_pipeline.py:163 (같은 pattern_key → patterns 1행 / occurrences 2행 / frequency 2)
- W3 unit/test_utterances.py:331 (같은 (session_id, sequence_no) 재insert → unique 위반)
- W4 unit/test_jobs.py:171 (lease 만료 회수 + 이전 token 의 complete 가 False)
- W5 unit/test_jobs.py:248 (attempts 상한 → failed + last_error, 재claim 불가)
- W6 unit/test_utterances.py:136 (voice_command 는 저장되나 job 미등록)
- W7 integration/test_pipeline.py:277 (검증 실패 응답 → fail_or_retry, 결과 0행)
- R1 unit/test_results.py:114 (3패턴 → 정확히 2개, high 가 medium 보다 먼저 — ordinal)
- R2 unit/test_results.py:197 (non-terminal job → analyzing + corrections 키 부재)
- R3 unit/test_results.py:267 (failed 1 + done 2 → partial_failure + 성공분 병존)
- G1 integration/test_gateway.py:8·194 (close 가 종료 기록보다 먼저)
- G2 integration/test_gateway.py:733 (무응답 → failed + 실패 이벤트, 무한 대기 없음)
- G3 integration/test_gateway.py:1128 (분기가 팩토리 한 곳에만 있음 — 소켓 계층이 nova 를 import 하지 않음)
- G4 integration/test_gateway.py:608 (픽스처 완주 → final 3행 + job 3건)

⚠️ 기존 SURVIVED 주석을 KILL 로 바꾸려 하지 않음 — 그것은 「이 자리는 뮤테이션으로 잴 수 없다」를 근거와 함께 남긴 것임. 그 자리는 다른 단정을 고르거나 SURVIVED 를 유지하고 이유를 적음.

⛔ 착수 조건 하나 — **codex 재리뷰가 도는 동안 소스를 변이시키지 않음.** 리뷰어가 리포를 읽으므로 변이된 코드를 리뷰하게 되고 판정이 무효가 됨. 2026-09-10 에 그것을 알아채고 변이를 리뷰 뒤로 미뤘음. 같은 이유로 `pytest` 동시 실행도 금지임(H-X).

2026-09-10 R1~R3 완료 (AC#2). 변이를 직접 걸어 FAIL 을 관측하고 무엇을 걸었는지 대상 테스트에 기록했다.

- R1: 두 축을 각각 잼. MAX_CORRECTIONS 2→3(개수) · severity ordinal case 식을 max(severity)로(정렬). 둘 다 test_top_two_corrections_ranked_by_severity_ordinal_not_text 가 FAIL.
- R2 규칙 1(연결 실패 최우선): 조건을 False 로 → 2건 FAIL.
- R2 규칙 3(analyzing 잠정 노출 금지): 조건을 False 로 → 4건 FAIL.
- R3: partial_failure=True 를 False 로 → FAIL.

⚠️ AC#4 를 함께 지켰다 — SURVIVED 를 KILL 로 위장하지 않았다. R1 변이 둘에 tiebreak 테스트가 통과하고 R3 변이에 drill 동승 테스트가 통과한다는 사실을 각 기록에 적었다. 대상 항목은 KILL 이지만 이웃 테스트는 그 축을 안 잡는다.

⚠️ 부수 관측 — R2 두 변이에서 「드릴 exchange 미달」 경고 로그가 실제로 났다. 즉 규칙 1·3 이 막는 것이 잠정 교정 노출만이 아니라 미달 로그 오염까지다. 모듈 docstring 이 그 이유를 이미 서술하는데, 그것이 관측으로 확인된 것은 이번이 처음이다.

⚠️ R2 규칙 1 의 「최우선」을 순서 이동으로 재지는 않았다 — 그 편집이 sed 로 안전하지 않아서다. 대신 이 테스트의 픽스처가 job 을 done 으로 두므로 규칙 1 이 없으면 규칙 5(final)로 떨어지고 그것이 「최우선이 아니면 실패한다」를 보인다. 그 한계를 기록에 적었다.

게이트: pytest 897 passed · 게이트 밖 ruff 0건 · format 100 files.

2026-09-10 G1~G4 완료 (AC#3). 변이를 직접 걸어 FAIL 을 관측하고 기록했다.

- G1(close 가 종료 기록보다 먼저): _close_and_record 의 종료 기록 블록을 adapter.close() 앞으로 옮겼다 → FAIL. 실패 메시지가 At index 0 diff: session.end_record != adapter.close 라 순서 자체를 잡는 것이 출력에 드러난다. ⛔ 「close 를 아예 부르지 않는」 변이가 아니라 순서만 바꾼 변이를 골랐다 — 전자는 호출 여부를 재고 G1 이 요구하는 것은 순서다.
- G2(연결 실패 가시화): TimeoutError 핸들러의 return CONNECT_TIMEOUT_REASON 을 return None 으로 → FAIL. ⛔ wait_for 자체를 제거하는 변이는 버렸다 — 이 리포에 pytest-timeout 이 없어 무한 대기가 테스트를 매달린다. 그 회차 로그에서 주입 타임아웃이 0.1초로 확인돼 그 판단이 맞았다.
- G3(포트 계약 · import 격리): session.py 에 nova import 를 넣으니 [session] 파라미터에서만 FAIL 하고 ws 는 통과했다 — 모듈별로 정확히 나뉘어 반응한다. ⚠️ import 그래프 단정은 소스 텍스트를 읽는 방식이라 런타임 변이로는 못 잰다. 변이를 import 문으로 준 이유가 그것이다.
- G4(시나리오 완주): _flush_analysis 본문 앞에 if True: return 을 넣어 job 등록을 건너뛰니 2건 FAIL(게이트웨이·소켓 양 계층). 후자가 assert 0 == 3 으로 떨어졌다.

게이트: pytest 897 passed · 게이트 밖 ruff 0건 · format 100 files · ty 통과.

남은 것은 AC#1(W1~W7 — W1 은 이전 세션에서 완료)과 AC#5(게이트 재측정 + AC 문서 항목 4 갱신)다.

2026-09-10 완료 — AC 항목 열넷 전부에 뮤테이션 KILL 확인을 붙였다.

W1(TASK-76 기록을 테스트로 옮김) · W2 · W3 · W4 · W5 · W6 · W7 · R1 · R2 · R3 · G1 · G2 · G3 · G4.

⛔ 이 회차에서 가장 값어치 있는 발견 — W5 의 두 변이가 서로 다른 테스트에 걸린다. MAX_ATTEMPTS 를 5에서 500으로 바꾸면 거동 테스트는 통과하고 상수 단정만 FAIL 한다(거동 테스트가 상수를 참조해 기대값을 만들기 때문에 상수를 따라간다). 상수를 그대로 두고 비교를 >= 에서 > 로 바꾸면 거동 테스트가 FAIL 하고 상수 단정은 통과한다. 즉 둘 중 하나만 있으면 W5 의 절반이 무보호다.

같은 구조가 W7 에도 있다 — 저장 전 거부는 claude_schema 의 confidence 범위 단정이 잡고 큐 보고는 pipeline 의 fail_or_retry 단정이 잡는다. 한쪽만 재면 job 이 running 에 남아 「lease expired without report」라는 거짓 사유로 종결되는 경로가 무보호로 남는다.

⚠️ 노트가 예정한 대상과 내가 고른 대상이 다른 자리 둘을 밝힌다. W3 은 노트가 「같은 (session_id, sequence_no) 재insert → unique 위반」을 골랐는데 그것은 W3 정의의 «추가 거동»이고, 나는 주 요구인 replace 계약을 골랐다. W7 은 노트가 통합 쪽만 골랐는데 정의가 둘을 요구하므로 양쪽을 다 쟀다.

⚠️ 노트의 줄 번호가 편집으로 밀려 있었다 — G3 는 1128 이 아니라 1391 근처였고 W7 의 277 은 다른 테스트가 됐다. 이름으로 다시 찾았다. 원칙 2(줄 번호로 가리키지 않는다)가 태스크뿐 아니라 테스트에도 적용된다는 사례다.

게이트 넷을 다시 쟀다: pytest 897 passed · ruff check exit 0 · format 34 files already formatted(백엔드) · 게이트 밖 ruff 0건 · format 100 files · ty check 통과 · 프론트 tsc exit 0 · eslint exit 0.

AC 문서 「선언 자리」 표의 항목 4 를 ✅ 충족으로 갱신했고, 그 위 판정 문장도 함께 고쳤다 — 남은 미충족이 항목 6 하나임을 명시했다. ⛔ 항목 6 은 재리뷰 HIGH 를 고친 뒤 재확인이 미수신이라 판정을 기록하지 못했다(TASK-70 소유). 「HIGH 를 고쳤다」는 Approve 가 아니다.
<!-- SECTION:NOTES:END -->
