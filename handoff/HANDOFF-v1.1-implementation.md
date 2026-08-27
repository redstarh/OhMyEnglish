# Handoff — 요구사항 v1.1 구현 (발음 시범·재발화 / 추천 학습 루틴)

> 이 갈래의 연속성만 담당한다. 제품 정본은 `handoff/HANDOFF.md`, 하네스는
> `handoff/HANDOFF-test-harness.md`, 수정 세션은 `handoff/HANDOFF-fix-session.md`다.
> 최종 갱신 **2026-08-27** · 기준 커밋 **HEAD ≥ `a02cae5`** · 브랜치 `design/first-vertical-slice`
>
> **다음 한 걸음: 계획 Task 4(시도 생명주기 서비스) → Task 5(Nova 어댑터).**

---

## 0. 다음 세션이 30초 안에 알아야 할 것

1. **요구사항이 v1.1로 올라갔다.** 신규 2건 — `PRD.md` **§10 발음 시범·재발화**, **§11 학습 이력 기반 추천 학습 루틴**.
2. **§10은 구현 중이고 9태스크 중 3개가 끝났다.** 계획: `docs/design/2026-08-27-pronunciation-echo-plan.md`
3. **§11은 설계만 끝났고 코드가 0줄이다.**
4. **지금 앱을 돌리면 발음 교정은 여전히 일어나지 않는다** — Nova 지시문(Task 5)이 없고 DB 저장(Task 6)이 없다. 토대 3개만 깔렸다.
5. 게이트를 돌릴 때 **cwd가 `app/backend`여야 한다**(§4).

---

## 1. 실측값 (2026-08-27, 이 handoff를 쓴 턴에 직접 실행)

```bash
cd app/backend && .venv/bin/pytest -q          # 269 passed
cd app/backend && .venv/bin/ruff check .        # All checks passed!
cd app/backend && .venv/bin/ruff format --check .  # 26 files already formatted
cd app/backend && ty check                      # All checks passed!
cd app/backend && .venv/bin/ruff check ../../tests ../../scripts   # Found 6 errors (베이스라인)
```

| 항목 | 값 |
|---|---|
| 테스트 | **269 passed** (v1.1 착수 전 기준선 241 → +28), skip/xfail 0 |
| ruff · format · ty | 전부 clean |
| `tests/**` ruff | **6건 잔존** — 하네스 5차수 정리 대상. 늘어나지 않았다 |
| dev DB | 마이그레이션 **2개**(001·003) · 세션 2 · 패턴 1 · `pronunciation_attempts` **0행** |
| 미커밋 | `.claude/settings.json`(untracked) — **지우지 마라**, 하네스의 "워크트리 금지"가 의존한다 |

---

## 2. 이번 세션이 한 것 — 커밋 8개

