// 홈 대시보드의 데이터 조회와 계산 (`TASK-296` · 리디자인 설계서
// `docs/design/2026-11-01-v0-home-redesign-design.md` §5). 화면 모양은 `HomeDashboard.tsx` 가 가짐.
// ⛔ 여기의 모든 수치는 API 응답에서 나옴 — 가짜 값을 두지 않음(설계서 §1 결정 3).

import { useEffect, useState } from "react";

import type {
  CourseDaySummary,
  CourseOverview,
  DailySummaryPayload,
  HistoryPayload,
  WeeklyReportPayload,
} from "@/lib/api";
import type { AdditionalLearningItem, AdditionalLearningKey } from "@/app/additionalLearning";

/** 칸 하나의 조회 상태. 칸마다 따로 들고 따로 실패함 — 한 요청의 실패가 다른 칸을 비우지 않음. */
export type Load<T> = { status: "loading" } | { status: "ready"; data: T } | { status: "error" };

/**
 * 조회 함수 하나를 마운트 뒤에 한 번 부름. `null` 응답과 reject 는 둘 다 `error` 임.
 * ⚠️ `fetcher` 는 모듈 수준 함수여야 함 — 렌더마다 새 함수를 주면 effect 가 매번 다시 돎.
 * 첫 렌더는 늘 `loading` 이라 서버 렌더와 어긋나지 않음(설계서 §5).
 */
export function useLoad<T>(fetcher: () => Promise<T | null>): Load<T> {
  const [state, setState] = useState<Load<T>>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    fetcher().then(
      (data) => {
        if (!cancelled) setState(data === null ? { status: "error" } : { status: "ready", data });
      },
      () => {
        // 백엔드가 꺼져 있으면 `fetch` 가 reject 함 — 그 칸만 오류로 그림.
        if (!cancelled) setState({ status: "error" });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [fetcher]);
  return state;
}

/** 브라우저 날짜 `Sun, Nov 1`. 마운트 뒤에만 정함 — 서버와 브라우저의 시각이 달라 어긋나므로. */
export function useTodayLabel(): string | null {
  const [label, setLabel] = useState<string | null>(null);
  useEffect(() => {
    const id = window.setTimeout(() => {
      setLabel(
        new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }),
      );
    }, 0);
    return () => window.clearTimeout(id);
  }, []);
  return label;
}

/** `YYYY-MM-DD` → `Oct 19`. 날짜 문자열을 직접 나눔 — `new Date("2026-10-19")` 는 UTC 로 읽혀 하루 밀릴 수 있음. */
export function shortDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  if (!y || !m || !d) return isoDate;
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

// ── 문법 코스 ──

/** 이번 회차에 끝낸 Day 인가. 판정은 코스 화면(`app/course/page.tsx`)과 같음: `completed_count >= cycle`. */
export function isDayDone(day: CourseDaySummary, cycle: number): boolean {
  return (day.progress?.completed_count ?? 0) >= cycle;
}

export function courseDoneCount(course: CourseOverview): number {
  return course.days.filter((day) => isDayDone(day, course.cycle)).length;
}

/** 「Continue your path」 줄: 진행 중 Day 와 그다음 Day 하나. */
export function pathDays(course: CourseOverview): CourseDaySummary[] {
  const index = course.days.findIndex((day) => day.day === course.current_day);
  if (index < 0) return course.days.slice(0, 2);
  return course.days.slice(index, index + 2);
}

export type DayStatus = "done" | "started" | "new";

export function dayStatus(day: CourseDaySummary, cycle: number): DayStatus {
  if (isDayDone(day, cycle)) return "done";
  return day.progress ? "started" : "new";
}

// ── 히스토리 ──

/** 최근 7일 중 학습한 날 수. `days` 순서에 기대지 않고 날짜로 정렬해 가장 최근 7개를 셈. */
export function learnedInLastWeek(history: HistoryPayload): { learned: number; window: number } {
  const recent = [...history.days].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, 7);
  return { learned: recent.filter((day) => day.learned).length, window: recent.length };
}

// ── 초점 패턴 ──

export type FocusItem = { key: string; targetForm: string; occurrences: number };

export type FocusView =
  | { status: "loading" }
  | { status: "error" }
  | { status: "empty" }
  | { status: "ready"; scope: "today"; items: FocusItem[] }
  | { status: "ready"; scope: "week"; weekStart: string | null; items: FocusItem[] };

/**
 * 오늘 분석된 패턴이 있으면 그것, 아니면 주간 상위 패턴 셋(설계서 §5).
 * ⚠️ 하루 요약이 끝나기 전에는 주간 패턴을 먼저 그리지 않음 — 그리면 칸의 내용이 뒤바뀌어 보임.
 */
export function focusView(
  daily: Load<DailySummaryPayload>,
  weekly: Load<WeeklyReportPayload>,
): FocusView {
  if (daily.status === "loading") return { status: "loading" };
  if (daily.status === "ready" && daily.data.analyzed && daily.data.patterns.length > 0) {
    return {
      status: "ready",
      scope: "today",
      items: daily.data.patterns.slice(0, 3).map((p) => ({
        key: p.pattern_key,
        targetForm: p.target_form,
        occurrences: p.occurrences,
      })),
    };
  }
  if (weekly.status === "loading") return { status: "loading" };
  const top = weekly.status === "ready" ? (weekly.data.metrics.top_patterns ?? []) : [];
  if (weekly.status === "ready" && top.length > 0) {
    return {
      status: "ready",
      scope: "week",
      weekStart: weekly.data.week_start,
      items: top.slice(0, 3).map((p) => ({
        key: p.pattern_key,
        targetForm: p.target_form,
        occurrences: p.occurrences,
      })),
    };
  }
  if (daily.status === "error" && weekly.status === "error") return { status: "error" };
  return { status: "empty" };
}

// ── 추가 학습 문구 ──

// 영어 문구 대비표. ⚠️ `additionalLearning.ts` 의 `label` 이 이미 영어면 그 값을 씀 — 문구의 정본은
// 그 목록임. 이 표는 목록이 한국어로 남아 있을 때의 대비일 뿐임.
const LABELS_EN: Record<AdditionalLearningKey, string> = {
  free_talk: "Free talk",
  weak_patterns: "Weak spots",
  five_questions: "5 questions",
  pronunciation: "Pronunciation",
  shadowing: "Shadowing",
  videos: "Learn with videos",
  course: "Grammar course",
  roleplay: "Work role-play",
};

const HANGUL = /[ㄱ-ㆎ가-힣]/;

export function practiceLabel(item: AdditionalLearningItem): string {
  return HANGUL.test(item.label) ? LABELS_EN[item.key] : item.label;
}

export function practiceNote(item: AdditionalLearningItem): string | undefined {
  if (!item.note) return undefined;
  return HANGUL.test(item.note) ? "Not ready yet" : item.note;
}
