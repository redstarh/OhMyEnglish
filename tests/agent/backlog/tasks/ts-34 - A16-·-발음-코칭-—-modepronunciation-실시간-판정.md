---
id: TS-34
title: A16 · 발음 코칭 — mode=pronunciation 실시간 판정
status: Blocked
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 07:43'
labels: []
dependencies: []
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A16. 대상: WS mode=pronunciation · services/pronunciation.py. 근거: PRD §10. ⛔ 알려진 상태: Phase 1 완료 선언문이 「발음 기능은 미동작」이라 적었고 TASK-75 가 미해결임 — 그러므로 이 영역은 실패를 예상하는 자리이고, ⛔ 그 예상이 관측을 대신하지 않음. ⛔ 스텁은 학습자 발화를 발명하므로 발음 오류를 만들 수 없음 — 실물 또는 p8_inject_pronunciation.py 우회가 필요함. ⛔ 채점·점수는 비범위임(PRD §10.3).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 발음 오류에 대해 올바른 발음 시범이 돌아옴
- [ ] #2 따라 말한 결과가 성공·실패·판정 불가 가운데 하나로 기록됨
- [ ] #3 전사문에 한글이 섞인 경우와 되물음이 신호로 기록됨 (PRD §10.2)
- [x] #4 미동작이면 무엇이 어디서 끊기는지 증거와 함께 적음 (TASK-75 와 이어 줌)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## B6 회차 (2026-09-19 · HEAD a34a143) — 차단됨 (AC 2/4)

수단: /tmp/b6_pron.py (사본 runs/2026-09-19-b6/evidence/driver-b6_pron.py) — ws_session.py 의 run() 을 부르는 얇은 래퍼임(그 파일의 main() 은 .harness/evidence/ 에 쓰는데 그 경로가 쓰기 경계 밖임). --mode pronunciation --wav p2k.wav,p2a.wav --silence-ms 12000 --timeout 120.
세션 d5497eaf-4e7f-4a8c-89a1-5bcc488c063c · mode=pronunciation · 07:30:53~07:32:21 UTC.
⛔ 브라우저가 아니라 WS 레그를 쓴 이유: p_app_path.py 는 「학습 시작」만 눌러 mode=pronunciation 진입을 만들지 못하고, 그 드라이버를 고치는 것은 금지 범위임. ⇒ 발음 배지 화면(A5-1·A5-2)은 이 회차의 사거리 밖임.

- AC#1 ✅ 시범이 돌아왔음: pronunciation 프레임 1건 · audio 294건. 코치가 소리를 지목하고(「the "th" sound … is voiced」) 문장 전체를 다시 읽으며 따라 말하기를 요청했음(「Please repeat: I finished the report and shared the results with my team.」). DB 에 시도 1행(nova_tool · th_as_t · sound_check=matched)과 패턴 pronunciation_th_as_t 가 생겼음.
- AC#2 ⚠️ 체크하지 않음: outcome=incorrect 가 남았으나 spoken_form=null 이고 resolved_at 이 세션 종료 시각과 같음 ⇒ 재발화 판정이 아니라 resolve_dangling 의 종료 수렴임. 학습자의 재발화는 실제로 있었음(utterances seq 2). 둘째 pronunciation 프레임은 오지 않았음. ⛔ 원인 미확정 — ws_session.py 가 코치의 턴을 기다리지 않고 재발화를 흘리는 형태라 배제하지 못함. 실물 3회 상한을 다 썼으므로 재현하지 않고 넘겼음. ⇒ 결함 TASK-236.
- AC#3 ❌ 체크하지 않음: 한글 전사(아이피니시트더리포트엔쉐어드더리절치위드마이팀)와 코치의 되물음이 둘 다 실제로 일어났는데 signal_source in ('korean_transcript','agent_reprompt') 는 0행. 두 writer 가 코드에 0곳이고 각각 결정 120(TASK-78.1)과 TASK-24 가 만들지 않기로 한 자리임. PRD R10-4 는 지금도 요구함 ⇒ 갈림을 사람이 정할 결함 TASK-237.
- AC#4 ✅ 끊기는 자리를 셋으로 갈라 적었음 — ⑴ 진입~tool 도착~패턴 연결은 끊기지 않음 ⑵ 재발화 판정에서 끊김(원인 미확정) ⑶ 보조 신호 writer 0곳(미구현이 아니라 지우기로 결정된 자리).

⛔ 본문의 알려진 상태가 낡았음: TASK-75 는 미해결이 아니라 Done(2026-09-10)이고 발음 전용 모드가 그 문제를 풀었음. 「발음 기능은 미동작」의 출처인 Phase 1 완료 선언문이 지금도 그 문장을 그대로 둠 ⇒ 결함 TASK-238.

결과: tests/agent/runs/2026-09-19-b6/result.md §7
<!-- SECTION:NOTES:END -->
