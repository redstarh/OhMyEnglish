# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-11-14 23시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-11-14/HANDOFF-2316.md`** (그 앞 판들은 `handoff/backup/<날짜>/`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/design/**` · 회차 노트(`tests/agent/runs/**/result.md`)**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **원장 잔여는 `TASK-325`(아이폰 · 사용자 결정으로 미룸) 하나뿐임** — 진행 중 0 · 결정 대기 0.
   회차 b18(고친 뒤 전체 재시험) 뒤 관찰 13건(`TASK-333`) · 영상 testid(`TASK-332`) · 리뷰 반영(`TASK-334`)까지 끝남.
   최신 보고서 `docs/ux/2026-11-14-b18-ux-flow-review/index.html` · 스토리보드 `docs/ux/2026-11-14-b18-user-scenarios/`.
   남은 관찰(태스크 아님 · 진행 여부를 사용자에게 물을 것): 홈 「This week: N / 7 days」가 학습 발화 없는 날도 셈 ·
   Weak spots 결과의 Start again 이 Free talk 제목으로 열림(세션 행이 같음) · 320 폭 결과 칸 18 px 칸 안 스크롤.
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
| 1 | 기준 커밋 | **`70f912b`** · `origin` 과 **0/0** (이 판을 담은 커밋은 `git log -1` 로 읽음) |
| 2 | 다음 한 걸음 | 원장 잔여 `TASK-325`(대기 · 미룸)뿐 — 새 지시를 받음 |
| 3 | 게이트 | 내가 측정(마지막) — 백엔드 `pytest` **1516 passed** · `ruff` 0 · `ruff format` 342 files · `ty` 0 · 프런트 `tsc` 0 · `eslint` 0 · `next build` 0 · `node --test` 53 passed |
| 4 | 착수 전 필수 | 미결 승인 0 · 결정 대기 0 · 진행 중 0 · 대기 1(`TASK-325`) |

⚠️ pytest 는 `app/backend` 에서 **경로 없이** `-k` 로 고름 — 시험 파일 경로를 넘기면 설정(`asyncio_mode`)이
빠져 async 시험이 모두 「지원 안 됨」으로 실패함(2026-11-14 실측 · 그 실패를 빨간 증거로 오인했던 적 있음).
⚠️ 사용자 백엔드는 `--reload` 가 없음 — 백엔드를 고치면 아이콘(`open ~/Applications/OhMyEnglish.app`)으로 다시 띄움.

## 이번 세션 요약 (2026-11-14)

- `TASK-318` Listen·Slow 제거 · 카드 높이 재측정
- `TASK-316` 회차 b16(TestAgent 두 탭 · Playwright) → 새 스토리보드 · 흐름 보고서 · 결함 넷
- `TASK-319` Start speaking 때 창이 튐 · `TASK-320` → 파란 바탕·testid · `TASK-321` 390 영상 잘림 ·
  `TASK-322` 홈과 코스의 Day 상태 불일치(공용 `dayStarted` · 시험 `dashboardData.test.mts`)
- `TASK-323` 사용자 결정 넷(빠른 카드·Grammar course 제거 · `/course` 리다이렉트 · 버튼 통일)
- `TASK-317` 말하는 동안 실시간 표시(Web Speech) · 사용자 실기기 확인 · `TASK-324` Auto 잘림
- `TASK-326` 말한 내용 = 문장 글자 · `TASK-327` 한글 발음 조각 제거 · `TASK-329` 보완안 9건 · `TASK-328` 번역 · KO
- `TASK-330` 회차 b18 전체 재시험 · `TASK-332` 영상 testid · `TASK-333` 관찰 13건 · `TASK-331`·`TASK-334` 리뷰 반영
- `TASK-325` 아이폰 지원은 미룸(Tailscale serve 가 가까운 길)

## 다음 세션이 먼저 볼 것

```bash
backlog task list --plain   # 잔여는 TASK-325 뿐
```
