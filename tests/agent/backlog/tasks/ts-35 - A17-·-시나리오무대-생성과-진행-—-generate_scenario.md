---
id: TS-35
title: A17 · 시나리오(무대) 생성과 진행 — generate_scenario
status: Done
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 06:35'
labels: []
dependencies: []
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A17. 대상: job generate_scenario · services/scenario_generator.py·scenario_progress.py·scenario_rotation.py · WS mode=scenario_intake. 근거: 설계서 2026-09-12-scenario-generator-design.md · 2026-09-12-scenario-rotation-70-30-design.md. ⚠️ 자동 테스트는 unit 5파일뿐이고 WS 종단 커버리지는 미확정임. ⛔ 무대 제목의 언어 같은 제품 판단은 판정하지 않고 결함에 적음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 시나리오가 생성돼 세션에 붙음
- [x] #2 회전 비율 70대 30 규약이 성립함
- [x] #3 시나리오 진행 상태가 턴을 넘어 이어짐
- [x] #4 mode=scenario_intake 진입이 성립함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
배치 B4 회차(2026-09-19 · runs/2026-09-19-b4/) 에서 AC 4건 전건을 쟀음. 증거: evidence/TS-35-scenario.json · TS-35-rotation-app-path.json · TS-35-ws-intake.json · TS-35-candidate-pool-boundary.json.

- AC#1: enqueue → claim → process_scenario 가 실제로 돌아 job 이 done 이고 learning_scenarios 에 source='generated' 1행이 생겼음. level 은 모델이 아니라 앱이 넣은 값(B1)임. 그 사용자의 다음 세션이 그 무대로 열렸고 scenario_pick='new' 였음(결정 80).
- AC#2: 순수 함수 30회에서 신규 9 · 반복 21 · 창마다 3 — 설계서 2026-09-12-scenario-rotation-70-30-design.md 의 기대값과 일치함. 앱 경로 12회(A2 사용자)는 NNNRRRRRRRRN 이고 서로 다른 무대 4종이었음.
- AC#3: 턴을 넘겨 load_session_scenario 를 두 번 읽어도 같은 무대였고, load_scenario_progress 가 sessions 1 · new_picks 1 · last_studied_on 2026-09-19(사용자 타임존 기준)를 냈음. 미학습 무대도 목록에 나왔음.
- AC#4: 실제 소켓 ?mode=scenario_intake 로 붙어 session_started 를 받고, 세션 행 mode 가 scenario_intake 로 적혔으며 종료가 generate_scenario job 을 걸었음(job 4건). 픽스처 사용자의 세션 집합은 내 세션 1행을 지워 27→27 로 복원했음.

⛔ 결함 1건을 별도로 등록했음 — TASK-232(수준이 올라간 학습자의 무대 후보가 그 수준의 1행으로 좁혀져 같은 무대만 반복됨). 회전 규칙 자체는 어긋나지 않아 AC#2 는 통과로 두었음.
⚠️ AC#1 의 모델 호출은 스텁임 — 실물 Claude 응답이 파서 계약(제목 언어·category 값역)을 지키는지는 이 회차가 재지 않았고 유료 호출 승인이 필요한 잔여 항목임.
<!-- SECTION:NOTES:END -->
