"""`plan_next_session` job 처리 — 프롬프트 조립 · Claude 1회 호출 · 저장 한 트랜잭션.

`process_plan`이 진입점이다(계획서 Task 3·7). 저장은 계획 1행 + 관찰 노트 1행 +
`users.current_level` 갱신 + job 종결을 **한 트랜잭션**에 담는다(설계서 §9 Contract) —
절반만 반영된 상태를 남기지 않는다. Claude 호출은 그 트랜잭션 **밖**이다: 네트워크 대기
동안 연결과 행 잠금을 들고 있으면 다른 job 이 막힌다(`jobs.py`의 호출 계약).

`build_plan_prompt`(Task 6)는 `PlanInput`(Task 4)을 Claude에게 보낼 프롬프트 문자열로
조립하는 **순수 함수**다 — DB에 닿지 않는다. 설계서 §4의 3계층 순서를 그대로 따른다:
① 오늘 다뤄야 하는 목록(due) → ② 최근 창(recent) → ③ 만성 사실(chronic) →
④ 발음 시도(별도 절) → ⑤ 출력 규격. 목록은 이미 계산된 **사실**이라 프롬프트가 그것을
다시 계산하라고 요구하지 않고, 무엇이 오늘의 약점이고 난이도를 어떻게 조절할지는 모델이
판단한다(§3.2의 승인된 경계).

발음 절을 문법 절과 분리하는 이유(§4.4 주의 2): 발음의 빈도는 **시도 수** 기준이고 문법은
**발생 수** 기준이라 계산 근거가 다르다. 한 정렬에 섞으면 발음이 부당하게 위/아래로 간다.

출력 규격(`_OUTPUT_SPEC`)의 키 이름은 Task 5의 검증 계약(`app.models.plan.PlanOutput`)과
**글자 그대로 같아야** 한다 — `extra="forbid"`라서 하나만 어긋나도 실물 모델 응답이 전부
거부된다. 지시문 크기 상한은 넣지 않는다 — 설계서 §3.4가 "구체 수치는 Nova 초기화 시간을
실측해 정한다"고 했고, 그 실측은 아직 하지 않았다(발명하지 않는다).

**리뷰 라운드 1 (2026-09-05)에서 잡힌 것 — 다시 만들지 말 것**:
* **Critical-1**: 복습·만성 목록에 `pattern_id`가 없으면 모델이 UUID를 지어낸다. 지어낸
  값이 형식만 맞으면 `focus_pattern_ids uuid[]`에 **FK가 없어서** 조용히 저장되고 복습·초점
  조회가 영구히 어긋난다 — 대역 테스트로는 안 드러난다. 그래서 각 줄에 `pattern_id`를 싣고
  `_OUTPUT_SPEC`이 "목록의 id를 그대로 복사하라, 지어내지 마라"를 명시한다. 짧은 번호로
  되매핑하는 대안은 기각했다 — 대응표라는 새 층이 새 실패 모드(목록 밖 번호)를 만든다.
* **Important-1**: 키 이름이 맞아도 **제약**(세 `target_level`의 일치, CEFR 값역,
  `instruction.focus`도 1~2개, 빈 문자열 금지)을 프롬프트가 말하지 않으면 Task 5가 응답을
  거부한다. `_OUTPUT_SPEC`에 그 제약을 문장으로 적어 넣었다.
  ⚠️ **고침 중에 필드 단위로 다시 대조해 2건을 더 찾았다**: ① `PlanOutput` 계열 전부가
  `extra="forbid"`라서 **모르는 키 하나가 응답 전체를 죽인다** — "Return one JSON object and
  nothing else"는 JSON **밖**의 산문만 막고 키는 막지 않는다 ② 열거한 셋(`sentence_length`·
  `hint_timing`·`level.reason`) 밖에도 `questions.prompt`·`context`·`contexts` 항목·`notes`
  항목이 `min_length=1`이다. 출력의 **모든** 문자열이 그 제약을 받으므로 한 문장으로 적었다.

**재리뷰 라운드 2 (2026-09-05)에서 잡힌 것 — 이쪽이 더 중요하다**:
* **Critical-1이 절반만 닫혀 있었다.** 라운드 1은 복습·만성 줄에 `pattern_id`를 실었지만
  `- focus:`는 "Pick from the lists **above**"라고 말했고, **위의 네 목록 중 둘은 id가 없다**
  (최근 교정 · 발음). 최근 교정 목록은 실제 `error_patterns` 행의 `pattern_key`를 부르면서
  id는 없으므로 모델이 거기서 초점을 고르면 **여전히 UUID를 지어내야** 하고, 원래의 조용한
  저장 경로가 그대로 살아난다 — 고친 문구가 오히려 그 선택을 초대했다. 그래서 `- focus:`가
  **두 목록을 이름으로 지목**하고, 나머지 두 절은 제목에서 "context only, never a focus
  source"라고 스스로 말한다. ⚠️ 이 경계는 발명한 것이 아니다 — 계획서 Task 7이 정한 허용
  집합이 `{r.pattern_id for r in due_reviews} | {m.pattern_id for m in chronic}`이고, 그
  가드는 다른 목록에서 고른 초점을 **어차피 하드 거부한다.** 프롬프트와 그 집합이 어긋나면
  정당한 응답이 거부된다.
* **발음 절에서 초점을 고를 수 없는 이유는 id 부재다** — `PronunciationTally`에는
  `target_sound`만 있어 **그 절의 값으로는** 유효한 `FocusPattern`을 만들 수 없다.
  ⚠️ **「발음은 초점이 될 수 없다」는 철회됐다** (`TASK-44`, 설계서
  `2026-09-08-pronunciation-review-cycle-design.md`). 발음 패턴은 이제 `next_review_at`을
  받아 **"Due for review today" 목록을 통해** 초점 허용 집합에 들어온다 — 그 목록은
  `pattern_id`를 싣는다. 바뀐 것은 "발음은 초점이 될 수 없다"이지 "이 절에서 고른다"가
  아니다. 이전 판이 이 자리에 적었던 「구현 공백 4」의 **알고 남긴 축소는 해소됐다.**
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

import asyncpg

from app.models.analysis import PRONUNCIATION_CATEGORY
from app.models.plan import CEFR_LEVELS, LevelDecision, PlanOutput, PlanValidationError, parse_plan
from app.services.chronic import ChronicMetric, deepest_recurrence
from app.services.jobs import ClaimedJob, complete, report_failure
from app.services.plan_input import (
    PlanInput,
    PronunciationTally,
    RecentUtterance,
    load_plan_input,
)
from app.services.review import DueReview
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# 콜드스타트 사유 — 복습 예정도 만성 지표도 0건이면 초점 후보가 없다. `logger.info`가 아니라
# **큐의 사유로** 남기는 이유: 나중에 "왜 계획이 없었나"를 job 이력에서 읽을 수 있다.
PLAN_NO_FOCUS_CANDIDATES = "no focus candidates yet"

# 이 슬라이스는 `'agent'`만 쓴다. Claude 가 실패하면 계획 행을 **만들지 않고**(§3.3이
# "계획 미사용을 행 부재로 판별한다"고 정했다) 세션 시작이 시나리오 뱅크로 떨어진다.
# `'fallback'`은 007 CHECK 의 값역이지만 이 슬라이스에 그 값을 쓰는 경로가 없다 — 나중에
# "계획은 만들었으나 뱅크 내용을 썼다"가 생기면 그때 쓴다.
_PLAN_SOURCE_AGENT = "agent"

_SESSION_OWNER_SQL = "select user_id from learning_sessions where id = $1"

_INSERT_PLAN_SQL = """
insert into session_plans
       (session_id, focus_pattern_ids, questions, target_level, reason, instruction, source)
