"use client";

// 홈 대시보드 (`TASK-296` · 리디자인 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §5).
// 배치는 v0 원본(`docs/design/2026-11-01-v0-home-redesign/oh-my-english-dashboard.tsx.txt`)의 본문을
// 따르고, 사이드바는 공통 틀(`components/app-shell.tsx`)이 가짐.
// ⛔ 세션 논리는 여기 두지 않음 — 이 칸은 `onStart` 하나만 받음(`app/page.tsx` 가 세션을 소유).
// ⛔ 「Start speaking」은 어떤 조회의 상태와도 무관하게 늘 눌림.

import Link from "next/link";
import type { ReactNode } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Flame,
  Headphones,
  Mic,
  Play,
  Plus,
  Sparkles,
  TrendingUp,
  Volume2,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  fetchCourse,
  fetchDailySummary,
  fetchHistory,
  fetchNextPlan,
  fetchWeeklyReport,
  type CourseOverview,
  type DailySummaryPayload,
  type HistoryPayload,
  type NextPlanSummary,
  type WeeklyReportPayload,
} from "@/lib/api";
import type { SessionEntry } from "@/lib/config";
import { cn } from "@/lib/utils";
import {
  ADDITIONAL_LEARNING,
  isAdditionalLearningEnabled,
  type AdditionalLearningKey,
} from "@/app/additionalLearning";
import {
  courseDoneCount,
  dayStatus,
  focusView,
  learnedInLastWeek,
  pathDays,
  plural,
  practiceLabel,
  practiceNote,
  shortDate,
  useLoad,
  useTodayLabel,
  type Load,
} from "./dashboardData";

/** 옛 「학습 시작」 버튼과 같은 진입 — `source` 를 명시함(진입점 설계서 §4). */
const RECOMMENDED_ENTRY: SessionEntry = { source: "recommended" };

function entryOf(key: AdditionalLearningKey): SessionEntry | null {
  return ADDITIONAL_LEARNING.find((item) => item.key === key)?.entry ?? null;
}

const CARD = "rounded-[24px] border border-border bg-card p-6 shadow-sm";

function Muted({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <p data-testid={testId} className="text-xs text-muted-foreground">
      {children}
    </p>
  );
}

export function HomeDashboard({ onStart }: { onStart: (entry: SessionEntry) => void }) {
  const plan = useLoad(fetchNextPlan);
  const history = useLoad(fetchHistory);
  const weekly = useLoad(fetchWeeklyReport);
  const course = useLoad(fetchCourse);
  const daily = useLoad(fetchDailySummary);

  return (
    <div className="text-foreground">
      <Header history={history} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.85fr)]">
        <HeroCard plan={plan} onStart={() => onStart(RECOMMENDED_ENTRY)} />
        <ProgressCard course={course} history={history} weekly={weekly} />
      </div>

      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
        <PathSection course={course} />
        <FocusSection daily={daily} weekly={weekly} onStart={onStart} />
      </div>

      <QuickCards onStart={onStart} />
      <MorePractice onStart={onStart} />
    </div>
  );
}

// ── 머리 ──

function Header({ history }: { history: Load<HistoryPayload> }) {
  const today = useTodayLabel();
  return (
    <header className="mb-8 flex flex-wrap items-center justify-between gap-3">
      <div>
        <p data-testid="home-date" className="min-h-4 text-xs font-semibold uppercase text-muted-foreground">
          {today ?? ""}
        </p>
        <h1 className="mt-1 text-2xl font-extrabold tracking-[-0.04em] text-foreground sm:text-[30px]">
          Welcome back<span className="text-brand">.</span>
        </h1>
      </div>
      <div
        data-testid="home-streak"
        data-state={history.status}
        className="flex items-center gap-2 rounded-full bg-card px-3 py-2 text-xs font-bold text-muted-foreground shadow-sm"
      >
        <Flame className="size-4 text-[#ff785d]" aria-hidden="true" />
        {history.status === "loading" && "Loading…"}
        {history.status === "error" && "Can't load your streak."}
        {history.status === "ready" &&
          (history.data.streak.current > 0
            ? `${plural(history.data.streak.current, "day", "days")} in a row`
            : "Start a streak today")}
      </div>
    </header>
  );
}

// ── 오늘의 연습 ──

