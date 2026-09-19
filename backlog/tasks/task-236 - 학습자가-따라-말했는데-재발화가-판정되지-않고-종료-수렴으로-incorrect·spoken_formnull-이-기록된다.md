---
id: TASK-236
title: 학습자가 따라 말했는데 재발화가 판정되지 않고 종료 수렴으로 incorrect·spoken_form=null 이 기록된다
status: To Do
assignee: []
created_date: '2026-09-19 07:41'
updated_date: '2026-09-19 08:23'
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
- [ ] #1 코치의 턴이 끝난 뒤에 재발화를 흘리는 수단으로 재현해, 재발화가 판정으로 닫히는지(spoken_form 이 채워지는지) 실물 왕복으로 확인했다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
코드로 좁힌 것 (2026-09-19 · TASK-240 · 호출 세션이 직접 읽었음).

1. 앱이 스스로 재발화를 판정할 수는 없음. record_attempt 는 Nova 의 tool 호출로만 열리고 닫힘 — 판정값이 오면 최신 pending 을 닫고, 오지 않으면 세션 종료의 resolve_dangling 이 수렴함. 그래서 「둘째 pronunciation 프레임이 오지 않았다」가 원인의 «자리»이고, 그 프레임이 왜 안 왔는지는 실물 상호작용에서만 가려짐.

2. ⛔ incorrect 수렴은 결함이 아님 — 캡틴 결정(2026-08-28)이 설계서 §3.2 의 unclear 를 «의도적으로 뒤집은» 계약임. resolve_dangling docstring 원문: 「학습자 관점에서 '대답을 못 한 것'은 못 한 것이다. 이후 학습도 그냥 틀림으로 본다 — '대답 안 함'만 따로 세는 규칙을 두지 않는다」. spoken_form 을 비우는 것도 같은 문단이 근거를 가짐(비우지 않으면 Nova 의 placeholder 가 학습자 발음으로 화면에 뜸). ⇒ unclear 로 바꾸는 것은 그 결정을 뒤집는 일이므로 이 태스크의 범위가 아님.

3. ⚠️ 그런데 그 결정의 «전제»와 구현의 «조건»이 어긋난 자리를 찾았음. 결정의 전제는 「대답을 못 했다」인데 수렴 조건은 「세션 끝에 outcome='pending' 이다」 하나임. 그 조건은 두 경우를 가르지 못함 — ⑴ 학습자가 정말 답하지 않음 ⑵ 학습자가 답했는데 코치가 그것을 재발화로 듣지 못함. 이 회차의 관측은 ⑵ 임(utterances seq 2 에 「i finished the report and shared the results with my team」이 실재함). ⇒ 결정이 값을 정할 때 ⑵ 를 보지 않았을 가능성이 있고, 그것은 제품 판단이라 사람이 정할 자리임. ⛔ 지금 고치지 않음.

4. 남은 관측: 둘째 프레임이 오지 않은 이유. 후보 둘 — ㉮ 드라이버가 코치의 턴 종료를 기다리지 않아 재발화가 시범 도중에 도착함(ws_session.py 는 「보내면서 받지 않는다」가 계약이고 모든 프레임의 t 가 뭉쳐 도착 시각을 잃음) ㉯ 타이밍이 맞아도 코치가 판정 tool 을 부르지 않음. ⇒ 코치의 턴 종료를 «기다리는» 드라이버로 실물 1회차를 돌려야 가려짐. 그 회차를 이 턴에 띄웠음.
<!-- SECTION:NOTES:END -->
