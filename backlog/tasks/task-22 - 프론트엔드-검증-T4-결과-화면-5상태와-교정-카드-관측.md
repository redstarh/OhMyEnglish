---
id: TASK-22
title: '프론트엔드 검증 T4: 결과 화면 5상태와 교정 카드 관측'
status: In Progress
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-06 15:12'
labels:
  - caps-req
dependencies:
  - TASK-21
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T4(C3·C4). 실물 글 모델 1회를 쓰는 유일한 프론트 태스크다(상한 승인됨). 자기순환을 피하려고 결과 API JSON과 화면을 대조한다 — API가 화면의 상류다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 5상태 라벨을 확인
- [x] #2 교정 카드 구조를 단정한다 — 원문/교정문 접두 2개 + 라벨 없는 셋째 줄이 비어 있지 않음
- [x] #3 결과 API가 낸 이유 문자열이 화면에 있는지 대조. 빈 문자열이면 FAIL이 아니라 BLOCKED
- [x] #4 얻은 세션 번호를 보존 목록에 적어 정리 대상에서 제외
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-06 착수. 캡틴 승인: 실물 모델 호출 1회 (browser_leg.md §9 상한).

⚠️ 선행 관계를 정직하게 적는다 — 감사가 이전에 순서 역전을 지적한 형태와 구별하기 위해서다. dependencies 의 TASK-21 은 형식상 In Progress 이지만 AC 5/5 이고 산출물이 커밋됐다(8e3d040 · 8ba78bd · 1157aa8). 열려 있는 이유는 신설 실행체 c2_render_hierarchy.py 의 재검토 미수신 하나뿐이다. T4 는 그 실행체를 쓰지 않는다 — 결과 화면(/results/<id>)을 재방문해 관측하는 경로이고 C2 주입 경로와 겹치지 않는다. 즉 재검토가 그 스크립트의 수정을 요구해도 T4 관측을 무효로 만들지 않는다. 이전 역전(TASK-21 이 In Progress 였을 때)은 계측이 A1-5 를 재지 못해 착수하면 거짓 판정이 나오는 상태였고, 이번은 그 조건이 아니다.

5상태의 생성 조건을 코드에서 확정했다 (app/services/results.py 규칙 1~5, 우선순위 순서대로 정확히 하나만 매칭):
1 connection_failed = learning_sessions.status='failed' (job 무관, 최우선)
2 no_utterances = analyze_utterance job 0건
3 analyzing = non-terminal(pending/running) job 1건 이상 — 교정 목록을 응답에 넣지 않는다
4 partial_failure = failed job 1건 이상 + non-terminal 0건 — done 교정은 포함
5 final = 1건 이상 전부 done
→ 실물 모델 호출이 필요한 것은 final 하나다. analyzing 은 WORKER_ENABLED=false 로 job 을 pending 에 두면 되고, connection_failed 는 stub_unresponsive 세션이 그 모양이다.

2026-09-06 T4 회차 완료 — AC 4/4. 판정 PASS (실행체 게이트 단정 48건 전건 통과). 회차 cfa512f6-5a4f-4b1d-b09a-9fa14fa91d5f.

실물 모델 호출은 analyze_utterance job 정확히 1건이다 (us.anthropic.claude-opus-5, attempts=1, done). 스텁 세션 1회는 원래 4건짜리라(analyze 3 + plan_next_session 1) 발화 seq 4·6과 plan job 을 지워 묶음을 하나만 남긴 뒤 워커를 잠깐 켰다. 켜기 직전 DB 전체 pending job 이 1건인 것을 직접 확인했다.

증거의 소유자는 회차 기록 tests/harness/runs/2026-09-06-t4-c3-c4-results-screen.md 다 — 여기서 재서술하지 않는다. 원시 판독과 스크린샷 6장 사본을 runs/ 에 추적으로 뒀다.

AC #4 (보존 목록): browser_leg.md §9 표에 5개를 corrections 수와 만든 방법까지 적었다. C3a analyzing 210233be · C3b final 6225ddaf (corrections 1) · C3c partial_failure b2f0d169 (0) · C3d connection_failed 76d9ef31 · C3e no_utterances d127dece.

