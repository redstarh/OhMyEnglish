"use client";

// 문법 코스 — 학습 목록 화면 (`TASK-286` · 설계서 `docs/design/2026-10-26-grammar-course-design.md` §7).
//
// ⛔ **화면은 둘뿐이다** — 이 목록과 `/course/[day]` 학습 화면(사용자 결정 1). Day 목록 · 날짜별
// 히트맵 · 최근 날짜 표를 한 화면에 둔다.
// ⚠️ 날짜는 서버가 학습자 시간대로 가른 값을 그대로 쓴다 — 화면이 다시 변환하지 않는다.

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCourse, type CourseDaySummary, type CourseOverview } from "@/lib/api";

const PAGE_STYLE = {
  maxWidth: 640,
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "sans-serif",
} as const;

const TITLE = "Grammar in Use BASIC";
const SUBTITLE = "영상 6편 · 단원 113개 · 한 문장씩 듣고 따라 말해요";
const BACK_LABEL = "← 학습 시작 화면으로";
const RESUME_LABEL = "이어서 학습 ▶";
const START_LABEL = "시작하기";
const HISTORY_HEADING = "학습 이력";
const HISTORY_NOTE = "날짜별 따라 한 횟수";
const LOAD_FAILED = "코스를 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요.";
const LOADING = "불러오는 중…";
const NO_RECENT = "아직 따라 한 문장이 없어요.";

/** 칸 색의 4단계 — 0회 · 1~9회 · 10~29회 · 30회 이상. */
function heatLevel(attempts: number): number {
  if (attempts <= 0) return 0;
  if (attempts < 10) return 1;
  if (attempts < 30) return 2;
  return 3;
}

const HEAT_COLORS = [
  "var(--surface)",
  "color-mix(in srgb, var(--accent) 30%, var(--surface))",
  "color-mix(in srgb, var(--accent) 60%, var(--surface))",
  "var(--accent)",
];

function minutes(seconds: number): string {
  return `${Math.round(seconds / 60)}분`;
}

