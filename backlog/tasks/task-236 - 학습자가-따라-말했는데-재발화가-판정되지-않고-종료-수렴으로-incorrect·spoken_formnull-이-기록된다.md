---
id: TASK-236
title: 학습자가 따라 말했는데 재발화가 판정되지 않고 종료 수렴으로 incorrect·spoken_form=null 이 기록된다
status: Done
assignee: []
created_date: '2026-09-19 07:41'
updated_date: '2026-09-19 08:48'
labels: []
dependencies: []
ordinal: 300000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치 B6 회차(2026-09-19 · HEAD a34a143)가 mode=pronunciation 실물 세션 1회에서 관측했음. ⛔ 원인은 미확정임 — 아래 「가리지 못한 것」을 먼저 읽을 것.

## 재현 (3단계)

1. 백엔드를 VOICE_ADAPTER=nova · WORKER_ENABLED=false 로 띄운다.
2. tests/harness/ws_session.py 의 run() 을 mode=pronunciation · wavs=[p2k.wav, p2a.wav] · silence_ms=12000 · timeout=120 으로 부른다. (첫 발화는 강한 한국어 억양판, 둘째는 같은 문장의 정확 발음판 — 「따라 말하기」 자리다.)
3. 그 세션의 pronunciation_attempts 를 읽는다.

## 기대

재발화(둘째 발화)를 코치가 듣고 판정해 outcome 이 correct 또는 incorrect 로 «판정에 의해» 닫히고 spoken_form 에 들린 형태가 남는다 (PRD R10-2 · AC10-2).

## 실제

- 시도 1행이 열렸음: signal_source=nova_tool · target_sound=th_as_t · sound_check=matched · target_form 은 시범 문장 전체. ⇒ 시범 경로 자체는 동작함.
- 그런데 outcome=incorrect · spoken_form=null · resolved_at 이 세션 종료 시각(2026-09-19 07:32:21.491263+00)과 같음.
- 둘째 pronunciation 프레임이 오지 않았음 (그 type 은 회차 전체에서 1건).
- 학습자의 재발화는 실제로 DB 에 있음 — utterances seq 2 「i finished the report and shared the results with my team」.
- services/pronunciation.py 의 resolve_dangling 이 「세션에 남은 pending 을 incorrect 로 수렴시키고 spoken_form 을 비운다 — 재발화를 실제로 못 들었으므로」 를 계약으로 적음. ⇒ 기록된 incorrect 는 「대답을 못 했다」로 수렴된 값이고, 학습자는 정확히 따라 말했는데 실패로 남았음.

## 가리지 못한 것 (원인 미확정)

ws_session.py 는 「보내면서 받지 않는다」가 계약이라 코치의 턴이 끝나기를 기다리지 않고 재발화를 흘림. 12초 간격을 뒀으나 코치의 시범이 그보다 길었는지 이 수단으로는 가릴 수 없음 — 모든 프레임의 t 가 32.728 로 뭉쳐 도착 시각을 잃음. 그러므로 이 결함은 「앱이 재발화를 판정하지 않는다」가 아니라 「이 수단으로는 재발화 판정을 관측하지 못했다」임. 실물 호출 승인 상한 3회를 이 배치가 다 썼으므로 재현을 돌리지 않고 넘김.
⚠️ 관측력은 증명됨 — 같은 수단이 첫 pronunciation 프레임을 1건 잡았음. 따라서 「둘째가 오지 않았다」 자체는 신뢰할 수 있고, 가릴 수 없는 것은 왜 오지 않았는지임.

## 증거

tests/agent/runs/2026-09-19-b6/result.md §7-2 · evidence/12-r3-pronunciation-frames.json · evidence/13-r3-post-db.txt · 드라이버 사본 evidence/driver-b6_pron.py

