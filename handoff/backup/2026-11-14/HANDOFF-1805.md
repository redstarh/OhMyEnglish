# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-11-01 14시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-11-01/HANDOFF-1400.md`** (그 앞 판들은 같은 폴더와 날짜별 폴더).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/design/**` · 회차 노트(`tests/agent/runs/**/result.md`)**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **다음 한 걸음은 `TASK-303` AC3 — 실제 Nova 회차**. 백엔드 수정(`f33ec27` · `4dc472c`)은 끝났고
   남은 것은 실물 확인뿐임: 영어 「Hey, end the lesson.」 뒤 확인 단계(보류된 확정 → 코치가 다시 물음 →
   Yes → 종료) · 확인 질문 뒤 학습 문장이 `learning` 으로 남는지 · 요청 만료 때 화면의 확인 안내가
   지워지는지. 회차 b10 의 입력 음성 생성기(`tests/agent/runs/2026-11-01-b10/synth.sh` · `compose.py`)를 씀.
2. ⛔ **결정 대기 `TASK-308`** — 390 폭 아래쪽 입구로 세션을 시작하면 카드가 화면 밖. 사용자에게 물어야 함.
3. ⛔ **스택은 실행 아이콘이 띄운 상태임** — `~/Applications/OhMyEnglish.app`. 백엔드 `:8002` =
   `VOICE_ADAPTER=nova` · dev DB · SSO 임시 자격증명(13:58 기준 약 12시간 유효) · 부모 launchd.
   프런트 `:3000` = 이 리포의 `next dev`. 실행 스크립트 정본은 `scripts/launcher/launch.sh`.
4. ⛔ **서버는 샌드박스(내 셸)에서 띄우지 않음**(사용자 지시) — 아이콘(`open`)이나 `launchctl submit`.
   회차용 백엔드는 `launchctl submit -l local.ohmyenglish.testbackend` 로 띄우고 끝나면 `launchctl remove`.
   ⚠️ 회차 중에는 사용자 브라우저도 시험용 서버에 붙음 — 시작 전에 알림(11:40 에 사용자 학습 4건이
   격리 DB 로 간 일이 있었음).
5. ⛔ **회차는 격리 DB `ohmyenglish_course_paid`** 에서 돌림. dev DB 기준선(14:00 직접 조회):
   learning_sessions 22 · utterances 145 · course_day_progress 1 · course_attempts 0.
   ⚠️ `/course/<day>` 와 홈 문장 연습은 열기만 해도 진도를 저장함.
6. ⛔ **Bedrock**: Nova 양방향 스트림은 API 키(bearer)를 거부함 · IAM 사용자 정책은 리전이 `us-west-2`
   뿐이라 `us-east-1` 이 거부됨(안내 `docs/ops/2026-11-01-iam-nova-permission-guide.html` · AWS 정책은
   사용자 몫). 실제 Nova 는 SSO(`kjihoon-bedrock`) 임시 키로만 됨.
7. ⚠️ **화면**: 영어 · 밝은 테마 · 사이드바. 홈 「Start speaking」 = 문법 코스 문장 연습(영상 없음)을
   오늘의 연습 카드 안에서 · 홈에서 추천 코치 대화는 빠짐(사용자 결정). 카드는 고정 높이
   (1400 528px · 390 672px) · 창 스크롤 이동 없음. 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §3.
8. ⚠️ 사용자 시나리오 화면 보드: `docs/ux/2026-11-01-user-scenarios/index.html` (실제 앱 화면 70단계).

## 인계 지표 4개

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`e2e86c0`** · `origin` 과 **0/0** (이 판을 담은 커밋은 `git log -1` 로 읽음) |
| 2 | 다음 한 걸음 | **`TASK-303`** AC3(실제 Nova 회차) — 그 밖에 결정 대기 `TASK-308` |
| 3 | 게이트 | 내가 측정(14:00) — 백엔드 `pytest` **1495 passed** · `ruff` 0 · `ruff format` 341 files · `ty` 0 · 하네스 게이트 112 passed · 프런트 `tsc` 0 · `eslint` 0 · `next build` 0. 측정 뒤 바뀐 것은 이 인계 파일과 원장뿐임 |
| 4 | 착수 전 필수 | 미결 승인 0 · 결정 대기 1(`TASK-308`) · 진행 중 1(`TASK-303`) |

## 이번 세션 요약 (2026-11-01 오전~오후)

- 영어 음성 명령 실물 확인(`TASK-300` · 영어 7/7 · 한국어 1/6) → 화면 안내를 영어 명령으로
- 세션을 오늘의 연습 카드 안에서(`TASK-301`) · 모든 화면 메뉴 전수 회차(`TASK-302`)
- 백엔드 음성 명령 확인 단계 결함 수정(`TASK-303`, 실물 확인 남음)
- 홈 Start speaking = 문장 연습 · 코치 대화 제거(`TASK-304`) · 머리 섹션 제거(`TASK-305`)
- 사용자 시나리오 화면 보드(`TASK-306`) · 카드 고정 높이·아래 영역 축소(`TASK-307`)
- `TASK-299` 는 사용자 결정으로 진행하지 않음

## 다음 세션이 먼저 볼 것

`TASK-303` 회차 전에 사용자에게 「회차 동안 앱이 시험용 서버에 붙는다」를 알리고 시작함.
`TASK-308` 은 AskUserQuestion 으로 물음. 답이 오면 그 턴에 `In Progress` 로 되돌림.

> 인계 확인(2026-11-01 14시대): 후속 탭 「OhMyEnglish — TASK-303 실물 회차 이어 가기」가 지표 4개를 직접 대조함 — 차이 없음. 이전 세션이 대조 결과를 받아 정리함.
