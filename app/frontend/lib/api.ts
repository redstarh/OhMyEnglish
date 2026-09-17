/**
 * 조회 API 클라이언트 — `GET /api/sessions/{id}/results` · `GET /api/sessions/next-plan`.
 * 응답 계약은 `app/backend/app/api/results.py` + `app/backend/app/services/results.py`가
 * 정본이다 (R2 상태 판정, R1 상위 2개, R3 부분 실패 플래그, R11-3 추천 이유).
 */

import { API_BASE } from "./config";

export type SessionResultStatus =
  | "analyzing"
  | "final"
  | "partial_failure"
  | "connection_failed"
  | "no_utterances";

export interface Correction {
  pattern_key: string;
  category: string;
  original_span: string;
  correction: string;
  target_form: string;
  reason: string;
  occurrences: number;
}

/**
 * 발음 카드 1장 (Task 8). **기계 키는 이 계약에 없다** — 설계서 §10 미결 4 결정:
 * `th_as_s` 같은 키는 값역이 열려 있고 실물 왕복 0회라 관측된 값이 없어서, 표시 문구를
 * 지금 정하면 발명값이 된다. 그래서 백엔드가 아예 내려주지 않는다.
 */
export interface PronunciationAttempt {
  /** Nova가 시범한 문장. 단 `signal_source`가 `nova_tool`이 아니면 **설명 문구**다. */
  target_form: string;
  /** `null`이면 대답 없이 끝난 시도다 (종료 수렴). 키는 언제나 있다. */
  spoken_form: string | null;
  outcome: "correct" | "incorrect" | "unclear";
  /**
   * 이 행이 **무엇 때문에 생겼는지** (003 CHECK · 024 가 넷째 값을 더했다).
   *
   * ⚠️ **`transcript_analysis` 가 빠져 있었다** — 024(결정 93)로 백엔드 값역이 넓어졌는데 이 타입이
   * 따라오지 않아, 그 값을 비교하는 코드가 `tsc` 에서 「겹치지 않는 비교」로 막혔다(`TASK-88.1`).
   * 화면이 갈래를 가르는 근거가 이 값이므로 값역이 낡으면 새 신호가 조용히 남의 갈래로 간다.
   */
  signal_source: "nova_tool" | "transcript_analysis" | "korean_transcript" | "agent_reprompt";
  /**
   * 이 시도가 **복습에 쓰이지 않는가** (사용자 결정 95 · `TASK-116.2`).
   *
   * 코치가 말한 소리와 기록된 소리가 어긋난 시도는 복습 시계를 돌리지 않는다(결정 82).
   * ⛔ 판정값 자체(`sound_check`)는 오지 않는다 — 기계 키이고 화면이 필요한 것은 이 한 가지다.
   * ⚠️ **미판정이 평시라 기본이 `false`** 다. 진행 중 세션의 시도도 `false` 로 온다.
   */
  review_excluded: boolean;
}

/**
 * 드릴이 계획만큼 돌았는지 (설계서 §2.3 · 캡틴 결정 10).
 *
 * ⚠️ **이 두 수를 화면에 렌더하지 않는다.** 소비자는 서버와 로그다 — 결정 10이 정한 용도는
 * 「지시문을 고치는 입력」 하나다. 분자와 분모를 나란히 주면 `9 / 12`로 읽히고 그것이 가장
 * 점수처럼 보이는 모양인데, 미달의 주어는 학습자가 아니라 **대화 모델**이라 학습자가 손쓸 수
 * 없는 수를 자기 점수로 읽게 된다. API가 보내는 것과 화면이 그리는 것이 어긋나 보이는 이 계약은
 * 의도된 것이고, 화면은 미달일 때 사실 진술 한 문장만 그린다.
 */
export interface DrillTurns {
  exchanges_observed: number;
  exchanges_expected: number;
}

/**
 * 세션 총평 (`TASK-62` · 설계서 `docs/design/2026-09-13-session-summary-design.md`).
 *
 * ⛔ **점수·등급 필드가 «없는 것이 계약»이다.** `R11-8` 이 *"임계값을 제품이 발명하지 않는다"* 이고
 * `R13-5` 가 *"점수는 이 요약의 것이 아님"* 이다 — 값역을 좁혀 구조가 그 경계를 강제한다.
 * ⚠️ `quote` 는 **부차**이고 학습자가 말한 영어 원문 그대로다(번역하지 않는다). 문구는 한국어다.
 */
