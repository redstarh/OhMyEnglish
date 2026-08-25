# Handoff — 자동 테스트 하네스

> 이 파일은 **테스트 하네스 작업의 연속성**만 담당한다. 제품·구현 정본은 `handoff/HANDOFF.md`이고
> 그 파일은 다른 세션이 소유하고 있으므로 건드리지 않는다.
> 최종 갱신: 2026-08-26 · 대상 커밋 `3c62770`

## 현재 상태 — 2차수 완료, 루프 일시 종료 (2/10 차수 사용)

| 항목 | 상태 |
|---|---|
| 하네스 절차 문서 | `docs/ops/2026-08-26-test-harness.html` (12절, tmux + Claude Code CLI + CDP) |
| 1차수 리포트(HTML) | `docs/ops/2026-08-26-test-harness-report.html` (스크린샷 임베드) |
| 회차 기록 | `tests/harness/runs/2026-08-26-run-1.md` · `-run-2.md` · 원장 `ROUNDS.md` |
| **F-1** 다크모드 색상 위계 역전 (HIGH) | ✅ **수정 완료**(`3c62770`) — 2차수에서 두 모드 실측 검증 |
| **F-2** `target_form` 불일치 (MEDIUM) | ⏸ **캡틴 결정 대기** — 스키마 변경 필요 |
| 앱 결함 신규(2차수) | **0건** |
| DB | baseline 완전 복원 (세션 2 · 패턴 1 · `frequency` 2) |
| 스택 | 백엔드 `:8002` baseline(`--log-level warning`) · 프론트 `:3000` · podman `ohmy-pg` — 전부 정상 |

## 방금 끝낸 것 (2차수)

- 수정 세션(`claude_air_3-14`)의 완료 보고를 **항목별로 재현 검증** — 커밋·워크트리·토큰·게이트 4개 전부 직접 확인
- **R1/R2**: 세션·결과·실패 화면 3곳 × 다크/라이트 = 전부 AA(4.5:1) 이상 + 확정이 부분보다 높은 대비
  (다크 16.91 vs 7.04 / 라이트 17.93 vs 7.00). 라이트 부분이 원래 2.85:1로 AA 미달이던 것도 해소
- **R3**: F-2 잔존 확인 + **조건 특정** — occurrence 2개 이상이며 서로 다른 `target_form`을 가진 패턴에서만 불일치
- **R4**: teardown 직전 스윕으로 1차수 F-7(미등록 세션) 교정 확인 + baseline 정확 복원
- **신규 커버**: E4(`voice_command` job 0건, W6) · E5(오류 0건 → `corrections: []`) · **E6(재분석 멱등 — W3 종단 최초)** · R8(라이트모드)
- **회귀**: A1 · A2 · B1~B5 · D1(206 passed) · D2(ruff·format·ty clean) · F-3(마이크 33프레임 재현)

## 다음에 할 것 — 우선순위

1. **F-2 스키마 결정(캡틴)** — `target_form`이 패턴 수준 일반형인가 문장별 교정형인가.
   선택지: ① 프롬프트가 일반형을 요구하게 바꾼다 ② `error_occurrences`로 컬럼을 내린다
   (마이그레이션 002 + NOT NULL 백필 + `tests/unit/test_results.py:88` 갱신) ③ 학습 제시 기능이
   의미를 확정할 때까지 API에서 뺀다. **결정되면 3차수를 열고 R3 재검증.**
   재현 최소 입력: `inject_errors.py --scenario E6` 한 문장(occurrence 2개를 두 번 모두 생성 확인)
2. **L계층(학습 제시) 착수 전 캡틴 결정 5건** — `tests/harness/scenarios-E-agent-learning.md`
   §"L계층 착수 전에 캡틴이 정해야 하는 것". 복습 간격 기준 시각 / `task_type` 매핑 /
   `mastery_score` 갱신 규칙 / 복습 대상 범위 / `target_form` 의미(=위 1번)
3. **실음성(N계층) N-0** — AWS 공식 문서에서 Nova Sonic 이벤트 스키마와 오디오 포맷 확정.
   **이것 없이 어댑터 구현 착수 금지.** 상세는 `tests/harness/scenarios-N-real-voice.md`
4. **문서 정합화(비차단)** — `HANDOFF.md`의 테스트 기준선 `201` → **206**

