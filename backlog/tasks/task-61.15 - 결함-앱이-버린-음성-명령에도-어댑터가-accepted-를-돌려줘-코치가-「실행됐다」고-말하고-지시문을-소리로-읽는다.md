---
id: TASK-61.15
title: '결함: 앱이 버린 음성 명령에도 어댑터가 accepted 를 돌려줘 코치가 「실행됐다」고 말하고 지시문을 소리로 읽는다'
status: In Progress
assignee: []
created_date: '2026-09-15 23:17'
updated_date: '2026-09-15 23:28'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 190000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관측 정본은 runs/2026-09-16-task61-14-prompt-change-regression §3-② 다(팔 end-en). 표지가 인식되지 않아 앱이 end 명령을 버린 턴에서, 코치가 「the session has been ended as requested」라 말하고 이어서 지시문 문장(「The app closes the session only on 'confirmed', so never skip that second call.」)과 자기 내부 추론을 그대로 소리로 읽었다. 그 팔의 recv.session_ended 는 종료 클릭 전까지 0 이고 audio 1189 · final 20 이다. 기전은 코드로 확인했다: 어댑터가 번역기의 이벤트만 보고 {status:accepted} 를 Nova 로 돌려주는데(audio_gateway/nova.py _flush_tool_results) 실행 판정은 그 뒤 앱 층에서 하고(audio_gateway/session.py 표지 게이트 · 결정 104 D5) 표지가 없으면 버린다. nova.py 의 _remember_tool_use docstring 이 이 위험을 이미 적어 뒀지만 그 방어는 번역기가 버린 경로만 덮는다. ⚠️ 표본 1이므로 크기를 모른다. ⚠️ TASK-61.13 과 같은 부류(코치의 말과 앱 상태가 갈림)이고 결정 112 의 근거를 넓힌다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 모양의 크기를 실물 회차로 센다 — 표지가 버려진 턴에서 코치가 실행됐다고 말하는 비율
- [x] #2 지시문·내부 추론이 학습자에게 읽히는 것이 그 팔에서만 나는지, 표지 정상 팔에서도 나는지 가른다
- [ ] #3 고치는 자리를 정한다: accepted 를 앱의 실행 판정 뒤로 미룰지, 버린 턴에 실패를 돌려줄지
- [ ] #4 고치면 실물 회차로 관측한다
<!-- AC:END -->
