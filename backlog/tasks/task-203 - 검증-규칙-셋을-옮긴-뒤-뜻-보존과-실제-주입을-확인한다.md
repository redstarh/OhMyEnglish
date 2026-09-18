---
id: TASK-203
title: '검증: 규칙 셋을 옮긴 뒤 뜻 보존과 실제 주입을 확인한다'
status: To Do
assignee: []
created_date: '2026-09-18 05:11'
labels: []
dependencies:
  - TASK-202
ordinal: 264000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-199 판단 §5 가 요구한 검증 단계. 번역은 게이트로 검증할 수 없으므로 항목 수 대조와 실제 주입 관측이 유일한 수단이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 상시 로드 줄 수·문자 수를 다시 세어 702줄 대비 줄어든 값을 적는다
- [ ] #2 새 세션에서 세 문서가 실제로 주입되는 것을 관측한다
- [ ] #3 문서끼리 가리키는 자리 전부가 유효함을 grep 으로 확인한다
- [ ] #4 뒤집힌 결정의 경위와 사용자 지시 원문이 유실되지 않았음을 대조한다
<!-- AC:END -->
