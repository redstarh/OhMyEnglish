---
id: TASK-288
title: '검증: 문법 코스 따라 하기의 실제 Nova 전사 경로 (격리 DB 유료 회차)'
status: Done
assignee: []
created_date: '2026-10-31 16:26'
updated_date: '2026-10-31 18:23'
labels: []
dependencies: []
ordinal: 353000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-287 이 남긴 미검증. stub 대신 실제 Nova 로 시도 POST → 전사 → 「내가 말한 문장」·낱말 판정 · course_attempts 집계 · 히트맵·이력 표를 확인함. 유료 회차는 dev DB 가 아닌 격리 DB 에서 돌림(TASK-191 의 근거) — 이번에는 새로 만든 ohmyenglish_course_paid 를 씀(ohmyenglish_worker 는 옛 스키마라 쓸 수 없었음, 노트 참고). 입력 음성은 합성 음성 파일을 Chrome 가짜 장치로 넣음. 물리 마이크 경로는 사람이 확인할 몫임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 격리 DB 를 쓰는 백엔드로 실제 Nova 시도가 전사를 돌려줌
- [x] #2 화면의 「내가 말한 문장」과 낱말 판정이 실제 전사로 나옴
- [x] #3 시도 집계가 DB·히트맵·이력 표에서 일치함
- [x] #4 dev DB 에 쓰기가 생기지 않았음을 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01
- 격리 DB: 기존 ohmyenglish_worker 는 마이그레이션 추적표가 없고 표 17개(옛 스키마)라 migrate.py 를 적용할 수 없었음. 지우면 TASK-255·256 유료 회차 기록이 사라지므로 두고, 새 격리 DB ohmyenglish_course_paid 를 만들어 migrate.py 로 033 까지 적용함(근거는 같음: dev DB 학습 데이터 오염 방지).
- 회차 b6(tests/agent/runs/2026-11-01-b6): 실제 전사 차단. Bedrock 이 AccessDeniedException 으로 거부함(시도 POST 2회 · 과금 없음). 브라우저 입력 경로는 정상(보낸 PCM 에 말소리 있음). 따라 함 횟수·DB 집계·히트맵·이력 표의 KST 묶음은 통과.
- 거부 원인(spike_nova_bidirectional.py · OMY_SPIKE_CAPTURE_BODY=1 로 본문 확인): IAM 사용자 ohmyenglish-local 에 amazon.nova-2-sonic-v1:0 의 bedrock:InvokeModel 을 허용하는 identity-based policy 가 없음. dev DB llm_calls 의 마지막 Nova 성공은 2026-09-26 03:01 UTC — 그 뒤 AWS 계정에서 정책이 빠졌음. 정책 기준은 docs/ops/iam-setup-nova-sigv4.md.
- ⛔ 사람의 조치 대기: 사용자가 AWS 콘솔에서 그 IAM 사용자에 Nova 2 Sonic InvokeModel 권한을 다시 붙여야 AC 1·2 를 잴 수 있음.
- 같은 회차의 결함 D1(전사기 실패를 「안 들렸다」로 읽고 시도로 기록) 은 이 태스크에서 고침: Nova 어댑터가 출력 스트림 예외를 failure 로 남기고, 전사기가 TranscriberUnavailable 을 올리고, 코스 시도·쉐도잉 낭독 판정 라우터가 503 으로 옮김. 새 테스트 5건은 옛 소스에서 모두 실패함을 확인함.