export interface SummaryWeakPoint {
  point: string;
  quote?: string;
}

export interface SessionSummary {
  went_well: string[];
  weak_points: SummaryWeakPoint[];
}

export interface SessionResultPayload {
  status: SessionResultStatus;
  partial_failure: boolean;
  // `analyzing`/`connection_failed`/`no_utterances`에서는 응답에 키 자체가 없다.
  corrections?: Correction[];
  // `corrections`와 달리 **항상 있다**(비면 `[]`) — R2 판정과 독립이다.
  pronunciation: PronunciationAttempt[];
  // `corrections`와 **같은 규약**으로 빠진다: 위 세 상태에서는 기대값이 기록돼 있어도 키가
  // 없고, 계획 없이 시작한 세션에서도 없다(관측 대상이 아니다).
  drill?: DrillTurns;
  // `TASK-79` — **분석 대상 발화는 있는데 그 job 이 아직 하나도 없다.** 종료 flush 가 실패한
  // 세션의 모양이고, 워커의 회복 스윕이 나중에 그 묶음을 걷으므로 그때의 `no_utterances`는
  // 영구가 아니다. 화면은 이 값이 참인 동안 폴링을 이어간다 — 이전 판은 프론트 상수(약 6초)로
  // 버텼는데 스윕이 언제 도는지 보장하는 계약이 없어 어떤 값도 맞을 수 없었다.
  // `pronunciation`처럼 **항상 있다** — 상태마다 키 존재를 갈라 읽지 않게 한다.
  awaiting_analysis: boolean;
  // `TASK-62` — 세션 총평. `corrections`·`drill` 과 **같은 규약**으로 빠진다: 총평 job 이 아직
  // 돌지 않았으면 키가 없다.
  // ⛔ **두 배열이 비어 있는 채로 오는 것은 「없음」이 아니다** — 「만들었고 담을 것이 없었다」다
  //   (발화 0건 세션이 그 모양이다). 그 구별을 화면이 지운다면 API 가 애써 가른 것이 사라진다.
  summary?: SessionSummary;
}

/**
 * 다음 세션 계획의 요약 (R11-3). 계획이 없으면 두 값이 **모두 null**이다 — 오류가 아니라
 * "아직 계획이 없다"이고, 화면은 그 자리를 비운다. 초점 패턴·질문 목록은 이 계약에 없다:
 * 질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.
 */
export interface NextPlanSummary {
  reason: string | null;
  target_level: string | null;
}

/**
 * `fetchSessionResults`와 달리 **던지지 않는다** — 계획 표시는 학습을 막지 않으므로
 * 응답이 실패면 조용히 빈 요약을 돌려준다. 단 네트워크 자체가 끊기면 `fetch`가 reject
 * 하므로 호출자가 그 경로를 잡아야 한다(`app/page.tsx`).
 */
export async function fetchNextPlan(): Promise<NextPlanSummary> {
  // 이유는 세션이 끝날 때마다 바뀐다 — 브라우저 휴리스틱 캐시에 걸리면 지난 계획이 남는다.
  const response = await fetch(`${API_BASE}/api/sessions/next-plan`, { cache: "no-store" });
  if (!response.ok) {
    return { reason: null, target_level: null };
  }
  return (await response.json()) as NextPlanSummary;
}

/** 그날 그 패턴을 틀린 자리 1건 (PRD §13 R13-2). 전부가 아니라 예시 하나다. */
export interface DailyErrorExample {
  original_span: string;
  correction: string;
  reason: string;
}

/** 그날 패턴 1종의 집계. 판정(만성 여부·개선 여부)은 이 계약에 없다 — R13-5. */
export interface DailyErrorPattern {
  pattern_key: string;
  category: string;
  target_form: string;
  occurrences: number;
  example: DailyErrorExample;
}