## 재개에 필요한 것

```bash
# 0) 프리플라이트 — 낡은 프로세스 함정 (실제로 걸렸던 항목)
curl -s localhost:8002/health                  # {"status":"ok"} — version 키 있으면 StockAgent다
ps -o lstart= -p $(lsof -nP -iTCP:8002 -sTCP:LISTEN -t)
find app/backend/app -name '*.py' -newermt '<위 시각>'   # 결과 있으면 재기동하고 시작

# 1) 새 차수 열기 — run_id.txt 오염 주의 (2번 재발했다)
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -tAc \
  "insert into harness_runs (git_commit, note) values ('<커밋>','<메모>') returning id" \
  | grep -oE '[0-9a-f-]{36}' | head -1 > .harness/run_id.txt

# 2) 패턴 baseline (teardown 복원 기준) — 지금은 1차수 것이 남아 있다
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -c \
  "drop table if exists harness_pattern_baseline;
   create table harness_pattern_baseline as select id, pattern_key, frequency, last_seen_at
     from error_patterns where user_id='00000000-0000-0000-0000-000000000001';"

# 3) 실행
cd app/backend
.venv/bin/python ../../tests/harness/ws_session.py --scenario A1
.venv/bin/python ../../tests/harness/inject_errors.py --scenario E6
.venv/bin/python ../../tests/harness/measure_contrast.py --shot-prefix /tmp/shot
```

정리 절차(3단계 + baseline 대조)는 `tests/harness/README.md` §정리. **teardown 직전에 미등록
세션 스윕을 반드시 한 번 돌린다** — 브라우저 레그는 자동 등록 훅이 없다.

## 하네스 운영에서 배운 함정 (반복하지 말 것)

| # | 함정 | 대응 |
|---|---|---|
| H-1 | `eval` 안의 `element.click()`은 **user activation을 만들지 않아** `AudioContext.resume()`이 멈춘다 → 화면이 `마이크 권한 요청 중`에서 정지 | 클릭은 CDP 실제 입력(플러그인 `click` 액션)으로만 |
| H-2 | `psql -tAc "insert … returning id"`가 id와 `INSERT 0 1`을 함께 출력해 `run_id.txt`를 오염시킨다 (2회 발생) | `grep -oE '[0-9a-f-]{36}' \| head -1` 고정 |
| H-3 | 브라우저 레그 세션이 부기에서 누락 | teardown 직전 시간창 스윕 |
| H-4 | 공유 dev DB에서 `frequency` 절대값 단정은 반드시 실패 | 델타로 단정 |
| H-5 | 스텁이 지연 0으로 재생 → 브라우저가 오디오 프레임을 못 보내고 전사문 DOM도 못 잡힌다 | 마이크 측정은 B5(무응답 10초) 창에서, 렌더 관측은 이벤트 도착 스로틀로 |
| H-6 | `prefers-color-scheme`은 페이지에서 바꿀 수 없다 | CDP `Emulation.setEmulatedMedia` (`measure_contrast.py`) |

## 세션 간 왕복 규약

- 테스트 세션 → 수정 세션: `tmux send-keys -t claude_air_3-14:0.0 '<한 줄>' Enter`.
  그 세션은 **agents 관리 화면**이므로 텍스트를 넣으면 새 작업이 생성된다(`enter to create`).
  진행 중 작업에 덧붙이려면 `space`로 답장창을 열고 **대상이 맞는지 상태 문구로 확인한 뒤**
  타이핑, 푸터가 `enter to send`로 바뀐 것을 보고 Enter.
- 수정 세션 → 테스트 세션: `tmux send-keys -t claude_air_5-49:0.0 '<한 줄>' Enter`.
- **10차수 상한.** 무한 루프 금지 — 상한에 닿으면 오류가 남아도 캡틴에게 보고하고 멈춘다.
- 역할 분리: 테스트 세션은 앱 코드를 수정하지 않고, 수정 세션은 자기 수정을 합격 판정하지 않는다.

## 미커밋 상태

`docs/ops/2026-08-26-test-harness.html` · `docs/ops/2026-08-26-test-harness-report.html` ·
`tests/harness/**` · 이 파일이 아직 untracked/미커밋이다. 커밋은 캡틴 확인 후.
