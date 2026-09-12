---
id: TASK-128
title: '이 축은 지시문 밖으로 나간다: 계획이 준 소리가 기록«과 코칭»을 끌어당긴다 — 더하기·덜기 두 방향이 모두 반증됐다'
status: In Progress
assignee: []
created_date: '2026-09-12 03:36'
updated_date: '2026-09-12 03:51'
labels: []
dependencies: []
ordinal: 133000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST. 두 회차가 지시문의 양쪽 방향을 다 반증했다.
① 더하기 — 조건절(«코칭한 소리가 계획의 그 소리면 그 키를, 다르면 실제로 코칭한 소리의 키를»): 3/3 실패 (runs/2026-09-12-task120-absent-planted-sound.md).
② 덜기 — 강제와 조건절을 «모두 제거»(사용자 결정 70): 3/3 실패 (runs/2026-09-12-task123-118-subtract-key-forcing.md ARM-B). 소리 줄에 target_sound 언급이 0 인데도 계획의 키 f_as_p 가 세 번 실렸다.
⇒ ⛔ 「지시문으로는 못 막는다」를 «이제» 말할 수 있다. 앞 회차는 더하는 방향만 반증했으므로 단정을 보류했고 이 회차가 나머지 절반을 채웠다.

⛔ 그리고 더 강한 것을 봤다 — 계획의 소리가 «코칭 내용까지» 끌어당긴다. ARM-B 의 코치는 arrive 의 /v/ 를 골라 «can sometimes sound a bit like f for some speakers» 로 설명했다. 심은 키가 f_as_p 인 것에 발화를 맞춰 간 모양이다. ⚠️ 표본 3 이고 pq13 의 /r/ 오류와 arrive 의 /v/ 가 같은 낱말에 있어 「계획이 끌었다」와 「그 낱말이 원래 눈에 띈다」를 가르지 못한다 — 단정하지 않는다.
⚠️ 결정 70 이 예고한 대가(같은 소리가 여러 키로 흩어짐)는 «발생하지 않았다» — 서로 다른 키가 팔마다 1개다. 흩어지지 않은 이유가 모델이 여전히 계획 키만 쓴다는 것이므로 그것은 좋은 소식이 아니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ⛔ 지시문 수정 안을 더 내지 않는다 — 두 방향이 반증됐으므로 이 태스크는 지시문 «밖»의 안만 다룬다
- [x] #2 안 A(기록 경로): 앱이 계획의 소리를 payload 에 주지 않거나 판정 시점에 고치는 자리가 있는지 코드로 본다. 무엇을 바꿀 수 있는지 file:line 으로 적는다. ⛔ 새 추상화를 만들지 않는다
- [x] #3 안 B(제품 요구사항): 계획이 준 소리를 「오늘 다룰 소리」가 아니라 「후보」로 내려받는 안을 적는다 — 그러면 코치가 실제 오류를 고르고 기록도 그것을 따른다. ⛔ 제품 판단이라 사용자 결정을 받는다
- [ ] #4 결정을 받은 뒤 판별 조건(pq13 + 오디오에 없는 소리를 심음)으로 재고 그 결과로 TASK-116 을 닫거나 남긴다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST — AC#2(기록 경로) 를 코드로 봤음. ⛔ Nova 를 쓰지 않았음.

결론: 「앱이 payload 를 고칠 자리」를 찾는 것이 문제의 형태가 아니었음. **고리가 닫혀 있음** — 복습 시계가 자기 자신을 먹임. 일곱 자리를 순서대로 적음(전부 직접 열어 확인).

1. services/review.py:255 — next_review_at 의 «유일한 writer» 임(그 모듈 머리주석이 그것을 명시함). 예정일이 오면 그 패턴이 due 가 됨.
2. services/plan.py:319-321 — due 패턴을 계획 프롬프트의 복습 목록에 실음. 발음이면 «target sound» 로 소리 키를 그대로 냄(TASK-44).
3. app/api/ws.py:158 _pronunciation_sound_or_none — 계획의 «발음 초점» 을 오늘의 소리로 고름(출처 순서 ① 계획 ② 놓친 소리 목록).
4. audio_gateway/nova.py _SOUND_INSTRUCTION — 그 키를 프롬프트에 이름으로 실음(전용 모드는 build_pronunciation_prompt).
5. 모델이 그 키를 target_sound 에 그대로 실음 — 실측 3/3 x2(강제판·조건판·제거판 전부). 지시문의 어느 방향으로도 바뀌지 않았음.
6. services/pronunciation.py record_attempt → link_pattern:475 — pattern_key 를 'pronunciation_' || target_sound 로 upsert·연결. ⛔ 임계값 없음(incorrect 1회에 만듦).
7. services/review.py:189 — sound_attempts 를 «btrim(a.target_sound) = p.sound» 로 매칭하고 signal_source='nova_tool' 만 봄 ⇒ 5번이 낸 키가 그대로 이력이 되어 1번이 다시 돎.

⇒ ⛔ **고리 안에 «독립 증거» 가 한 곳도 없음.** 계획이 소리 X 를 고르고, 모델이 X 를 되풀이하고, X 의 시계가 그 되풀이로 전진함. 그래서 「연습하지 않은 소리가 전진한다」(TASK-116)는 payload 결함이 아니라 «구조» 임.

앱이 쓸 수 있는 독립 신호가 있는가 — ⛔ 없음. 코치가 «무엇을» 코칭했는지는 agent 발화 전사문에만 있고 그것은 자연어임(예: «the s sound in process»). 소리 키(f_as_p)와 대조하려면 키→자연어 매핑이 필요하고 그 키는 models/pronunciation.py 규약상 «모델이 지어내는 값» 이라 값역이 고정되지 않음(link_pattern docstring 이 그 흩어짐을 이미 적었음). ⇒ 판정 시점 교정은 신뢰할 수 없음.

⛔ 그래서 코드만으로 닫히지 않음. AC#3(제품 요구사항)이 유일하게 남은 지렛대이고 그것은 사용자 결정 사안임 — 고리를 끊는 자리는 «2번·3번»(계획이 그 키를 모델에게 이름으로 주는 것)임.

2026-09-12 KST — AC#3 사용자 결정을 받았음: 결정 72(계획이 오늘의 소리를 «이름으로» 주지 않고 «후보» 로만 내려받는다). 대장 docs/ops/captain-instruction-register.md 에 기록했음 — 물은 주체는 이 세션(ohmyenglish-19)이고 AskUserQuestion 으로 직접 물었음. 기각한 둘도 근거와 함께 적었음.
사용자 판단의 요지: 「느슨하지만 진짜인 시계가 촘촘하지만 가짜인 시계보다 낫다」.
⛔ 감수한 대가 둘을 대장에 명시했음 — 간격 반복이 느슨해짐 · 전용 모드의 뜻이 「오늘의 소리」에서 「발음만 다룬다」로 바뀜.
<!-- SECTION:NOTES:END -->
