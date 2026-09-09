---
id: TASK-80
title: '결함: SigV4 자격증명 쌍이 원자적으로 선택되지 않아 동작하던 인증이 깨질 수 있다'
status: To Do
assignee: []
created_date: '2026-09-09 22:55'
labels: []
dependencies: []
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-10 TASK-70 재리뷰가 P2 로 지적했음. 근거: app/backend/app/config.py 의 prepare_bedrock_credentials 부근 setdefault 경로.

시나리오: 환경에 AWS_ACCESS_KEY_ID 만 남아 있고 설정 파일에 **다른** 키 쌍과 bearer 가 있는 경우. setdefault 가 환경의 access key 를 존중하면서 설정의 secret key 를 채워 **섞인 쌍**을 만들고, 그것을 완전한 SigV4 로 판단해 **bearer 까지 프로세스 환경에서 제거함.** 결과적으로 동작하던 인증이 잘못된 서명으로 바뀜.

⚠️ AC F5 가 「bearer↔SigV4 전환이 설정 교체」를 요구하는 자리임. 지금 코드가 그 전환을 한 곳에 격리한 것은 맞으나 **부분 자격증명 상태**를 다루지 않음.

⚠️ 리뷰가 함께 지적한 것: 기존 테스트는 환경에 두 SigV4 값을 **모두** 넣는 경우만 다뤄 이 부분 자격증명 시나리오를 잡지 못함.

⛔ 결정 41 이 자격증명 회전을 면제했으나 이것은 회전이 아니라 **선택 로직의 결함**이라 그 면제에 걸리지 않음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 access key 와 secret key 를 쌍으로 선택한다 — 한쪽만 있는 상태를 완전한 SigV4 로 판단하지 않는다
- [ ] #2 부분 자격증명에서 bearer 를 제거하지 않는다 — 동작하던 인증을 깨지 않는 것이 기준이다
- [ ] #3 부분 자격증명 시나리오를 테스트로 고정하고 무력화에서 FAIL 하는 것을 확인한다
<!-- AC:END -->
