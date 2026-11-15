---
id: TASK-343
title: '리뷰: TASK-325 아이폰 준비 변경(11dcdc6..db23060)의 codex 리뷰를 받아 반영함'
status: Done
assignee: []
created_date: '2026-11-15 01:02'
updated_date: '2026-11-15 04:10'
labels: []
dependencies: []
ordinal: 410000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [x] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
codex 리뷰 수신: 프런트 정확성 지적 없음. 보안 셋 — HIGH tailnet 기기 누구나 인증 없이 전체 접근 · MEDIUM next dev 가 *:3000 으로 들음(LAN 직접 접근) · MEDIUM WS 가 아무 Origin 이나 받음. 실제 상태 확인 후 판단.

판단·조치: ① HIGH(tailnet 기기 누구나 전체 접근) — 실제 tailnet 은 같은 계정(red7368) 맥 두 대뿐 · 공유 기기 없음(tailscale status) → 위험은 본인 기기 범위. 인증 없음은 남음 → 기기 공유·ACL 확대 전 사용자 판단으로 넘김. ② MEDIUM next dev *:3000 — 사실 · package.json dev 를 --hostname 127.0.0.1 로(allowedDevOrigins 에 localhost 추가 · H-CA 반대 방향). ③ MEDIUM WS 아무 Origin — 사실 · _origin_allowed 허용 목록(localhost·127.0.0.1:3000 + EXTRA_ALLOWED_ORIGINS · Origin 없음은 받음) · 받기 전에 닫음. 시험 먼저(남의 출처 accept 로 실패 → 통과 · 허용 둘은 과잉 차단 방지). pytest 1521 · ruff 0 · format 342 · ty 0 · tsc 0 · eslint 0. 재기동 중 SSO 만료로 아이콘이 로그인을 기다림.

2026-11-15 11:2x: 아이콘 재기동이 SSO 승인 시간 초과로 실패 → 화면이 내려감. 화면만 launchctl submit -l local.ohmyenglish.frontend(/private/tmp/_omy-frontend.sh · npm run dev)로 되살림 — 127.0.0.1:3000 에서만 들음 확인. 확인: localhost 하이드레이션 OK · tailnet(IP 고정) 보안 문맥·같은 출처·콘솔 오류 0. 남은 것: 백엔드는 옛 판(80536 · 자격증명 만료)이라 WS 출처 거절은 사용자가 아이콘을 다시 눌러 SSO 승인한 뒤 확인. ⚠️ launchd 작업 local.ohmyenglish.frontend 는 남아 있음 — 아이콘은 떠 있는 화면을 그대로 씀(충돌 없음).

2026-11-15 사용자 지시로 아이콘 재기동(새 백엔드 pid 39748 · SSO 갱신). 실서버 확인: /ws/session 에 Origin https://evil.example.com · http://192.168.0.5:3000 → 둘 다 HTTP 403(수락 전 거부) · backend.log 'connection rejected (403 Forbidden)' · ohmyenglish.learning_sessions 25 → 25(행 생성 없음). 허용 출처 수락은 tests/integration/test_ws.py 가 맡음(실서버에서 수락 시험은 세션 행을 만들어 하지 않음).
<!-- SECTION:NOTES:END -->