values ($1, $2, $3, $4, $5, $6, $7)
"""

# §6.3 덧붙이기만 한다 — 갱신·삭제하지 않는다. `window_from`·`window_to`는 이 노트가 어떤
# 발화 범위를 근거로 쓰였는지를 남긴다.
_INSERT_NOTE_SQL = """
insert into learner_notes (user_id, note, window_from, window_to)
values ($1, $2, $3, $4)
"""

_UPDATE_LEVEL_SQL = "update users set current_level = $2 where id = $1"


class _LeaseLost(Exception):
    """`complete`가 0행 — 저장 트랜잭션을 롤백시키기 위한 내부 신호.

    `analysis.py`의 같은 뜻 예외와 관례를 공유하지만 그쪽은 private 이라 재사용할 수 없다.
    """


# h-doc 학습자 프로필이 문구를 지배한다: 단문·단일 절 기준 · 일상 → 업무 협업 순서 ·
# 목표 수준(AWS 보고 문형)으로 예문을 만들지 않는다. 아래 목록은 이미 계산된 사실이라
# 모델에게 다시 계산하라고 요구하지 않는다 — 무엇이 약점이고 얼마나 어려운지는 모델이 정한다.
_PROMPT_HEADER = """\
You plan the next English speaking session for one Korean learner.

Learner profile: can handle greetings, small talk, and simple daily-life sentences; mostly uses
short patterns such as "I want to...", "I need to...", "I'd like to...". Long-term goal is to
join business meetings and report project status. Start from daily life and move toward work
topics — do not write examples at the long-term goal level.

Sentence length: default to short, single-clause sentences built on patterns like the ones above.
Extend length and clause count gradually as the learner is ready — never jump straight to the
long-term goal level. This applies to instruction.sentence_length and to the example questions.

