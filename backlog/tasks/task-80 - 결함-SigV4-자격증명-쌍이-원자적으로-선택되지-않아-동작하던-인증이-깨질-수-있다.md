---
id: TASK-80
title: '결함: SigV4 자격증명 쌍이 원자적으로 선택되지 않아 동작하던 인증이 깨질 수 있다'
status: Done
assignee: []
created_date: '2026-09-09 22:55'
updated_date: '2026-09-10 00:34'
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
- [x] #1 access key 와 secret key 를 쌍으로 선택한다 — 한쪽만 있는 상태를 완전한 SigV4 로 판단하지 않는다
- [x] #2 부분 자격증명에서 bearer 를 제거하지 않는다 — 동작하던 인증을 깨지 않는 것이 기준이다
- [x] #3 부분 자격증명 시나리오를 테스트로 고정하고 무력화에서 FAIL 하는 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 구현 완료 — 쌍을 한 출처에서만 가져오게 고쳤다.

무엇을 바꿨는가: 키마다 setdefault 하던 루프를 없애고, 환경에 SigV4 값이 하나도 없을 때만 .env 의 «완전한 쌍»을 올린다. 환경에 절반이라도 있으면 환경이 정본이고 .env 에서 아무것도 빌려 오지 않는다. 그러면 섞인 쌍이 만들어지지 않으므로 missing_sigv4 가 부분 상태를 정확히 부분으로 판정하고 bearer 를 지우지 않는다(AC#1·AC#2).

⚠️ AC 범위를 한 걸음 넘긴 것을 밝힌다 — 세션 토큰도 쌍과 같은 출처에서만 오게 했다. AC 는 access·secret 만 이름을 들지만 임시 자격증명은 셋이 한 세트라 셸의 영구 키 쌍에 .env 의 임시 토큰이 붙으면 서명이 거부된다. 같은 함수의 같은 기전이고 AC#2 의 기준(동작하던 인증을 깨지 않는다)에 그대로 걸려서 함께 닫았다. 환경에 남아 있는 잔여 토큰은 건드리지 않는다 — 환경을 지우는 것은 이 함수의 몫이 아니다.

AC#3 무력화 확인 — 두 방향을 각각 잡았다.
⑴ any 를 all 로 바꾸면(부분 상태에서 다시 빌려 옴) 부분 자격증명 테스트 2건이 FAIL 한다. 직접 관측했다.
⑵ 세션 토큰 주입을 쌍 블록 «밖»으로 옮기면 세션 토큰 테스트 1건이 FAIL 한다. 직접 관측했다.
⛔ 두 무력화가 서로 다른 테스트를 잡는다 — 하나만 확인하면 다른 쪽 방어가 무보호로 남는다.

⚠️ 두 방향을 모두 테스트한 이유: 구현이 AWS_ACCESS_KEY_ID 의 존재만 보고 분기하면 secret 만 있는 케이스가 조용히 통과한다.

게이트: pytest 895 passed · ruff check exit 0 · format 34 files already formatted · ty check 통과 · 게이트 밖 ruff 0건.
<!-- SECTION:NOTES:END -->
