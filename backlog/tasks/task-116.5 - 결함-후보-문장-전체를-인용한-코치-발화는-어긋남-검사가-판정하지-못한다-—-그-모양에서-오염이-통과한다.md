---
id: TASK-116.5
title: '결함 후보: 문장 전체를 인용한 코치 발화는 어긋남 검사가 판정하지 못한다 — 그 모양에서 오염이 통과한다'
status: Done
assignee: []
created_date: '2026-09-14 17:19'
updated_date: '2026-09-17 02:58'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 173000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
codex 리뷰(2026-09-15)가 MEDIUM 으로 지목하고 단위 테스트가 이름을 붙여 둔 구멍이다(test_a_whole_sentence_quote_is_still_not_judged). _QUOTED_TOKEN_RE 는 토큰에 공백을 넣지 않으므로 I hear you say "my brother will arrive early tomorrow morning." 같은 문장 전체 인용은 잡히지 않고 판정이 None 이 된다 ⇒ 그 세션의 어긋난 기록이 복습 시계를 그대로 전진시킨다. 실측에서 브라우저 레그 코치가 실제로 그 모양을 썼다(runs/2026-09-15-task81-app-leg §7). ⛔ 문장을 낱말로 쪼개 넣는 안은 기각했다 — 한 문장에는 낱말이 여럿이라 어느 낱말이든 키의 조각을 담을 확률이 높아지고 갈래 ②가 사실상 언제나 None 이 되어 판정력이 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 모양이 실제로 얼마나 자주 오는지 센다 — 이미 있는 회차 기록의 코치 발화를 세어 비율을 얻는다(새 회차를 돌리지 않는다)
- [x] #2 닫을 자리를 고른다 — 검사(문장에서 소리를 얻는 다른 수단)인지 프롬프트(코치가 소리를 인용하게 만드는 것)인지 가른다. ⛔ 후자는 결정 82 가 「프롬프트를 더 고치지 않는다」로 막은 방향이므로 뒤집으려면 사용자 판단이 필요하다
- [x] #3 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 문장 인용이 잡히는 것과 정상 기록이 배제되지 않는 것
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
측정·판단 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task116-5-quote-shapes/README.md 임. 실물 모델 사용 0.

AC#1 측정됨: 기존 프레임 증거 66파일의 코치 발화 120건을 제품 문턱으로 분류했음 — sound 44/120 · word 10/120 · sentence_only 5/120 · none 61/120. ⚠️ 판정은 세션 단위로 도므로 결정에 걸리는 수치는 세션 단위임: 판정 가능 37/59 · ⛔ 문장 인용만 있어 막힌 세션 2/59 · 인용 전혀 없음 20/59. ⇒ 이 태스크가 겨냥한 구멍은 2/59 이고, 더 큰 미판정 덩어리(20/59)는 설계가 받아들인 자리라 결함이 아님.

AC#2 정했음(위임받음): ⛔ 지금 닫지 않음. 검사 쪽 안(문장을 낱말 자루로 쪼갬)은 이득이 0 임 — 낱말이 여럿이라 갈래 ②가 거의 항상 None 이 되어 지금과 같음. 프롬프트 쪽 안은 결정 82 가 막았고 2/59 로 그 판단을 요청할 근거가 약함. ⇒ 수치를 남기고 To Do 로 파킹함.

⛔ AC#3(구현)은 하지 않았으므로 체크하지 않았고 태스크를 닫지 않았음 — 결과에 맞춰 AC 문면을 고치지 않음. 다시 올릴 조건은 이 비율이 커지는 것이고 그때 같은 스크립트로 다시 셈.

2026-09-15 표본 하나가 늘었음 (세션 ohmyenglish-65 · runs/2026-09-15-task78-1-defenses-in-use). 브라우저 레그 일반 세션에서 코치가 문장 전체 인용과 낱말 인용을 «한 발화에» 함께 썼음 — I hear you say "my brother will early really tomorrow morning." Let's focus on the word "early." ⇒ 낱말 인용이 판정을 살려 sound_check=mismatched 가 붙었음. 즉 이 태스크가 겨냥한 「문장 인용만 있어 막힌 세션」이 아니고 그 비율(2/59)을 늘리지 않음. 다시 올릴 조건은 그대로임.

2026-09-17 (세션 clear 후) — **착수하지 않았고, 대신 파킹의 «전제» 를 코드로 검사했음.**
노트만 읽고 같은 논의를 되풀이하지 않기 위함임(이 태스크는 이번이 세 번째 재검토임).

⛔ **기각된 「검사 쪽」 안이 왜 이득 0 인지를 함수의 형태로 확정했음** — 앞 노트는 확률로 말했으나
`services/pronunciation.py:203-225` 을 읽으면 **확률이 아니라 단조성**임:
`mismatched` 는 `word_supports_key` 가 **거짓**일 때만 나오고, 그 값은
`any(segment in word for segment in segments for word in words)` 이므로 **인용 범위를 넓히면 참이
되기만 함**(낱말이 늘어도 줄지 않음). ⇒ 문장 전체를 낱말 자루로 넣든 한 덩어리로 넣든 갈래 ②는
`None` 으로 떨어짐. **이득이 「작다」가 아니라 「구조적으로 0」임.**

