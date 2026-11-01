---
id: TASK-300
title: '검증: 영어 음성 명령 실물 확인과 결과 화면의 교정·요약 표시 (리디자인 남은 미검증)'
status: In Progress
assignee: []
created_date: '2026-11-01 01:35'
updated_date: '2026-11-01 02:25'
labels: []
dependencies: []
ordinal: 365000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
리디자인(TASK-292~298) 뒤 확인하지 못한 둘. ① 영어 음성 명령(Hey, end the lesson 등)이 실제 Nova 세션에서 통하는가 — 통하면 화면 안내의 한국어 명령을 영어로 바꿈(설계서 §6-6) ② 분석이 끝난 세션의 결과 화면(교정·요약)이 영어 화면에서 어떻게 보이는가. 격리 DB ohmyenglish_course_paid · 실제 Nova(SSO) · 분석 워커. 사용자 지시 2026-11-01 「확인하지 못한것 확인해 Test Agent 를 사용해서」.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 app-test-agent 가 실제 Nova 세션에서 영어 음성 명령을 시험하고 결과를 기록함
- [x] #2 분석이 끝난 세션의 결과 화면을 확인하고 남은 한국어를 기록함
- [ ] #3 결과에 따라 화면 안내 문구를 고치거나 미결로 기록함
- [x] #4 dev DB 쓰기가 없음을 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01 10:55 사용자 지시로 회차 b10 을 중간에 멈춤(「테스트 잠시 멈춰. 잠시후에 다시 요청할께」).
- 멈춘 시점까지: 격리 DB 에 실제 Nova 세션 4개(상한 6). 에이전트 마지막 보고는 「일시 정지 뒤 재개가 서버에서 통함(8번 발화가 learning 으로 저장됨)」 — 영어/한국어 어느 명령이었는지와 화면 확인은 result.md 가 없어 미정리. 산출물(음성·드라이버·증거)은 tests/agent/runs/2026-11-01-b10/ 에 미커밋으로 남음.
- 정리: 회차 Chrome·드라이버 종료(남은 Chrome 은 사용자 것뿐) · 회차용 launchd 백엔드 제거 · 아이콘으로 사용자 스택 복원(nova · dev DB · 부모 launchd). dev DB 는 기준선 그대로(sessions 18 · utterances 144 · progress 0 · attempts 0).
- 재개할 때: 격리 DB 의 이번 회차 세션 분석이 워커 없이 대기 중일 수 있음 · SSO 는 13:25 KST 만료(재개가 그 뒤면 아이콘으로 다시 로그인).

회차 b10 완료(tests/agent/runs/2026-11-01-b10 · 실제 세션 6).
- 영어 명령 7/7 서버 동작(종료 3 · 정지 2 · 계속 2) · 한국어 명령 1/6(실패 5건은 모두 Nova ASR 이 한국어를 영어 문장으로 전사). ⇒ 화면 안내의 명령을 영어로 바꿈(AC3, 아래).
- 결과 화면: 한글 11줄 모두 백엔드 필드(교정 reason · summary went_well/weak_points · daily example reason) — UI 상수 한국어 0. target_form 은 결과 화면이 그리지 않음.
- 결함: D2(재개가 confirmed 단계로 오면 Paused 표시가 남음 · 프런트) · D3(결과 화면이 final 에서 폴링을 멈춰 15~18초 늦은 총평이 안 보임 · 프런트) → 이 태스크에서 고침. D1(영어 종료가 requested 없이 confirmed — 확인 안내 없음 · yes 가 학습 발화로 분석됨) · D4(확인 질문 뒤 학습 문장이 command_confirmation 으로 저장) → 백엔드 음성 명령 판정이라 TASK-303 으로 분리.
- dev DB: 재개 기준선(19·144·0·0) 그대로.
<!-- SECTION:NOTES:END -->