절차 문서 갱신: §9 보존 표 · §8-④ 첫 대조 정정(보존 세션이 새 패턴을 만들면 '패턴 수 == baseline 행 수'가 깨진다 — 실측 7→8) · §8-0 baseline 사본을 v2 로(runs/2026-09-06-pattern-baseline-v2.tsv, 8행) · §11-8·10 닫힘 · §11-9 는 답을 확정하고 캡틴 결정으로 남김.

⛔ 통과로 적지 않은 것: A4-2 기대값 교차 대조는 교정 2건 이상 세션이 없어 평가 불가 → 판별력 미확인. 스텁 픽스처로는 원리적으로 어렵다 (오류 두 문장이 같은 패턴으로 묶이고 R1 이 패턴 단위로 그룹한다). 늘리려면 실물 호출을 더 쓴다 → 캡틴 결정. 그 밖에 발음 카드(C5)·partial_failure 의 done 교정 경로·폴링 정지 조건은 재지 않았다.

⚠️ C3e no_utterances 의 전제: 워커가 꺼져 있어야 유지된다. 켜면 flush_ended_sessions 가 지운 job 을 되살려 analyzing 으로 바뀐다. 백엔드는 stub + WORKER_ENABLED=false 로 복원했다.

2026-09-06 C3 리뷰 수신 — 결론 CHANGES REQUESTED (CRITICAL·HIGH 없음). 차단 4건 + 내 테스트가 잡은 1건, 전부 직접 재현하고 고쳤다.

① corrections 키 부재를 0으로 읽는 것이 공허 통과를 만들었다 — 재현: final 에서 키를 지우고 화면도 0장이면 checked 14→6, fails=[] 통과. A4-1·A4-2 전체가 조용히 사라진다. §11-9 가 요구하는 '교정 2건 이상 세션 추가' 가 primaries 마스크를 벗긴다는 지적도 맞다 → 상태별로 키 존재 자체를 단정한다.
② sentinel 대조의 독립 판별력이 0이었다 — 등호가 이미 함의한다. 반증 입력에서 어긋남 2건. 코드에서 지우고 browser_leg §5 A4-2 대조 ① 도 철회, 회귀 방지 테스트를 박았다.
③ A3-1 음성 대조가 세션 1건이면 항진명제 → 2건 미만이면 미평가로 갈라 낸다. 실측 확인.
④ READ_JS 가 location.href 를 담고도 단정하지 않았다 → 세션 id 로 끝나는지 단정(내비게이션 커밋 확인). C2 MEDIUM-1 과 같은 형태였다.
⑤ 내 게이트 테스트가 실행체 결함을 잡았다 — 카드가 API 보다 많으면 IndexError 트레이스백으로 죽어 이름 있는 FAIL 을 잃었다 → 경계 가드.

게이트 테스트 신설: tests/harness/test_c3_gates.py 24 passed (실물 판독값 위 변이 18종 + 없는세션 4종 + sentinel 회귀 + green). 게이트 안이다.

종단 재확인: 5세션 회차 판정 57건 PASS exit 0 (48→57) · 단일 세션 회차는 A3-1 미평가로 갈린다 · DB 변화 0(결과 화면 재방문은 세션을 만들지 않는다).
게이트: 666 passed · ruff/format/ty 통과 · 프론트 exit 0 · 게이트 밖 6 errors/4 files 유지.

리뷰가 §8-④ 정정에 단 조건(v2 가 v1 공유 7행에 drift 0 인 시점에 떴는가)에 답했다 — 그렇다. 재스냅샷 직전 drift 0 을 그 턴에 직접 확인했고 v2 머리주석에 뜬 시각이 있다. 회차 기록 §5 가 소유한다.

⛔ 요약을 좁혔다: 관측한 것은 다섯 상태의 라벨과 안내 문구이고 교정 카드 렌더는 final 하나에서만 봤다. partial_failure 의 done 교정 경로는 미관측이다.
미결: 3차 재검토 미수신.
<!-- SECTION:NOTES:END -->