HEAD: a34a143
시나리오: TS-34 (AC#2) — 테스트 원장(tests/agent) 의 ID 임
관련: TASK-75 (Done · 규칙 9·11 이 발음을 막는 문제를 발음 전용 모드로 풀었음)

## 제안 (직접 고치지 않았음)

1. 먼저 «관측 수단»을 갖추는 것이 선행함 — 코치의 턴이 끝난 뒤에 재발화를 흘리는 드라이버가 필요함. p_app_path.py 가 --next-wait-ms·--quiet-ms 로 그 박자를 이미 갖고 있으나 「학습 시작」만 눌러 mode=pronunciation 진입을 만들지 못함. 화면의 「발음 집중」 버튼으로 진입하는 갈래를 그 드라이버에 더하는 안.
2. 그 수단으로 재현했는데도 둘째 tool 이 오지 않으면, 그때는 지시문 쪽(규칙 9·10 의 닫는 tool 규약)을 보는 것이 다음 자리임.
3. ⚠️ resolve_dangling 의 수렴 규칙 자체는 건드리지 않는 쪽을 권함 — 그것은 캡틴 결정(2026-08-28)이 unclear 를 뒤집어 세운 것임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 코치의 턴이 끝난 뒤에 재발화를 흘리는 수단으로 재현해, 재발화가 판정으로 닫히는지(spoken_form 이 채워지는지) 실물 왕복으로 확인했다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
코드로 좁힌 것 (2026-09-19 · TASK-240 · 호출 세션이 직접 읽었음).

1. 앱이 스스로 재발화를 판정할 수는 없음. record_attempt 는 Nova 의 tool 호출로만 열리고 닫힘 — 판정값이 오면 최신 pending 을 닫고, 오지 않으면 세션 종료의 resolve_dangling 이 수렴함. 그래서 「둘째 pronunciation 프레임이 오지 않았다」가 원인의 «자리»이고, 그 프레임이 왜 안 왔는지는 실물 상호작용에서만 가려짐.

2. ⛔ incorrect 수렴은 결함이 아님 — 캡틴 결정(2026-08-28)이 설계서 §3.2 의 unclear 를 «의도적으로 뒤집은» 계약임. resolve_dangling docstring 원문: 「학습자 관점에서 '대답을 못 한 것'은 못 한 것이다. 이후 학습도 그냥 틀림으로 본다 — '대답 안 함'만 따로 세는 규칙을 두지 않는다」. spoken_form 을 비우는 것도 같은 문단이 근거를 가짐(비우지 않으면 Nova 의 placeholder 가 학습자 발음으로 화면에 뜸). ⇒ unclear 로 바꾸는 것은 그 결정을 뒤집는 일이므로 이 태스크의 범위가 아님.

3. ⚠️ 그런데 그 결정의 «전제»와 구현의 «조건»이 어긋난 자리를 찾았음. 결정의 전제는 「대답을 못 했다」인데 수렴 조건은 「세션 끝에 outcome='pending' 이다」 하나임. 그 조건은 두 경우를 가르지 못함 — ⑴ 학습자가 정말 답하지 않음 ⑵ 학습자가 답했는데 코치가 그것을 재발화로 듣지 못함. 이 회차의 관측은 ⑵ 임(utterances seq 2 에 「i finished the report and shared the results with my team」이 실재함). ⇒ 결정이 값을 정할 때 ⑵ 를 보지 않았을 가능성이 있고, 그것은 제품 판단이라 사람이 정할 자리임. ⛔ 지금 고치지 않음.

4. 남은 관측: 둘째 프레임이 오지 않은 이유. 후보 둘 — ㉮ 드라이버가 코치의 턴 종료를 기다리지 않아 재발화가 시범 도중에 도착함(ws_session.py 는 「보내면서 받지 않는다」가 계약이고 모든 프레임의 t 가 뭉쳐 도착 시각을 잃음) ㉯ 타이밍이 맞아도 코치가 판정 tool 을 부르지 않음. ⇒ 코치의 턴 종료를 «기다리는» 드라이버로 실물 1회차를 돌려야 가려짐. 그 회차를 이 턴에 띄웠음.

---

## B7 회차 (2026-09-19 · HEAD 000530b) — 원인을 가렸음: ㉮ 임. ㉯ 는 반증됐음

⛔ **이 결함의 「가리지 못한 것」이 닫혔음.** 후보 넷 가운데 항목 4 가 세운 둘을 실물 1회차로 가렸음.

**결론: 앱은 재발화를 듣고 판정 tool 을 부름.** 코치의 턴이 끝난 것을 프레임으로 확인한 뒤에 재발화를 흘리면 둘째 pronunciation 프레임이 오고 DB 행이 판정값으로 닫힘. ⇒ ㉯(타이밍이 맞아도 코치가 판정 tool 을 부르지 않는다)는 반증됐고, B6 의 관측은 그 회차 드라이버가 만든 것임.

| 관측 | B6 | B7 |
|---|---|---|
| 둘째 pronunciation 프레임 | 오지 않았음 | 왔음 (t=21.881 · outcome=correct) |
| outcome | incorrect (종료 수렴) | correct (판정) |
| spoken_form | null | i finished the report and shared the results with my team |
| resolved_at 과 세션 종료 | 같음 | 1.839초 먼저 |

세션 5b370010-9ab1-429c-a3ff-27e30f334864 · 08:36:43~08:37:06 UTC · 실물 Nova 1회(llm_calls 38→39).

**수단**: tests/agent/runs/2026-09-19-b7/b7_turnwait.py — 보내기·받기를 동시에 돌아 프레임마다 도착 시각을 각자 기록하는 새 드라이버임(ws_session.py 를 고치지 않았음). 이 회차는 404 프레임에 서로 다른 t 값 132개이고, B6 은 311 프레임 전부가 t=32.728 한 값이었음.

**턴 종료 판정**: agent final 1건 이상 AND audio 프레임이 4000ms 동안 0건. 근거는 audio_gateway/nova.py:1070 이 stopReason=END_TURN 에서 _flush_pending_agent_text() 를 돌려 agent final 을 만드는 것임.

**타이밍이 맞았다는 근거** (㉯ 를 반증하려면 이것이 선행함): 코치 시범 음성 첫 audio t=6.357 · 마지막 audio t=13.342 · agent final t=13.348 · 턴 종료 판정 t=17.350 · 둘째 발화 송출 시작 t=17.350. 둘째 발화 «전» audio 344건 · «뒤» audio 44건(t=22.049 부터)이고 13.342~22.049 사이에 코치 음성이 0건임. ⇒ 둘째 발화는 시범 도중이 아니라 턴이 닫힌 뒤에 도착했음.

**관측력 증명** (§7-7): 같은 드라이버가 첫 pronunciation 프레임을 t=6.230 에 1건 잡았음. 그리고 실물을 돌리기 «전에» 가짜 서버(b7_fake_ws.py)로 둘째 프레임만 다르게 둔 두 판을 돌려 verdict 가 second_tool_arrived / second_tool_absent 로 갈리는 것을 보였음 — 이 판정에 판별력이 있음.

## ⚠️ 여전히 가르지 못한 것 — ㉮ «안»의 기전

가른 것은 「드라이버냐 앱이냐」까지임. B6 의 드라이버가 어느 성질로 그 결과를 만들었는지는 분리하지 않았음. 남은 후보 둘:
1. 재발화의 «도착 시점» — B6 은 코치의 턴 종료를 기다리지 않았음.
2. 소켓 «역압» — B6 은 30여 초 동안 소켓을 읽지 않았고 모든 프레임이 송출 직후 한꺼번에 읽혔음. 수신 버퍼가 차면 서버의 쓰기가 막혀 _pump_adapter_events 가 함께 멈춤. B6 에서 사용자의 둘째 final 이 코치의 첫 partial «보다 먼저» 온 순서가 그 정지와 맞아떨어짐(B7 은 그 순서가 반대였음).

이 회차의 드라이버가 둘을 «함께» 고쳤으므로 어느 하나만으로 재현되는지는 모름. ⚠️ 그 구별은 대상 앱의 결함과 무관함 — 둘 다 드라이버의 성질임. 실물 1회로 갈렸으므로 승인된 2회차를 돌리지 않았음.

## 이 회차가 닫지 «못한» 것 — 본문 항목 3

본문의 「결정의 전제(대답을 못 했다)와 수렴 조건(세션 끝에 pending 이다)이 어긋난 자리」는 그대로 남음. 이 회차는 그 구별이 실제로 문제가 되는 경우 ⑵(학습자가 답했는데 코치가 못 들음)가 «드라이버 때문»이었음을 보였을 뿐이고, 실사용에서 같은 구멍이 열리는지는 다른 물음임. 그것은 제품 판단이므로 사람이 정할 자리임 — ⛔ 이 회차는 고치지 않았음.

## 곁에서 나온 관측 — sound_check 가 비었음 (⛔ 새 결함으로 만들지 않았음 · 뿌리가 다름)

이 회차의 행은 sound_check 가 NULL 임(B6 은 matched 였음). 앱과 같은 창으로 코치 발화를 읽어 sound_check_verdict 를 직접 돌려 기전을 확인했음: 이 회차의 코치는 소리를 «여는 따옴표 다음에 공백» 을 넣어 인용했고 그런 자리가 12곳인데, _QUOTED_TOKEN_RE 는 따옴표 바로 뒤에 글자가 오기를 요구하므로 토큰을 하나도 못 뽑아 None 이 났음. 같은 글에서 그 공백만 없애면 matched 가 됨.
⚠️ 잘못된 배제를 내지는 않음(None 은 안전한 쪽임). 잃은 것은 결정 82 가 세운 검증 신호 자체임 — 어긋남을 잡을 기회가 그 회차에서 0이 됨. ⚠️ 모델의 인용 문체에 달렸으므로 간헐임.
제안: 그 정규식이 여는 따옴표 뒤 공백을 건너뛰게 하는 안. 별건 결함으로 올릴지는 호출 세션이 정할 자리임.

## 증거

tests/agent/runs/2026-09-19-b7/result.md · evidence/07-real-round-frames.json(프레임 전부·시각 각자) · evidence/08-post-real-round-db.txt · evidence/02-fake-emit-second.json·03-fake-no-second.json(판별력) · evidence/09-sound-check-probe.txt · evidence/11-post-teardown-counters.txt · 드라이버 b7_turnwait.py · 가짜 서버 b7_fake_ws.py
HEAD: 000530b · 시나리오: TS-34 (AC#2 — 이 회차가 체크했음)

⛔ 앱 결함이 아니었음 — 관측이 만든 것임 (2026-09-19 · 회차 B7 · 호출 세션이 증거를 직접 열어 확인).

원인 판정: 후보 ㉮(드라이버 탓)이고 ㉯(앱·프롬프트 탓)는 반증됐음.

내가 직접 확인한 것 — tests/agent/runs/2026-09-19-b7/evidence/07-real-round-frames.json 을 열어 pronunciation 프레임을 셌음:
- 프레임 2건임. t=6.230 (phase=await_first_tool · outcome=pending) · t=21.881 (phase=await_second_tool · outcome=correct).
⇒ 코치의 턴이 끝난 것을 «프레임으로» 확인한 뒤 재발화를 흘리면 앱이 그것을 판정으로 닫음.

DB 근거(회차 문서 §4-4): outcome=correct · spoken_form="i finished the report and shared the results with my team" · resolved_at 08:37:05.031683Z 이고 세션 ended_at 08:37:06.870254Z ⇒ 판정이 종료보다 1.839초 «먼저» 났음. B6 은 두 시각이 같아 resolve_dangling 의 수렴이었음 — 그것이 판정과 수렴을 가르는 자리임.

⇒ 앱은 재발화를 듣고 판정 tool 을 부르며 spoken_form 을 함께 남김. B6 의 관측은 그 회차 드라이버가 만든 것임. 앱을 고치지 않음.

⚠️ 남은 것 하나(앱과 무관): ㉮ 안의 어느 성질이 B6 을 깨뜨렸는지는 가르지 못했음. 후보 둘 — 재발화의 도착 시점 / 소켓 역압(B6 은 30여 초 소켓을 읽지 않았고 모든 프레임이 t=32.728 에 한꺼번에 읽혔음. 그러면 서버 쓰기가 막혀 _pump_adapter_events 가 함께 멈춤. B6 에서 사용자의 둘째 final 이 코치의 첫 partial «보다 먼저» 온 순서가 그 정지와 맞아떨어지고, B7 은 순서가 반대였음). 둘 다 드라이버의 성질이라 대상 앱의 결함과 무관하고, 가르려면 실물 1회가 더 필요하므로 돌리지 않았음.

⚠️ 앞서 노트에 적은 항목 3(「결정의 전제와 구현의 조건이 어긋난다」)은 그대로 살아 있음 — resolve_dangling 의 수렴 조건이 「세션 끝에 pending」 하나라서 「답하지 않음」과 「답했는데 못 들음」을 가르지 못함. 다만 이 회차가 「정상 경로에서는 판정이 먼저 닫는다」를 보였으므로 그 어긋남이 실제로 발현하는 조건은 «관측·네트워크 이상»이고 평시 경로가 아님. 제품 판단이라 고치지 않고 그대로 둠.
<!-- SECTION:NOTES:END -->
