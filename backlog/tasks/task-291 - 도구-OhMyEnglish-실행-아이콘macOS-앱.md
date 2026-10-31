---
id: TASK-291
title: '도구: OhMyEnglish 실행 아이콘(macOS 앱)'
status: Done
assignee: []
created_date: '2026-10-31 18:27'
updated_date: '2026-10-31 18:35'
labels: []
dependencies: []
ordinal: 356000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
아이콘을 누르면 SSO 세션(kjihoon-bedrock)을 확인해 없으면 aws sso login 창을 띄우고, 있으면 그대로 SSO 임시 자격증명으로 백엔드(nova · dev DB)와 프런트를 띄우고 브라우저로 화면을 엶.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 아이콘이 있는 .app 번들이 있고 실행 스크립트는 리포에 있음
- [x] #2 SSO 없음·있음 두 갈래가 동작함
- [x] #3 실행 뒤 :8002(nova)·:3000 이 응답하고 브라우저가 열림
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01
- 실행 스크립트 scripts/launcher/launch.sh · 번들 빌드 scripts/launcher/build_app.sh · 아이콘 icon.svg. 번들은 ~/Applications/OhMyEnglish.app, 바탕화면에 별칭. 기록은 ~/Library/Logs/OhMyEnglish/(launcher·backend·frontend).
- SSO 있음 갈래: 아이콘(open → LaunchServices)으로 실행해 :8002 = nova · SSO 임시 자격증명 · dev DB(.env), 부모 launchd 확인. :3000 응답 · 브라우저 탭 열림. 헤드리스로 /course 렌더링 확인.
- SSO 없음 갈래: 없는 프로필(OMY_SSO_PROFILE)로 세션 0초 판정 → aws sso login 호출 → 실패 대화상자 · 백엔드 무변경까지 확인. ⚠️ 실제 만료 세션에서 브라우저 로그인 창이 뜨는 것은 사용자의 승인이 필요해 보지 못했음.
- ⚠️ 시험 중 실패 대화상자가 사용자 화면에 떴고, 내 셸에서 직접 실행한 1회가 서버를 샌드박스 아래에서 띄웠음 → 사용자 지적(「sandbox 에서 띄우지마」)에 따라 백엔드·프런트를 모두 내리고 아이콘으로 다시 띄움.
- codex 리뷰 수용 2(HIGH 다른 작업 트리의 :8002 를 내릴 수 있음 · MEDIUM :3000 의 아무 프로그램을 프런트로 간주) → 둘 다 프로세스 작업 폴더가 이 리포인지로 판정하게 고침. 고친 판을 아이콘으로 다시 실행해 확인함.
- 로그 3개에서 자격증명 문자열 0건 확인.
<!-- SECTION:NOTES:END -->
