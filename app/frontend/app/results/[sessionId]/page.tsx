"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  fetchSessionResults,
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

const PARTIAL_FAILURE_NOTICE = "일부 발화는 분석하지 못했다 — 재시도되지 않습니다";

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
        if (!TERMINAL_STATUSES.has(data.status)) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setFetchError(err instanceof Error ? err.message : "결과를 불러오지 못했습니다");
        // 네트워크 오류는 terminal이 아니다 — 회복 가능하므로 계속 폴링한다.
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [sessionId]);

  const showCorrections = result?.status === "final" || result?.status === "partial_failure";
  // `corrections`는 상태에 따라 키가 없다(R2 규칙 1·2·3) — 여기서 한 번만 빈 배열로 정리한다.
  const corrections = result?.corrections ?? [];
  // 발음 카드는 R2 판정과 **독립**이라 `showCorrections`를 타지 않는다 — `analyzing`
  // 중에도 보인다(근거: `app/backend/app/services/results.py` 모듈 docstring 마지막 절).
  const pronunciation = result?.pronunciation ?? [];

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
        </>
      )}
    </main>
  );
}
