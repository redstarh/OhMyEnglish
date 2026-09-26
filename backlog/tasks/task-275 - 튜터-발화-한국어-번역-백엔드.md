---
id: TASK-275
title: 튜터 발화 한국어 번역 백엔드
status: Done
assignee: []
created_date: '2026-09-26 04:24'
updated_date: '2026-09-26 05:19'
labels: []
dependencies: []
ordinal: 339000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
말풍선 [번역] 버튼의 백엔드. 발화는 (session_id, sequence_no) 로 가리킴
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET 또는 POST /api/sessions/{id}/utterances/{seq}/translation 이 한국어 번역을 줌
- [x] #2 번역은 한 번만 만들고 저장해 재사용함(마이그레이션 포함)
- [x] #3 LLM 호출 비용이 llm_calls 에 기록됨
- [x] #4 화면 [번역] 버튼을 연결하고 번역문을 말풍선 안에 보여 줌
- [x] #5 단위 테스트와 게이트 통과
- [x] #6 리뷰 반영 후 커밋하고 dev DB 에 032 를 적용함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현: 032(utterances.translation_ko · llm_calls purpose 'translation') · services/translation.py(저장된 번역 재사용 · 실패는 저장 안 함 · 모델 호출 중 커넥션 미보유) · POST /api/sessions/{id}/utterances/{seq}/translation(404·503·실패 200 null) · 화면은 조각별 요청 후 이어 붙임, 번역은 말풍선 안 <p> 밖. 게이트: pytest 1449 passed · ruff 0 · ruff format 통과 · ty 0 · tsc 0 · eslint 0 errors. 실물: 격리 DB ohmyenglish_t274 에서 실물 Claude 1회 — 두 번째 요청 재사용, llm_calls 1행(translation · 136/26 토큰), 없는 순번 404. 브라우저: /tmp/t275_drive.py(CORS 래퍼 /tmp/t275_app.py · 사본 :3001) PASS — 두 말풍선 번역 표시 · 줄 textContent 불변. 첫 시도 FAIL 은 CORS 사전 요청 400(오리진 :3001) 때문이었고 실패 문구 경로가 그때 확인됨.

리뷰(opus) CRITICAL·HIGH 0 · MEDIUM 2 반영: 번역 요청 거부 시 loading 고착 → .catch 로 failed · 학습자 발화도 번역되던 것 → SELECT 에 speaker='agent'(학습자 순번 404 · 모델 0회 테스트). LOW 6 반영: 저장이 다른 행을 덮지 않는 단정. LOW 3·4·5 미반영(무해·기존 관행). 재검증: pytest 1450 passed · ruff 0 · format 통과 · ty 0 · tsc 0 · eslint 0 errors · 브라우저 드라이버 PASS · 학습자 순번 404.

커밋 1ef6727. dev DB: 백업 ~/Backups/OhMyEnglish/ohmyenglish-before-TASK-275-20260926-1418.dump 뒤 apply_migrations 만 실행(시드 미실행) — schema_migrations 30 · translation_ko 컬럼 1. :8002 재기동(PID 79219) · 새 경로 404 응답 확인. 격리 DB ohmyenglish_t274 와 :8012·:3001·:9334 는 정리함.
<!-- SECTION:NOTES:END -->