You decide what the weakness really is, which situations to practise it in, and the difficulty.
The lists below are **facts**, already computed. Do not recompute them and do not drop any of them.
"""

# 발음은 시도 수 기준, 문법은 발생 수 기준이라 계산 근거가 다르다(§4.4 주의 2) — 한 정렬에
# 섞으면 발음이 부당하게 위/아래로 간다. 그래서 별도 절로 두고 그 사실을 문장으로도 알린다.
# ⚠️ 닫는 `"""`를 새 줄에 두지 않는다(리뷰 M2) — 그러면 이 문자열이 `\n`으로 끝나
# `build_plan_prompt`의 `"\n".join`이 개행을 하나 더 얹는다. 다른 절 제목(예: "Chronic
# metrics ...:")은 한 줄 문자열이라 그 문제가 없다 — 발음 절만 제목과 목록 사이에
# 빈 줄이 하나 더 생겼었다.
# ⚠️ 줄바꿈 위치는 설계서 §5.6의 문안과 다르다 — **단어는 한 자도 바꾸지 않았고** 줄바꿈만
# 옮겼다. 설계서 판은 `"Due for review\ntoday"`로 인용 제목을 쪼갰는데, 다른 절 제목을
# **이름으로 인용하는 규약**(`_OUTPUT_SPEC`의 `- focus:`가 같은 두 제목을 인용하고
# `test_plan.py`가 `f'"{bare}"'`로 그것을 잰다)이 인용을 한 덩어리로 두는 것을 전제한다.
_PRONUNCIATION_NOTE = """\
Pronunciation attempts (context only — these tallies carry no pattern_id, so do not pick a focus
from this section; a pronunciation pattern that is ready to revisit appears in
"Due for review today" above with its pattern_id. Counted per attempt, not per error occurrence,
so do not rank these against the grammar counts above):"""

# `TASK-81` — 발음이 초점 **한 자리**를 얻게 하는 규칙. `TASK-78`이 통제 대조로 확정한 결함을
# 닫는다: 발음 패턴은 `TASK-44` 이후 이미 초점 후보인데(위 `_format_due_reviews`가 `pattern_id`와
# 함께 싣는다) 그것을 고를 이유를 프롬프트가 한 줄도 주지 않아 모델이 문법만 골랐고, 그 결과
# 세션 지시문의 `Focus on:`이 문법만 담아 **앱 경로에서 발음 코칭이 0회**가 됐다.
#
# ⚠️ **조건은 「복습 예정일에 걸릴 때」다** — 무조건 붙이지 않는다. 「Pronunciation attempts」 절은
# `pattern_id`를 싣지 않으므로 그 절의 값으로는 유효한 초점을 만들 수 없고, 모델이 거기서 고르면
# `process_plan`의 허용 집합이 **계획 전체를 하드 거부**한다. 그래서 판정 재료는 시도 집계가
# 아니라 `due_reviews`의 `category`다.
#
# ⛔ **문법 초점을 없애지 않는다** — 규칙 9의 `Grammar first`는 캡틴 결정 B-2의 구현이고 계획의
# 문법 초점은 학습자의 실제 오류 패턴에서 나온 것이다. 초점 상한이 2개라(PRD.md:188 R11-2) 발음이
# 한 자리를 가져가면 나머지 한 자리가 문법으로 남는다 — 「자리를 내주는 것」과 「밀어내는 것」이
# 갈리는 지점이 그 상한이다.
# ⚠️ 닫는 `"""`를 새 줄에 두지 않는다(`_PRONUNCIATION_NOTE`와 같은 이유 — `"\n".join`이 개행을
# 하나 더 얹어 절 사이 간격이 이 절만 달라진다).
#
# ⛔ **셋째 줄은 「초점 자리를 내주는 것」만으로 부족하다는 관측에서 나왔다**
# (캡틴 지시 2026-09-10 · 안 1). 초점 자리를 내주고 세션 지시문의 소리 줄이 규칙 9·4 를
# 대체하게까지 했는데도 실물 왕복에서
# 발음 코칭이 나지 않았다(`runs/2026-09-10-task75-rule9-rule11-replacement.md`). 그 회차가 찾은
# 이유는 **계획 블록의 나머지가 소리 줄을 압도한다**는 것이다 — 초점·힌트 시점·질문 다섯이 전부
# 관사를 가리키면 코치가 관사로 가는 것이 **다수 지시를 따르는 행동**이 된다.
# 그래서 계획 블록 전체가 한 방향을 가리키게 하고, 질문이 그 소리를 반복해 만들어 **어긋날 기회
# 자체를 만든다.**
# ⚠️ **문법 초점을 밀어내지 않는다** — 질문이 둘을 함께 담을 수 있고 그 사실을 규칙이 말한다.
# 캡틴이 감수한 비용은 「그 세션에서 문법 연습 질문이 줄어드는 것」이고
# 「문법이 사라지는 것」이 아니다.
#
# ⛔ **넷째·다섯째 줄은 결정 57(`TASK-86`)이 더했고, 셋째 줄이 «지켜졌는데도» 안 됐다는 관측에서
# 나왔다.** 셋째 줄(「그 소리를 담은 낱말로 질문을 만들어라」)은 실제로 지켜졌다 — 커밋 `00c7d39`
# 뒤에 생성된 제품 계획의 질문 다섯이 전부 `an` 낱말로 짜였다. 그런데 그 **모양**이 형태 사용
# 지시였고(`Use "an update" or "an action plan". Example: "I want to make an action plan."`) 코치는
# 그것을 **관사 드릴로 수행**했다. 제품·하네스 계열 57회에서 `toolUse` 0 이고, 대화의 관사 지시
# 출처가 **그 질문 5개**로 확정됐다(질문을 빼면 사라졌다 —
# `runs/2026-09-11-task106-matched-sound.md` §7 · `runs/2026-09-11-task86-priority-line.md` §3).
# ⇒ 「그 소리를 담은 낱말」과 「그 소리를 연습하는 질문」은 다르다. 셋째 줄은 **낱말**만 정하고
# 질문의 **모양**을 열어 뒀고, 모델은 그 자리를 형태 사용 지시로 채웠다.
#
# ⛔ **다섯째 줄은 프롬프트 안의 모순을 닫는다.** `_OUTPUT_SPEC`의 `questions:` 불릿이
# *"Same target form, different situations"* 를 **무조건** 요구한다 — 발음 초점에서 고정되는 것은
# 형태가 아니라 **소리**이므로 그 요구가 그대로면 모델이 형태 드릴로 가는 것이 **지시를 따르는
# 행동**이 된다. ⚠️ 그 문구를 `_OUTPUT_SPEC`에서 지우지 않는 이유: 문법 계획에서는 맞는 요구이고
# (발음 초점이 없으면 이 블록 자체가 붙지 않는다) 지우면 요청받지 않은 거동 변경이 된다. 그래서
# **조건부인 이 자리에서만** 예외를 말한다 — `test_plan.py`의 음성 케이스가 그 경계를 잰다.
_PRONUNCIATION_FOCUS_RULE = """\
Pronunciation focus for today:
- A pronunciation pattern is due for review in the list above. Give it
  one of the two focus slots, and keep the other slot for a grammar pattern from those two lists.
