"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchWeeklyReport,
  type WeeklyReportPayload,
  type WeeklyTopPattern,
} from "@/lib/api";

/**
 * 주간 학습 리포트 화면 (`TASK-26.6` · 결정 91 · `PRD:117`).
 *
 * ⛔ **점수·등급·달성률을 그리지 않는다** — PRD §15.3 의 비범위이고 R13-5 의 톤 계약이다. 그래서
 * 이 화면에는 수가 둘뿐이다: 발생 수와 패턴 종 수(사실).
 * ⚠️ 문구는 이 화면이 소유한다 — API 는 수와 사실만 준다(히스토리 화면과 같은 규약).
 * ⚠️ 「아직 없음」과 「담을 것이 없었음」을 갈라 말한다: 전자는 `analyzed=false`, 후자는 배열이 빈
 *    것이다. 합쳐 말하면 학습자가 기능이 고장난 것으로 읽는다.
 */

const HEADING = "Weekly report";
const LOADING_NOTICE = "Loading the report...";
const FAILED_NOTICE = "I couldn't load the report.";
const NOT_YET_NOTICE = "No weekly report yet. Study for a week, and you will get one.";
const HISTORY_LINK_LABEL = "← History";
const TOP_ERRORS_HEADING = "Common mistakes this week";
const IMPROVING_HEADING = "Getting better";
const NEXT_HEADING = "Try next week";
const NOTHING_TO_SAY = "Nothing to show for this week.";

/** 주 범위 문구 — 시작 월요일과 그 주 일요일을 함께 보인다. */
function weekRange(weekStart: string): string {
  const start = new Date(`${weekStart}T00:00:00`);
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const format = (value: Date) => `${value.getMonth() + 1}/${value.getDate()}`;
  return `${format(start)} ~ ${format(end)}`;
}

const patternLine = (item: WeeklyTopPattern) =>
  `${item.target_form} — ${item.occurrences}× (${item.category})`;

const SECTION_STYLE = { marginTop: "1.5rem" } as const;
const MUTED = { color: "var(--foreground-muted)" } as const;

function Sentences({ heading, items }: { heading: string; items: string[] }) {
  return (
    <section style={SECTION_STYLE}>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.4rem" }}>{heading}</h2>
      {items.length === 0 ? (
        <p style={{ ...MUTED, margin: 0 }}>{NOTHING_TO_SAY}</p>
      ) : (
        <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
          {items.map((line) => (
            <li key={line} style={{ margin: "0.25rem 0" }}>
              {line}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function WeeklyReportPage() {
  const [report, setReport] = useState<WeeklyReportPayload | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const payload = await fetchWeeklyReport();
      if (!alive) return;
      // ⛔ `null` 은 통신·서버 오류다 — 「리포트가 없다」와 다른 사실이므로 다른 문구를 쓴다.
      if (payload === null) setFailed(true);
      else setReport(payload);
      setLoading(false);
    })();
    return () => {
      alive = false;
    };
  }, []);

  const metrics = report?.metrics ?? {};
  const insights = report?.insights ?? {};
  const topPatterns = metrics.top_patterns ?? [];

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem" }}>
      <h1>{HEADING}</h1>
      {loading && <p style={MUTED}>{LOADING_NOTICE}</p>}
      {failed && <p style={{ color: "var(--danger)" }}>{FAILED_NOTICE}</p>}
      {!loading && !failed && report !== null && !report.analyzed && (
        <p style={MUTED}>{NOT_YET_NOTICE}</p>
      )}
      {!loading && !failed && report !== null && report.analyzed && report.week_start !== null && (
        <>
          <p style={MUTED}>{weekRange(report.week_start)}</p>
          <p style={{ margin: "0.5rem 0 0" }}>
            Lessons {metrics.session_count ?? 0} · Mistakes {metrics.occurrence_count ?? 0} · Patterns{" "}
            {metrics.pattern_count ?? 0}
          </p>
          <section style={SECTION_STYLE}>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.4rem" }}>{TOP_ERRORS_HEADING}</h2>
            {topPatterns.length === 0 ? (
              <p style={{ ...MUTED, margin: 0 }}>{NOTHING_TO_SAY}</p>
            ) : (
              <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                {topPatterns.map((item) => (
                  <li key={item.pattern_key} style={{ margin: "0.25rem 0" }}>
                    {patternLine(item)}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <Sentences heading={IMPROVING_HEADING} items={insights.improving ?? []} />
          <Sentences heading={NEXT_HEADING} items={insights.next_scenarios ?? []} />
        </>
      )}
      <p style={{ marginTop: "2rem" }}>
        <Link href="/history">{HISTORY_LINK_LABEL}</Link>
      </p>
    </main>
  );
}
