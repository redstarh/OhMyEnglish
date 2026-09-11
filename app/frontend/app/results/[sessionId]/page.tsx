"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchDailySummary,
  fetchSessionResults,
  SessionResultsError,
  type DailySummaryPayload,
  type PronunciationAttempt,
  type SessionResultPayload,
  type SessionResultStatus,
} from "@/lib/api";

const POLL_INTERVAL_MS = 2000;

// R2 매핑 표(AC 문서 §R2) — terminal 상태면 폴링을 멈춘다.
const TERMINAL_STATUSES = new Set<SessionResultStatus>([
  "final",
  "partial_failure",
  "connection_failed",
  "no_utterances",
]);

const STATUS_LABEL: Record<SessionResultStatus, string> = {
  analyzing: "분석 중",
  final: "확정",
  partial_failure: "부분 실패",
  connection_failed: "연결 실패",
  no_utterances: "분석 대상 없음",
};

// 한 문장 안에서 문체를 섞지 않는다 (TASK-57) — 이전 판은 `일부 발화는 분석하지 못했다 —
// 재시도되지 않습니다`로 앞이 해라체, 뒤가 합쇼체였다. 이 화면의 다른 문구는 `~습니다`·`~어요`다.
const PARTIAL_FAILURE_NOTICE = "분석하지 못한 발화가 있습니다 — 재시도되지 않습니다";

// 조회 실패 문구 — **화면이 소유한다** (TASK-55). 예외의 `message`를 그대로 그리면 HTTP 상태
// 코드(`404`)와 `fetch`의 영어 오류가 학습자에게 노출된다. 상태 코드는 아래 두 함수의 분류
// 입력이고 문구에는 들어가지 않는다 — 그래서 `404을`/`404를` 같은 조사 문제도 함께 사라진다.
const NOT_FOUND_NOTICE = "그 학습 결과를 찾을 수 없습니다.";
const UNAVAILABLE_NOTICE = "그 학습 결과를 열 수 없습니다.";
const RETRYING_NOTICE = "결과를 불러오지 못했습니다. 다시 시도하고 있습니다...";

// 결과 화면에서 빠져나갈 인앱 수단 (TASK-55). 조회가 실패한 화면에서는 이것이 유일한 출구다 —
// 그전에는 학습자가 브라우저 뒤로가기 말고는 나갈 방법이 없었다.
const HOME_LINK_LABEL = "← 학습 시작 화면으로";
// 히스토리 진입점 (PRD §15 · `TASK-107`). ⛔ 링크를 두지 않으면 그 화면에 **도달할 길이 없다** —
// 이 리포가 네 번 낸 「reader 0곳」의 화면 버전이다. 세션을 마친 자리가 되짚기 좋은 자리다.
const HISTORY_LINK_LABEL = "학습 히스토리 보기 →";

/**
 * 폴링을 이어갈지 정한다. **판정을 여기 한 곳에 모아 두는 것이 계약이다** — 흩어 두면
 * 「어느 상태에서 멈추는가」를 코드 여러 곳에서 읽어야 하고, `TASK-56`·`TASK-77`·`TASK-79` 가
 * 각각 그 판정을 건드렸다.
 *
 * `분석 대상 없음`을 **첫 판독으로 확정하지 않는다** (`TASK-77` · 캡틴 결정 2026-09-10):
 * 종료 경로의 flush 가 실패하면(`_flush_analysis`가 예외를 삼킨다 — 분석 1건보다 세션과 전사문이
 * 중요하다) 세션이 `completed` + job 0 으로 남고 결과 API 가 R2 규칙 2 로 `no_utterances`를 낸다.
 * **그 상태는 영구가 아니다** — 워커가 유휴일 때 `flush_ended_sessions`가 그 묶음을 걷어 job 을
 * 건다. 첫 판독에서 멈추면 그 뒤에 나온 교정을 학습자가 **영구히** 보지 못한다.
 *
 * ⛔ **그 판정을 상수로 하지 않는다** (`TASK-79`). 이전 판은 `NO_UTTERANCES_RECHECKS = 3`
 * (약 6초)로 버텼는데 **스윕이 언제 도는지 보장하는 계약이 없어 어떤 상수도 맞을 수 없다** —
 * 게다가 워커는 큐가 빌 때만 스윕하므로 분석이 밀리는 동안에는 아예 돌지 않는다. 그러면 네 번째
 * 판독에서 폴링이 멈추고, 뒤늦게 나온 교정을 화면이 영구히 표시하지 않는다.
 *
 * 대신 **서버가 회복 대상인지 알려준다**: `awaiting_analysis`는 「분석 대상 발화는 있는데 그 job 이
 * 아직 0건」이라는 DB 사실이다(`services/results.SessionResult`가 뜻을 소유한다). 워커 상태와
 * 무관하므로 스윕이 언제 돌든 판정이 성립한다.
 *
 * ⚠️ **이것이 「영구 폴링」을 되살리는 것이 아니다.** 회복이 끝나면 job 이 생겨 그 값이 거짓이
 * 되고 폴링이 멈춘다. 그리고 발화가 0건인 세션(진짜로 말하지 않은 세션)은 처음부터 거짓이라
 * **첫 판독에 멈춘다** — 이전 판보다 오히려 빠르다.
 */
