"use client";

import { useEffect, useState } from "react";
import { fetchWeeklyReport, type WeeklyReportPayload } from "@/lib/api";

/**
 * 세션 중에 음성 명령으로 열리는 주간 리포트 요약 (`TASK-61.6` · 결정 107).
 *
 * ⛔ **화면을 옮기지 않고 이 패널로 보여 주는 것이 계약이다.** 리포트 화면 셋은 모두 별 페이지라
 * 이동하면 `page.tsx` 의 언마운트 정리가 소켓을 닫아 **세션이 끝난다**(결정 107 ②). 그러면
 * 「되돌릴 수 있는 명령」이라는 전제가 무너지고 확인 절차(결정 102 ③)가 필요해진다.
 *
 * ⚠️ **전용 화면(`/history/weekly`)과 같은 `/api/weekly-report` 를 읽고 같은 필드를 보인다** —
 * 지표 한 줄의 문면을 그 화면과 같게 맞췄다. 문구 상수를 공유하지 않는 것은 그 페이지를 이
 * 태스크에서 고치지 않기 위한 것이고, 값을 다시 세는 자리는 없다.
 *
 * ⛔ **판단 문장(`insights`)은 담지 않는다** — 학습 중에 읽을 분량이 아니고, 그것을 보는 자리는
 * 전용 화면이다. 이 패널은 「지금 어디까지 왔나」를 한 줄로 답하는 것까지다.
 */

const TITLE = "주간 리포트";
const LOADING_NOTICE = "불러오는 중…";
const FAILED_NOTICE = "리포트를 불러오지 못했어요";
const NOT_READY_NOTICE = "아직 주간 리포트가 만들어지지 않았어요";
const CLOSE_LABEL = "닫기";
const TOP_PATTERN_HEADING = "자주 나온 오류";

/** 학습 중에 읽을 분량으로 끊는다 — 전용 화면은 전부 보인다. */
const TOP_PATTERN_LIMIT = 3;

type LoadState = "loading" | "failed" | "loaded";

export function WeeklyReportPanel({ onClose }: { onClose: () => void }) {
  const [state, setState] = useState<LoadState>("loading");
  const [report, setReport] = useState<WeeklyReportPayload | null>(null);

  // **마운트당 한 번** 읽는다. 폴링하지 않는다 — 주간 리포트는 세션 종료가 거는 job 이 만들므로
  // 이 세션이 도는 동안 바뀌지 않는다.
  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      const payload = await fetchWeeklyReport().catch(() => null);
      if (cancelled) return;
      // ⛔ `null` 은 통신·서버 오류뿐이다 — 리포트가 없을 때도 서버는 200 을 준다(`lib/api.ts`).
      // 그래서 「없음」과 「못 읽음」을 갈라 말한다.
      setReport(payload);
      setState(payload === null ? "failed" : "loaded");
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const metrics = report?.metrics ?? {};
  const topPatterns = (metrics.top_patterns ?? []).slice(0, TOP_PATTERN_LIMIT);
  const ready = report !== null && report.analyzed && report.week_start !== null;

  return (
    <section
      style={{
        marginTop: "1rem",
        padding: "0.75rem 1rem",
        border: "1px solid var(--foreground-muted)",
        borderRadius: "0.5rem",
      }}
    >
      <h2 style={{ fontSize: "1rem", marginTop: 0, marginBottom: "0.5rem" }}>{TITLE}</h2>
      {state === "loading" && (
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{LOADING_NOTICE}</p>
      )}
      {state === "failed" && (
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{FAILED_NOTICE}</p>
      )}
      {state === "loaded" && !ready && (
        <p style={{ color: "var(--foreground-muted)", margin: 0 }}>{NOT_READY_NOTICE}</p>
      )}
      {state === "loaded" && ready && (
        <>
          <p style={{ margin: 0 }}>
            학습 {metrics.session_count ?? 0}회 · 오류 {metrics.occurrence_count ?? 0}건 · 패턴{" "}
            {metrics.pattern_count ?? 0}종
          </p>
          {topPatterns.length > 0 && (
            <>
              <h3 style={{ fontSize: "0.9rem", marginBottom: "0.25rem" }}>{TOP_PATTERN_HEADING}</h3>
              <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                {topPatterns.map((pattern) => (
                  <li key={pattern.pattern_key}>
                    {pattern.target_form} · {pattern.occurrences}회
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      <button
        type="button"
        onClick={onClose}
        style={{ marginTop: "0.75rem", padding: "0.4rem 0.9rem" }}
      >
        {CLOSE_LABEL}
      </button>
    </section>
  );
}
