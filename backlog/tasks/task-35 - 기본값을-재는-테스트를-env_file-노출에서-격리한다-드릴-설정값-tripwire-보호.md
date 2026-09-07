---
id: TASK-35
title: 기본값을 재는 테스트를 env_file 노출에서 격리한다 (드릴 설정값 tripwire 보호)
status: To Do
assignee: []
created_date: '2026-09-07 17:02'
labels: []
dependencies: []
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Batch C 리뷰가 Minor(F-4) 로, 최종 리뷰가 triage 로 올렸다. tests/unit/test_config.py 와 tests/integration/test_gateway.py 의 '기본값이 4·5다' / '기본값에서 질문 5개가 전부 열거된다'(캡틴 결정 2 회귀 방어) 단정이 Settings 의 env_file=".env"(app/backend/app/config.py:46) 를 통해 주변 환경에 열려 있다.

팀리드 실측(2026-09-08): 리포 루트에 .env 는 없고 app/backend/.env 가 실재한다(1.6k · DRILL 키 0건). env_file 은 프로세스 cwd 기준이고 게이트는 app/backend 에서 돈다(pyproject.toml:33 testpaths=["../../tests"]) → .env 는 app/backend/.env 로 해석되므로 창이 실재한다. 셸 환경변수 창도 열려 있다(현재 DRILL 0건).

⚠️ 최종 리뷰의 정정('루트에 .env 가 없으니 창이 닫혀 있다')은 경로를 잘못 잡았다 — 팀리드가 재확인해 바로잡았다.

⛔ 위험이 이 계획으로 커졌다: .env.example 첫 줄이 'Copy this file to app/backend/.env' 이고 그 파일에 이제 DRILL_TURNS_MIN=4·DRILL_COUNT=5 가 들어 있다 → 표준 온보딩이 테스트가 읽는 파일에 그 키를 심는다. 값이 같으면 무해하지만 .env.example 이 스스로 튜닝을 권하므로 누가 값을 바꾸면 기본값 단정이 조용히 의미를 잃는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 기본값을 단정하는 테스트가 주변 환경(app/backend/.env · 셸 환경변수)과 무관하게 통과하는 것을 보장한다 — 방법(monkeypatch·_env_file=None·격리 픽스처 등)은 선택하고 근거를 남긴다
- [ ] #2 무력화로 판별력을 증명한다 — app/backend/.env 나 셸에 DRILL_COUNT 를 다른 값으로 넣은 상태에서도 기본값 단정이 통과하는 것을 실제로 관측한다
- [ ] #3 같은 노출을 가진 다른 기본값 테스트가 있는지 훑고 결과를 적는다 — Settings 의 필드는 이 둘만이 아니다
<!-- AC:END -->