export function shouldKeepPolling(
  status: SessionResultStatus,
  awaitingAnalysis: boolean,
): boolean {
  if (!TERMINAL_STATUSES.has(status)) return true;
  if (status === "no_utterances") return awaitingAnalysis;
  return false;
}

/**
 * 4xx는 영구 오류다 — 같은 요청을 되풀이해도 같은 답이 온다 (TASK-56). `TERMINAL_STATUSES`와
 * **같은 뜻으로** 폴링을 멈춘다. 5xx와 네트워크 실패(`fetch` 자체가 reject)는 회복 가능하므로
 * 계속 폴링한다 — 이 갈림이 없던 이전 판은 없는 세션 화면을 2초마다 영구히 다시 불렀다.
 */
function isPermanentFailure(err: unknown): boolean {
  return err instanceof SessionResultsError && err.status >= 400 && err.status < 500;
}

/** 학습자에게 보일 문구를 고른다. 기계 낱말(`API`·상태 코드·영어 예외)을 쓰지 않는다. */
function failureNotice(err: unknown): string {
  if (err instanceof SessionResultsError) {
    if (err.status === 404) return NOT_FOUND_NOTICE;
    if (err.status < 500) return UNAVAILABLE_NOTICE;
  }
  return RETRYING_NOTICE;
}

// 드릴 미달 안내 (설계서 §2.3 · 캡틴 결정 10). **숫자를 쓰지 않는 것이 계약이다** — API는
// `drill`로 두 수를 보내지만 여기서 렌더하는 것은 이 한 문장뿐이고, 두 수의 소비자는 서버·로그다
// (결정 10이 정한 용도는 「지시문을 고치는 입력」 하나다). 분자와 분모를 나란히 두면 `9 / 12`로
// 읽히고 그것이 가장 점수처럼 보이는 모양인데, 이 화면의 톤 계약은 "채점하지 않습니다,
// 시범합니다"(`docs/storyboard.html`:101)다.
// **주어를 세션에 둔다** — 미달의 주어는 학습자가 아니라 대화 모델이므로(결정 10) 학습자를
// 주어로 쓰면 손쓸 수 없는 수를 자기 잘못으로 읽는다. 문구는 설계서 §2.3의 예시 그대로다.
const DRILL_SHORTFALL_NOTICE = "오늘은 드릴이 계획보다 짧았어요.";

// 발음 카드 문구 (Task 8). 어휘는 `docs/storyboard.html` 03b(:129-133)를 따른다 —
// "채점하지 않습니다. 시범합니다"(:101)가 이 화면의 톤 계약이라 점수·정답률을 쓰지 않는다.
const PRONUNCIATION_HEADING = "발음";
const MODELED_LABEL = "시범 문장";
const SPOKEN_LABEL = "내 발화";
// `spoken_form`이 null인 `incorrect` 행 = 대답 없이 끝난 시도(종료 수렴 §3.2).
// 빈칸으로 두면 "들었지만 아무것도 안 들렸다"로 읽히므로 그 사실을 문장으로 적는다.
const NO_ANSWER_NOTICE = "대답 없이 끝났어요";
// 신호 행(`korean_transcript`)은 Nova의 시범이 아니라 우리 감지기의 **관찰**이다.
// 같은 라벨을 쓰면 그 설명 문구가 "이렇게 발음하세요"로 보인다(TASKS.md A-2 후단 ①).
const SIGNAL_LABEL = "관찰된 신호";

