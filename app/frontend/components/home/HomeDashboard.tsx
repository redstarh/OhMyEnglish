"use client";

// 홈 대시보드 (`TASK-296` · 리디자인 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §5).
// 배치는 v0 원본(`docs/design/2026-11-01-v0-home-redesign/oh-my-english-dashboard.tsx.txt`)의 본문을
// 따르고, 사이드바는 공통 틀(`components/app-shell.tsx`)이 가짐.
// ⛔ 세션 논리는 여기 두지 않음 — 이 칸은 `onStart` 와 그려진 세션 화면만 받음(`app/page.tsx` 가 세션을 소유).
// ⛔ 「Start speaking」은 어떤 조회의 상태와도 무관하게 늘 눌림.
// ⛔ 「Start speaking」은 코치 대화가 아니라 문법 코스의 문장 연습을 이 카드 안에 엶(`TASK-304` · 설계서 §3).
//    추천 코치 대화의 시작점은 홈에서 뺐음(사용자 결정 「코치 대화 빼기」). 문장 연습은 소켓이 없어 이동을 잠그지 않음.
// ⛔ 세션 화면은 `session` 으로 받아 오늘의 연습 카드 안에 그림(`TASK-301` · 설계서 §3). 그동안
//    다른 세션을 열거나 화면을 떠나는 링크·버튼은 잠김 — 떠나면 소켓이 닫혀 세션이 끝남.

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Headphones,
  Mic,
  Play,
  Plus,
  TrendingUp,
  Volume2,
} from "lucide-react";

import { lockedLinkProps } from "@/components/app-shell";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  fetchCourse,
  fetchDailySummary,
  fetchHistory,
  fetchWeeklyReport,
  type CourseOverview,
  type DailySummaryPayload,
  type HistoryPayload,
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
  type Load,
} from "./dashboardData";
import { HomeCoursePractice } from "./HomeCoursePractice";

function entryOf(key: AdditionalLearningKey): SessionEntry | null {
  return ADDITIONAL_LEARNING.find((item) => item.key === key)?.entry ?? null;
}

const CARD = "rounded-[24px] border border-border bg-card p-6 shadow-sm";
// 홈의 섹션 라벨은 모두 「Your progress」 의 글꼴·색을 씀(`TASK-310` 사용자 지시 — 섹션 사이의 통일성).
const LABEL = "text-xs font-bold uppercase tracking-[0.14em]";

function SectionLabel({ children, as: Tag = "p", onDark = false }: { children: ReactNode; as?: "p" | "h2"; onDark?: boolean }) {
  // ⚠️ 남색 대기 카드 위에서만 흰 글자를 씀 — `--foreground-muted` 는 `--hero` 위에서 읽히지 않음.
  return <Tag className={cn(LABEL, onDark ? "text-white/75" : "text-muted-foreground")}>{children}</Tag>;
}

function Muted({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <p data-testid={testId} className="text-xs text-muted-foreground">
      {children}
    </p>
  );
}

/** 잠긴 링크 — 세션 중에 화면을 떠나지 못하게 함(공통 틀의 메뉴와 같은 속성). */
function LockLink({
  href,
  locked,
  className,
  children,
  testId,
}: {
  href: string;
  locked: boolean;
  className: string;
  children: ReactNode;
  testId: string;
}) {
  const { lockClassName, ...lockProps } = lockedLinkProps(locked);
  return (
    <Link href={href} data-testid={testId} {...lockProps} className={cn(className, lockClassName)}>
      {children}
    </Link>
  );
}