/**
 * 오늘(학습자 타임존) 오류 요약 (PRD §13). 계약의 정본은
 * `app/backend/app/api/daily.py` + `app/backend/app/services/daily_summary.py`다.
 *
 * `analyzed`가 「그날 분석이 돌고 오류 0건」과 「그날 학습이 없었다」를 가른다(R13-7) — 두 개수만
 * 보면 구별되지 않는다. `patterns`·두 개수는 항상 있다(비면 `[]`·`0`).
 */
export interface DailySummaryPayload {
  summary_date: string;
  analyzed: boolean;
  occurrence_count: number;
  pattern_count: number;
  patterns: DailyErrorPattern[];
  /**
   * 오늘(학습자 타임존) 시나리오를 하나라도 마쳤는가 (PRD §14 R14-1 · `TASK-2`).
   *
   * 기준은 「시나리오가 붙은 세션이 정상 종료됐다」이고 **드릴 교대 수는 조건이 아니다** —
   * 미달의 주어가 학습자가 아니라 대화 모델이기 때문이다(캡틴 결정 10). 근거의 정본은
   * `docs/design/2026-09-11-daily-completion-design.md` §3.1 이다.
   */
  completed_today: boolean;
  /** 오늘 마친 시나리오 수. 판정은 `completed_today` 가 갖는다 — 1개로 충분하다(R14-5). */
  completed_scenarios: number;
}

/**
 * `fetchNextPlan`과 같은 규약으로 **던지지 않는다** — 하루 요약은 세션 교정 표시를 막지 않는다.
 * 실패하면 `analyzed: false`를 돌려주고 화면은 그 절을 그리지 않는다.
 *
 * ⚠️ 그래서 조회 실패와 「그날 학습이 없었다」가 화면에서 같은 결과를 낸다. 의도한 것이다 —
 * 결과 화면의 주 내용은 방금 세션의 교정이고, 하루 요약을 못 읽었다고 그것을 가리지 않는다.
 */
export async function fetchDailySummary(): Promise<DailySummaryPayload> {
  const empty: DailySummaryPayload = {
    summary_date: "",
    analyzed: false,
    occurrence_count: 0,
    pattern_count: 0,
    patterns: [],
    completed_today: false,
    completed_scenarios: 0,
  };
  // 하루 요약은 분석이 끝날 때마다 바뀐다 — 캐시에 걸리면 지난 판독이 남는다.
  const response = await fetch(`${API_BASE}/api/daily-summary`, { cache: "no-store" });
  if (!response.ok) {
    return empty;
  }
  return (await response.json()) as DailySummaryPayload;
}

/**
 * 결과 API가 실패 상태를 응답했을 때 던진다 (TASK-55·TASK-56).
 *
 * ⛔ **`status`는 화면 문구가 아니라 분류용이다.** 이전 판은 `결과 API가 ${status}을
 * 반환했습니다`를 던졌고 결과 화면이 그것을 그대로 그려서 학습자가 `404`를 봤다. 학습자 문구는
 * 화면이 소유하고(`app/results/[sessionId]/page.tsx`), 이 `message`는 콘솔·로그용이라 영어다 —
 * 한국어로 쓰면 다음 사람이 화면에 그려도 되는 문장으로 착각한다.
 *
 * 폴링을 멈출지 판단하는 근거도 이 `status`다: 4xx는 같은 요청을 되풀이해도 같은 답이 온다.
 */
export class SessionResultsError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`session results request failed: HTTP ${status}`);
    this.name = "SessionResultsError";
    this.status = status;
  }
}