- 회차 b7: D1 고쳐짐 확인(수동·자동 모두 503 · 화면 「판정을 쓸 수 없어요」 · 횟수·DB 그대로 · 자동 흐름은 이어짐). 시도 POST 4회 모두 503.
- codex 리뷰(D1 변경분) HIGH 2 수용: 연결 열기·초기화 전송 실패가 500 으로 빠짐 · 오디오 전송 실패 뒤 조용하면 「안 들렸다」가 됨 → 둘 다 TranscriberUnavailable 로 고치고 실패 테스트 2건을 먼저 씀. 이어진 LOW 1(코드 결함도 503 으로 감) 은 수용해 503 전에 logger.exception 으로 원인을 남김.
- b7 관찰 수용: 앞 문장의 안내가 다음 문장 동안 남던 것 → 문장마다 안내를 지움(page.tsx run).
- 내가 직접: 최신 코드로 거부 시도 1건 → 503 · 격리 DB attempts 2→2. dev DB 는 세션 시작과 같음(attempts 0 · progress 0 · llm_calls 109) — AC 4 충족.
- 게이트(마지막 변경 뒤): pytest 1484 passed · ruff 0 · ruff format 341 files · ty 0 · tsc 0 · eslint 오류 0(기존 경고 1).
- 스택은 VOICE_ADAPTER=stub + dev DB 로 되돌림. 남은 AC 1·2·3 은 IAM 권한 복구 뒤 실제 전사로 다시 잼(b6 의 audio/ 입력과 드라이버 재사용).

2026-11-01 사용자 지시: 「nova 권한은 zshrc 의 aws bedrock api key 를 사용해서 연결해」
- 확인: 설치된 SDK(aws_sdk_bedrock_runtime 0.10.0)는 SigV4 만 등록함. SDK 의 APIKeyAuthScheme(Authorization: Bearer)을 끼운 일회성 탐침(리포 밖 · 삭제함)으로 양방향 스트림을 열었음.
- 결과(응답 본문 직접 확인): bearer → HTTP 403 {"Message":"This operation does not support API Keys"}. 대조군 SigV4 → 같은 시각 IAM 거부(no identity-based policy allows bedrock:InvokeModel on amazon.nova-2-sonic-v1:0).
- 결론: Bedrock 이 InvokeModelWithBidirectionalStream 에서 API 키를 받지 않음(2026-08 실측과 같음 · app/backend/app/config.py 머리말에 기록된 그 사실). 앱 코드는 바꾸지 않았음. Nova 를 붙일 길은 IAM 사용자 ohmyenglish-local 의 SigV4 권한 복구뿐임(docs/ops/iam-setup-nova-sigv4.md 「최소권한 정책 JSON」).

2026-11-01 SSO 경로로 완료
- 사용자 질문 「aws sso 로그인 하면되는거야?」 → 확인: SSO 프로필 kjihoon-bedrock(AdministratorAccess · 같은 계정)의 세션이 살아 있었음. Nova SDK 는 SSO 프로필을 읽지 않으므로 aws configure export-credentials 로 임시 키를 환경에 넣고 백엔드를 띄움(앱 코드 변경 없음 · 앱은 환경 SigV4 를 정본으로 씀). 스파이크 PASS(대조군 거부 확인).
- ⚠️ 임시 자격증명 만료 2026-11-01T04:25:09Z. 그 뒤에는 aws sso login --profile kjihoon-bedrock 뒤 재기동이 필요함. 상시 사용은 IAM 사용자 권한 복구가 덜 번거로움.
- 회차 b8(tests/agent/runs/2026-11-01-b8): 실제 전사 3종 통과 — (a) the server is very slow today. 전부 match · (b) …very fast today. → 원문 slow 밑줄 · (c) the server is slow today → 원문 very 취소선. 자동 모드 2문장 실제 전사 후 진행. 새 결함 0. Nova 호출 5회.
- 내가 직접 대조: 격리 DB course_attempts 7(새 5행 전사 비어 있지 않음) · llm_calls 5(nova-2-sonic, input 3004 · output 194 토큰) · API 히트맵 오늘 7회 · 이력 11/1 Day 1 Unit 1 3문장 7회. dev DB 는 세션 시작과 같음(0 · 0 · 109). 스크린샷 ATTEMPT-b·c 를 직접 열어 밑줄·취소선을 봤음.
- 남은 것: 물리 마이크 장치 경로는 사람이 확인할 몫임(에이전트는 가짜 장치만 씀).
<!-- SECTION:NOTES:END -->