function HeroCard({ plan, onStart }: { plan: Load<NextPlanSummary>; onStart: () => void }) {
  // ⚠️ `reason` 은 백엔드가 한국어로 줌 — 그대로 보임(설계서 §6 미결 1 · `TASK-299`).
  const reason = plan.status === "ready" ? plan.data.reason : null;
  const level = plan.status === "ready" ? plan.data.target_level : null;
  return (
    <div
      data-testid="home-hero"
      data-state={plan.status}
      className="rounded-[24px] bg-hero p-6 text-white shadow-xl shadow-hero/10 sm:p-8"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-white/80">
            <Sparkles className="size-3" aria-hidden="true" /> Today&apos;s practice
          </span>
          {plan.status === "loading" ? (
            <div className="mt-5 h-[84px] max-w-[420px] animate-pulse rounded-xl bg-white/10" aria-label="Loading" />
          ) : (
            <h2
              data-testid="home-hero-reason"
              className={cn(
                "mt-5 max-w-[480px] break-keep font-extrabold leading-[1.2] tracking-[-0.03em] text-white",
                reason ? "text-xl sm:text-2xl" : "text-3xl sm:text-[42px] sm:leading-[1.06]",
              )}
            >
              {reason ?? "Let's talk in English."}
            </h2>
          )}
          <p className="mt-4 max-w-[390px] text-sm leading-6 text-white/75">
            Talk with your coach. Try to say more each time.
          </p>
        </div>
        <div className="hidden size-16 shrink-0 rounded-2xl bg-white/10 sm:grid sm:place-items-center">
          <Mic className="size-7 text-white/80" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <Button
          data-testid="start-session"
          onClick={onStart}
          size="lg"
          className="rounded-xl bg-white px-5 font-bold text-hero hover:bg-brand-soft"
        >
          <Play data-icon="inline-start" aria-hidden="true" /> Start speaking
        </Button>
        <span data-testid="home-level" className="text-xs font-semibold text-white/75">
          {level ? `Speaking · Level ${level}` : "Speaking"}
        </span>
      </div>
    </div>
  );
}

// ── 진도 ──

function ProgressCard({
  course,
  history,
  weekly,
}: {
  course: Load<CourseOverview>;
  history: Load<HistoryPayload>;
  weekly: Load<WeeklyReportPayload>;
}) {
  const done = course.status === "ready" ? courseDoneCount(course.data) : 0;
  const total = course.status === "ready" ? course.data.days.length : 0;
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  const week = history.status === "ready" ? learnedInLastWeek(history.data) : null;

  return (
    <div className={CARD} data-testid="home-progress">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">Your progress</p>
          <div data-testid="home-course-progress" data-state={course.status} className="mt-2">
            {course.status === "loading" && <Muted>Loading…</Muted>}
            {course.status === "error" && <Muted>Can&apos;t load the course.</Muted>}
            {course.status === "ready" && (
              <p className="text-3xl font-extrabold tracking-[-0.05em]">
                {done}
                <span className="text-lg text-muted-foreground"> / {total} days</span>
              </p>
            )}
          </div>
        </div>
        <div className="grid size-12 place-items-center rounded-2xl bg-brand-soft text-brand">
          <TrendingUp className="size-5" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-brand-bright" style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-2 text-[11px] font-semibold text-muted-foreground">
        <span>Grammar course</span>
        <span data-testid="home-week-days" data-state={history.status}>
          {history.status === "loading" && "Loading…"}
          {history.status === "error" && "Can't load this week."}
          {week && `This week: ${week.learned} / ${week.window} days`}
        </span>
      </div>
      <WeeklyStats weekly={weekly} history={history} />
    </div>
  );
}

function Stat({ value, label, testId }: { value: string; label: string; testId: string }) {
  return (
    <div data-testid={testId}>
      <p className="text-lg font-extrabold">{value}</p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  );
}