| 커밋 | 내용 |
|---|---|
| `c02dddb` | 문서 정합화 — 폐기 문서 이관, 카테고리 코드값 통일 |
| `c138190` | **요구사항 v1.1** — `PRD.md` §10·§11 신설, v1.0 사본 백업 |
| `d696043` | 설계 — 발음 설계서 신설 + 학습 코치 설계서 **정본 승격**(미결 3건 종결) |
| `167592a` | 구현 계획 9태스크 (TDD) |
| `f7b8ccc` | **003 마이그레이션** `pronunciation_attempts` |
| `a0eff8e` | **tool 페이로드 검증 모델** |
| `e6833c9` | **포트 확장** `PronunciationEvent` + 세션 분기 |
| `a02cae5` | 요구사항 v1.1 공유용 스냅샷 (Slack #clawair 전송) |

---

## 3. 남은 작업 — 계획 Task 4~9

정본: `docs/design/2026-08-27-pronunciation-echo-plan.md` (각 태스크에 실제 코드와 예상 passed 수가 있다)

| # | 태스크 | 현재 상태 (2026-08-27 grep 실측) |
|--:|---|---|
| **4** | **시도 생명주기 서비스** | `app/backend/app/services/pronunciation.py` **파일 없음** |
| **5** | **Nova 어댑터 연결** ← 가장 값이 크다 | `toolConfiguration` 0곳 · `toolUse` 0곳 · `SYSTEM_PROMPT` 발음 규칙 **0곳** |
| **6** | 세션 저장·한글 신호·종료 수렴 | `record_attempt` 0곳 · 한글 감지(`가-힣`) 0곳. 현재는 **방송만** 한다 |
| **7** | 패턴 연결 (`error_patterns` upsert) | 0곳 |
| **8** | 결과 화면 발음 카드 | 백엔드 0곳 · 프론트 **0파일** |
| **9** | 하네스 5차수 P9~P12 | 미작성 |

**Task 5까지 하면 학습자가 실제로 발음 피드백을 받기 시작한다.** 스파이크로 동작을 이미 확인한 부분이다(§5).

### §11 (추천 학습 루틴) — 별도 계획이 아직 없다

설계서 `docs/design/2026-08-25-learning-coach-agent-design.md`(정본) §12.1의 **2슬라이스**로 가기로 결정됐다. 계획 문서를 쓰는 것이 첫 걸음이다.

| 확인 항목 | 실측 |
|---|---|
| 테이블 `session_plans`·`learner_notes`·`pattern_attempts` | **전부 없음** (003의 `pattern_attempts` 언급은 "왜 합치지 않는가" **주석**이다) |
| 컬럼 `next_review_at`·`mastery_score`·`review_tasks`·`current_level`·`self_difficulty`·`impact_score`·`suggested_contexts` | **각 앱 참조 0곳** |
| `sessions.py:29` | 여전히 `order by created_at, id limit 1` — 고정 시나리오 1개 |
| `port.py` `start()` | 인자 없음 — 지시문을 넘길 자리가 없다 |

**권고 순서**: §10 Task 4~6 → §11 슬라이스 1(데이터 유실 정지) → §10 Task 7~8 → §11 슬라이스 2.
슬라이스 1을 먼저 하는 이유: `suggested_contexts`는 모델이 산출해도 지금 **버려지고 소급이 불가능하다**.

---

## 4. 반복하지 말 것 (이번 세션에 실제로 걸린 함정)

| # | 함정 | 대응 |
|---|---|---|
| **H-A** | **게이트의 cwd가 판정의 일부다.** 리포루트에는 ruff 설정이 없어 거기서 돌리면 기본 규칙으로 `check .` **56 errors** · `format --check .` **21 files**가 난다. 회귀가 아니다 | 반드시 `cd app/backend` 후 판정. 이 handoff를 쓰다가 나도 한 번 걸렸다 |
| **H-B** | `python3 scripts/migrate.py`는 **돌지 않는다** — 시스템 python에 asyncpg가 없다 | `app/backend/.venv/bin/python scripts/migrate.py` |
| **H-C** | `git add -A`가 `.claude/settings.json`을 끌어들인다 | 경로를 명시해 add한다 |
| **H-D** | **유니온 타입을 넓히는 변경은 모든 소비처와 함께 착지해야 한다.** `AdapterEvent`에 5번째 타입을 넣자 `ty`가 `session.py`의 `event.kind`를 잡았다 — 분기가 없으면 런타임 `AttributeError`로 세션이 죽는다 | 포트 확장과 `isinstance` 분기를 한 커밋에 |
| **H-E** | `db_conn` 픽스처는 테스트 하나를 **트랜잭션 하나**로 감싼다. CHECK 위반이 트랜잭션을 abort시켜 **한 테스트에 `pytest.raises`를 두 번 넣을 수 없다** | 음성 케이스마다 테스트를 쪼갠다 |
| **H-F** | `ty`는 `tests/`까지 본다. 억제 주석은 **오류가 보고되는 그 줄**에 붙여야 한다(호출 첫 줄에 붙이면 `unused-ignore` 경고) | `bogus=1,  # ty: ignore[unknown-argument]` |
| **H-G** | macOS에 `tac`이 없다 | `tail -r` 또는 `git log --reverse` |
| **H-H** | `PRD.md`는 `:29`~`:117`, `requirements-summary.md`는 `:15`~`:60`이 **줄 단위로 인용**된다(실측 13곳·5곳) | 새 내용은 **문서 끝에만** 추가. 기존 절은 **한 줄 → 한 줄** 교체만. 규약은 각 문서 맨 아래 |

---

## 5. 결정과 근거 (뒤집지 말 것 — 뒤집으려면 근거를 반박해야 한다)

**① 발음 판정 주체 = Nova (전사문 경로 아님).**
4차수 P2가 실측했다 — 음소를 치환해 발음해도 ASR이 원문으로 복원해 전사문에 흔적이 **0**이다. 전사문만 받는 분석 워커는 **원리적으로** 발음을 판정할 수 없다. `services/analysis.py:48`의 금지 카테고리 설정은 옳다.

**② Nova tool use가 동작한다 — 그리고 지시하면 Nova가 실제로 교정한다.**
2026-08-27 스파이크(`tests/harness/runs/2026-08-27-P-tooluse-spike/`, git 추적). `promptStart.toolConfiguration`이 받아들여지고 `contentStart(type=TOOL,role=TOOL)` → `toolUse` → `contentEnd(stopReason=TOOL_USE)` 순서로 온다. `inputSchema.json`은 **JSON 문자열**이어야 한다.

Nova가 실제로 낸 응답: *"Say this after me: I think I found three very useful videos."* → *"Now you repeat that sentence for me."*

→ **4차수의 "Nova도 발음을 지적하지 않았다"는 능력 부재가 아니라 지시 부재였다.** 이 결론이 캡틴의 "수정 보류" 결정을 뒤집은 근거다.

재현: `cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1m.wav --tools`

**③ Nova는 재발화 *전에* tool을 부른다** (`outcome: "pending"`, `spoken_form: "[awaiting user repetition]"`).
그래서 시도를 **2단계 생명주기**로 모델링한다: `pending` INSERT → 판정 UPDATE → **세션 종료 시 남은 `pending`을 `unclear`로 수렴**. 마지막 규칙이 핵심 방어다 — `pending`을 영구히 남기면 미판정 시도가 숙련도를 왜곡한다.

**④ Nova가 스키마 enum을 어겼다** (`pending`은 내가 준 enum에 없던 값).
그래서 ⓐ `pending`을 정식 값으로 승격했고 ⓑ 페이로드를 **신뢰하지 않고 강등·폐기**한다. 엄격 검증으로 거부하지 않는 이유는 전례다 — 1차수 I-5에서 모델 출력에 엄격 검증을 걸었을 때 발화가 5회 재시도 끝에 `failed`가 됐다.

**⑤ 교정 예산 = B안.** 일반 세션은 문법 우선, 발음은 보조 신호가 뜬 경우만 개입. 발음 집중은 추가 학습 메뉴의 독립 항목. 근거: 안 들리는 일은 드문데 매 턴 예산을 뺏기면 핵심 루프가 흔들린다.

**⑥ 학습 코치 설계서 미결 3건 종결.** 최근 창 14일 **유지** / 정답 판정은 **두 경로 병존**(문법=분석 워커, 발음=Nova tool) / `impact_score` **영구 제외**.

**⑦ `pronunciation_attempts`를 `pattern_attempts`와 합치지 않는다.** 그 표는 `unique(pattern_id, utterance_id)`로 "패턴이 있는 발화의 재발화"를 센다. 발음 시도는 패턴이 아직 없을 수 있고, tool 호출이 발화가 아니며, `target_form`·`signal_source`처럼 자리가 없는 필드를 갖는다.

---

## 6. 미결 — 소유자별

### 캡틴 결정 대기

1. **`toolResult`를 Nova에 돌려보내야 하는가.** 스파이크에서 안 보냈는데 `END_TURN`으로 정상 종료했지만 **1회 관측**이다. 다중 턴에서 멈추는지 미검증. **기본안: 보내지 않는다.** 확인 방법은 `--tools`에 2턴 주입을 더하는 것.
2. **`agent_reprompt` 보조 신호를 유지할 가치가 있는가.** 문구 매칭이라 취약하다. **첫 구현에서 제외했고 그래서 R10-4의 절반이 미충족이다.** 5차수 관측 후 판정.
3. **발음 `pattern_key`의 값역.** `target_sound`를 Nova가 만들면 키가 흩어질 수 있다(`th_as_s` vs `theta_to_s`). **기본안: §5.6 규약 재사용**(기존 키 주입 + 재사용 우선).
4. 이월 중인 기존 게이트 3건 — 실물 마이크 1회 / 발음 픽스처 보정 / M계층 반영 단위(A·B 함께 쓰기)

### 내 작업

- **계획 Task 7의 버그를 미리 잡아 두었다**: `error_patterns.target_form`이 **not null**이라 계획에 쓴 upsert가 그대로면 실패한다. 값을 채워야 한다.
- 계획 Task 6·8의 테스트 본문에 `...`가 남아 있다 — 기존 `test_gateway.py`·`test_results.py`의 가짜 어댑터 헬퍼 이름을 확인하지 않았다. **파일을 열어 재사용**하고 새로 만들지 않는다.
- `tests/**` ruff 6건 — 하네스 5차수에서 정리
- **추적 체크리스트 HTML** (캡틴 요청) — 요구사항 상세 기능이 설계·구현에 실제로 반영됐는지 대조표. 구현이 끝난 뒤 만든다

---

## 7. 다음 세션 진입 절차

1. 이 파일과 `handoff/HANDOFF.md`를 읽는다 (CLAUDE.md `<handoff>` 규약).
2. `git log --oneline --reverse c02dddb~1..HEAD`로 위 커밋 표와 대조 (**HEAD ≥ `a02cae5`**).
3. 게이트 4개를 **`app/backend` cwd에서** 돌려 §1의 수치와 일치하는지 확인한다. 다르면 그 차이를 먼저 설명한다.
4. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다.
5. 계획 `docs/design/2026-08-27-pronunciation-echo-plan.md`의 **Task 4**부터 TDD로 진행한다.
6. **각 태스크 완료 직후 이 파일을 갱신한다** — 별도 지시를 기다리지 않는다.

## 8. 관련 문서

| 문서 | 역할 |
|---|---|
| `docs/PRD.md` (v1.1) | **요구사항 정본.** §10·§11이 이 작업의 근거 |
| `docs/requirements-summary.md` (v1.1) | 학습자 관점 요약, PRD와 같은 버전 |
| `docs/share/2026-08-27-requirements-v1.1.md` | Slack 공유용 스냅샷 (파생본 — 손으로 고치지 말 것) |
| `docs/design/2026-08-27-pronunciation-echo-design.md` | §10 설계 (4 Lenses · PS1~PS10) |
| `docs/design/2026-08-27-pronunciation-echo-plan.md` | §10 **구현 계획 9태스크** |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | §11 설계 (**정본 승격**, 2슬라이스) |
| `docs/storyboard.html` | 03b 발음 시범 · 03c 추천 루틴 화면 |
| `tests/harness/runs/2026-08-27-P-tooluse-spike/` | tool use 실증 원자료 |
| `docs/backup/superseded/README.md` | 폐기 문서 규약 (수정 금지) |
