---
id: TS-34
title: A16 · 발음 코칭 — mode=pronunciation 실시간 판정
status: Done
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 11:21'
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
- [x] #2 따라 말한 결과가 성공·실패·판정 불가 가운데 하나로 기록됨
- [x] #3 미동작이면 무엇이 어디서 끊기는지 증거와 함께 적음 (TASK-75 와 이어 줌)
- [x] #4 보조 신호 둘(한글 전사·되물음)로 pronunciation_attempts 에 행이 생기지 않고 분석도 실패하지 않음 — PRD v1.5 §16 이 그 기록 요구를 철회했음 (AC16-1·AC16-2)
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

## B7 회차 (2026-09-19 · HEAD 000530b) — AC#2 를 채웠음 (AC 3/4 · Blocked 유지)

수단: tests/agent/runs/2026-09-19-b7/b7_turnwait.py (회차 디렉터리의 새 드라이버 · 대상 소스를 고치지 않았음). 보내기와 받기를 «동시에» 돌아 프레임마다 도착 시각을 각자 기록하고, 코치의 턴 종료를 프레임으로 판정한 뒤에 재발화를 흘림.
턴 종료 판정 규칙: agent final 프레임 1건 이상 AND audio 프레임이 4000ms 동안 0건. 근거는 audio_gateway/nova.py:1070 이 stopReason=END_TURN 에서 _flush_pending_agent_text() 를 돌려 agent final 을 만드는 것임 — 그 프레임이 Nova 의 턴 경계가 WS 로 새어 나온 자리임.
판별력을 먼저 증명했음: 가짜 서버(b7_fake_ws.py)로 둘째 pronunciation 프레임만 다르게 둔 두 판을 돌려 verdict 가 second_tool_arrived / second_tool_absent 로 갈리는 것을 보였음. 스텁 어댑터로는 세션이 41ms 만에 닫혀 이 측정이 성립하지 않음(실측).

세션 5b370010-9ab1-429c-a3ff-27e30f334864 · mode=pronunciation · 08:36:43~08:37:06 UTC · 실물 Nova 1회.

- AC#2 ✅ 채웠음: 둘째 pronunciation 프레임이 t=21.881 에 outcome=correct 로 왔고, DB 행이 outcome=correct · spoken_form 채워짐 · resolved_at 이 세션 종료보다 1.839초 «먼저» 로 닫혔음. ⇒ resolve_dangling 의 종료 수렴이 아니라 판정임. 타이밍 근거: 코치의 마지막 audio t=13.342 · agent final t=13.348 · 둘째 발화 송출 시작 t=17.350(음성 정지 4.008초 뒤) · 13.342~22.049 사이 코치 음성 0건. 둘째 발화 뒤 상한 75초로 기다렸고 실제 0.27초에 왔음.
- AC#3 ❌ 여전히 미충족 — 보조 신호 writer 가 코드에 0곳임(결함 TASK-237 이 사람의 결정으로 올려 둠). 이 회차의 사거리 밖임.
- 부분 확인이므로 Done 이 아니고 Blocked 로 둠.

곁에서 나온 관측 둘 (⛔ 새 결함으로 올리지 않았음):
1. sound_check 가 NULL 로 남았음 — 코치가 소리를 12번 인용했는데도임. 이 회차의 코치는 여는 따옴표 뒤에 공백을 넣어 인용했고(«따옴표 공백 th 따옴표» 형태) _QUOTED_TOKEN_RE 가 토큰을 하나도 못 뽑아 sound_check_verdict 가 None 을 냈음. 같은 글에서 그 공백만 없애면 matched 가 됨(evidence/09-sound-check-probe.txt 에 세 입력의 판정이 있음). 잘못된 배제를 내지는 않으나 결정 82 가 세운 검증 신호가 그 회차에서 0이 됨. B6 은 matched 였으므로 간헐임.
2. interrupted 프레임 1건 — 코치가 4.35초 조용해진 뒤에 시작한 발화가 barge-in 으로 표시됐음. 판정은 정상으로 났으므로 결함이 아니고, 배지·화면 영역(A5-1·A5-2)을 볼 회차의 재료임.

결과: tests/agent/runs/2026-09-19-b7/result.md

AC#3 을 바꿨음 (2026-09-19 · TASK-246 · 사용자 결정). 원래 문면은 PRD R10-4·AC10-3 을 따라 보조 신호 둘의 기록을 요구했으나, 사용자가 그 요구를 철회하는 쪽을 골랐음 — 결정 120 과 TASK-24 를 정본으로 인정함. PRD 가 v1.5 로 개정돼 §16 이 그 근거를 담고, 결정 기록은 docs/design/2026-09-19-decision-r10-4-auxiliary-signals-withdrawn.md 임. 새 AC 는 §16.4 의 AC16-1·AC16-2 를 가리킴. 이 턴에 직접 확인한 것: 리포에서 korean_transcript·agent_reprompt 를 쓰는 코드가 값역 선언(models/pronunciation.py:42)과 주석(services/review.py:256)뿐이고 writer 는 0곳임. 과거 행은 korean_transcript 3건이 실재해 값역을 좁히지 않은 근거가 성립함(nova_tool 4건). 회차 B6 이 두 조건을 실제로 만들었는데 신호 행이 0건이었던 그 관측이 지금은 «요구대로 동작한 것»임.
<!-- SECTION:NOTES:END -->