- Do not drop the grammar focus to make room — the learner works on both today. If those two
  lists carry no grammar pattern, the pronunciation pattern alone is fine.
- Write the questions so they give that sound repeated chances to come up: build them around
  words that contain it, so the learner says it several times. Where you can, let the same
  question still exercise the grammar focus — one sentence can carry both.
- Shape each of those questions as speaking practice for the sound. Write them
  not as an exercise in which form to use: the learner already knows which word belongs there,
  so do not tell them to "use" a form and do not hand them a sentence to read back. Ask for
  something of their own that contains those words, so the sound is the part they have to get
  right.
- The output spec below asks the questions to share one target form. For a pronunciation focus
  read it this way: the constant is the sound, and the situations around it change."""

# `TASK-108` — **검증이 요구하는 것을 프롬프트가 말하게 한다.** `models/plan.py`의 AC11-2 가드는
# 초점이 `deepest_recurrence`를 포함하지 않으면 계획 전체를 거부하는데, 조립된 프롬프트에는
# `deepest`가 **0건**이었다(2026-09-11 실측 — 14,030자를 직접 grep 했다.
# `runs/2026-09-11-task86-sound-shaped-questions.md` §1의 거부 사유가 그것이다). 만성 절은 사실만
# 싣고 어느 것이 「가장 깊은 재발」인지 지목하지 않으므로 모델이 `chronic.py`의 순위 규칙을
# **추측**해야 했고, 틀리면 정당한 응답이 거부됐다.
#
# ⛔ **검증에서 요구를 내리는 쪽을 고르지 않았다** — AC11-2는 캡틴 결정이고(`TASK-108` AC#3)
# 이 태스크가 정하는 것은 그 규칙을 **어디서 집행하는가**다. 가드를 지우면 요구사항이 아무 데서도
# 집행되지 않고, 실물 1건이 우연히 최다 빈도를 고른 것과 재현성을 다시 구분할 수 없게 된다
# (`parse_plan` docstring이 그 판정 되돌림의 경위를 소유한다).
#
# ⛔ **순위를 여기서 다시 계산하지 않는다** — 표식을 붙일 대상은 `services/chronic.py`의
# `deepest_recurrence`가 정하고, `process_plan`이 `parse_plan`에 넘기는 값도 **같은 함수**의
# 결과다. 두 곳이 같은 함수를 부르는 것이 「프롬프트와 검증이 갈라지지 않는다」의 구현이다.
# ⚠️ 그래서 `build_plan_prompt`의 인자 목록은 바뀌지 않는다(순수 함수도 유지된다) — 재료가
# `PlanInput.chronic` 안에 이미 있고 `deepest_recurrence`도 순수 함수다.
#
# ⚠️ **조건은 「만성 목록이 비지 않을 때」다** — 비면 `deepest_recurrence`가 `None`이고 그때
# `parse_plan`은 이 규칙을 적용하지 않는다(콜드스타트). 프롬프트가 무조건 요구하면 존재하지 않는
# 패턴을 초점에 넣으라고 말하게 된다.
# ⚠️ **셋째 줄이 발음 초점 규칙과의 자리 배분을 닫는다.** 초점 상한이 2개이므로(PRD.md:188
# R11-2) 발음이 한 자리를 가져가면 남은 자리가 이 패턴이다 — 그 말을 하지 않으면 위 블록의
# *"keep the other slot for a grammar pattern"*이 **아무 문법 패턴이나** 되는 것으로 읽히고,
# 그 선택이 `parse_plan`에서 거부된다.
_DEEPEST_FOCUS_RULE = """\
Deepest recurrence:
- One line in the chronic list above is marked [deepest recurrence]. That marking is computed from
  the facts in that list, so you do not rank them yourself.
- Today's focus must include that pattern_id. A plan that leaves it out is rejected — copy it into
  focus even if another pattern looks more urgent to you.