export function HomeDashboard({
  onStart,
  session = null,
}: {
  onStart: (entry: SessionEntry) => void;
  /** 진행 중인 세션 화면. 있으면 오늘의 연습 카드가 그것을 그리고 나머지 이동이 잠김. */
  session?: ReactNode;
}) {
  const locked = session !== null && session !== undefined;
  // 오늘의 연습 카드가 문장 연습을 그리는 중인가. 세션이 열리면 세션이 이김.
  const [practicing, setPracticing] = useState(false);
  const showPractice = practicing && !locked;
  const history = useLoad(fetchHistory);
  const weekly = useLoad(fetchWeeklyReport);
  const course = useLoad(fetchCourse);
  const daily = useLoad(fetchDailySummary);
  const reloadCourse = course.reload;

  // ⛔ 코치 세션은 문장 연습이 내려간 뒤에 엶 — 같은 틱에 열면 세션의 getUserMedia 가 연습이 마이크를
  //    놓기 전에 돌아 두 획득이 겹쳤음(codex 리뷰 HIGH). 그래서 연습이 열려 있으면 닫기만 하고, 시작할
  //    세션을 ref 에 둔 뒤 아래 effect 가 엶. 자식의 언마운트 정리(마이크 놓기·진도 저장)는 같은 커밋에서
  //    부모 effect 보다 먼저 돎.
  const pendingRef = useRef<SessionEntry | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  // 아래쪽 입구(More practice · 빠른 카드 · 초점 패턴)만 지나는 길임 — 「Start speaking」은 `onOpen` 을 씀.
  const startSession = useCallback(
    (entry: SessionEntry) => {
      revealHero(heroRef.current);
      if (!practicing) {
        onStart(entry);
        return;
      }
      pendingRef.current = entry;
      setPracticing(false);
    },
    [onStart, practicing],
  );
  // 연습이 닫힌 뒤 — 미뤄 둔 세션을 열고, 코스 개요를 다시 읽어 대기 카드·진도가 저장된 진도와 맞게 함
  // (회차 b12 D1). 다시 읽기는 닫을 때의 저장을 기다린 뒤 조회함(`fetchCourse`).
  const wasPracticing = useRef(false);
  useEffect(() => {
    if (practicing) {
      wasPracticing.current = true;
      return;
    }
    if (!wasPracticing.current) return;
    wasPracticing.current = false;
    reloadCourse();
    const pending = pendingRef.current;
    pendingRef.current = null;
    if (pending) onStart(pending);
  }, [practicing, onStart, reloadCourse]);

  return (
    <div className="text-foreground">
      {/* 날짜·인사·연속 학습 머리는 뺐음(`TASK-305` 사용자 지시). 화면 제목은 낭독기에만 남김. */}
      <h1 className="sr-only">Home</h1>

      {/* 오늘의 연습 카드는 연습에서 내용만큼의 높이이고, 대기·세션은 그 높이와 같은 `HERO_HEIGHT` 를 씀(`TASK-310`). */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.85fr)]">
        <HeroCard
          heroRef={heroRef}
          course={course}
          practicing={showPractice}
          onOpen={() => setPracticing(true)}
          onClose={() => setPracticing(false)}
          onDayFinished={reloadCourse}
          session={locked ? session : null}
        />
        <ProgressCard course={course} history={history} weekly={weekly} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
        <PathSection course={course} locked={locked} />
        <FocusSection daily={daily} weekly={weekly} onStart={startSession} locked={locked} />
      </div>

      <QuickCards onStart={startSession} locked={locked} />
      <MorePractice onStart={startSession} locked={locked} />
    </div>
  );
}

// ── 오늘의 연습 ──

// 오늘의 연습 카드의 대기·세션 높이(`TASK-310` 사용자 지시) — 연습 상태의 카드 높이와 같게 둠.
// 연습 상태는 높이를 주지 않음 — 문장 칸(`SentencePractice.tsx`)이 상태·문장 길이와 무관한 고정 크기라
// 카드도 늘 같은 높이가 되고, 아래쪽에 빈 공간이 남지 않음. 이 값은 그 높이를 실제 화면에서 잰 것임.
// 근거는 설계서 §3 「문장 칸 고정 · 카드는 내용 높이」가 가짐. 문장 칸의 줄·여백을 바꾸면 이 값도 다시 잼.
//   1400 폭 479.5 px → 30rem(480 px) · 390 폭 536 px → 33.5rem(536 px) (회차 b15 `measure-*.json`).
const HERO_HEIGHT = "h-[33.5rem] sm:h-[30rem]";

// ⛔ 아래쪽 입구로 시작할 때 카드가 화면을 벗어나 있으면 카드로 스크롤함(`TASK-308` 사용자 결정) — 세션은
//    카드 안에서 돎. 카드가 이미 다 보이면 움직이지 않음. 「Start speaking」은 창을 옮기지 않는 `TASK-305`
//    규칙을 그대로 따름(이 함수를 부르지 않음).
function revealHero(hero: HTMLElement | null) {
  if (!hero) return;
  const rect = hero.getBoundingClientRect();
  if (rect.top >= 0 && rect.bottom <= window.innerHeight) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  hero.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
}

