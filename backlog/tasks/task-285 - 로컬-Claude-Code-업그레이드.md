---
id: TASK-285
title: 로컬 Claude Code 업그레이드
status: Done
assignee:
  - Codex
created_date: '2026-10-24 03:31'
updated_date: '2026-10-24 03:32'
labels: []
dependencies: []
type: chore
ordinal: 350000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 요청에 따라 이 Mac의 Claude Code CLI를 업데이트하고 업데이트 후 버전과 실행 여부를 확인한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 기존 설치 방식에 맞춰 Claude Code 업데이트가 성공한다.
- [x] #2 업데이트 후 Claude Code의 설치 버전과 정상 실행을 확인한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 기존 native 설치 경로와 버전 확인.
2. 내장 claude update로 현재 업데이트 채널의 최신 버전 설치.
3. claude --version과 실행 경로를 확인하고 원장 완료 처리.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
기존 설치: /Users/redstar/.local/bin/claude → /Users/redstar/.local/share/claude/versions/2.1.302. claude update에서 2.1.310 업데이트 진행 중.

claude update 종료 코드 0: Successfully updated from 2.1.302 to version 2.1.310. 검증: claude --version → 2.1.310 (Claude Code), symlink가 versions/2.1.310을 가리킴, claude update --help 정상 종료.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
사용자 요청에 따라 native Claude Code 설치를 2.1.302에서 2.1.310으로 업데이트했다. 내장 claude update 성공, 새 버전 출력, 실행 파일 링크와 CLI 도움말 정상 실행을 확인했다.
<!-- SECTION:FINAL_SUMMARY:END -->