- If a pronunciation pattern is also due for review above, those two are today's focus: the marked
  chronic pattern and that pronunciation pattern."""

# 키 이름은 Task 5(`app.models.plan.PlanOutput`, `extra="forbid"`)와 글자 그대로 같아야 한다 —
# 하나만 어긋나면 실물 모델 응답이 검증 단계에서 전부 거부된다. 초점 1~2개·질문 3~5개는
# PRD.md:188(R11-2)의 문서 근거가 있는 값이고, 그 외 임계값은 넣지 않는다(발명하지 않는다).
# ⚠️ 지시문 크기 상한도 넣지 않는다 — 설계서 §3.4가 그 수치는 실측 후에 정한다고 했다.
_OUTPUT_SPEC = """\
Return one JSON object and nothing else. Keys:
- focus: one or two patterns, each {pattern_id, pattern_key, target_form}. Pick only from the
  "Due for review today" list or the "Chronic metrics" list above — they are
  the only two lists that carry pattern_id, and a pattern taken from anywhere else is rejected.
  Copy pattern_id exactly as given there; never invent one.
- questions: three to five items, each {prompt, context}. Same target form, different
  situations.
- target_level: one CEFR code (A1|A2|B1|B2|C1|C2). It must equal level.target_level and
  instruction.target_level — all three must match.
- reason: one short sentence **in Korean**, addressed to the learner, saying why today's practice
  is this. Never leave it empty.
- instruction: {target_level, focus:[{pattern_key, target_form}], sentence_length, hint_timing,
  contexts}. instruction.target_level must equal the top-level target_level. instruction.focus
  also has one or two items (pattern_key and target_form only — no pattern_id here).
  sentence_length and hint_timing are short English phrases spliced into the tutor's
  instructions and must not be empty. contexts is the list of situations for today.
- level: {action: keep|up|down, target_level, reason}. Move at most one CEFR step from the current
  level, in either direction. Going down is allowed and is better than staying too hard. reason
  must not be empty.
- notes: observations worth keeping that numbers cannot hold — for example "adds articles in short
  sentences but drops them once the sentence gets longer". An empty list is fine here.

