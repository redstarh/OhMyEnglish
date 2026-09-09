---
id: TASK-69
title: '문서 정정: P계층 판정 서술 셋이 원자료와 어긋난다 — 「능력은 있고 지시만 없다」 추론과 상태 열'
status: To Do
assignee: []
created_date: '2026-09-09 14:22'
labels: []
dependencies: []
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
test Agent 회차가 셋을 찾았고 팀리드가 원자료로 확인했다. ① 5차수 통제 대조가 잰 것은 「프롬프트가 tool 호출을 강제하는가」이고 「모델이 발음 오류를 감지하는가」가 아니다 — p2a(정확 발음 · ASR 이 원문과 일치)에도 스파이크 프롬프트가 toolUse 1건을 냈다. 즉 「프롬프트가 원인」 결론은 유지되나 거기서 「능력은 있고 지시만 없다」로 넘어가는 추론은 이 관측이 지지하지 않는다. 걸리는 자리 둘: runs/2026-09-09-run-5.md 「이 차수의 결정적 결과」 절 · docs/design/2026-09-08-pronunciation-review-cycle-design.md §9 약점 1 의 2026-09-09 갱신 블록. ② scenarios-P-pronunciation.md 의 상태 열이 정본이 아니게 됐다 — P9~P12 가 「미실행」인 채 5차수가 P10·P12 를 닫았다. ③ run-5.md 의 「p2 쌍 실물 완료」가 원자료와 어긋난다 — 팀리드가 tests/harness/runs/2026-09-09-run-5-live/transcripts-repr-9664afd1.txt 를 직접 읽어 확인했다. 그 세션이 흘린 것은 p1m·p1k·p2m 셋이고 p2a·p2k 는 앱 경로 미실행이다. ⚠️ 그 파일이 TASK-65 의 근거도 함께 준다 — seq=3 이 p1k 인데 앱 경로에서 영어로 전사됐다(스파이크에서는 한글이다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ①의 추론을 두 자리에서 정정한다 — 무엇을 쟀고 무엇을 재지 않았는지로 바꾼다. 결론을 지우지 말고 근거의 범위를 좁힌다
- [ ] #2 ②의 상태 열을 정본이 아니라고 표시하거나 갱신한다 — 개수를 세는 서술로 바꾸지 않는다(H-O)
- [ ] #3 ③을 원자료에 맞게 고친다 — p2a·p2k 가 앱 경로 미실행임을 적고 그것이 이월 항목임을 P계층 정본과 맞춘다
- [ ] #4 ⛔ 본문을 고친 커밋에서 그것을 설명하는 문장도 함께 고친다 — 이 리포의 지배 실패 모드다
<!-- AC:END -->
