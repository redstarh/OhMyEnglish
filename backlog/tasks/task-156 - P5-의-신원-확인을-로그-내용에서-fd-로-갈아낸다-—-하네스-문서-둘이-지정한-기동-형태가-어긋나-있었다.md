---
id: TASK-156
title: P5 의 신원 확인을 로그 내용에서 fd 로 갈아낸다 — 하네스 문서 둘이 지정한 기동 형태가 어긋나 있었다
status: Done
assignee: []
created_date: '2026-09-17 03:16'
updated_date: '2026-09-17 03:17'
labels: []
dependencies: []
ordinal: 217000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-155 회차가 드러냈다. browser_leg.md §2 의 P5 는 /tmp/omy-backend.log 에서 'Started server process [pid]' 를 찾아 로그의 신원을 세우는데 그 줄은 uvicorn INFO 라 --log-level warning 스택에서는 애초에 찍히지 않는다(실측: 로그 0바이트). 그래서 같은 문서가 「레벨은 info 여야 한다」를 요구했는데 tests/harness/README.md:93 의 기동 형태는 --log-level warning 이고 handoff 도 그것을 baseline 으로 적었다 — 두 문서가 정면으로 어긋난 채였고 그 사이에서 P5 가 조용히 죽는다. ⛔ 두 문서의 레벨을 맞추는 쪽으로 닫지 않는다 — 검사를 레벨에 의존하지 않게 고치는 것이 더 강하다(회차가 실제로 쓴 방법이 lsof -p pid 의 fd 1w·2w 다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 P5 의 ② 를 로그 내용 대신 lsof 의 열린 fd 로 세우고, 고친 P5 를 그대로 돌려 통과를 본다
- [x] #2 그 검사가 실패도 낼 수 있는지 확인한다 — 다른 파일을 가리키면 실패해야 한다
- [x] #3 레벨 요구를 걷고 두 기동 형태가 둘 다 성립함을 적는다 — 이전 판의 근거를 지우지 않고 경위로 남긴다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-17 — `TASK-155` 회차의 관측을 그 자리에서 닫았음.

**AC#1** — `browser_leg.md` §2 의 P5 ② 를 `lsof -nP -p <pid> -Fn` 의 열린 파일 목록으로 갈아냈음.
`os.path.realpath` 를 함께 보는 이유는 macOS 의 `/tmp` 가 `/private/tmp` 심볼릭 링크라서임
(`lsof` 가 `/private/tmp/omy-backend.log` 로 보고함 — 원경로로만 비교하면 못 찾음).
고친 P5 를 그대로 돌린 출력: `P5: pid 19296 · 기동 15:19 전 · 소스 53건 → 통과`.

**AC#2** — 판별력을 확인했음. 빈 `/tmp/omy-decoy.log` 를 만들어 같은 검사를 걸었더니
`/tmp/omy-backend.log → 통과` · `/tmp/omy-decoy.log → 실패` 였음. ⇒ 통과가 「무엇이든 통과」가 아님.

**AC#3** — 「레벨은 `info` 여야 한다」를 걷고 두 형태(`info`·`warning`)가 둘 다 성립함을 적었음.
⛔ **이전 판의 근거를 지우지 않았음** — 2026-09-09 의 그 요구는 «그때의 ②» 에 대해 옳았고, 그 사실과
2026-09-17 에 무엇이 바뀌어 걷혔는지를 함께 남겼음. 기동 순서 블록의 주석도 같이 고쳤음.
⚠️ **레벨을 내리면 잃는 것을 명시했음** — uvicorn 기동·요청 줄이 사라지므로 「로그 0줄」을 통과
근거로 쓰기 전에 그 채널이 오류를 잡는지 먼저 증명해야 함(그 회차 §3 이 값역 밖 입력으로 32줄을
만들어 세운 것이 선례임).

**곁가지 하나** — `runs/2026-09-17-review-task-baseline.tsv` 머리말에 정렬 키를 적었음. 그 파일은
`pattern_key, review_stage` 로 떴는데 그 둘로도 동순위가 셋 남아(같은 패턴의 stage 1 이 3행)
행 순서를 그대로 비교하면 값이 같은데도 차이가 나 보임. 회차가 그 자리에서 1분을 썼음.
<!-- SECTION:NOTES:END -->