const OUTCOME_LABEL: Record<PronunciationAttempt["outcome"], string> = {
  correct: "✓ 좋아요",
  incorrect: "다시 연습해요",
  unclear: "잘 안 들렸어요",
};

// 색은 `app/globals.css`의 4개 토큰만 쓴다 — 하드코딩 색이 다크모드 위계를 뒤집은
// 1차수 F-1의 재발 방지. `unclear`는 오류가 아니라 미판정이므로 danger가 아니라 muted다.
const OUTCOME_COLOR: Record<PronunciationAttempt["outcome"], string> = {
  correct: "var(--foreground)",
  incorrect: "var(--danger)",
  unclear: "var(--foreground-muted)",
};

// 오늘 학습 완료 문구 (PRD §14 R14-4 · AC14-5). 사용자가 확정한 요구사항이 「하나의 학습
// 시나리오를 마치면 그날 학습을 완료한 것으로 봄」이고, 그 표시를 보고 **이어 갈지 종료할지**
// 학습자가 판단한다. 그래서 이 문장은 점수판이 아니라 **판단 재료**다 — 드릴 미달 문구를
// 「달성은 그리지 않는다」로 둔 결정 10 과 어긋나지 않는다(그쪽은 학습자가 손쓸 수 없는 수였다).
// ⚠️ 개수는 2개 이상일 때만 붙인다 — `시나리오 1개`는 판정과 같은 말을 두 번 하는 것이다.
const dailyDoneNotice = (scenarios: number) =>
  scenarios > 1 ? `오늘 학습을 마쳤어요 — 시나리오 ${scenarios}개` : "오늘 학습을 마쳤어요";

// 오늘 요약 절 (PRD §13 R13-4 · AC13-4). 어휘는 세션 교정 카드와 같은 것을 쓴다 — 같은 화면에서
// 두 절이 다른 낱말로 같은 것을 부르면 학습자가 다른 개념으로 읽는다.
const DAILY_HEADING = "오늘 무엇을 틀렸는지";
// 반복은 사실 진술이라 적는다 — 학습자가 무엇을 되풀이했는지 알아야 다음 초점이 이해된다.
// **1번일 때는 쓰지 않는다**: 「오늘 1번」은 아무것도 말하지 않으면서 개수 표시만 남긴다.
const dailyRepeatNotice = (occurrences: number) => `오늘 ${occurrences}번 나왔어요`;

const DAILY_CARD_STYLE = {
  // 세션 교정 카드(사각 테두리)와 발음 카드(왼쪽 규칙선) 사이의 위계를 새로 만들지 않는다 —
  // 하루 요약은 방금 세션보다 뒤에 오고 무게가 가벼워야 하므로 발음 카드와 같은 모양을 쓴다.
  borderLeft: "3px solid var(--foreground-muted)",
  paddingLeft: "0.75rem",
  margin: "0.75rem 0",
} as const;

const PRONUNCIATION_CARD_STYLE = {
  // 문법 교정 카드와 나란히 두되 한 덩어리로 읽히게 왼쪽 규칙선만 쓴다 — 색 토큰이
  // 4개뿐이어서 muted로 사각 테두리를 두르면 위계상 문법 카드보다 무거워진다.
  borderLeft: "3px solid var(--foreground-muted)",
  paddingLeft: "0.75rem",
  margin: "0.75rem 0",
} as const;

const PRONUNCIATION_LABEL_STYLE = {
  margin: "0.25rem 0 0",
  fontSize: "0.8rem",
  color: "var(--foreground-muted)",
} as const;

