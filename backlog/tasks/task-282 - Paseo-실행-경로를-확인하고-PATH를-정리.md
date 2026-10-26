---
id: TASK-282
title: Paseo 실행 경로를 확인하고 PATH를 정리
status: Done
assignee: []
created_date: '2026-10-18 03:15'
updated_date: '2026-10-18 03:16'
labels: []
dependencies: []
priority: low
type: chore
ordinal: 346000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Paseo 명령을 현재 셸에서 찾지 못하는 원인을 확인하고 재실행할 수 있도록 경로를 설정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Paseo 설치 여부와 앱 위치를 확인한다.
- [x] #2 Paseo의 GUI 실행 방식과 새 에이전트 세션 적용 방식을 확인한다.
- [x] #3 Claude 설정에서 새 Paseo 세션의 리전 값을 검증한다.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Paseo는 PATH에 등록되는 CLI가 아니라 /Applications/Paseo.app GUI 앱이며, 현재 실행 중임을 확인했다. 실행/활성화 명령은 `open -a Paseo`이다.

Paseo가 GUI로 시작되면 ~/.zshrc를 상속하지 않을 수 있어 ~/.claude/settings.json의 env에 AWS_REGION=us-east-1 및 AWS_DEFAULT_REGION=us-east-1을 추가했다. JSON에서 두 값을 검증했다.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Paseo는 CLI가 아닌 GUI 앱임을 확인했다. 새 Claude 세션이 Paseo 실행 방식과 관계없이 us-east-1을 사용하도록 Claude 설정에 두 AWS 리전 변수를 명시했다.
<!-- SECTION:FINAL_SUMMARY:END -->
