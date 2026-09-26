---
id: TASK-271
title: 튜터 발화가 길어 학습자 발화 기회를 놓침
status: Done
assignee: []
created_date: '2026-09-26 03:08'
updated_date: '2026-09-26 03:17'
labels: []
dependencies: []
ordinal: 335000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 신고 2026-09-26: 튜터 설명이 길고 교정도 장황해 학습자가 말할 틈 없이 튜터만 연달아 말함. 짧게 묻고 단순하게 교정한 뒤 다음 턴으로 넘어가야 함
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 방금 세션 기록으로 원인을 확정함
- [x] #2 재현 테스트를 먼저 세우고 수정함
- [x] #3 백엔드 게이트 통과
- [x] #4 리뷰 반영 후 커밋함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
원인(세션 93fb0361 · 2026-09-26 11:58 KST): ① 발음 tool 결과({status: recorded}, TASK-269) 뒤 Nova 가 턴을 이어 말해 이미 한 말을 또 함 — 긴 코치 턴(5·6·8·14·16번)이 전부 tool 호출 직후. 코치 평균 길이 11:28 세션 111자 → 11:58 세션 252자. TASK-61.5 의 제어 tool 중복 발화와 같은 기전. ② 규칙 1·4 가 길이·교정 형태를 느슨하게 둬 문법 설명·낱말 드릴로 번짐. ③ 발음 판정 3건 모두 correct — 관사 문법 초점과 소리 키 an_as_a 가 겹쳐 없는 오류를 교정함(이번 범위 밖). 수정: _PRONUNCIATION_RECEIPT(되풀이 금지 · 요청 전이면 한 문장으로 요청 · 대기) · 규칙 1 에 under 20 words · 규칙 4 를 한 문장 recast 로. 게이트: pytest 1437 passed · ruff 0 · ruff format 331 files · ty 0. 미확인: 실물 Nova 가 영수증 문구를 따르는지는 다음 실사용 대화에서 확인해야 함.

리뷰(opus) CRITICAL 0 · HIGH 2 반영: ① 규칙 4 의 낱말 드릴 금지가 _SOUND_INSTRUCTION(낱말 재발화 요구)과 충돌 → 금지·한 문장 요구를 뺌(규칙 9 의 3단계와도 충돌했음 · MEDIUM) ② 판정 호출에도 같은 영수증을 주면 맞게 말한 뒤 또 따라 말하게 함 → _PENDING_RECEIPT / _JUDGEMENT_RECEIPT 로 가름 · 판정 영수증 테스트 추가. 최종 게이트: pytest 1438 passed · ruff 0 · ruff format 331 files · ty 0.
<!-- SECTION:NOTES:END -->
