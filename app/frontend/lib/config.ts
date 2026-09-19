/**
 * 백엔드 주소 — 하드코딩하지 않는다. `NEXT_PUBLIC_API_BASE`가 없으면
 * 로컬 개발 기본값(`http://localhost:8000`)으로 떨어진다.
 */
export const API_BASE: string = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/**
 * 세션 하나가 어느 문으로 들어왔는지 (`TASK-10.2` · 진입점 설계서
 * `docs/design/2026-09-12-additional-learning-entry-design.md`).
 *
 * ⛔ **값을 여기서 발명하지 않는다** — `mode` 는 `api/ws.py` 가 아는 값이고 `source` 는 001 의
 * `learning_sessions_learning_source_check` 가 가둔다. 그 값역을 문자열 리터럴로 좁혀 두는 이유는
 * 오타가 **조용히 말하기 세션으로 떨어지는 것**을 타입 검사에서 잡기 위함이다.
 *
 * ⚠️ 네 표면이 있다: 모드 없음(자유 대화·약점 패턴 집중) · `pronunciation` · `shadowing` ·
 * `scenario_intake`. 갈리는 기준은 **지시문이 실제로 달라지는가**이고 그 판정은 설계서 §2 가
 * 소유한다.
 *
 * ⛔ **`scenario_intake` 가 넷째로 갈라진 근거**(`TASK-5` Task 6 · 사용자 결정 79): 「질문 답변 5개」는
 * 이전까지 모드가 없어 자유 대화·약점 패턴 집중과 **구별되지 않았다.** 그 셋이 모두
 * `source: "additional"` 이라 그 값으로는 가릴 수 없고, 가르지 못하면 자유 대화 세션에 질문 다섯
 * 지시가 샌다. 값역의 정본은 018 의 `learning_sessions_mode_check` 다.
 */
export interface SessionEntry {
  mode?: "pronunciation" | "shadowing" | "scenario_intake";
  source?: "recommended" | "additional";
  /**
   * 연습할 쉐도잉 문장 (`TASK-166` — 영상 학습의 [연습하기] 가 이것을 쓴다).
   *
   * ⛔ **이것이 없으면 영상에서 담은 문장을 연습할 수 없다** — 그때까지 클립 선택은 자동이었고
   * (`_ATTACH_SHADOWING_CLIP_SQL`) 사용자가 고를 표면이 없었다.
   * ⚠️ **`mode: "shadowing"` 일 때만 뜻이 있다.** 다른 모드에서는 서버가 읽지 않는다 — 타입으로
   * 묶지 않은 이유는 그 제약이 서버 쪽 정책이고, 여기서 다시 표현하면 두 곳이 갈리기 때문이다.
   * ⚠️ 없는 id 를 주면 서버가 **조용히 자동 선택으로 떨어뜨린다**(설계서 §6).
   */
  itemId?: string;
  /**
   * 이 세션을 **무엇으로 열었는가** (`TASK-242` — 결함 `TASK-234`).
   *
   * ⛔ **없으면 화면 진입이다** — 서버가 넘기지 않으면 001 의 기본값(`ui`)이 쓰이므로 여기서
   * `"ui"` 를 실어 보내지 않는다. 기본값을 두 곳에 두면 한쪽이 조용히 낡는다.
   * ⚠️ **이것이 없던 동안 음성으로 연 세션과 버튼으로 연 세션이 같은 행을 남겼다** — `PRD.md:76`
   * 이 요구하는 구분 가운데 「버튼으로 골랐는가 음성으로 말했는가」를 셀 수 없었다.
   * ⚠️ 값역의 정본은 001 의 `learning_sessions_started_via_check` 다(`schedule` 도 그 안에 있으나
   * 아직 쓰는 경로가 없어 여기 담지 않는다 — 생기는 턴에 그때 더한다).
   */
  via?: "voice_command";
  /**
   * 학습자가 **고른 오류 패턴** — 그 패턴으로 즉시 드릴을 연다 (`TASK-241` · 결함 `TASK-233`).
   *
   * 요구 정본은 `docs/PRD.md:70` 과 `docs/requirements-summary.md:53-54` 다 — 「자주 틀리는 패턴을
   * 직접 보고, 해당 패턴으로 즉시 학습을 만들 수 있음」. 그때까지 결과 화면은 패턴을 **보여 주기만**
   * 했고 `pattern_key` 가 React key 로만 쓰였다.
   * ⚠️ **없는 키를 보내도 학습은 열린다** — 서버가 계획의 초점으로 떨어뜨린다(`?item` 과 같은
   * 관례). 학습자가 방금 사라진 카드를 눌렀을 때 막히지 않게 하는 것이 그 근거다.
   * ⛔ **`mode` 없이도 뜻이 있는 유일한 필드다** — 즉시 드릴은 말하기 세션이고 말하기는 `mode`
   * 값역에 없다(없는 것이 기본값이다). 그래서 `entryFromQuery` 의 「`mode` 가 없으면 `null`」이
   * 이 필드에는 걸리지 않는다.
   */
  patternKey?: string;
}

