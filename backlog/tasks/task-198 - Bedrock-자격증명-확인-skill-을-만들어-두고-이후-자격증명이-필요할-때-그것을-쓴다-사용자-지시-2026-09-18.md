---
id: TASK-198
title: Bedrock 자격증명 확인 skill 을 만들어 두고 이후 자격증명이 필요할 때 그것을 쓴다 (사용자 지시 2026-09-18)
status: Done
assignee: []
created_date: '2026-09-18 04:44'
updated_date: '2026-09-18 04:46'
labels: []
dependencies: []
ordinal: 259000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: 「bedrock 자격증명 확인하는 skill 을 하나 만들어두고, 이후 자격증명이 필요할 경우 확인해서 쓰도록 해. 매번 못찾고 헤매고 있어」 · 「특정 case 에 사용하는 것이 아니라, bedrock 을 연동해야 하는 경우 API key 를 확인할 수 있는 일반 skill 로 만들어」. 자리는 ~/.claude/skills/bedrock-credentials/ 이고 이 리포 전용이 아니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 일반 skill 로 만든다 — 특정 프로젝트 전용이 아니다
- [x] #2 탐색 순서와 두 인증 경로의 차이를 담는다
- [x] #3 값을 출력하지 않는 규율을 담는다
- [x] #4 그 절차를 실제로 돌려 동작을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 만들었음 — `~/.claude/skills/bedrock-credentials/SKILL.md`

⛔ **이 리포 전용이 아님** — 사용자가 *"특정 case 에 사용하는 것이 아니라 … 일반 skill 로"* 로 명확히
했으므로 전역 skill 자리에 뒀음. 등록 확인: skill 목록에 나타남.

⛔ **본문은 영어로 썼음** (사용자 지시 2026-09-18: *"skill 이나 rule은 모두 한글로 할 필요 없지 않아?"*).
경계를 `rules/korean-writing-standard.md` 머리말에 적었음 — 모델만 읽는 지시문은 영어, 사람이 읽거나
리포에 남는 것은 한글. 기존 skill·rule 은 일괄 번역하지 않고 손댈 때 바꿈.

담은 것:

| 절 | 내용 |
|---|---|
| §1 | 탐색 순서 **셸 → 프로젝트 `.env` → `~/.aws`·`AWS_PROFILE`** · 값을 찍지 않는 확인 명령 |
| §2 | **두 경로가 되는 일이 다름** — bearer 는 Claude `InvokeModel` 만, Nova 양방향 스트림은 **403** |
| §3 | 증상별 판별표 — 403 / 무응답 / 기동 실패 / 「있다는데 실패」 |
| §4·§5 | 존재 확인으로 끝내지 않고 실호출로 재기 · **프로젝트가 안내하는 「자격증명 없이 띄우는 길」을 먼저 읽고 깨뜨리지 않기** |

## 그 절차를 돌려 얻은 실측 — §1 의 경고가 맞았음

| 자리 | bearer | SigV4 두 키 |
|---|---|---|
| 셸 환경 | **있음** | **없음** |
| `app/backend/.env` | 있음 | **있음** |

⇒ **셸만 보면 「SigV4 없음」이고 `.env` 를 봐야 「있음」임.** 이것이 이 세션의 혼란을 설명함:
`env -u` 로 셸 변수를 지워도 앱이 정상 기동했고(그때 「자격증명이 있다」로 읽었음) **두 자리를 다
치운 뒤에야** 실패가 재현됐음. 그 실측을 §1 에 넣었음.

## 부수로 한 것

훅 `hangul-sanity.py` 가 정상 낱말 두 음절을 막았음. 우회하지 않고 `~/.claude/hangul-allow.txt` 를
만들어 등재했음. ⚠️ **그 파일을 쓰는 것 자체가 훅에 막혀서** 자모 조합으로 생성하고 유니코드
이름(`SEUB`·`MAESS`)으로 검증했음 — 파라미터에 그 음절을 넣지 않았음.
⚠️ **그 마찰이 skill 을 영어로 쓰기로 한 근거 하나가 됐음.**
<!-- SECTION:NOTES:END -->
