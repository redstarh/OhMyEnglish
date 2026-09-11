"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHistory, type HistoryDay, type HistoryPayload } from "@/lib/api";

// 문구는 이 화면이 소유한다 — API 는 수와 사실만 준다(`results` 화면과 같은 규약).
const HEADING = "학습 히스토리";
const LOADING_NOTICE = "히스토리를 불러오는 중입니다...";
const FAILED_NOTICE = "히스토리를 불러오지 못했습니다.";
const HOME_LINK_LABEL = "← 학습 시작 화면으로";

// ⛔ 자정 직후의 `current` 는 «어제까지»의 값이다(PRD §15 R15-3) — 두 문구를 갈라 쓰지 않으면
// 학습자가 오늘 이미 한 것으로 읽는다. 설계서 §6 이 이 구분을 요구한다.
function streakNotice(current: number, todayDone: boolean): string {
  if (current === 0) return "지금 이어지는 연속 학습일은 없어요";
  return todayDone ? `${current}일 연속 학습 중이에요` : `어제까지 ${current}일 연속이에요`;
}

// 최장은 0일 때 쓰지 않는다 — 「최장 0일」은 아무것도 말하지 않는다.
const longestNotice = (longest: number) => `최장 연속 ${longest}일`;

/**
 * 한 줄의 오른쪽 사실. 셋을 갈라 말한다:
 * 학습이 없던 날 · 학습했고 요약이 있는 날 · **학습했는데 요약이 없는 날**(012 이전).
 * ⛔ 마지막을 「오류 0건」으로 쓰지 않는다 — 그것은 「분석했고 오류가 없었다」라는 다른 사실이다.
 */
function dayFact(row: HistoryDay): string {
  if (!row.learned) return "";
  if (!row.analyzed) return "분석 기록 없음";
  if (row.occurrence_count === 0) return "오류 없음";
  return `오류 ${row.occurrence_count}건 · 패턴 ${row.pattern_count}종`;
}

const ROW_STYLE = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  padding: "0.35rem 0",
} as const;

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
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif" }}>
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
            {history.days.map((row) => (
              <div key={row.day} style={ROW_STYLE}>
                <span style={{ color: row.learned ? undefined : "var(--foreground-muted)" }}>
                  {row.day} {row.learned ? "· 학습함" : ""}
                </span>
                <span style={{ color: "var(--foreground-muted)" }}>{dayFact(row)}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <p style={{ marginTop: "2rem" }}>
        {/* 밑줄은 여기서 준다 — `globals.css` 의 전역 `a` 가 `text-decoration: none` 이다
            (결과 화면과 같은 이유). */}
        <Link href="/" style={{ textDecoration: "underline" }}>
          {HOME_LINK_LABEL}
        </Link>
      </p>
    </main>
  );
}
