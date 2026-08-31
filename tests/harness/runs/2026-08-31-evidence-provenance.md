# 원자료 출처 지도 — `.harness/evidence/` → 커밋 경로 (2026-08-31)

**왜 이 파일이 있는가.** 커밋된 리포트 `docs/ops/2026-08-26-test-harness-report.html`이
`:501`·`:732-733`에서 `.harness/evidence/*.json`과 `.harness/backend*.log`를 **가장 강한 주장의
원자료로 인용**한다. 그런데 `.harness/`는 `.git/info/exclude`로 제외된 작업 디렉터리라
디스크가 지워지면 복원 경로가 없었다. 2026-08-31에 캡틴 지시로 **고유 증거를 커밋했고**,
그 리포트는 스냅샷 규약상 사후 편집하지 않으므로(`docs/backup/superseded/README.md` 규약 1)
**인용을 해석할 대조표를 여기 둔다.**

`.harness/evidence/`는 지우지 않았다 — 작업 디렉터리로 계속 쓰이고, 리포트의 인용 문자열도
이 머신에서는 그대로 해석된다.

## 커밋한 것 — 차수는 문서 근거로 정했다 (추측하지 않았다)

전부 **바이트 동일**을 확인하고 복사했다(`md5`).

| `.harness/` 원본 | 커밋 경로 | 차수를 그렇게 판단한 근거 |
|---|---|---|
| `evidence/C1-session-transcript.png` | `2026-08-26-run-1/` | `2026-08-26-run-1.md:26` — C1 세션 화면 관통 PASS |
| `evidence/C2-partial-gray.png` | `2026-08-26-run-1/` | `2026-08-26-run-1.md:27` — C2 partial→final 전환 PASS |
| `evidence/C3d-connection-failed.png` | `2026-08-26-run-1/` | `2026-08-26-run-1.md:28` — C3 결과 화면 5상태 PASS. `C3d`는 그 중 `연결 실패` 하위 상태다(`docs/ops/2026-08-26-test-harness.html:1010`이 `C3d`↔`B5`↔`연결 실패`로 정의) |
| `evidence/A2-r2-frames.json` | `2026-08-26-run-2/` | `-r2` 접미어가 2차수 재실행분을 뜻한다. 같은 규칙의 `A1-r2`·`B5-r2`가 이미 그 폴더에 있다 |
| `evidence/B2-r2-frames.json` | `2026-08-26-run-2/` | 위와 같다 |
| `evidence/Q3-A1-frames.json` | `2026-08-26-run-3/` | **`2026-08-26-run-3.md:133`이 원자료로 명시**했다 |
| `evidence/Q3-A2-frames.json` | `2026-08-26-run-3/` | 위와 같다 |
| `evidence/Q3-B5-frames.json` | `2026-08-26-run-3/` | 위와 같다 |
| `evidence/E6-injection.json` | `2026-08-26-run-3/` | **`2026-08-26-run-3.md:134`가 원자료로 명시**했다. 2차수 폴더의 같은 이름 파일과 **내용이 다르다** — 3차수 재실행분이고, 2차수분을 덮어쓰지 않았다 |
| `evidence/E1-injection.json` | `2026-08-26-run-4/` | **`2026-08-26-run-4.md:143`이 원자료로 명시**했다. 1차수 폴더의 같은 이름 파일과 **내용이 다르다** — 4차수 재실행분이다 |
| `backend-nova-r4.log` | `2026-08-26-run-4/` | `2026-08-26-run-4.md:143`·`:152`가 원자료로 명시했다(73줄 uvicorn 액세스 로그) |
| `evidence/P-tooluse-nova-protocol.json` | `2026-08-27-P-tooluse-spike/` | 같은 폴더의 커밋본 `P-tooluse-nova-events.json`(8K)은 `note`·`date`가 붙은 **정리본**이고, 이것은 그 뒤에 있는 **원본 프로토콜 덤프**(400K, `usageEvent` 스트림)다. 이름이 달라 충돌하지 않는다 |

## 커밋하지 않은 것

| `.harness/` 원본 | 이유 |
|---|---|
| `backend.log` | `2026-08-26-run-1/backend.log`와 **바이트 동일**하다(MD5 `28c2ecd5…`). 이미 커밋돼 있다 |
| `evidence/` 나머지 9건 | 커밋본과 바이트 동일하다 — `A1`·`A1-r2`·`A2`·`B2`·`B5`·`B5-r2`·`E3`·`E4`·`E5` |
| `run_id.txt` · `caller_pane.txt` | tmux 세션 스크래치다. 리포트가 인용하지 않는다 |

## ⚠️ 소속 불명 2건 — `2026-08-26-unattributed/`

바이트는 살렸으나 **어느 차수 문서도 자기 원자료라고 적지 않았다.** 차수를 추측해서
차수 폴더에 넣으면 증거 기록이 오염되므로 별도 폴더에 두었다. 상세는 그 폴더의 `README.md`.

---

_작성 2026-08-31. 지시: 캡틴 — "`.harness/`의 고유 증거를 커밋해라."_