function HeroCard({
  heroRef,
  course,
  practicing,
  onOpen,
  onClose,
  onDayFinished,
  session,
}: {
  heroRef: RefObject<HTMLDivElement | null>;
  course: Load<CourseOverview>;
  practicing: boolean;
  onOpen: () => void;
  onClose: () => void;
  onDayFinished: () => void;
  session: ReactNode;
}) {
  const inSession = session !== null;
  const expanded = inSession || practicing;
  const current =
    course.status === "ready" ? (course.data.days.find((day) => day.day === course.data.current_day) ?? null) : null;
  // ⛔ 세션·연습을 열어도 창의 스크롤과 포커스를 옮기지 않음(`TASK-305` 사용자 지시) — 예전의
  //    `scrollIntoView` 가 「Start speaking」을 누르면 화면을 위로 끌어올렸음. 예외는 아래쪽 입구뿐임
  //    (`revealHero` · `TASK-308`).

  if (expanded) {
    // ⛔ 세션·연습 중에는 밝은 카드로 바꿈 — 대화·쉐도잉·리포트 패널과 문장 연습 칸이 `--foreground`
    //    글자색을 쓰므로 남색 바탕 위에서는 읽히지 않음. 자리·너비는 대기 카드와 같음.
    // ⛔ 문장 연습은 높이를 주지 않고 내용만큼임(`TASK-310` 사용자 지시) — `TASK-307` 의 고정 높이가
    //    결과 칸 자리를 카드 아래쪽 빈 공간으로 남겼음. 세션은 대기와 같은 `HERO_HEIGHT` 를 씀.
    // ⚠️ 코치 대화는 줄이 계속 늘어나므로 대화 기록 칸(`SessionChat.tsx`)이 남은 높이를 채우고 그 안에서만
    //    스크롤함. 쉐도잉·리포트 패널이 대화 아래에 더 붙어 기록 칸이 최소 높이까지 줄어든 뒤에만
    //    `home-hero-body` 가 받침으로 스크롤함.
    return (
      <div
        ref={heroRef}
        data-testid="home-hero"
        data-state={course.status}
        data-mode={inSession ? "session" : "practice"}
        className={cn(CARD, "flex flex-col", inSession && HERO_HEIGHT)}
      >
        <div className="flex shrink-0 items-center justify-between gap-3">
          <SectionLabel>Today&apos;s practice</SectionLabel>
          {inSession ? null : (
            <button type="button" data-testid="practice-close" onClick={onClose} className="omy-button">
              ← Close
            </button>
          )}
        </div>
        <div
          data-testid="home-hero-body"
          className={cn("flex min-h-0 flex-1 flex-col", inSession && "-mr-2 overflow-y-auto overscroll-contain pr-2")}
        >
          {inSession ? session : <HomeCoursePractice onDayFinished={onDayFinished} />}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={heroRef}
      data-testid="home-hero"
      data-state={course.status}
      data-mode="idle"
      className={cn(
        "flex flex-col justify-center rounded-[24px] bg-hero p-6 text-white shadow-xl shadow-hero/10 sm:justify-between sm:p-8",
        HERO_HEIGHT,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <SectionLabel onDark>Today&apos;s practice</SectionLabel>
          {course.status === "loading" ? (
            <div className="mt-5 h-[84px] max-w-[420px] animate-pulse rounded-xl bg-white/10" aria-label="Loading" />
          ) : (
            <h2
              data-testid="home-hero-title"
              className="mt-5 max-w-[480px] break-keep text-3xl font-extrabold leading-[1.1] tracking-[-0.03em] text-white sm:text-[38px]"
            >
              {current ? `Day ${current.day}: listen and say it.` : "Listen and say it."}
            </h2>
          )}
          <p className="mt-4 max-w-[390px] text-sm leading-6 text-white/75">
            Hear a short sentence. Say it out loud. See what you said.
          </p>
        </div>
        <div className="hidden size-16 shrink-0 rounded-2xl bg-white/10 sm:grid sm:place-items-center">
          <Mic className="size-7 text-white/80" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <Button
          data-testid="start-session"
          onClick={onOpen}
          size="lg"
          className="rounded-xl bg-white px-5 font-bold text-hero hover:bg-brand-soft"
        >
          <Play data-icon="inline-start" aria-hidden="true" /> Start speaking
        </Button>
        <span data-testid="home-hero-day" className="text-xs font-semibold text-white/75">
          {current ? `Day ${current.day} · Units ${current.first_unit}–${current.last_unit}` : "Grammar course"}
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
          <SectionLabel>Your progress</SectionLabel>
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
    <div className="mb-2.5 flex items-center justify-between gap-3">
      <div>
        <SectionLabel as="h2">{title}</SectionLabel>
        <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
      </div>
      {action}
    </div>
  );
}

const STATUS_TEXT = { done: "Done", started: "In progress", new: "Up next" } as const;

function PathSection({ course, locked }: { course: Load<CourseOverview>; locked: boolean }) {
  const { lockClassName, ...pathLock } = lockedLinkProps(locked);
  return (
    <section data-testid="home-path" data-state={course.status}>
      <SectionHead
        title="Continue your path"
        sub="Small steps, real conversations."
        action={
          <LockLink
            href="/course"
            testId="home-path-all"
            locked={locked}
            className={cn(buttonVariants({ variant: "ghost" }), "text-xs font-bold text-brand")}
          >
            View all <ChevronRight data-icon="inline-end" aria-hidden="true" />
          </LockLink>
        }
      />
      {/* 줄 높이를 줄였음(`TASK-307`) — 배지 36 px · 위아래 10 px · 제목과 단원을 한 줄에 둠. */}
      <div className="flex flex-col gap-2">
        {course.status === "loading" && <div className={cn(CARD, "h-[58px] animate-pulse p-4")} />}
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
                {...pathLock}
                className={cn(
                  lockClassName,
                  "flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-2.5 shadow-sm transition-colors hover:bg-accent",
                )}
              >
                <div
                  className={cn(
                    "grid size-9 shrink-0 place-items-center rounded-xl text-[9px] font-extrabold leading-none",
                    status === "done" ? "bg-tint-mint text-[#2e7d57]" : "bg-muted text-muted-foreground",
                  )}
                >
                  {status === "done" ? <Check className="size-4" aria-hidden="true" /> : `DAY ${day.day}`}
                </div>
                <p className="min-w-0 flex-1 truncate text-sm font-bold">
                  Day {day.day} · {STATUS_TEXT[status]}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    Units {day.first_unit}–{day.last_unit}
                  </span>
                </p>
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
  locked,
}: {
  daily: Load<DailySummaryPayload>;
  weekly: Load<WeeklyReportPayload>;
  onStart: (entry: SessionEntry) => void;
  locked: boolean;
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
          disabled={weakEntry === null || locked}
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

const QUICK_BASE =
  "block rounded-2xl px-4 py-3.5 text-left transition-shadow hover:shadow-md focus-visible:ring-3 focus-visible:ring-ring/50 outline-none disabled:pointer-events-none disabled:opacity-50";

function QuickBody({ icon, tag, title, text }: { icon: ReactNode; tag: string; title: string; text: string }) {
  return (
    // 아이콘·글·배지를 한 줄에 둠(`TASK-307`) — 예전의 아이콘 아래 `mb-8` 빈칸을 없앴음.
    <div className="flex items-center gap-3">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-white">{icon}</div>
      <div className="min-w-0 flex-1">
        <h3 className="text-sm font-extrabold text-foreground">{title}</h3>
        <p className="text-xs leading-5 text-muted-foreground">{text}</p>
      </div>
      <span className="shrink-0 self-start rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-muted-foreground">
        {tag}
      </span>
    </div>
  );
}

function QuickCards({ onStart, locked }: { onStart: (entry: SessionEntry) => void; locked: boolean }) {
  const shadowing = entryOf("shadowing");
  const weak = entryOf("weak_patterns");
  return (
    <div className="mt-6 grid gap-4 md:grid-cols-3">
      <button
        type="button"
        data-testid="quick-shadowing"
        disabled={shadowing === null || locked}
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
      <LockLink href="/videos" testId="quick-videos" locked={locked} className={cn(QUICK_BASE, "bg-tint-peach")}>
        <QuickBody
          icon={<Headphones className="size-5 text-[#c75f39]" aria-hidden="true" />}
          tag="Watch"
          title="Listen & notice"
          text="Hear real English in short clips."
        />
      </LockLink>
      <button
        type="button"
        data-testid="quick-weak-patterns"
        disabled={weak === null || locked}
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

function MorePractice({ onStart, locked }: { onStart: (entry: SessionEntry) => void; locked: boolean }) {
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
              <LockLink key={item.key} href={item.href} testId={`practice-${item.key}`} locked={locked} className={className}>
                {label}
              </LockLink>
            );
          }
          const entry = item.entry;
          return (
            <Button
              key={item.key}
              data-testid={`practice-${item.key}`}
              variant="outline"
              size="lg"
              disabled={!isAdditionalLearningEnabled(item) || locked}
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
