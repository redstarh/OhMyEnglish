"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { fetchSessionResults, type SessionResultPayload, type SessionResultStatus } from "@/lib/api";

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

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>학습 결과</h1>

      {!sessionId && <p style={{ color: "#c00" }}>세션 id가 없습니다.</p>}

      {sessionId && !result && (
        <p style={{ color: fetchError ? "#c00" : undefined }}>{fetchError ?? "결과를 불러오는 중입니다..."}</p>
      )}

      {result && (
        <>
          <p style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{STATUS_LABEL[result.status]}</p>

          {result.status === "partial_failure" && <p>{PARTIAL_FAILURE_NOTICE}</p>}

          {showCorrections && (
            <div style={{ marginTop: "1rem" }}>
              {(result.corrections ?? []).length === 0 && <p>표시할 교정이 없습니다.</p>}
              {(result.corrections ?? []).map((correction) => (
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
                  <p style={{ margin: "0.25rem 0", color: "#555" }}>{correction.reason}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
