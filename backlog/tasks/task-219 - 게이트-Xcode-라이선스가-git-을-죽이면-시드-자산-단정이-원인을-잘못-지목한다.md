---
id: TASK-219
title: '게이트: Xcode 라이선스가 git 을 죽이면 시드 자산 단정이 원인을 잘못 지목한다'
status: Done
assignee: []
created_date: '2026-09-18 18:46'
updated_date: '2026-09-18 18:49'
labels: []
dependencies: []
ordinal: 280000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-19 세션 시작에 git 이 전부 exit 69 로 죽었다 — 'You have not agreed to the Xcode license agreements'. xcode-select 가 /Applications/Xcode.app 을 가리키고 그 라이선스가 미동의라 /usr/bin/git 셰임이 아무 명령도 못 돌린다. 게이트에 두 가지로 번졌다: 내 git 명령이 전부 막혔고, test_seeded_clip_audio_files_exist_in_the_repository 가 git check-ignore 의 returncode 를 1 과만 견주어 69 를 받고 '<파일> 가 .gitignore 에 걸려 있다 — 배포되지 않는다' 로 실패했다. 그 문면은 거짓이다 — 파일은 추적되고 있고 깨진 것은 git 이다. 우회는 DEVELOPER_DIR=/Library/Developer/CommandLineTools 이고 항구적 해결은 sudo 가 필요해 사람 몫이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정이 git 실행 실패와 '무시되고 있다' 를 가른 문면으로 실패한다
- [x] #2 docs/ops/pitfalls.md 게이트 절에 H-CH 로 남는다
- [x] #3 pytest·ruff·format·ty 넷이 통과한다
<!-- AC:END -->
