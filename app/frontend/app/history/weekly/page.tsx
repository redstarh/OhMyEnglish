"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchWeeklyReport,
  type WeeklyReportPayload,
  type WeeklyTopPattern,
} from "@/lib/api";
import { weekName, weekRangeLabel, weekRelation, type WeekRelation } from "@/lib/learnerDate";

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
// `TASK-329` — 홈에서 들어와도 돌아가는 버튼이 「← History」뿐이었음(390 에서는 로고만 홈으로 감).
const HOME_LINK_LABEL = "← Home";
const IMPROVING_HEADING = "Getting better";

/**
 * 본문이 리포트의 주를 부르는 말 (`TASK-329`). 11-14 에 연 지난주 리포트가 「this week」라고 했음.
 * ⛔ 「this week」는 리포트의 주가 학습자의 이번 주일 때만 씀 — 기준은 서버가 준 `this_week_start` 임.
 */
const PERIOD_PHRASE: Record<WeekRelation, string> = {
  this: "this week",
  last: "last week",
  other: "that week",
};
// 다음에 해 볼 것 — 지난주 리포트의 「다음 주」는 학습자의 이번 주임.
const NEXT_HEADING: Record<WeekRelation, string> = {
  this: "Try next week",
  last: "Try this week",
  other: "Try next",
};
const topErrorsHeading = (relation: WeekRelation) => `Common mistakes ${PERIOD_PHRASE[relation]}`;
const nothingToSay = (relation: WeekRelation) => `Nothing to show for ${PERIOD_PHRASE[relation]}.`;
// 다음 제안의 빈 문구는 기간을 말하지 않음(`TASK-333` N6) — 「Try this week」 아래에 「… for last week.」가 나와
// 제목과 본문이 다른 주를 말했음(회차 b18 N6).
const NO_SUGGESTIONS = "No suggestions yet.";

const patternLine = (item: WeeklyTopPattern) =>
  `${item.target_form} — ${item.occurrences}× (${item.category})`;

const SECTION_STYLE = { marginTop: "1.5rem" } as const;
const MUTED = { color: "var(--foreground-muted)" } as const;

function Sentences({ heading, items, empty }: { heading: string; items: string[]; empty: string }) {
  return (
    <section style={SECTION_STYLE}>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.4rem" }}>{heading}</h2>
      {items.length === 0 ? (
        <p style={{ ...MUTED, margin: 0 }}>{empty}</p>
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
  const weekStart = report?.analyzed ? report.week_start : null;
  const relation = weekStart ? weekRelation(weekStart, report?.this_week_start) : "other";
  const periodName = weekName(relation);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem" }}>
      {/* `TASK-329` — 제목에 리포트의 기간을 넣음. 열린 날짜와 다른 주일 수 있음(대개 지난주). */}
      <h1 data-testid="weekly-heading">{weekStart ? `${HEADING} · ${weekRangeLabel(weekStart)}` : HEADING}</h1>
      {loading && <p style={MUTED}>{LOADING_NOTICE}</p>}
      {failed && <p style={{ color: "var(--danger)" }}>{FAILED_NOTICE}</p>}
      {!loading && !failed && report !== null && !report.analyzed && (
        <p style={MUTED}>{NOT_YET_NOTICE}</p>
      )}
      {!loading && !failed && report !== null && report.analyzed && report.week_start !== null && (
        <>
          {periodName && <p style={MUTED} data-testid="weekly-period">{periodName}</p>}
          <p style={{ margin: "0.5rem 0 0" }}>
            Lessons {metrics.session_count ?? 0} · Mistakes {metrics.occurrence_count ?? 0} · Patterns{" "}
            {metrics.pattern_count ?? 0}
          </p>
          <section style={SECTION_STYLE}>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.4rem" }}>{topErrorsHeading(relation)}</h2>
            {topPatterns.length === 0 ? (
              <p style={{ ...MUTED, margin: 0 }}>{nothingToSay(relation)}</p>
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
          <Sentences heading={IMPROVING_HEADING} items={insights.improving ?? []} empty={nothingToSay(relation)} />
          <Sentences
            heading={NEXT_HEADING[relation]}
            items={insights.next_scenarios ?? []}
            empty={NO_SUGGESTIONS}
          />
        </>
      )}
      <p style={{ marginTop: "2rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
        <Link href="/history" data-testid="weekly-history" className="omy-button">
          {HISTORY_LINK_LABEL}
        </Link>
        <Link href="/" data-testid="weekly-home" className="omy-button">
          {HOME_LINK_LABEL}
        </Link>
      </p>
    </main>
  );
}
