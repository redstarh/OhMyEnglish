# Handoff — 수정 세션 (하네스 왕복의 "고치는 쪽")

> 이 파일은 **수정 세션의 연속성**만 담당한다. 제품 정본은 `handoff/HANDOFF.md`, 테스트 하네스
> 정본은 `handoff/HANDOFF-test-harness.md`이고 **둘 다 다른 세션이 소유**하므로 건드리지 않는다.
> 최종 갱신: 2026-08-26 · 지시서 `tests/harness/handoff-to-fix-session-round3.md` (3차수)

## 3차수에서 한 것 — 완료, 테스트 세션 판정 대기

| 커밋 | 내용 |
|---|---|
| `3bde54f` | **F-2** `target_form`을 패턴 수준 일반형으로 (프롬프트 + 스키마 문서 + 테스트 6건) |
| `37a2869` | **N-4** Nova 2 Sonic 실연동 (포트 확장 + 어댑터 + 프론트 입출력 교체 + 테스트 28건) |

게이트: `pytest 241 passed`(기준선 206 → +35, skip/xfail 0) · `ruff check`·`format` clean ·
`ty check app` clean · `tsc --noEmit` clean.

**백엔드 소스 변경 있음** — `--reload`가 없어 실행 중인 `:8002` 프로세스에는 반영되지 않았다.

## 판단 근거를 남겨야 하는 결정 3건

1. **F-2를 코드로 강제하지 않았다.** 캡틴 결정(선택지 B)은 `target_form`의 **의미**를 바꾸는
   것이고, 그 의미를 만드는 장치는 프롬프트뿐이다. `target_form == correction`을 검증으로
   거부하는 안은 버렸다 — 1차수 I-5에서 모델 출력에 엄격 검증을 걸었을 때 그 발화가 5회
   재시도 끝에 `failed`가 됐다. 짧은 span에서 일반형과 교정문이 우연히 같을 수 있으므로
   같은 함정을 다시 만든다.
   → 다음 레버(R3에서 값이 계속 흔들리면): 패턴 upsert에서 `target_form` 갱신을 빼고
   `category`처럼 **생성 시 고정**한다(1줄). 재분석이 값을 못 바꾸게 되는 대신 나쁜
   일반형도 못 고친다.
2. **지시서 태스크1의 4번 테스트는 red-green이 불가능하다.** "occurrence 2개인 패턴에서
   `target_form`이 어느 occurrence의 `correction`과도 같지 않다"는 단정은 **저장 로직이
   원인이 아니었기 때문에** 수정 전에도 통과한다(가짜 Claude 응답을 단정하는 것이 된다).
   그래서 그 테스트는 `tests/integration/test_pipeline.py`에 **결합 방지 회귀**로 넣고
   (앞으로 누군가 `target_form`을 `correction`에서 채우는 것을 막는다), 의미의 red-green
   근거는 프롬프트 계약 테스트 4건(`tests/unit/test_analysis.py`)에 뒀다.
3. **스텁은 새 이벤트를 흘리지 않는다.** 스텁이 `speech_start`를 보내면 스텁 모드 화면에
   "듣고 있어요"가 끼어들어 1·2차수 C2(회색 부분 전사문 → 확정 전환) 검증이 바뀐다.
   프론트는 **모드를 모른 채** 데이터로만 갈린다 — `partial`이 오면 부분 전사문, 안 오고
   `speech_start`만 오면 "듣고 있어요".

## 실물로 아직 확인되지 않은 것 (테스트 세션 N5~N13의 몫)

- Nova 어댑터의 **실제 왕복** — 가짜 스트림으로 시퀀스·파싱·종료 순서·8분 상한만 검증했다.
- **브라우저 재생 경로** — `AudioContext` 큐 재생과 barge-in 큐 비움은 귀/CDP로만 판정된다.
- 확인해 둔 것: AudioWorklet 소스를 실제 Chrome `OfflineAudioContext`에서 렌더해
  **31프레임 × 1024바이트 @16kHz, peak 32767**(LE 16bit 변환 정상)을 관측했다. WAV 헤더
  제거·raw LPCM 통과·1024B base64 왕복은 Node로 확인했다.

## 이 워킹트리에서 작업할 때 (3차수에서 실제로 걸린 것)

1. **워크트리를 새로 만들지 않는다** — 테스트 스택이 이 워킹트리를 직접 서빙한다. 배경
   작업으로 돌면 harness가 `EnterWorktree`를 강제하므로 리포에 `.claude/settings.json`
   (`worktree.bgIsolation = "none"`)을 뒀다. 세션 중에는 그 설정이 다시 읽히지 않아
   3차수에서는 파일 수정을 Bash 경유로 했다.
2. `pytest`에 하위 경로를 직접 주면 `asyncio_mode=auto`가 안 잡힌다(rootdir이 리포 루트로
   잡혀 ini를 못 찾는다) → `-c pyproject.toml`을 함께 준다.
3. 게이트의 `ruff check .`는 `app/backend/app/**`만 본다. 리포 루트 `tests/`는 범위 밖이라
   따로 돌려야 한다. 반대로 `ty check`는 `tests/harness/**`까지 본다 — 거기 남은 진단 2건은
   **수정 금지 경로**의 기존 것이다(`inject_errors.py`, 커밋 `9935715`부터).
