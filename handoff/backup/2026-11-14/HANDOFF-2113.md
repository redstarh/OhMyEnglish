# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-11-14 18시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-11-14/HANDOFF-1805.md`** (그 앞 판들은 `handoff/backup/<날짜>/`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/design/**` · 회차 노트(`tests/agent/runs/**/result.md`)**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **다음 한 걸음은 `TASK-317` — 문장 연습에서 말하는 동안 내용을 실시간으로 보임**. 설계
   `docs/design/2026-11-14-live-readback-transcript-design.md`(권장안 C: 브라우저 Web Speech 로 표시 ·
   끝난 문장을 텍스트로 서버가 판정). 사용자 결정 §11-1: Web Speech 사용(소리가 Google 로 감을 수용) ·
   말 없음은 Try 에 세지 않음. 18시대에 구현을 opus 에이전트에 맡겼음 — 결과를 받아 게이트를 직접 돌리고
   codex 리뷰를 거침. AC #4(실제 마이크로 말하는 동안 글자가 보임)는 **사용자가 직접** 확인해야 함
   (§2-2: 시험 Chrome 의 인식기는 가짜 오디오를 전사하지 않음).
2. ⛔ **스택은 실행 아이콘이 띄운 상태임** — `~/Applications/OhMyEnglish.app`. 백엔드 `:8002` =
   `VOICE_ADAPTER=nova` · dev DB · SSO 임시 자격증명 · 부모 launchd. 프런트 `:3000` = 이 리포의 `next dev`.
3. ⛔ **서버는 내 셸에서 띄우지 않음**(사용자 지시) — 아이콘(`open`)이나 `launchctl submit`.
   회차용 백엔드는 `launchctl submit -l local.ohmyenglish.testbackend`(격리 DB `ohmyenglish_course_paid`)로
   띄우고 끝나면 `launchctl remove` 뒤 아이콘으로 복원. 회차 전에 사용자에게 알림.
4. ⛔ **TestAgent 실측(회차 b16)**: 전용 런처 `~/.claude/test-agent/run.sh` 안에서는 Playwright 가
   브라우저를 띄우지 못함(SIGTRAP) → 샌드박스 밖 헤드리스 Chrome 을 띄우고 `connectOverCDP`. 헤드리스
   TestAgent 는 복합 셸 명령에 승인을 요구 → 단일 명령만. Playwright 1.58.2 는 `tests/agent/tools/`.
   Paseo 탭에서 대화형으로 돌리면 승인 요청이 뜸 — `paseo terminal capture` 로 감시함.
5. ⚠️ `/course/<day>` 와 홈 문장 연습은 열기만 해도 진도를 저장함(같은 위치를 다시 씀). dev DB 를
   바꾸지 않으려면 Start 를 누르지 않거나 저장 요청을 `page.route` 로 막음.
6. ⚠️ **화면**: 메뉴는 Home 하나 · 학습은 홈 Today's practice 에서만(`/course`·`/course/<day>` 는 홈으로
   리다이렉트) · 빠른 카드·Grammar course 제거 · 이동·실행 버튼은 모두 `omy-button`. 설계서
   `docs/design/2026-11-01-v0-home-redesign-design.md` §3 이 정본.
7. ⚠️ 새 스토리보드 `docs/ux/2026-11-14-user-scenarios/index.html`(12장면) · 흐름·논리 점검 보고서
   `docs/ux/2026-11-14-ux-flow-review/index.html`(`build.py` 로 생성). 보고서 §2 의 B~E 보완안 중
   사용자 결정이 아닌 것(기간 문구 · Back→Previous · 기록 날짜 줄 연결 등)은 **아직 태스크가 아님** —
   진행할지 사용자에게 물어야 함.

## 인계 지표 4개

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`13cbe5c`** · `origin` 과 **0/0** (이 판을 담은 커밋은 `git log -1` 로 읽음) |
| 2 | 다음 한 걸음 | **`TASK-317`**(In Progress · AC 2/4) — 구현 결과 수신 · 게이트 · 리뷰 · 사용자 실물 확인 |
| 3 | 게이트 | 내가 측정(18시대 · 프런트만 바뀜) — 프런트 `tsc` 0 · `eslint` 0 · `next build` 0 · `node --test` 4 passed · 하네스 112 passed. 백엔드는 이 세션에서 바뀌지 않음(마지막 측정 11-01: pytest 1495 · ruff 0 · ty 0) |
| 4 | 착수 전 필수 | 미결 승인 0 · 결정 대기 0 · 진행 중 1(`TASK-317`) |

## 이번 세션 요약 (2026-11-14)

- `TASK-318` Listen·Slow 제거 · 카드 높이 재측정
- `TASK-316` 회차 b16(TestAgent 두 탭 · Playwright) → 새 스토리보드 · 흐름 보고서 · 결함 넷
- `TASK-319` Start speaking 때 창이 튐 · `TASK-320` → 파란 바탕·testid · `TASK-321` 390 영상 잘림 ·
  `TASK-322` 홈과 코스의 Day 상태 불일치(공용 `dayStarted` · 시험 `dashboardData.test.mts`)
- `TASK-323` 사용자 결정 넷(빠른 카드·Grammar course 제거 · `/course` 리다이렉트 · 버튼 통일)
- `TASK-317` 원인 측정(30초 빈 대기 · 고정 녹음 창) · 설계 · 0단계 G2 측정

## 다음 세션이 먼저 볼 것

```bash
backlog task view TASK-317 --plain
```
