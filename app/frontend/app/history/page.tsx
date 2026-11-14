"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHistory, type HistoryDay, type HistoryPayload } from "@/lib/api";
import { dayFact, groupHistoryRows, saidNothing } from "@/lib/historyRows";
import { gapLabel } from "@/lib/learnerDate";

// 문구는 이 화면이 소유한다 — API 는 수와 사실만 준다(`results` 화면과 같은 규약).
const HEADING = "History";
const LOADING_NOTICE = "Loading your history...";
const FAILED_NOTICE = "I couldn't load your history.";
const HOME_LINK_LABEL = "← Home";
const WEEKLY_LINK_LABEL = "Weekly report →";

// ⛔ 자정 직후의 `current` 는 «어제까지»의 값이다(PRD §15 R15-3) — 두 문구를 갈라 쓰지 않으면
// 학습자가 오늘 이미 한 것으로 읽는다. 설계서 §6 이 이 구분을 요구한다.
function streakNotice(current: number, todayDone: boolean): string {
  if (current === 0) return "No streak right now.";
  return todayDone ? `${current}-day streak!` : `${current}-day streak until yesterday`;
}

// 최장은 0일 때 쓰지 않는다 — 「최장 0일」은 아무것도 말하지 않는다.
const longestNotice = (longest: number) => `Best streak: ${longest} ${longest === 1 ? "day" : "days"}`;

// 날짜 줄 오른쪽 사실(`dayFact`)과 그 문구의 근거는 `lib/historyRows.ts` 가 가짐(`TASK-333` 에서 옮김).
const NOT_ANALYZED_HINT =
  "What you say in a lesson is checked for mistakes after each of your turns. “Not analyzed yet” means nothing you said that day has been checked.";

const ROW_STYLE = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  padding: "0.35rem 0",
} as const;

/**
 * 날짜 한 줄 (`TASK-329`). 공부한 날은 그날의 결과로 감 — 세션이 하나면 그 결과로 바로 가고, 여럿이면
 * 줄을 펼쳐 고름. 이전에는 줄이 눌리지 않아 결과 화면이 세션 직후에만 닿았음.
 * ⚠️ 이 줄은 목록 항목이라 이동 버튼 모양(`omy-button`)을 쓰지 않음(설계서 §3 `TASK-311` 의 범위 밖).
 */
function DayRow({ row }: { row: HistoryDay }) {
  const sessions = row.sessions ?? [];
  const label = `${row.day}${row.learned ? " · Studied" : ""}`;
  const fact = <span style={{ color: "var(--foreground-muted)" }}>{dayFact(row)}</span>;

  if (sessions.length === 1) {
    return (
      <div style={ROW_STYLE}>
        <Link href={`/results/${sessions[0].session_id}`} data-testid="history-day-link">
          {label} →
        </Link>
        {fact}
      </div>
    );
  }
  if (sessions.length > 1) {
    return (
      <details data-testid="history-day-group">
        <summary style={{ ...ROW_STYLE, cursor: "pointer" }}>
          {/* flex 로 두면 브라우저의 펼침 표시가 사라짐 — 눌러 펼친다는 단서를 글자로 둠. */}
          <span>
            {label} · {sessions.length} lessons ▾
          </span>
          {fact}
        </summary>
        <ul style={{ margin: "0 0 0.5rem", paddingLeft: "1.2rem" }}>
          {sessions.map((item) => (
            <li key={item.session_id} style={{ margin: "0.25rem 0" }}>
              <Link href={`/results/${item.session_id}`} data-testid="history-session-link">
                {item.title} →
              </Link>
            </li>
          ))}
        </ul>
      </details>
    );
  }
  return (
    <div style={ROW_STYLE}>
      <span style={{ color: row.learned ? undefined : "var(--foreground-muted)" }}>{label}</span>
      {fact}
    </div>
  );
}

/** 공부하지 않은 날이 이어진 구간 한 줄 (`TASK-333` N8). 눌리지 않음 — 갈 결과가 없음. */
function GapRow({ from, to }: { from: string; to: string }) {
  return (
    <div style={ROW_STYLE} data-testid="history-gap">
      <span style={{ color: "var(--foreground-muted)" }}>{gapLabel(from, to)}</span>
    </div>
  );
}

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryPayload | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchHistory()
      .then((data) => {
        if (cancelled) return;
        if (data === null) setFailed(true);
        else setHistory(data);
      })
      .catch(() => {
        // 네트워크 자체가 끊기면 `fetch` 가 reject 한다 — 빈 화면 대신 실패를 말한다.
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem" }}>
      <h1>{HEADING}</h1>

      {!history && !failed && <p>{LOADING_NOTICE}</p>}
      {failed && <p style={{ color: "var(--danger)" }}>{FAILED_NOTICE}</p>}

      {history && (
        <>
          <p style={{ fontSize: "1.1rem" }}>
            {streakNotice(history.streak.current, history.streak.today_done)}
          </p>
          {history.streak.longest > 0 && (
            <p style={{ color: "var(--foreground-muted)" }}>
              {longestNotice(history.streak.longest)}
            </p>
          )}

          {/* 날짜별 줄 — 학습이 없던 날도 그린다. 그 날이 보이지 않으면 연속이 어디서 끊겼는지
              알 수 없고, 그러면 위의 연속일 수가 근거 없는 숫자가 된다(R15-5). */}
          <div style={{ marginTop: "1.5rem" }}>
            {/* 빈 날은 이어진 만큼 한 줄로 접음(`TASK-333` N8) — 끊긴 자리는 그대로 보임. */}
            {groupHistoryRows(history.days).map((item) =>
              item.kind === "day" ? (
                <DayRow key={item.row.day} row={item.row} />
              ) : (
                <GapRow key={`gap-${item.to}`} from={item.from} to={item.to} />
              ),
            )}
          </div>
          {/* 설명 줄은 「Not analyzed yet」이 보이는 날이 있을 때만 — 「Nothing said」인 날은 뜻이 분명함(`TASK-333` N5). */}
          {history.days.some((row) => row.learned && !row.analyzed && !saidNothing(row)) && (
            <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--foreground-muted)" }} data-testid="history-not-analyzed-hint">
              {NOT_ANALYZED_HINT}
            </p>
          )}
        </>
      )}

      {/* ⛔ 주간 리포트로 가는 길 (`TASK-26.6`). 화면이 있어도 닿는 길이 없으면 소비자가 0곳인
          것과 같다 — 이 리포가 네 번 낸 실패가 그 형태다(`data-first` §3). */}
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/history/weekly" data-testid="history-weekly" className="omy-button omy-button-primary">
          {WEEKLY_LINK_LABEL}
        </Link>
      </p>

      <p style={{ marginTop: "0.5rem" }}>
        {/* 이동은 홈과 같은 버튼 모양임(`TASK-311` 사용자 지시). */}
        <Link href="/" data-testid="history-home" className="omy-button">
          {HOME_LINK_LABEL}
        </Link>
      </p>
    </main>
  );
}