function clock(seconds: number): string {
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function shortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${Number(month)}/${Number(day)}`;
}

function DayRow({
  item,
  cycle,
  current,
}: {
  item: CourseDaySummary;
  cycle: number;
  current: boolean;
}) {
  const progress = item.progress;
  const doneThisCycle = (progress?.completed_count ?? 0) >= cycle;
  const ratio = doneThisCycle
    ? 1
    : Math.min(1, (progress?.position_sec ?? 0) / Math.max(1, item.duration_sec));
  let status: string;
  // ⛔ 날짜는 서버가 학습자 시간대로 바꾼 `last_completed_date` 다 — UTC 시각을 잘라 쓰면 KST 00~09시
  // 완료가 전날로 보였다(회차 2026-10-26-b1 D1).
  if (doneThisCycle && progress?.last_completed_date) {
    status = `완료 · ${shortDate(progress.last_completed_date)}`;
  } else if (
    progress &&
    (progress.position_sec > 0 || progress.sentence_index > 0 || progress.unit !== item.first_unit)
  ) {
    status = `Unit ${progress.unit} · 문장 ${progress.sentence_index + 1} · ${clock(progress.position_sec)}`;
  } else {
    status = "아직 안 함";
  }
  return (
    <div
      data-testid={`course-day-${item.day}`}
      style={{
        border: `1px solid ${current ? "var(--accent)" : "var(--border)"}`,
        borderRadius: 12,
        padding: "10px 12px",
        marginTop: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontWeight: current ? 700 : 400 }}>
          Day {item.day} · Unit {item.first_unit}–{item.last_unit} · {minutes(item.duration_sec)}
        </span>
        <span style={{ color: "var(--foreground-muted)", fontSize: "0.85rem" }}>{status}</span>
      </div>
      <div
        style={{
          height: 6,
          borderRadius: 99,
          background: "var(--surface)",
          marginTop: 6,
          overflow: "hidden",
        }}
      >
        <div style={{ width: `${ratio * 100}%`, height: "100%", background: "var(--accent)" }} />
      </div>
      <div style={{ marginTop: 8 }}>
        <Link
          href={`/course/${item.day}`}
          style={{
            display: "inline-block",
            padding: "6px 12px",
            borderRadius: 8,
            fontSize: "0.85rem",
            background: current ? "var(--accent)" : "var(--surface)",
            color: current ? "var(--on-accent)" : "var(--foreground)",
            border: "1px solid var(--border)",
          }}
        >
          {current ? RESUME_LABEL : START_LABEL}
        </Link>
      </div>
    </div>
  );
}

function Heatmap({ cells }: { cells: CourseOverview["heatmap"] }) {
  // 칸을 주(열) × 요일(행)로 놓는다. 첫 칸 앞을 비워 요일을 맞춘다 — 0 = 일요일.
  const lead = cells.length > 0 ? new Date(`${cells[0].date}T00:00:00`).getDay() : 0;
  return (
    <div>
      <div
        data-testid="course-heatmap"
        style={{
          display: "grid",
          gridTemplateRows: "repeat(7, 12px)",
          gridAutoFlow: "column",
          gridAutoColumns: "12px",
          gap: 3,
          marginTop: 8,
        }}
      >
        {Array.from({ length: lead }, (_, index) => (
          <i key={`lead-${index}`} />
        ))}
        {cells.map((cell) => (
          <i
            key={cell.date}
            title={`${cell.date} · ${cell.attempts}회`}
            data-attempts={cell.attempts}
            style={{ borderRadius: 3, background: HEAT_COLORS[heatLevel(cell.attempts)] }}
          />
        ))}
      </div>
      <div
        style={{
          display: "flex",
          gap: 3,
          alignItems: "center",
          fontSize: "0.7rem",
          color: "var(--foreground-muted)",
          marginTop: 6,
        }}
      >
        적음
        {HEAT_COLORS.map((color) => (
          <i
            key={color}
            style={{ width: 10, height: 10, borderRadius: 2, display: "inline-block", background: color }}
          />
        ))}
        많음
      </div>
    </div>
  );
}

export default function CourseListPage() {
  const [overview, setOverview] = useState<CourseOverview | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCourse()
      .then((value) => {
        if (cancelled) return;
        if (value) setOverview(value);
        else setFailed(true);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={PAGE_STYLE}>
      <Link href="/" style={{ color: "var(--foreground-muted)", fontSize: "0.85rem" }}>
        {BACK_LABEL}
      </Link>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
        <h1 style={{ fontSize: "1.3rem" }}>{TITLE}</h1>
        {overview ? (
          <span style={{ color: "var(--foreground-muted)" }}>{overview.cycle}회차</span>
        ) : null}
      </div>
      <p style={{ color: "var(--foreground-muted)", fontSize: "0.85rem" }}>{SUBTITLE}</p>

      {failed ? <p style={{ marginTop: 16 }}>{LOAD_FAILED}</p> : null}
      {!overview && !failed ? <p style={{ marginTop: 16 }}>{LOADING}</p> : null}

      {overview ? (
        <>
          <section>
            {overview.days.map((item) => (
              <DayRow
                key={item.day}
                item={item}
                cycle={overview.cycle}
                current={item.day === overview.current_day}
              />
            ))}
          </section>

          <section style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: "1rem" }}>
              {HISTORY_HEADING}{" "}
              <span style={{ color: "var(--foreground-muted)", fontWeight: 400, fontSize: "0.8rem" }}>
                · {HISTORY_NOTE}
              </span>
            </h2>
            <Heatmap cells={overview.heatmap} />
            {overview.recent.length === 0 ? (
              <p style={{ color: "var(--foreground-muted)", marginTop: 10, fontSize: "0.85rem" }}>
                {NO_RECENT}
              </p>
            ) : (
              <table
                data-testid="course-recent"
                style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", marginTop: 10 }}
              >
                <thead>
                  <tr style={{ color: "var(--foreground-muted)", textAlign: "left" }}>
                    <th>날짜</th>
                    <th>Day</th>
                    <th>단원</th>
                    <th>따라 한 문장</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.recent.map((row) => (
                    <tr key={row.date} style={{ borderTop: "1px solid var(--border)" }}>
                      <td>{shortDate(row.date)}</td>
                      <td>{row.days.join(", ")}</td>
                      <td>
                        {row.first_unit === row.last_unit
                          ? row.first_unit
                          : `${row.first_unit}–${row.last_unit}`}
                      </td>
                      <td>
                        {row.sentences}문장 · {row.attempts}회
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
