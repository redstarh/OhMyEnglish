---
id: TASK-272
title: 영어 학습 화면을 채팅 말풍선형으로 재디자인
status: Done
assignee: []
created_date: '2026-09-26 04:13'
updated_date: '2026-09-26 04:21'
labels: []
dependencies: []
ordinal: 336000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 요청 2026-09-26: 첨부 이미지 2장(Free Talk with AI · 번역 버튼형) 참고. 튜터 말풍선(왼쪽·아바타·음성/번역 버튼) · 학습자 말풍선(오른쪽·색) · 하단 중앙 마이크
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 현재 학습 화면 구조를 파악함
- [x] #2 튜터·학습자 말풍선과 하단 마이크 배치로 바꿈
- [x] #3 프런트 게이트 통과
- [x] #4 브라우저 화면을 직접 확인함
- [x] #5 리뷰 반영 후 커밋함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현: 대화 영역을 app/SessionChat.tsx 로 분리(page.tsx 773→671행). 튜터 왼쪽 회색 말풍선+AI 아바타 · 학습자 오른쪽 옅은 보라 · 머리에 제목+학습 종료 · 발에 마이크 상태(버튼 아님 · 상시 음성). 하네스 계약 유지: 줄마다 <p>+<strong>질문: /답변: </strong>(눈에서만 숨김) · 글자색은 foreground/muted 토큰만 — 그래서 참고 이미지의 진한 바탕+흰 글자 학습자 말풍선은 따르지 않음. 발화별 음성·번역 버튼은 백엔드가 없어 넣지 않음. 게이트: tsc 0 · eslint 0 errors(API_BASE 미사용 경고 1건은 변경 전부터 있음). 화면: /tmp 사본의 미리보기 경로(:3001)를 헤드리스 Chrome 으로 라이트·다크·듣는 중 3장 캡처해 직접 확인 · DOM 에서 줄 textContent 가 '질문: …' 모양 5/5.

리뷰(opus) CRITICAL 0 · HIGH 1 · MEDIUM 3 반영: 알림 셋을 스크롤 영역 밖으로 · --on-accent 토큰(다크 흰 글자 2.75:1 → #16122e 6.6:1) · 맨 아래 근처일 때만 자동 스크롤 · 정지·종료 중 마이크 안내 문구. LOW 미반영: p_readback_leg.py 의 'section p' 가 대화 줄까지 모음(인쇄만 하고 단정 없음) · 숨김 기법 · 테두리 대비. 게이트: tsc 0 · eslint 0 errors · pytest 1438 passed. 다크+정지+듣는 중 화면을 다시 캡처해 확인함.
<!-- SECTION:NOTES:END -->