Do not add any key that is not listed above — one unknown key makes the whole response invalid.
Empty lists are allowed where said above; empty strings are not — every string anywhere in the
object must be non-empty.
"""


# 목록이 0건이면 제목은 유지하고 명시적 placeholder(예: "(none due today)")를 넣는다 —
# `audio_gateway/nova.py`(§10 R10-2 계열)의 선례("0건이면 블록을 아예 넣지 않는다. 제목만
# 남으면 빈 목록 자체를 지시로 오해할 여지가 있다")와 **일부러 다르다**: 여기 5개 절은
# 항상 같은 순서로 고정돼야 모델이 "이 절이 왜 통째로 없지?"를 궁금해하지 않는다 —
# "없다"고 명시적으로 말하는 쪽이 이 자리에서는 모호성이 더 적다(리뷰 M1).


def _format_due_reviews(due_reviews: list[DueReview]) -> str:
    """설계서 §4.1 — 오늘 다뤄야 하는 목록. 판정을 다시 하지 않고 그대로 나열한다.

    `pattern_id`를 반드시 싣는다(리뷰 Critical-1) — 안 실으면 모델이 UUID를 지어내고,
    형식만 맞은 가짜 id가 FK 없는 `focus_pattern_ids`에 조용히 저장돼 복습 조회가 어긋난다.

    발음 패턴은 `target_form`이 **소리 키**(`an_as_a`)라서 낱말을 바꿔 `target sound`로 낸다
    (`TASK-44`, 설계서 `2026-09-08-pronunciation-review-cycle-design.md` §5.6 ④).
    ⚠️ **이 분기는 `TASK-44`로 살아 있는 문제가 됐다** — 그전에는 발음 패턴의
    `next_review_at`이 영원히 null이라 이 목록에 못 들어왔다. 이제 들어오는데 `target form`
    으로 내면 모델이 소리 키를 **연습할 문장으로** 읽을 여지가 생기고, 그것이 1차수 F-2와
    같은 부류의 오류다(카드의 두 값이 서로 다른 것을 가리킨다). `category`가 이미 같은 줄에
    실리므로 분기 재료는 여기 있다.
    """
    if not due_reviews:
        return "(none due today)"
    return "\n".join(
        f"- {review.pattern_key} [pattern_id: {review.pattern_id}] ({review.category}): "
        f"{'target sound' if review.category == PRONUNCIATION_CATEGORY else 'target form'} "
        f'"{review.target_form}", due since {review.next_review_at.isoformat()}, '
        f"mastery {review.mastery_score}"
        for review in due_reviews
    )


def _format_recent(recent: list[RecentUtterance]) -> str:
    """설계서 §4.2 — 최근 창(14일) 안의 학습 발화와 그에 붙은 교정."""
    if not recent:
        return "(no learner utterances in this window)"
    lines: list[str] = []
    for utterance in recent:
        lines.append(f'- [{utterance.said_at.isoformat()}] "{utterance.transcript}"')
        for correction in utterance.corrections:
            lines.append(
                f"    correction: {correction.pattern_key} ({correction.category}) — "
                f'"{correction.original_span}" -> "{correction.correction}" '
                f"({correction.severity}, confidence {correction.confidence})"
            )
    return "\n".join(lines)


def _format_chronic(
    chronic: list[ChronicMetric],
    chronic_pattern_ids: set[UUID],
    *,
    deepest_pattern_id: UUID | None,
) -> str:
    """설계서 §6.1/§6.2 — 만성 지표는 사실만 담는다. 판정 문구는 결정론적 신호 하나뿐이다:
    3단계(1·3·7일)를 완주한 뒤 재발한 패턴에 사실 문장을 덧붙인다. 만성 여부의 최종 판단은
    모델이 한다 — 여기서 "만성이다"라고 선언하지 않는다.

    `pattern_id`를 싣는 이유는 `_format_due_reviews`와 같다(리뷰 Critical-1). `span`·`max_gap`은
    `timedelta`를 `str()`로 새면 `"9 days, 0:00:00"`처럼 나와 `0:00:00`이 별개 필드로 읽힐 수
    있다(리뷰 Important-6) — 그래서 `.days` 정수만 낸다. `max_gap`은 발생이 1건뿐인 패턴이면
    `None`이다(`chronic.py`).

    `deepest_pattern_id`는 `build_plan_prompt`가 `deepest_recurrence`로 계산해 넘긴다 — **여기서
    순위를 다시 내지 않는다**(`TASK-108`, `_DEEPEST_FOCUS_RULE` 위 주석이 근거를 소유한다).
    **키워드 인자를 필수로 둔다**: `None`이 "만성 목록이 비었다"는 **유효한 값**이라 기본값을 주면
    잊은 호출자와 구분되지 않는다 — `parse_plan`의 같은 인자와 같은 이유다.
    """
    if not chronic:
        return "(no chronic metrics yet)"
    lines: list[str] = []
    for metric in chronic:
        max_gap_text = "n/a" if metric.max_gap is None else f"{metric.max_gap.days} days"
        line = (
            f"- {metric.pattern_key} [pattern_id: {metric.pattern_id}] ({metric.category}): "
            f"frequency {metric.frequency}, seen in {metric.recurring_sessions} sessions "
            f"across {metric.recurring_days} days, span {metric.span.days} days, "
            f"longest gap {max_gap_text}"
        )
        if metric.pattern_id in chronic_pattern_ids:
            line += "  [completed all three review stages before, then came back]"
        if deepest_pattern_id is not None and metric.pattern_id == deepest_pattern_id:
            line += "  [deepest recurrence]"
        lines.append(line)
    return "\n".join(lines)


def _format_pronunciation(pronunciation: list[PronunciationTally]) -> str:
    """설계서 §4.4 — 발음 시도 집계. 점수·등급은 요구하지 않는다.

    하지 않는 것 목록: requirements-summary.md:120-121.
    """
    if not pronunciation:
        return "(no pronunciation attempts in this window)"
    return "\n".join(
        f"- {tally.target_sound}: {tally.outcome}, {tally.attempts} attempts, "
        f"last seen {tally.last_seen.isoformat()}"
        for tally in pronunciation
    )


def build_plan_prompt(data: PlanInput) -> str:
    """다음 세션 계획 프롬프트를 조립한다 (설계서 §4, 계획서 Task 6). 순수 함수 — DB 없음.

    절 순서는 §4의 3계층 그대로다: ① 오늘 다뤄야 하는 목록 → ② 최근 창 → ③ 만성 사실 →
    ④ 발음 시도(별도 절) → ⑤ 출력 규격. 출력 규격의 키 이름은 Task 5의 검증 계약과 같아야
    하고(모듈 docstring 참조), 지시문 크기 상한은 아직 넣지 않는다(§3.4).

    ⑤ 앞에 **조건부 규칙 블록 둘**이 붙는다 — 발음 초점(`TASK-81`, 발음이 복습 예정일 때) ·
    가장 깊은 재발(`TASK-108`, 만성 목록이 비지 않을 때). 둘 다 조건이 있는 이유는 각 상수 위
    주석이 소유한다. **무조건 붙이면 요구가 거짓이 되는 경우가 있다**는 것이 공통 근거다.
    """
    # `TASK-108` — 순위는 만성 목록을 소유한 쪽이 낸다(`chronic.py`). `process_plan`이
    # `parse_plan`에 넘기는 값도 같은 함수의 결과라 프롬프트와 검증이 갈라지지 않는다.
    deepest = deepest_recurrence(data.chronic)
    sections = [
        _PROMPT_HEADER,
        "Due for review today (facts, already computed — do not recompute):",
        _format_due_reviews(data.due_reviews),
        "",
        f"Recent learner utterances (context only, never a focus source — "
        f"{data.window_from.isoformat()} to {data.window_to.isoformat()}):",
        _format_recent(data.recent),
        "",
        "Chronic metrics (facts only — you decide whether a pattern counts as chronic):",
        _format_chronic(
            data.chronic,
            data.chronic_pattern_ids,
            deepest_pattern_id=None if deepest is None else deepest.pattern_id,
        ),
        "",
        _PRONUNCIATION_NOTE,
        _format_pronunciation(data.pronunciation),
        "",
        f"Current level: {data.current_level}",
        "",
    ]
    # `TASK-81` — 발음이 복습 예정일에 걸린 계획에만 붙는다. 판정 재료가 `due_reviews`의
    # `category`인 이유는 상수 위 주석이 소유한다(시도 집계에는 `pattern_id`가 없다).
    if any(review.category == PRONUNCIATION_CATEGORY for review in data.due_reviews):
        sections += [_PRONUNCIATION_FOCUS_RULE, ""]
    # `TASK-108` — 만성 목록이 비면 강제할 대상이 없고 `parse_plan`도 그때 이 규칙을 적용하지
    # 않는다(콜드스타트). 발음 규칙 **뒤에** 두는 이유: 남은 초점 자리를 좁히는 더 구체적인
    # 말이라 나중에 읽히는 자리가 맞다.
    if deepest is not None:
        sections += [_DEEPEST_FOCUS_RULE, ""]
    sections.append(_OUTPUT_SPEC)
    return "\n".join(sections)


def _implied_action(current: str, target: str) -> str:
    """실제 이동이 뜻하는 라벨. `parse_plan`이 두 값을 이미 CEFR 값역으로 좁힌 **뒤에만**
    부른다 — 그래서 `CEFR_LEVELS.index`가 가드 없이 안전하다."""
    if target == current:
        return "keep"
    return "up" if CEFR_LEVELS.index(target) > CEFR_LEVELS.index(current) else "down"


def _warn_on_level_action_mismatch(job_id: UUID, current_level: str, level: LevelDecision) -> None:
    """`level.action`이 실제 이동과 어긋나면 한 줄 남긴다 — **저장은 거부하지 않는다.**

    정본은 `level.target_level`이다(한 단계 제약과 세 값 일치 검증을 이미 통과한 값).
    `action`은 사람이 읽는 라벨이라 잘못 붙은 것이 계획 전체를 버릴 이유는 아니다(Task 5
    리뷰가 이 태스크로 넘긴 것 — `action="down"`인데 상향 A2→B1 같은 조합이 출력 계약을
    통과한다). 다만 **조용히 삼키지 않는다**: 관측이 없으면 프롬프트가 라벨을 잘못 유도하고
    있다는 신호를 잃는다. `warning`인 이유는 함정 H-Z다(지정된 실행에서 INFO 가 안 보인다).
    """
    implied = _implied_action(current_level, level.target_level)
    if level.action == implied:
        return
    logger.warning(
        "job %s: level.action %r disagrees with the actual move %s -> %s (implies %r) — "
        "target_level wins; the label is kept as a label only",
        job_id,
        level.action,
        current_level,
        level.target_level,
        implied,
    )


async def _store_plan(
    conn: asyncpg.Connection, job: ClaimedJob, data: PlanInput, plan: PlanOutput
) -> None:
    """계획 1행 + 노트 1행 + 수준 갱신 + `complete` — 호출자가 연 **한 트랜잭션** 안에서.

    넷을 쪼개면 절반만 반영된 상태가 남는다(설계서 §9 Contract): 계획은 있는데 수준이 안
    올라갔거나, 노트만 남고 계획이 없는 상태를 사용자가 다음 세션에서 그대로 만난다.

    ⚠️ **`complete`의 반환값을 반드시 본다.** `False`는 lease 가 더 이상 우리 것이 아니라는
    뜻이고(`jobs.complete` docstring), 그때 위 세 쓰기를 커밋하면 그 job 을 다시 claim 한
    워커가 또 쓴다 — 계획은 `unique(session_id)`에 막히지만 **노트는 append-only 라 중복
    행이 남는다.** 그래서 트랜잭션 **안에서** 예외를 올려 통째로 롤백시킨다.
    """
    await conn.execute(
        _INSERT_PLAN_SQL,
        job.session_id,
        # `uuid[]` 컬럼이다 — UUID 리스트를 그대로 넘긴다. asyncpg 가 네이티브로 받으므로
        # `str()`을 씌우면 안 된다.
        [item.pattern_id for item in plan.focus],
        # ⚠️ jsonb 에는 **str 만** 바인딩된다 — 파이썬 list/dict 는 `DataError: expected str`
        # 다(슬라이스 1 실측). `ensure_ascii=False`가 한글을 그대로 보존한다.
        json.dumps([question.model_dump() for question in plan.questions], ensure_ascii=False),
        plan.target_level,
        plan.reason,
        # ⚠️ 이 직렬화는 **`InstructionFocus`에 `pattern_id`가 없다는 사실에 의존한다** —
        # `json.dumps`는 UUID 를 직렬화하지 못한다(`TypeError`). 누군가 "타입이 둘이라
        # 중복이다"라며 `FocusPattern`으로 통일하면 이 줄이 그 자리에서 깨진다. 두 타입이
        # 나뉜 이유는 `models/plan.py`의 `InstructionFocus` docstring 이 소유한다.
        json.dumps(plan.instruction.model_dump(), ensure_ascii=False),
        _PLAN_SOURCE_AGENT,
    )
    await conn.execute(
        _INSERT_NOTE_SQL,
        data.user_id,
        json.dumps(
            {"observations": plan.notes, "level_reason": plan.level.reason}, ensure_ascii=False
        ),
        data.window_from,
        data.window_to,
    )
    # 정본은 `target_level`이다 — `level.action`은 라벨일 뿐이다(위 경고 참조).
    await conn.execute(_UPDATE_LEVEL_SQL, data.user_id, plan.level.target_level)
    if not await complete(conn, job.id, job.lease_token):
        raise _LeaseLost


async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """claim 된 `plan_next_session` job 하나를 끝까지 처리한다 (설계서 §3.1의 두 번째 화살표).

    claim 은 호출자(워커)가 이미 했다 — 이 함수는 입력 읽기 → (트랜잭션 **밖**) Claude
    호출 → 검증 → 저장 한 트랜잭션 + `complete`까지 한다.

    `process_analysis`와 같은 규약으로 **어떤 실패도 예외로 올리지 않는다**: 워커 루프가 한
    job 때문에 죽으면 그 사용자는 계획을 영구히 못 받는다. 모든 실패는 `report_failure`로
    큐에 보고한다 — 예외를 밖으로 새게 두면 job 이 `running`에 남아 lease 만료까지 갔다가
    "lease expired without report"라는 **거짓 사유**로 종결된다. 유일한 무보고 경로는 lease
    상실이다: 그 job 은 이미 우리 것이 아니므로 남의 job 에 사유를 쓰지 않는다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return

    try:
        async with pool.acquire() as conn:
            owner_id = await conn.fetchval(_SESSION_OWNER_SQL, job.session_id)
            data = None if owner_id is None else await load_plan_input(conn, owner_id)
    except Exception as exc:  # DB 장애 · 무효 타임존 — 큐에 보고하고 재시도에 맡긴다
        logger.exception("job %s: loading plan input failed", job.id)
        await report_failure(pool, job, f"{type(exc).__name__}: {exc}")
        return

    if data is None:
        await report_failure(pool, job, f"session {job.session_id} not found")
        return

    # 허용 집합은 **프롬프트가 초점 출처로 지목한 두 목록**과 같아야 한다(Task 6 의 `- focus:`가
    # "Due for review today"·"Chronic metrics" 두 절 제목을 그대로 인용한다). 어긋나면 정당한
    # 계획이 거부된다 — 두 곳이 갈라질 수 없게 여기서 한 번 만들어 프롬프트와 검증에 같이 쓴다.
    allowed_pattern_ids = {review.pattern_id for review in data.due_reviews} | {
        metric.pattern_id for metric in data.chronic
    }
    if not allowed_pattern_ids:
        # 콜드스타트 — 두 목록이 **둘 다 비었다**(모든 항목이 `pattern_id`를 가지므로 집합이
        # 비는 것과 같은 조건이다). `PlanOutput.focus`는 최소 1개를 요구하는데 고를 후보가
        # 없어 **무엇을 내도 거부된다** → 확실히 거부될 호출에 비용을 쓰지 않는다.
        # ⚠️ 폴백을 막지 않는다: 계획 행 부재로 세션 시작이 시나리오 뱅크로 떨어지는 것이
        # §3.3 이 정한 동작이고 그 경로는 그대로다.
        await report_failure(pool, job, PLAN_NO_FOCUS_CANDIDATES)
        return

    try:
        raw = await claude.analyze(build_plan_prompt(data))
    except Exception as exc:
        logger.exception("job %s: claude call failed", job.id)
        await report_failure(pool, job, f"{type(exc).__name__}: {exc}")
        return

    # AC11-2 — "가장 깊은 재발"의 순위는 만성 목록을 소유한 쪽이 낸다(`chronic.py`). 여기서
    # 계산해 넘기는 이유는 허용 집합과 같다: `parse_plan`은 출력만 보므로 **무엇이 최상위인지
    # 알 수 없다**(`set[UUID]`에는 순서가 없고, 애초에 깊이 축은 프롬프트에 실린 만성 지표에만
    # 있다). 만성 목록이 비면 `None`이고 그때 그 규칙은 적용되지 않는다 — 복습 예정만 있는
    # 사용자는 허용 집합이 비지 않으므로 위 콜드스타트 분기로도 걸리지 않는다.
    deepest = deepest_recurrence(data.chronic)
    try:
        plan = parse_plan(
            raw,
            current_level=data.current_level,
            allowed_pattern_ids=allowed_pattern_ids,
            deepest_pattern_id=None if deepest is None else deepest.pattern_id,
        )
    except PlanValidationError as exc:
        # 예상된 결과다 — 반쯤 검증된 계획을 쓰지 않는다(§9 Failure). 스택트레이스 없이 사유만.
        logger.warning("job %s: plan output rejected: %s", job.id, exc)
        await report_failure(pool, job, f"plan contract violated: {exc}")
        return

    _warn_on_level_action_mismatch(job.id, data.current_level, plan.level)

    try:
        async with pool.acquire() as conn, conn.transaction():
            await _store_plan(conn, job, data, plan)
    except _LeaseLost:
        # 계획·노트·수준 갱신이 함께 롤백됐다. 이 시도의 산출물은 통째로 버린다 — 같은 job 은
        # 이미 다른 claim 이 들고 있다. `report_failure`를 부르지 않는다(우리 job 이 아니다).
        logger.warning("job %s: lease lost, plan rolled back", job.id)
    except Exception as exc:
        logger.exception("job %s: storing plan failed", job.id)
        await report_failure(pool, job, f"{type(exc).__name__}: {exc}")
