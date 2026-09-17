---
id: TASK-174
title: '미확인 ③: 실물 음성 어댑터로 쉐도잉 왕복을 확인한다'
status: To Do
assignee: []
created_date: '2026-09-17 22:06'
labels: []
dependencies: []
ordinal: 235000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
지금 백엔드가 VOICE_ADAPTER=stub 이라 실물 음성 경로가 이 세션에서 검증되지 않았다. 영상에서 담은 문장으로 쉐도잉을 열어 실물 왕복이 되는지 본다. 이전 절차는 handoff/backup/2026-09-18/HANDOFF-0328.md 85행이 가리키는 형태다 — 다른 포트에 VOICE_ADAPTER=nova 로 띄운다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실물 어댑터의 기동 형태와 필요 자격증명을 확인하고 :8002 를 건드리지 않는 별 포트로 띄움
- [ ] #2 영상에서 담은 문장으로 쉐도잉 한 바퀴를 실물로 돌려 관측함
- [ ] #3 관측 전후 pronunciation_attempts·analysis_jobs 수를 적음
<!-- AC:END -->
