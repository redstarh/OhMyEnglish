# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-11-01 05시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-11-01/HANDOFF-0457.md`** (그 앞 판들은 같은 폴더의 날짜별).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/design/**` · 회차 노트(`tests/agent/runs/**/result.md`)**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **원장 잔여는 사람의 결정 1건뿐임** — `TASK-299`(백엔드가 만드는 한국어 문구를 영어로 바꿀지).
   사용자가 답하기 전에는 손대지 않음. 그 밖의 `To Do`·`In Progress` 는 0건임.
2. ⛔ **스택은 실행 아이콘이 띄운 상태임** — `~/Applications/OhMyEnglish.app`(바탕화면 별칭).
   백엔드 `:8002` = `VOICE_ADAPTER=nova` · dev DB · SSO 임시 자격증명 · 부모 launchd.
   프런트 `:3000` = 이 리포의 `next dev`. 실행 스크립트 정본은 `scripts/launcher/launch.sh`(`TASK-291`).
3. ⛔ **사용자 지시: 서버를 샌드박스(내 셸)에서 띄우지 않음.** 띄울 때는 아이콘(`open`)이나
   `launchctl submit` 을 씀. 회차용 백엔드도 그렇게 띄웠고 끝나면 `launchctl remove` 로 내렸음.
4. ⛔ **SSO 임시 자격증명은 2026-11-01 13:25 KST 에 만료됨** — 그 뒤 실제 Nova 를 쓰려면 아이콘을
   다시 누름(세션이 30분 미만이면 `aws sso login` 창을 띄움). Bedrock API 키는 Nova 양방향 스트림에서
   거부됨(응답 본문 「This operation does not support API Keys」 · `TASK-288`).
5. ⛔ **IAM 사용자 `ohmyenglish-local` 의 정책은 리전이 `us-west-2` 로만 적혀 있어 거부됨**(앱은
   `us-east-1`). 고치는 법은 `docs/ops/2026-11-01-iam-nova-permission-guide.html`(`TASK-290`).
   ⛔ AWS 정책은 내가 바꾸지 않음 — 사용자의 몫임.
6. ⛔ **회차는 dev DB 가 아니라 격리 DB `ohmyenglish_course_paid` 에서 돌림** + `VOICE_ADAPTER=stub`
   (리디자인 설계서 §8). ⚠️ `/course/<day>` 는 열기만 해도 5초마다 진도를 저장함 — 헤드리스 스크린샷도
   차단 없이 dev 스택에 대면 dev DB 에 행이 생김(이번 세션에 한 번 생겨 지웠음).
7. ⚠️ **화면은 이제 영어 · 밝은 테마 · 사이드바임**(v0 리디자인 `TASK-292`~`298`). 옛 회차 드라이버는
   한국어 문구로 골랐으므로 새 회차는 `data-testid` 로 고름. 목록은 설계서 §4 와 회차 b9 노트에 있음.
8. ⚠️ 음성 명령 안내는 영어 문장 안에 한국어 명령(「헤이, 학습 종료」 · 「네」)을 남겼음 — 영어 명령이
   실물에서 통하는지 확인되지 않았음(설계서 §6-6).
9. ⛔ DB 배치·psql 경로·Bedrock SigV4 규칙은 이전 판과 같음(`handoff/backup/2026-11-01/HANDOFF-0457.md`).

## 인계 지표 4개

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`6a04a26`** · `origin` 과 **0/0** (이 판을 담은 커밋은 `git log -1` 로 읽음) |
| 2 | 다음 한 걸음 | **사용자 결정 대기 `TASK-299`** — 그 밖의 잔여 0건 |
| 3 | 게이트 | 내가 측정 — 백엔드 `pytest` **1484 passed** · `ruff` 0 · `ruff format` 341 files · `ty` 0 · 하네스 게이트 테스트 112 passed. 프런트 `tsc` 0 · `eslint` 0 · `next build` 0. 측정 뒤 바뀐 것은 이 인계 파일과 원장뿐임 |
| 4 | 착수 전 필수 | 미결 승인 0 · 결정 대기 1(`TASK-299`) |

## 이번 세션 요약 (2026-11-01)

- 문법 코스 스토리보드 재검증(`TASK-287`) — 결함 넷과 codex 지적 넷을 고침
- 밑줄 위치·자동 재생 결정 반영(`TASK-289`) · 전사기 실패를 503 으로(`TASK-288`)
- 실제 Nova 전사 검증 완료(`TASK-288`) — SSO 임시 자격증명으로 연결
- IAM 권한 안내 HTML(`TASK-290`) · 실행 아이콘(`TASK-291`)
- v0 홈 리디자인(`TASK-292`~`298`) — Tailwind·shadcn 도입 · 실데이터 대시보드 · 전 화면 영어 ·
  사이드바 공통 틀 · 하네스 갱신 · 통합 회차 b9·b9r 통과. 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md`

## 다음 세션이 먼저 볼 것

`TASK-299` 의 사용자 답을 받으면 그 턴에 상태를 `In Progress` 로 되돌리고 진행함.
그 밖의 새 지시가 오면 태스크 등록부터 함(`rules/task-management.md` §3).