export async function fetchSessionResults(sessionId: string): Promise<SessionResultPayload> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/results`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new SessionResultsError(response.status);
  }
  return (await response.json()) as SessionResultPayload;
}

/** 연속 학습일 (PRD §15). `today_done` 이 자정 직후의 `current` 를 오해 없이 쓰게 한다. */
export interface Streak {
  current: number;
  longest: number;
  today_done: boolean;
}

/**
 * 히스토리 한 줄. `learned` 와 `analyzed` 는 **다른 사실**이다 — `daily_error_summary` 가
 * 2026-09-11 에 생겼으므로 그 이전 날짜는 학습했어도 요약이 없다. 합쳐 읽으면 그 날들이
 * 「학습 없음」으로 보인다(설계서 `2026-09-11-streak-and-history-design.md` §6).
 */
export interface HistoryDay {
  day: string;
  learned: boolean;
  completed_scenarios: number;
  analyzed: boolean;
  occurrence_count: number;
  pattern_count: number;
}

export interface HistoryPayload {
  streak: Streak;
  days: HistoryDay[];
}

/**
 * 히스토리 조회. 실패하면 **`null`** 이다 — 빈 히스토리를 돌려주면 화면이 「학습 기록이 없다」는
 * 거짓을 그린다. 전용 화면이므로 실패를 실패로 말해야 한다(`fetchDailySummary` 와 반대인 이유:
 * 그쪽은 결과 화면의 곁가지라 조용히 비우는 편이 낫다).
 */
export async function fetchHistory(): Promise<HistoryPayload | null> {
  const response = await fetch(`${API_BASE}/api/history`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as HistoryPayload;
}

/** 주간 리포트의 상위 오류 한 종 (`TASK-26` · PRD:117). */
export interface WeeklyTopPattern {
  category: string;
  pattern_key: string;
  target_form: string;
  occurrences: number;
}

/**
 * 주간 리포트의 **사실**. ⛔ 판정을 담지 않는다 — R11-8 이 「조회는 사실을 제공하고 판단은 학습
 * 분석 Agent 가 한다」로 그 경계를 정했다.
 * ⚠️ 리포트가 아직 없으면 `{}` 로 온다(키는 항상 있다) — 그래서 필드가 전부 옵셔널이다.
 */
export interface WeeklyMetrics {
  session_count?: number;
  occurrence_count?: number;
  pattern_count?: number;
  top_patterns?: WeeklyTopPattern[];
}

/** 주간 리포트의 **모델 판단** 둘. 점수·등급을 담을 자리가 없다(값역이 계약이다). */
export interface WeeklyInsights {
  improving?: string[];
  next_scenarios?: string[];
}

/**
 * 주간 리포트 한 벌. `analyzed` 가 「아직 없음」과 「만들었다」를 가른다 — `week_start` 가 `null`
 * 이면 한 주도 만들어지지 않았다는 뜻이다.
 */
export interface WeeklyReportPayload {
  week_start: string | null;
  analyzed: boolean;
  metrics: WeeklyMetrics;
  insights: WeeklyInsights;
}

/**
 * 주간 리포트 조회. 실패하면 **`null`** 이다 — `fetchHistory` 와 같은 이유로 전용 화면이므로
 * 실패를 실패로 말한다(빈 리포트를 돌려주면 「그 주에 아무 일도 없었다」는 거짓을 그린다).
 * ⛔ 서버는 리포트가 없을 때도 **200** 을 주므로 `null` 은 오직 통신·서버 오류다.
 */
export async function fetchWeeklyReport(): Promise<WeeklyReportPayload | null> {
  const response = await fetch(`${API_BASE}/api/weekly-report`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as WeeklyReportPayload;
}

/* ─── 영상으로 배우기 (`TASK-167` · 설계서 `docs/design/2026-09-18-video-learning-design.md` §3) ─── */

/** 목록 화면의 카드 하나. ⛔ 썸네일 URL 이 없다 — `thumbnailUrl(youtube_id)` 로 조립한다. */
export interface VideoSummary {
  id: string;
  youtube_id: string;
  title: string;
  channel_name: string;
  phrase_count: number;
  /** 제목·채널을 받은 지 30일이 지났는가. 서버가 계산한다 — 화면이 날짜를 비교하지 않는다. */
  metadata_stale: boolean;
}

/** 담은 문장 하나. 이름이 쉐도잉 payload 와 같다(`ShadowingSetup` 과 맞춘 것이다). */
export interface VideoPhrase {
  id: string;
  transcript: string;
  clip_start_sec: number;
  clip_end_sec: number;
}

/** 학습 화면이 한 번의 왕복으로 받는 것. */
export interface VideoDetail {
  id: string;
  youtube_id: string;
  title: string;
  channel_name: string;
  metadata_stale: boolean;
  phrases: VideoPhrase[];
}

/**
 * 담기·갱신의 결과. `created` 가 **화면 문구를 가른다** — 담았다 vs 이미 담아 둔 영상이다.
 *
 * ⛔ 중복은 오류가 아니라 갱신이다(설계서 §1 질문 2) — 정책이 메타데이터 보관을 30일로 제한하므로
 * 갱신 경로가 있어야 하고, 그것을 담기와 같은 요청이 겸한다.
 */
export interface StoredVideo {
  id: string;
  youtube_id: string;
  title: string;
  channel_name: string;
  created: boolean;
}

/**
 * 쓰기 요청의 결과 — **실패의 종류를 화면에 알린다.**
 *
 * ⛔ 이 리포의 기존 조회 함수는 실패에 `null` 을 주는데(전용 화면) 쓰기는 그럴 수 없다: 설계서 §7 이
 * 문구를 **갈라** 정했고(「이 링크에서 영상을 찾지 못했어요」 vs 「지금 확인할 수 없어요」) `null`
 * 하나로는 그 둘을 가릴 수 없다. 그래서 이 갈래만 결과형을 쓴다.
 */
export type WriteResult<T> = { ok: true; value: T } | { ok: false; reason: WriteFailure };

/**
 * `refused` = 서버가 값역으로 거부했다(422) · `unavailable` = 그 밖(네트워크·서버 오류·404).
 *
 * ⚠️ 404 를 따로 두지 않는다 — 목록에서 지운 직후에만 생기고 화면이 이미 그 카드를 지웠다.
 */
export type WriteFailure = "refused" | "unavailable";

async function writeJson<T>(
  path: string,
  method: "POST" | "DELETE",
  body?: unknown,
): Promise<WriteResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      cache: "no-store",
      ...(body === undefined
        ? {}
        : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    });
    if (!response.ok) {
      return { ok: false, reason: response.status === 422 ? "refused" : "unavailable" };
    }
    // 204 에는 몸통이 없다 — `json()` 을 부르면 던진다.
    if (response.status === 204) {
      return { ok: true, value: undefined as T };
    }
    return { ok: true, value: (await response.json()) as T };
  } catch {
    return { ok: false, reason: "unavailable" };
  }
}

/** 담아 둔 영상 전부. 실패하면 `null` — 전용 화면이므로 빈 목록으로 거짓을 그리지 않는다. */
export async function fetchVideos(): Promise<VideoSummary[] | null> {
  const response = await fetch(`${API_BASE}/api/videos`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return ((await response.json()) as { videos: VideoSummary[] }).videos;
}

/** 영상 하나와 담은 문장 전부. 없거나 실패하면 `null`. */
export async function fetchVideo(videoId: string): Promise<VideoDetail | null> {
  const response = await fetch(`${API_BASE}/api/videos/${videoId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as VideoDetail;
}