function WeeklyStats({ weekly, history }: { weekly: Load<WeeklyReportPayload>; history: Load<HistoryPayload> }) {
  const report = weekly.status === "ready" && weekly.data.analyzed ? weekly.data : null;
  const dash = weekly.status === "loading" ? "…" : "–";
  const longest =
    history.status === "ready" ? String(history.data.streak.longest) : history.status === "loading" ? "…" : "–";
  return (
    <div className="mt-6 border-t border-border pt-5" data-testid="home-weekly-stats" data-state={weekly.status}>
      <div className="grid grid-cols-3 gap-2 text-center">
        <Stat testId="stat-sessions" label="Sessions" value={report ? String(report.metrics.session_count ?? 0) : dash} />
        <Stat testId="stat-best-streak" label="Best streak" value={longest} />
        <Stat testId="stat-patterns" label="Patterns" value={report ? String(report.metrics.pattern_count ?? 0) : dash} />
      </div>
      <p className="mt-3 text-center text-[11px] text-muted-foreground">
        {weekly.status === "error" && "Can't load your weekly report."}
        {weekly.status === "ready" &&
          (report
            ? report.week_start
              ? `Weekly report · week of ${shortDate(report.week_start)}`
              : "Weekly report"
            : "No weekly report yet.")}
      </p>
    </div>
  );
}

// ── 이어 가기 ──

function SectionHead({ title, sub, action }: { title: string; sub: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div>
        <h2 className="text-lg font-extrabold tracking-tight text-foreground">{title}</h2>
        <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
      </div>
      {action}
    </div>
  );
}

const STATUS_TEXT = { done: "Done", started: "In progress", new: "Up next" } as const;

function PathSection({ course }: { course: Load<CourseOverview> }) {
  return (
    <section data-testid="home-path" data-state={course.status}>
      <SectionHead
        title="Continue your path"
        sub="Small steps, real conversations."
        action={
          <Link
            href="/course"
            data-testid="home-path-all"
            className={cn(buttonVariants({ variant: "ghost" }), "text-xs font-bold text-brand")}
          >
            View all <ChevronRight data-icon="inline-end" aria-hidden="true" />
          </Link>
        }
      />
      <div className="flex flex-col gap-3">
        {course.status === "loading" && <div className={cn(CARD, "h-[76px] animate-pulse p-4")} />}
        {course.status === "error" && (
          <div className={cn(CARD, "p-4")}>
            <Muted>Can&apos;t load the course.</Muted>
          </div>
        )}
        {course.status === "ready" &&
          pathDays(course.data).map((day) => {
            const status = dayStatus(day, course.data.cycle);
            return (
              <Link
                key={day.day}
                href={`/course/${day.day}`}
                data-testid={`path-day-${day.day}`}
                data-status={status}
                className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 shadow-sm transition-colors hover:bg-accent"
              >
                <div
                  className={cn(
                    "grid size-11 shrink-0 place-items-center rounded-xl text-[10px] font-extrabold",
                    status === "done" ? "bg-tint-mint text-[#2e7d57]" : "bg-muted text-muted-foreground",
                  )}
                >
                  {status === "done" ? <Check className="size-4" aria-hidden="true" /> : `DAY ${day.day}`}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold">
                    Day {day.day} · {STATUS_TEXT[status]}
                  </p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    Units {day.first_unit}–{day.last_unit}
                  </p>
                </div>
                <span className="hidden text-[11px] font-semibold text-muted-foreground sm:block">
                  {Math.round(day.duration_sec / 60)} min
                </span>
                <span className="grid size-7 place-items-center rounded-xl border border-border">
                  <ArrowRight className="size-4" aria-hidden="true" />
                </span>
              </Link>
            );
          })}
      </div>
    </section>
  );
}

// ── 초점 패턴 ──

function FocusSection({
  daily,
  weekly,
  onStart,
}: {
  daily: Load<DailySummaryPayload>;
  weekly: Load<WeeklyReportPayload>;
  onStart: (entry: SessionEntry) => void;
}) {
  const view = focusView(daily, weekly);
  const weakEntry = entryOf("weak_patterns");
  const when =
    view.status !== "ready"
      ? ""
      : view.scope === "today"
        ? "today"
        : view.weekStart
          ? `· week of ${shortDate(view.weekStart)}`
          : "this week";
  return (
    <section data-testid="home-focus" data-state={view.status}>
      <SectionHead title="Focus patterns" sub="Your coach is watching these." />
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        {view.status === "loading" && <Muted>Loading…</Muted>}
        {view.status === "error" && <Muted>Can&apos;t load your patterns.</Muted>}
        {view.status === "empty" && <Muted>No patterns yet. Start speaking to find them.</Muted>}
        {view.status === "ready" &&
          view.items.map((item) => (
            <div
              key={item.key}
              data-testid="focus-pattern"
              className="border-b border-border py-3 first:pt-1 last:border-0 last:pb-1"
            >
              <p className="text-xs font-bold">{item.targetForm}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {plural(item.occurrences, "time", "times")} {when}
              </p>
            </div>
          ))}
        <Button
          data-testid="focus-practice"
          variant="ghost"
          disabled={weakEntry === null}
          onClick={() => weakEntry && onStart(weakEntry)}
          className="mt-3 w-full text-xs font-bold text-brand"
        >
          <Plus data-icon="inline-start" aria-hidden="true" /> Practice a pattern
        </Button>
      </div>
    </section>
  );
}