function outcomeLabel(outcome: PronunciationAttempt["outcome"]): string {
  // 값역은 003 CHECK가 강제하지만 HTTP 응답은 외부 경계다 — 모르는 값이 오면 지우지 않고
  // 그대로 보여준다. 조용히 사라지면 "판정이 없었던 시도"로 잘못 읽힌다.
  return OUTCOME_LABEL[outcome] ?? outcome;
}

function resolveSessionId(param: string | string[] | undefined): string | null {
  if (typeof param === "string") return param;
  if (Array.isArray(param) && param.length > 0) return param[0];
  return null;
}

export default function ResultsPage() {
  const params = useParams<{ sessionId: string | string[] }>();
  const sessionId = resolveSessionId(params.sessionId);

  const [result, setResult] = useState<SessionResultPayload | null>(null);
  const [daily, setDaily] = useState<DailySummaryPayload | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    async function poll(): Promise<void> {
      try {
        const data = await fetchSessionResults(sessionId as string);
        if (cancelled) return;
        setResult(data);
        setFetchError(null);
        // `TASK-79` — 판독 사이에 들고 갈 상태가 없다. 회복 대상인지를 **서버가 판독마다**
        // 알려주므로 프론트가 횟수를 세지 않는다(이전 판은 연속 판독 수를 셌다).
        if (shouldKeepPolling(data.status, data.awaiting_analysis)) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setFetchError(failureNotice(err));
        // 회복 가능한 실패(5xx·네트워크)만 다시 부른다 — 4xx는 terminal이다(`isPermanentFailure`).
        if (!isPermanentFailure(err)) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [sessionId]);

  // 하루 값은 **상태가 바뀔 때마다 한 번** 읽는다. 폴링(2초)에 태우지 않는 이유: 오류 요약은
  // 분석 저장 트랜잭션에서만 갱신되므로 분석 중에 반복해 읽어도 같은 값이고 요청만 는다.
  //
  // ⛔ **terminal 을 기다리지 않는다** (`TASK-2`). 이전 판은 `TERMINAL_STATUSES` 를 조건으로 걸어서
  // 분석이 `analyzing` 에 머무는 동안 **「오늘 학습을 마쳤어요」가 아예 뜨지 않았다** — 화면을 열어
  // 직접 확인했다. 완료 여부는 **분석과 독립**이다(세션이 끝난 순간의 DB 사실이고 PRD §14 의
  // 요구사항은 그 자리에서 이어 갈지 판단하는 것이다). `status` 가 바뀔 때 다시 읽으므로 분석이
  // 끝난 뒤의 오류 절도 같은 효과가 채운다.
  const status = result?.status;
  useEffect(() => {
    let cancelled = false;
    void fetchDailySummary().then((data) => {
      if (!cancelled) setDaily(data);
    });
    return () => {
      cancelled = true;
    };
  }, [status]);

  const showCorrections = result?.status === "final" || result?.status === "partial_failure";
  // `corrections`는 상태에 따라 키가 없다(R2 규칙 1·2·3) — 여기서 한 번만 빈 배열로 정리한다.
  const corrections = result?.corrections ?? [];
  // 발음 카드는 R2 판정과 **독립**이라 `showCorrections`를 타지 않는다 — `analyzing`
  // 중에도 보인다(근거: `app/backend/app/services/results.py` 모듈 docstring 마지막 절).
  const pronunciation = result?.pronunciation ?? [];
  // 미달일 때만 그린다. 미달이 아니면 **아무것도 그리지 않는다** — 달성을 알리는 문장은
  // 그 자체로 점수판이 된다. 상태 조건을 여기서 다시 쓰지 않는 이유: `drill` 키는 서버가
  // 이미 R2 규약대로 뺀다(`analyzing`/`connection_failed`/`no_utterances`에서는 없다).
  // 키 부재(`undefined`)와 `null`을 함께 막는다 — HTTP 응답은 외부 경계이고, 서버 계약은
  // "키를 뺀다"이지만 그 계약이 깨졌을 때 화면이 예외로 죽는 것이 가장 나쁜 결과다.
  const drill = result?.drill;
  const drillFellShort = drill ? drill.exchanges_observed < drill.exchanges_expected : false;
  // 그날 분석이 돌고 오류가 0건이면 **아무것도 그리지 않는다**(AC13-5). 결정 10이 드릴 달성
  // 문구에 내린 판단과 같다 — 달성을 알리는 문장은 그 자체로 점수판이 된다. `analyzed`가 거짓인
  // 경우(그날 학습이 없었다 · 조회 실패)도 같은 결과이고, 그 뜻의 정본은 `lib/api.ts`가 갖는다.
  const dailyPatterns = daily?.analyzed ? daily.patterns : [];
  // AC14-5 — 마치지 않았으면 **문구를 쓰지 않는다**(0개를 알리는 문장도 쓰지 않는다).
  const completedToday = daily?.completed_today ?? false;

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>학습 결과</h1>

      {!sessionId && <p style={{ color: "var(--danger)" }}>세션 id가 없습니다.</p>}

      {sessionId && !result && (
        <p style={{ color: fetchError ? "var(--danger)" : undefined }}>
          {fetchError ?? "결과를 불러오는 중입니다..."}
        </p>
      )}

      {result && (
        <>
          <p style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{STATUS_LABEL[result.status]}</p>

          {result.status === "partial_failure" && <p>{PARTIAL_FAILURE_NOTICE}</p>}

          {/* 세션에 대한 사실 진술 한 줄이다 — 오류가 아니므로 danger를 쓰지 않고, 상태
              라벨과 위계를 다투지 않도록 muted로 둔다. */}
          {drillFellShort && (
            <p style={{ color: "var(--foreground-muted)" }}>{DRILL_SHORTFALL_NOTICE}</p>
          )}

          {/* 오늘 학습 완료 — 교정보다 **먼저** 온다. 「오늘 다 했나」가 그 아래를 읽는 틀이고,
              학습자가 이어 갈지 정하는 자리이기 때문이다(R14-4). 상태 라벨과 위계를 다투지
              않도록 muted 로 둔다 — 색 토큰은 `globals.css` 의 4개만 쓴다. */}
          {completedToday && (
            <p style={{ color: "var(--foreground-muted)" }}>
              {dailyDoneNotice(daily?.completed_scenarios ?? 0)}
            </p>
          )}

          {showCorrections && (
            <div style={{ marginTop: "1rem" }}>
              {/* PS9 단정 2 — 발음 시도가 있으면 빈 상태 문구를 쓰지 않는다. 4차수 실측에서
                  정확 발음 세션과 오류 발음 세션의 결과 화면이 똑같았던 것이 이 요구사항의
                  출발점이다(`docs/storyboard.html`:140). */}
              {corrections.length === 0 && pronunciation.length === 0 && (
                <p>표시할 교정이 없습니다.</p>
              )}
              {corrections.map((correction) => (
                <div
                  key={correction.pattern_key}
                  style={{
                    border: "1px solid #ddd",
                    borderRadius: 8,
                    padding: "1rem",
                    margin: "0.75rem 0",
                  }}
                >
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>원문:</strong> {correction.original_span}
                  </p>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>교정문:</strong> {correction.correction}
                  </p>
                  {/* 한 줄 이유는 원문·교정문보다 덜 강조한다 — 위계는 테마 토큰이 만든다. */}
                  <p style={{ margin: "0.25rem 0", color: "var(--foreground-muted)" }}>
                    {correction.reason}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* 발음 카드 — 문법 교정 카드 **아래**에 붙는다(`docs/storyboard.html`:140).
              시도 1건 = 1카드이고 소리별로 묶지 않는다(설계서 §10 미결 4). key에 배열
              인덱스를 쓰는 것은 순서가 삽입 순으로 고정된 append-only 목록이기 때문이다 —
              폴링으로 뒤에 행이 붙어도 앞쪽 인덱스는 같은 시도를 계속 가리킨다. */}
          {pronunciation.length > 0 && (
            <div style={{ marginTop: "1.5rem" }}>
              <h2 style={{ fontSize: "1rem" }}>{PRONUNCIATION_HEADING}</h2>
              {pronunciation.map((attempt, index) =>
                attempt.signal_source === "nova_tool" ? (
                  <div key={index} style={PRONUNCIATION_CARD_STYLE}>
                    <p style={PRONUNCIATION_LABEL_STYLE}>{MODELED_LABEL}</p>
                    <p style={{ margin: "0.25rem 0" }}>{attempt.target_form}</p>
                    <p style={PRONUNCIATION_LABEL_STYLE}>{SPOKEN_LABEL}</p>
                    <p
                      style={{
                        margin: "0.25rem 0",
                        color:
                          attempt.spoken_form === null ? "var(--foreground-muted)" : undefined,
                      }}
                    >
                      {attempt.spoken_form ?? NO_ANSWER_NOTICE}
                    </p>
                    <p style={{ margin: "0.25rem 0", color: OUTCOME_COLOR[attempt.outcome] }}>
                      {outcomeLabel(attempt.outcome)}
                    </p>
                  </div>
                ) : (
                  // 신호 행은 시범이 아니라 우리 감지기의 관찰이다 — `target_form`이 문장이
                  // 아니라 설명 문구라서 "시범 문장" 라벨을 붙이면 그 문구를 따라 읽게 된다.
                  <div key={index} style={PRONUNCIATION_CARD_STYLE}>
                    <p style={PRONUNCIATION_LABEL_STYLE}>{SIGNAL_LABEL}</p>
                    <p style={{ margin: "0.25rem 0", color: "var(--foreground-muted)" }}>
                      {attempt.target_form}
                    </p>
                  </div>
                )
              )}
            </div>
          )}

          {/* 오늘 요약 — 방금 세션의 교정·발음 **아래**에 붙는다. 위계가 그 순서다: 학습자가
              먼저 보는 것은 방금 말한 것이고, 하루 전체는 그 뒤에 되짚는 것이다.
              key 에 `pattern_key`를 쓴다 — 하루 안에서 패턴 1종은 1행이므로 유일하다. */}
          {dailyPatterns.length > 0 && (
            <div style={{ marginTop: "1.5rem" }}>
              <h2 style={{ fontSize: "1rem" }}>{DAILY_HEADING}</h2>
              {dailyPatterns.map((item) => (
                <div key={item.pattern_key} style={DAILY_CARD_STYLE}>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>원문:</strong> {item.example.original_span}
                  </p>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>교정문:</strong> {item.example.correction}
                  </p>
                  <p style={{ margin: "0.25rem 0", color: "var(--foreground-muted)" }}>
                    {item.example.reason}
                  </p>
                  {item.occurrences > 1 && (
                    <p style={{ margin: "0.25rem 0", color: "var(--foreground-muted)" }}>
                      {dailyRepeatNotice(item.occurrences)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* 출구는 상태와 무관하게 **같은 자리에** 둔다 (TASK-55) — 화면마다 다른 자리에 두면
          학습자가 매번 다시 찾는다. `<p>`로 감싸도 상태 라벨보다 뒤에 오므로 C3 하네스가
          지목하는 「`main`의 첫 직계 `<p>`」는 그대로다(`tests/harness/c3_results_screen.py`). */}
      <p style={{ marginTop: "2rem" }}>
        {/* ⛔ **밑줄을 여기서 준다.** `globals.css`의 전역 `a`가 `text-decoration: none`이라
            링크가 본문 글자와 구별되지 않는다(수정 직후 화면을 열어 직접 봤다). 색 토큰은 4개뿐이고
            링크색 토큰이 없으므로 어포던스를 **밑줄**로 만든다. 전역 `a` 규칙은 고치지 않는다 —
            이 화면 밖의 링크까지 바꾸는 결정이라 이 태스크의 범위가 아니다. */}
        <Link href="/" style={{ textDecoration: "underline" }}>
          {HOME_LINK_LABEL}
        </Link>
      </p>
      <p style={{ marginTop: "0.5rem" }}>
        <Link href="/history" style={{ textDecoration: "underline" }}>
          {HISTORY_LINK_LABEL}
        </Link>
      </p>
    </main>
  );
}
