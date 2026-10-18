---
id: TASK-283
title: Paseo와 Codex의 Bedrock GPT 네 모델을 1M context로 사용하도록 설정한다
status: Done
assignee:
  - Codex
created_date: '2026-10-18 03:58'
updated_date: '2026-10-18 04:01'
labels:
  - codex
  - paseo
  - bedrock
dependencies: []
documentation:
  - docs/design/2026-10-18-codex-bedrock-context.md
modified_files:
  - docs/design/2026-10-18-codex-bedrock-context.md
type: chore
ordinal: 348000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 요청: Paseo Codex 모델 목록의 openai.gpt-6.1-sol, openai.gpt-6-astra, openai.gpt-6-luna, openai.gpt-5.6-terra가 각각 AWS Bedrock에서 1M context를 지원하는지 확인하고, 전역 Codex와 Paseo에서 동일한 1M 설정을 사용하도록 변경한다. 현재 대화에 보고된 한도는 258,400 토큰이다. 홈 디렉터리 설정 변경은 사용자 요청 범위에 포함되며 기존 설정과 복구 가능한 백업을 보존한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 네 모델의 AWS 공식 context 사양을 확인한다.
- [x] #2 전역 Codex와 Paseo의 네 모델에 1M context 설정을 적용하고 기존 무관한 설정을 보존한다.
- [x] #3 변경된 설정을 실제 Codex 로드 경로로 검증하고 재시작 또는 새 대화가 필요한 범위를 기록한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. AWS 모델 카드에서 네 모델의 context 용량을 확인한다.
2. ~/.codex/config.toml 및 model-catalog.json의 실제 로드/우선순위와 Paseo Codex app-server 연결을 확인한다.
3. 기존 파일을 백업하고 전역 context/자동 compaction 한도와 네 모델의 카탈로그를 일치시킨다. 무관한 모델이나 자격증명은 변경하지 않는다.
4. 설정 파싱, 네 모델 메타데이터 및 격리된 Codex app-server의 실제 config/model 응답을 확인한다. 실행 중인 사용자 대화는 중단하지 않고 적용 시점을 명시한다.

공식 AWS 확인: Sol은 1M, Astra/Luna/Terra는 1,050,000 토큰을 지원한다. 사용자 요청에 맞춰 공통 model_context_window=1,000,000 및 model_auto_compact_token_limit=900,000을 설정하고, 카탈로그 네 모델의 context_window/max_context_window를 1,000,000으로 맞춘다. 기존 effective_context_window_percent=95는 유지하므로 실제 세션 표시 한도는 950,000 토큰이다. 이 여유분과 적용 시점을 사용자에게 명시한다. Paseo는 별도 context override 없이 동일한 Codex app-server 및 ~/.codex 설정을 사용한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
전역 설정과 네 모델 카탈로그를 원본 백업 후 변경했다. 백업: /Users/redstar/.codex/backups/20261018-130028-context-1m/. 무관한 TOML/JSON 의미와 카탈로그의 무관한 바이트를 보존했으며 기존 파일 권한을 유지했다.

격리된 codex app-server --strict-config --stdio의 config/read에서 1,000,000 context / 900,000 자동 요약을 확인했다. 네 모델 각각 실제 amazon-bedrock ephemeral 요청이 OK/completed로 성공했고 thread/tokenUsage/updated에서 modelContextWindow=950,000을 확인했다. 기존 95% 여유분을 유지한 결과다. 사용자 세션을 재시작하지 않았으며 기존 Agent는 재로드해야 적용된다.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
AWS 공식 모델 카드에서 네 모델의 1M 이상 context 지원을 확인하고 전역 Codex 설정과 사용자 모델 카탈로그를 동일한 1,000,000 토큰으로 맞췄다. 자동 compaction 시작점은 900,000 토큰이며 기존 5% 여유분을 유지해 실제 보고되는 한도는 950,000 토큰이다. Paseo의 Codex provider가 같은 전역 설정을 읽는 경로를 확인했다.

Codex app-server의 실제 설정 읽기와 네 Bedrock 모델의 짧은 응답 요청으로 적용을 검증했다. 네 모델 모두 950,000 한도를 보고하고 정상 응답했다. 1M 근처 대형 입력 부하 테스트는 수행하지 않았다. 원본 백업과 검증/적용 시점을 docs/design/2026-10-18-codex-bedrock-context.md에 기록했다. 새 Agent부터 적용되고 이미 실행 중인 Agent는 재로드가 필요하다.
<!-- SECTION:FINAL_SUMMARY:END -->