/**
 * `/ws/session` WebSocket 주소. `API_BASE`의 http(s) 스킴만 ws(s)로 바꾼다.
 *
 * 진입 정보는 **쿼리 문자열**로 실린다 — 소켓 열기 전에 서버가 알아야 하는 값이라(세션 행과
 * 지시문이 그 값으로 갈린다) 첫 프레임으로 보낼 수 없다.
 */
export function sessionSocketUrl(entry: SessionEntry = {}): string {
  const base = `${API_BASE.replace(/^http/, "ws")}/ws/session`;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(entryQuery(entry))) {
    params.set(key, value);
  }
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

/**
 * 진입 정보의 질의 표현 — **인코더와 디코더가 같은 표를 본다** (`TASK-168`).
 *
 * ⛔ 화면이 이 이름들을 직접 적지 않게 하는 것이 이 함수의 목적이다. 영상 학습의 [연습하기] 가
 * `/?mode=…&source=…&item=…` 로 대시보드에 들어오는데, 만드는 쪽과 읽는 쪽이 각자 필드를 적으면
 * **한쪽이 조용히 다른 부분집합을 다룬다** — 실제로 첫 판이 그랬다(만드는 쪽은 셋을 실었고 읽는
 * 쪽은 둘만 읽으며 `source` 를 다시 하드코딩했다).
 */
function entryQuery(entry: SessionEntry): Record<string, string> {
  const query: Record<string, string> = {};
  if (entry.mode) query.mode = entry.mode;
  if (entry.source) query.source = entry.source;
  if (entry.itemId) query.item = entry.itemId;
  if (entry.via) query.via = entry.via;
  if (entry.patternKey) query.pattern = entry.patternKey;
  return query;
}

/**
 * 대시보드로 돌아가 이 진입으로 세션을 여는 주소 (`TASK-241`).
 *
 * ⛔ **화면이 질의 이름을 직접 적지 않게 하는 것이 이 함수의 목적이다** — `entryQuery` 와 같은
 * 근거이고, 영상 학습의 [연습하기] 가 그 이름들을 손으로 적어 한쪽이 조용히 다른 부분집합을
 * 다루던 자리가 실재했다(`TASK-168`).
 * ⚠️ **`/` 로 돌아가는 것이 계약이다** — 세션 화면은 별도 라우트가 아니라 대시보드가 진입 질의를
 * 읽어 여는 구조다(`entryFromQuery` 의 소비자가 그것이다).
 */
export function dashboardEntryHref(entry: SessionEntry): string {
  const params = new URLSearchParams(entryQuery(entry));
  const query = params.toString();
  return query ? `/?${query}` : "/";
}

/**
 * `entryQuery` 의 역함수 — 질의 문자열에서 진입 정보를 읽는다. 진입 정보가 없으면 `null`.
 *
 * ⛔ **`mode` 도 `pattern` 도 없으면 `null` 이다.** 세션을 여는 뜻이 담긴 질의만 받아들이고, 그 밖의
 * 질의(추적 파라미터 등)로 세션이 열리지 않게 한다.
 * ⚠️ **`pattern` 이 둘째 신호로 붙었다** (`TASK-241`) — 즉시 드릴은 **말하기** 세션이고 말하기는
 * `mode` 값역에 없다(없는 것이 기본값이다). `mode` 만 보면 그 진입을 아예 표현할 수 없어, 이전
 * 판이라면 패턴을 실어 보내도 대시보드가 `null` 로 읽고 세션을 열지 않았다.
 * ⛔ **아무 질의나 받아들이는 쪽으로 넓히지 않는다** — 두 이름을 명시로 열거하는 것이 「세션을
 * 여는 뜻」을 지키는 자리다.
 * ⚠️ 값역을 여기서 좁히지 않는다 — 알 수 없는 `mode` 는 서버가 경고하고 말하기로 떨어뜨린다
 * (`services/session_modes.policy_for`). 화면이 먼저 거부하면 그 규약이 두 곳에 갈린다.
 */
export function entryFromQuery(search: string): SessionEntry | null {
  const params = new URLSearchParams(search);
  const mode = params.get("mode");
  const pattern = params.get("pattern");
  if (!mode && !pattern) {
    return null;
  }
  const entry: SessionEntry = {};
  if (mode) {
    entry.mode = mode as SessionEntry["mode"];
  }
  if (pattern) {
    entry.patternKey = pattern;
  }
  const source = params.get("source");
  if (source) {
    entry.source = source as SessionEntry["source"];
  }
  const item = params.get("item");
  if (item) {
    entry.itemId = item;
  }
  const via = params.get("via");
  if (via) {
    entry.via = via as SessionEntry["via"];
  }
  return entry;
}
