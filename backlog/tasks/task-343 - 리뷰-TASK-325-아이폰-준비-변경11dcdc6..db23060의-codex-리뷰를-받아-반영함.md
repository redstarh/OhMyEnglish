---
id: TASK-343
title: '리뷰: TASK-325 아이폰 준비 변경(11dcdc6..db23060)의 codex 리뷰를 받아 반영함'
status: In Progress
assignee: []
created_date: '2026-11-15 01:02'
updated_date: '2026-11-15 01:12'
labels: []
dependencies: []
ordinal: 410000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [ ] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
codex 리뷰 수신: 프런트 정확성 지적 없음. 보안 셋 — HIGH tailnet 기기 누구나 인증 없이 전체 접근 · MEDIUM next dev 가 *:3000 으로 들음(LAN 직접 접근) · MEDIUM WS 가 아무 Origin 이나 받음. 실제 상태 확인 후 판단.

판단·조치: ① HIGH(tailnet 기기 누구나 전체 접근) — 실제 tailnet 은 같은 계정(red7368) 맥 두 대뿐 · 공유 기기 없음(tailscale status) → 위험은 본인 기기 범위. 인증 없음은 남음 → 기기 공유·ACL 확대 전 사용자 판단으로 넘김. ② MEDIUM next dev *:3000 — 사실 · package.json dev 를 --hostname 127.0.0.1 로(allowedDevOrigins 에 localhost 추가 · H-CA 반대 방향). ③ MEDIUM WS 아무 Origin — 사실 · _origin_allowed 허용 목록(localhost·127.0.0.1:3000 + EXTRA_ALLOWED_ORIGINS · Origin 없음은 받음) · 받기 전에 닫음. 시험 먼저(남의 출처 accept 로 실패 → 통과 · 허용 둘은 과잉 차단 방지). pytest 1521 · ruff 0 · format 342 · ty 0 · tsc 0 · eslint 0. 재기동 중 SSO 만료로 아이콘이 로그인을 기다림.
<!-- SECTION:NOTES:END -->
