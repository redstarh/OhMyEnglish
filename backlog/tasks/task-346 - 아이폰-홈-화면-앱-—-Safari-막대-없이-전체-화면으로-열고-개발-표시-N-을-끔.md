---
id: TASK-346
title: 아이폰 홈 화면 앱 — Safari 막대 없이 전체 화면으로 열고 개발 표시 N 을 끔
status: In Progress
assignee: []
created_date: '2026-11-15 04:27'
updated_date: '2026-11-15 04:31'
labels: []
dependencies: []
ordinal: 413000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 2026-11-15: 「맨위에 주소표시와 맨 아래 회색표시 즐겨찾기가 있는 것은 계속 떠 있어야 하는거야?」 → 결정: 홈 화면 앱으로 만듦(권장) · N 표시 끔(권장).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 웹 앱 매니페스트·아이콘·애플 메타 태그를 더해 홈 화면에 추가하면 standalone 으로 열림
- [x] #2 next.config 에서 개발 표시(devIndicators)를 끔
- [x] #3 iOS 시뮬레이터에서 홈 화면 앱으로 열어 막대 없이 한 화면에 들어감을 확인함
- [ ] #4 실기기 홈 화면 앱에서 음성 인식 실시간 표시를 사용자가 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-15 구현: app/manifest.ts(display standalone · 바탕/테마 #f7f8fc · 아이콘 192·512) · app/apple-icon.png(180) · layout appleWebApp(capable · title · statusBarStyle default) · next.config devIndicators:false. 실측: /manifest.webmanifest 200 · <link rel=manifest> · apple-touch-icon · apple-mobile-web-app-title 출력. ⚠️ AC3 은 바꿔 확인함 — 이 Xcode 에 Simulator.app(화면)이 없어 simctl 로는 「홈 화면에 추가」를 누를 수 없음. 대신 standalone 크기(428×879 · 393×793)로 Chromium 실측: 홈·연습·진도 넘침 0 · 카드가 화면을 채움 · N 표시 없음(스크린샷). mobile-fit ALL PASS · node --test 60 · next build 0 · tsc 0 · eslint 0.
<!-- SECTION:NOTES:END -->