// ── 빠른 카드 셋 ──

const QUICK_BASE = "block rounded-2xl p-5 text-left transition-shadow hover:shadow-md focus-visible:ring-3 focus-visible:ring-ring/50 outline-none";

function QuickBody({ icon, tag, title, text }: { icon: ReactNode; tag: string; title: string; text: string }) {
  return (
    <>
      <div className="mb-8 flex items-center justify-between">
        <div className="grid size-10 place-items-center rounded-xl bg-white">{icon}</div>
        <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-muted-foreground">{tag}</span>
      </div>
      <h3 className="text-sm font-extrabold text-foreground">{title}</h3>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{text}</p>
    </>
  );
}

function QuickCards({ onStart }: { onStart: (entry: SessionEntry) => void }) {
  const shadowing = entryOf("shadowing");
  const weak = entryOf("weak_patterns");
  return (
    <div className="mt-8 grid gap-5 md:grid-cols-3">
      <button
        type="button"
        data-testid="quick-shadowing"
        disabled={shadowing === null}
        onClick={() => shadowing && onStart(shadowing)}
        className={cn(QUICK_BASE, "bg-tint-sky")}
      >
        <QuickBody
          icon={<Volume2 className="size-5 text-brand" aria-hidden="true" />}
          tag="Speak"
          title="Shadow a sentence"
          text="Listen, repeat, make it yours."
        />
      </button>
      <Link href="/videos" data-testid="quick-videos" className={cn(QUICK_BASE, "bg-tint-peach")}>
        <QuickBody
          icon={<Headphones className="size-5 text-[#c75f39]" aria-hidden="true" />}
          tag="Watch"
          title="Listen & notice"
          text="Hear real English in short clips."
        />
      </Link>
      <button
        type="button"
        data-testid="quick-weak-patterns"
        disabled={weak === null}
        onClick={() => weak && onStart(weak)}
        className={cn(QUICK_BASE, "bg-tint-mint")}
      >
        <QuickBody
          icon={<BookOpen className="size-5 text-[#2e7d57]" aria-hidden="true" />}
          tag="Review"
          title="Repair your mistakes"
          text="Fix one mistake. Make it a habit."
        />
      </button>
    </div>
  );
}

// ── 추가 학습 ──
// ⛔ PRD §7 — 권장량 완료와 무관하게 늘 보임. 목록의 정본은 `additionalLearning.ts` 임.

function MorePractice({ onStart }: { onStart: (entry: SessionEntry) => void }) {
  return (
    <section className="mt-8" data-testid="home-more-practice">
      <SectionHead title="More practice" sub="Pick any time. You don't need to finish today's practice first." />
      <div className="flex flex-wrap gap-2">
        {ADDITIONAL_LEARNING.map((item) => {
          const label = practiceLabel(item);
          const note = practiceNote(item);
          const className = cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-xl bg-card px-4");
          if (item.href) {
            return (
              <Link key={item.key} href={item.href} data-testid={`practice-${item.key}`} className={className}>
                {label}
              </Link>
            );
          }
          const entry = item.entry;
          return (
            <Button
              key={item.key}
              data-testid={`practice-${item.key}`}
              variant="outline"
              size="lg"
              disabled={!isAdditionalLearningEnabled(item)}
              title={note}
              onClick={() => entry && onStart(entry)}
              className="rounded-xl bg-card px-4"
            >
              {label}
              {note ? <span className="text-muted-foreground">({note})</span> : null}
            </Button>
          );
        })}
      </div>
    </section>
  );
}
