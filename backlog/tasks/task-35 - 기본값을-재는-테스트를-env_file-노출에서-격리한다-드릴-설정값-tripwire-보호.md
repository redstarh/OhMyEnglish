---
id: TASK-35
title: 기본값을 재는 테스트를 env_file 노출에서 격리한다 (드릴 설정값 tripwire 보호)
status: Done
assignee: []
created_date: '2026-09-07 17:02'
updated_date: '2026-09-08 09:25'
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
- [x] #1 기본값을 단정하는 테스트가 주변 환경(app/backend/.env · 셸 환경변수)과 무관하게 통과하는 것을 보장한다 — 방법(monkeypatch·_env_file=None·격리 픽스처 등)은 선택하고 근거를 남긴다
- [x] #2 무력화로 판별력을 증명한다 — app/backend/.env 나 셸에 DRILL_COUNT 를 다른 값으로 넣은 상태에서도 기본값 단정이 통과하는 것을 실제로 관측한다
- [x] #3 같은 노출을 가진 다른 기본값 테스트가 있는지 훑고 결과를 적는다 — Settings 의 필드는 이 둘만이 아니다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-08 완료 (재개 세션). ⚠️ **이 태스크를 지금 한 이유**: TASK-45 AC#2 가 `.env.example` 에 `SHADOWING_*` 3개를 넣어 **노출을 넓혔다** — 이 태스크의 ⛔ 상자가 경고한 「표준 온보딩이 테스트가 읽는 파일에 키를 심는다」가 그만큼 커졌다.

**착수 전 실측 (원장 기록과 일치)**: `app/backend/.env` 실재(1.6k) · 그 안에 DRILL/SHADOWING 키 **0건** · 루트 `.env` **없음** · 셸에 DRILL/SHADOWING **0건**. 즉 창은 **열려 있지만 아직 통과하지 않았다.**

**AC#2 (무력화 실증) — 창이 둘이고 둘 다 실제로 통과시켰다.**
① **셸 창**: `DRILL_COUNT=9 SHADOWING_REPEAT_COUNT=7` → `test_drill_settings_default_to_four_and_five` 와 `test_shadowing_settings_default_to_the_range_identities` **2건 red**(`assert 7 == 1`).
② **`.env` 파일 창**: 백업(md5 기록) 후 그 파일에 `DRILL_COUNT=3 · CLAUDE_MODEL_ID=bogus-from-dotenv` 등을 심어 실행 → **`test_claude_schema.py` red**(`bogus-from-dotenv` 누출). ⛔ 복원은 **md5 대조로 바이트 동일을 확인**했고 오염 키 0건을 재확인했다.
③ **수정 후 같은 오염에서 전체 스위트 767 passed** (두 창 **동시** 오염). 셸만 오염시킨 재확인도 767 passed.

**AC#3 (같은 노출 훑기) — 이 태스크가 지목한 2곳이 아니라 4곳이었다.**
| 자리 | 어떻게 찾았나 | 처리 |
|---|---|---|
| `tests/unit/test_config.py` | 원장이 지목 | `_env_file=None` + `_no_settings_env` 픽스처 |
| `tests/integration/test_gateway.py` | 원장이 지목 | `_settings()` 에 `_env_file=None` + 그 테스트에 `delenv("DRILL_COUNT")` |
| **`tests/unit/test_claude_schema.py`** | **내가 훑어 찾았다** (`settings.\w* ==` grep) — `claude_model_id` 를 리터럴로 단정한다 | `_test_settings()` 에 `_env_file=None` + `delenv("CLAUDE_MODEL_ID")` |
| **`tests/integration/test_ws.py`** | **전체 스위트를 오염 상태로 돌려 찾았다** — `drill_turns_expected` 가 `297 == 12` 로 깨졌다 | `ws_app` 픽스처에 `pin_settings_env` |
| `tests/integration/test_worker.py` | 위 픽스처의 자매(docstring 이 서로를 가리킨다) | `app_settings` 에 같은 배선 (선제) |
⚠️ **전체 스위트를 오염 상태로 돌리는 것이 grep 보다 강한 훑기였다** — grep 으로 못 찾은 4번째를 그것이 찾았다.

**AC#1 (격리 보장) — 방법을 셋으로 갈랐고 근거가 각각 다르다.**
1. **선언값 단정** `test_declared_defaults_are_immune_to_the_environment` 신설. `Settings.model_fields[…].default` 는 **클래스**에 있어 **두 창 어느 것도 닿을 수 없다.** 실측: `DRILL_COUNT=9 SHADOWING_REPEAT_COUNT=7 SHADOWING_PLAYBACK_RATE=1.75` 프로세스에서 선언값은 `5·1·1.0` 그대로였고 인스턴스는 `9·7·1.75` 로 오염됐다. **⛔ 이것이 무력화할 수 없는 tripwire 다** — 깨지는 유일한 경로가 「누가 config.py 의 기본값을 바꾼 것」이고 그것이 우리가 알고 싶은 사건이다.
2. **단위 테스트**: `_env_file=None`(파일 창) + `_no_settings_env` 픽스처(셸 창). 픽스처는 키 목록을 손으로 들지 않고 **`Settings.model_fields` 에서 유도**한다 → 필드가 늘면 자동으로 따라온다(AC#3 의 구조적 답). ⛔ `database_url` 은 남긴다 — 전역으로 지우면 conftest 의 DB 픽스처가 죽는다.
3. **통합 테스트**: `pin_settings_env` (`tests/conftest.py`). ⚠️ **여기서 한 번 틀렸고 고쳤다** — 처음엔 「지우기」로 구현했는데 **`.env` 파일이 그 자리를 대신 채워** `test_ws` 가 계속 red 였다. 앱은 자기 `get_settings()` 를 읽으므로 `_env_file=None` 을 쓸 수 없다 → **선언된 기본값으로 못 박는 것**으로 바꿨다(우선순위가 `init kwargs > 환경변수 > .env` 이므로 환경변수에 기본값을 심으면 두 창이 한 번에 닫힌다). 못 박을 수 없는 것(필수 `database_url` · 기본값이 `None` 인 자격증명 넷)은 지운다.
⚠️ **대소문자 결함도 고쳤다** — `model_config` 의 `case_sensitive` 가 **`False`** 라 `Drill_Count` 같은 변형도 값을 먹인다. `delenv(NAME.upper())` 만으로는 남으므로 `os.environ` 을 훑어 대소문자 무관하게 지운다.

**게이트 (이 턴에 직접 돌렸다)**: **767 passed**(기준선 766 + 신규 tripwire 1) · `ruff check .` exit 0 · `ruff format --check .` 33 files · `ty check` exit 0 · 게이트 밖 `ruff` **6 errors** · `format --check ../../tests` **4 files**.
⚠️ **`ty` 억제 3건을 새로 달았다** — `_env_file` 이 pydantic-settings 가 런타임에 합성하는 인자라 `ty`(alpha)가 `unknown-argument` 로 본다. 리포에 같은 이유의 `# ty: ignore[missing-argument]` 선례가 있다.
⛔ **사고 하나를 내고 되돌렸다**: `ruff check --fix ../../tests/` 를 넓게 돌려 **범위 밖 `tests/harness/**` 3파일**이 고쳐지고 게이트 밖 기준선이 **6 → 3** 으로 줄었다. 그 6건은 `TASK-37` AC#6 이 소유한 **유지값**이라 `git checkout` 으로 되돌리고 6 을 재확인했다. **교훈: `--fix` 를 디렉터리에 걸지 않고 내가 건드린 파일에만 건다.**
<!-- SECTION:NOTES:END -->