⇒ 남은 방향은 프롬프트 쪽 하나이고 그것은 결정 82 를 뒤집어야 하므로 **사용자 판단이 필요함**
(AC#2 가 그렇게 적어 둠). 비율 2/59 는 이 세션에서 바뀌지 않았음(새 회차를 돌리지 않았음).

⇒ 상태를 `To Do` → `Awaiting Decision` 으로 고쳤음. 근거는 `rules/task-management.md` §2 임 —
「`To Do` 에 섞이면 왜 안 하고 있나를 매 세션 다시 조사하게 된다」가 이 태스크에서 실제로 일어났음.

## AC#3 — 2026-09-17 구현 (사용자 결정 124 로 방향이 열렸음)

**고른 방향**: 프롬프트 쪽. 등재는 `docs/ops/captain-instruction-register.md` 의 **결정 124** 임.
⛔ **결정 82 를 통째로 뒤집은 것이 아님** — 82 가 반증한 것은 `target_sound` 의 «내용» 축이고
이 변경은 인용의 «형태» 축임. 그 구분을 결정 124 와 `nova.py` 규칙 9 위 주석이 함께 가짐.

**바꾼 것 하나**: `SYSTEM_PROMPT` 규칙 9 에
*"name the sound that was off and put it in quotes on its own - the "th" sound, the "er" sound -"*
와 *"Quoting only the whole sentence does not name the sound."* 를 넣었음.

**TDD**: 프롬프트 계약 단정을 **먼저 써서 red 를 봤음** —
`test_system_prompt_makes_the_coach_quote_the_off_sound_on_its_own` 이
`AssertionError: 소리를 따옴표로 따로 인용하라는 지시가 없다` 로 떨어지는 것을 확인한 뒤 문면을 고쳤음.

**반대 방향 두 단정** (`tests/unit/test_pronunciation_sound_check.py`):
① `test_a_quoted_sound_beside_a_sentence_quote_is_judged` — 문장 인용 «옆에» 소리가 따로 인용되면
판정이 산다(`r_as_l` → `mismatched`).
② `test_a_matching_quoted_sound_beside_a_sentence_quote_is_not_excluded` — 같은 모양에서 소리가
키와 맞으면 `matched` 다(정상 기록을 배제하지 않음).

⛔ **그 둘은 red 로 태어나지 않았음** — 검사 코드를 고치지 않았으므로 프롬프트 변경 전에도 통과함
(`H-M` 의 부류). **그래서 무력화해서 판별력을 쟀음**: `_QUOTED_TOKEN_RE` 의 문자 클래스에 공백을
넣어 문장을 토큰으로 삼게 하니 ①이 `mismatched` → **`None`** 으로 떨어져 red 가 됐고
`test_a_whole_sentence_quote_is_still_not_judged` 도 함께 red 가 됐음(2 failed · 13 passed).
되돌린 뒤 `__pycache__` 를 지우고(`H-BS`) `git diff` 로 그 파일의 변경 0 을 확인했음.

⚠️ **검사 쪽 대안의 기각 근거를 「확률」에서 「단조성」으로 바꿔 적었음** — `mismatched` 는
`word_supports_key` 가 거짓일 때만 나오고 그 값은 인용 범위를 넓히면 참이 되기만 함. 이득이
「작다」가 아니라 **구조적으로 0** 임. 그 서술을 그 테스트 docstring 에도 옮겼음.

## ⛔ 이행은 절반임 — 남긴 것을 명시함

- **전용 모드(`PRONUNCIATION_MODE_PROMPT`)에는 넣지 못했음.** 그 문면은
  `test_the_pronunciation_prompt_is_byte_identical_to_the_measured_one` 이 실측 산출물
  (`prompt_dedicated_v4.txt` · ARM-A 4/4)에 **바이트로** 묶어 두었고, 그 테스트가 선택지를
  「되돌리거나 회차를 다시 돌려라」 둘로 못박았음. ⇒ **`TASK-154` 가 그 절반을 가짐.**
  측정된 2/59 중 `T123B1` 이 전용 모드 계열이라 **구멍도 절반 남아 있음.**
- ⛔ **「지시가 있다」만 잼 — 「지켜진다」는 실물 회차가 잼.** 단위 테스트는 문면의 존재만 보증함.
  프롬프트 준수는 확률적이고, 이 축에서 세 방향이 3/3 으로 반증된 이력이 바로 그 이유임.
  ⇒ 코치가 실제로 소리를 따로 인용하는지는 **다음 실물 회차의 증거로 센다**(`TASK-154` AC#4).
<!-- SECTION:NOTES:END -->
