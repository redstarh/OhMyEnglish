---
id: TASK-281
title: Bedrock 공통 리전을 us-east-1로 변경
status: Done
assignee: []
created_date: '2026-10-18 03:06'
updated_date: '2026-10-18 03:08'
labels: []
dependencies: []
modified_files:
  - app/backend/.env
priority: medium
type: chore
ordinal: 345000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Claude와 Codex가 공통으로 사용하는 Amazon Bedrock 리전 설정 위치를 확인하고 us-east-1로 통일한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Claude와 Codex의 Bedrock 설정 원본 위치를 확인한다.
- [x] #2 공통 리전을 us-east-1로 변경한다.
- [x] #3 두 도구에서 해석되는 리전 값을 검증한다.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
공통 원본은 ~/.zshrc의 AWS_REGION 및 AWS_DEFAULT_REGION이며 새 셸에서 Claude가 상속한다. Codex는 ~/.codex/config.toml의 [model_providers.amazon-bedrock.aws].region을 사용한다. 두 위치와 앱 백엔드 .env를 us-east-1로 변경했다.

검증: 새 zsh 셸 AWS_REGION=us-east-1, AWS_DEFAULT_REGION=us-east-1; Codex 구성 region=us-east-1; app/backend/.env AWS_REGION=us-east-1.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Claude 공통 셸 환경, Codex Bedrock 구성, OhMyEnglish 백엔드 환경의 AWS 리전을 us-east-1로 통일했다. 새 셸 및 구성 파일에서 해석값을 확인했다.
<!-- SECTION:FINAL_SUMMARY:END -->
