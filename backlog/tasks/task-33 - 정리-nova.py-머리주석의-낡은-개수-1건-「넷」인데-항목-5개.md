---
id: TASK-33
title: '정리: nova.py 머리주석의 낡은 개수 1건 (「넷」인데 항목 5개)'
status: To Do
assignee: []
created_date: '2026-09-07 15:34'
updated_date: '2026-09-07 15:41'
labels: []
dependencies: []
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
app/backend/app/audio_gateway/nova.py:5 가 '문서만 읽고는 알 수 없었던 것 넷:' 인데 아래 번호 목록이 5개다(5번 'tool use가 동작한다'). Batch B 구현자가 발견해 판정을 요청했고, 팀리드가 BASE(a1d6ce8) 에서 5번 항목의 존재와 이 배치가 머리주석을 건드리지 않은 것(첫 hunk 가 :51 부터)을 직접 확인했다 — 이 배치가 만든 것이 아니라 b31227a(Nova 발음 tool 연결) 가 항목을 더하면서 개수를 안 고친 것이다. 규약(Surgical Changes: 요청 범위 밖은 언급만) 에 따라 Batch B 에서 고치지 않고 등록한다. 같은 부류(본문 고치고 그것을 설명하는 개수 문장 안 고침)이고 이 리포의 지배 실패 모드다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 nova.py 머리주석의 개수 서술을 고친다 — 숫자를 세지 않는 서술로 바꾸는 것도 정당한 선택이다(Batch B 의 F-5 픽스가 그 선례이고 근거를 함께 남겼다)
- [ ] #2 구현자가 이미 훑어 정확함을 확인한 4건(factory.py '넷 다' · ws.py '네 개' · PreparedPlan '둘' · 축 목록 '둘')은 다시 세지 않는다 — 보고서 batch-B-report.md 의 표가 그 근거다
- [ ] #3 nova.py 의 F-5 수정문 안의 낡은 개수도 함께 고친다 — '이 배치가 축을 셋 더하면서(무대·질문↔규칙2·질문↔규칙3·드릴반복·우선순위)' 에서 괄호가 5개를 열거하고 git diff a1d6ce8..HEAD 로 확인한 실제 추가 축도 5개다. 개수가 왜 낡는지 설명하는 문장 안에 낡은 개수가 있다(라운드 2 재리뷰가 부수로 지적 · Important 아님 — 역사 서술이라 현재 동작을 오인시키지 않는다)
<!-- AC:END -->