/**
 * 영상을 담거나 이미 담은 것의 메타데이터를 갱신한다.
 *
 * ⚠️ **URL 을 그대로 넘긴다** — 식별자를 뽑는 것은 서버의 일이다(`parse_youtube_id`).
 */
export async function storeVideo(input: {
  url: string;
  title: string;
  channelName: string;
}): Promise<WriteResult<StoredVideo>> {
  return writeJson<StoredVideo>("/api/videos", "POST", {
    url: input.url,
    title: input.title,
    channel_name: input.channelName,
  });
}

/** 영상만 지운다. **담은 문장은 남는다**(설계서 §1 질문 1). */
export async function removeVideo(videoId: string): Promise<WriteResult<void>> {
  return writeJson<void>(`/api/videos/${videoId}`, "DELETE");
}

/** 구간과 들은 문장을 담는다. */
export async function storePhrase(
  videoId: string,
  input: { transcript: string; clipStartSec: number; clipEndSec: number },
): Promise<WriteResult<VideoPhrase>> {
  return writeJson<VideoPhrase>(`/api/videos/${videoId}/phrases`, "POST", {
    transcript: input.transcript,
    clip_start_sec: input.clipStartSec,
    clip_end_sec: input.clipEndSec,
  });
}

/** 담은 문장 하나를 지운다. ⚠️ 경로에 영상 id 가 필요하다 — 문장은 그 영상의 하위 자원이다. */
export async function removePhrase(
  videoId: string,
  phraseId: string,
): Promise<WriteResult<void>> {
  return writeJson<void>(`/api/videos/${videoId}/phrases/${phraseId}`, "DELETE");
}
