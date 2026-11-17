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
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  Mic,
  Sparkles,
  Play,
  Plus,
  TrendingUp,
} from "lucide-react";

import { LOCKED_TITLE, lockedLinkProps } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
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
import { weekName, weekRangeLabel, weekRelation } from "@/lib/learnerDate";
import { cn } from "@/lib/utils";
import { useShowTranslation } from "@/lib/translationSetting";
import { useExtrasFromQuery } from "./homeExtras";
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
// 홈에 보일 추가 학습 입구(`TASK-338` 사용자 결정 2026-11-15) — 「일단 매일매일 연습하는 것만 있으면 될 것 같아,
// 필요하면 나중에 넣자」. More practice 전체와 Focus patterns 의 Practice a pattern 을 숨김.
// ⛔ 지우지 않고 숨기기만 함 — 다시 넣을 때는 이 값을 `true` 로 바꿈. 음성 명령(추가 학습 시작)은 이 값과 무관하게 남음.
// ⚠️ 주소 `?extras=1` 이면 이 값과 무관하게 보임 — 수동 하네스 드라이버의 진입 길(`TASK-341` · `homeExtras.ts`).
const HOME_EXTRAS = { morePractice: false, focusPractice: false } as const;
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
  /** `label` 은 누른 버튼의 이름임 — 코치 세션 머리의 제목이 됨(`TASK-333` N3). */
  onStart: (entry: SessionEntry, label?: string) => void;
  /** 진행 중인 세션 화면. 있으면 오늘의 연습 카드가 그것을 그리고 나머지 이동이 잠김. */
  session?: ReactNode;
}) {
  const locked = session !== null && session !== undefined;
  const searchParams = useSearchParams();
  const requestedDay = Number(searchParams.get("day"));
  const initialPracticeDay = Number.isInteger(requestedDay) && requestedDay > 0 ? requestedDay : undefined;
  // `?extras=1` 이면 숨긴 추가 학습 입구를 보임 — 수동 하네스 드라이버의 진입 길(`TASK-341`).
  const extrasByQuery = useExtrasFromQuery();
  const showMorePractice = HOME_EXTRAS.morePractice || extrasByQuery;
  const showFocusPractice = HOME_EXTRAS.focusPractice || extrasByQuery;
  // 오늘의 연습 카드가 문장 연습을 그리는 중인가. 세션이 열리면 세션이 이김.
  const [practicing, setPracticing] = useState(initialPracticeDay !== undefined);
  // 문장 연습이 여는 Day — 비어 있으면 코스의 현재 Day 임. Continue your path 에서 고르면 그 Day 임(`TASK-314`).
  const [practiceDay, setPracticeDay] = useState<number | undefined>(initialPracticeDay);
  // 진도 화면의 Day 줄은 `/?day=N` 으로 옴 — 질의만 바뀌는 이동에서는 상태가 남으므로 값이 바뀔 때 다시 엶
  // (`TASK-345` codex 리뷰 · 렌더 중 상태 맞춤 — 효과에서 setState 하지 않음).
  const [seenDay, setSeenDay] = useState(initialPracticeDay);
  if (seenDay !== initialPracticeDay) {
    setSeenDay(initialPracticeDay);
    if (initialPracticeDay !== undefined && !locked) {
      setPracticeDay(initialPracticeDay);
      setPracticing(true);
    }
  }
  const showPractice = practicing && !locked;
  // 모바일 머리·요약은 대기 때만 보임 — 연습·세션은 카드가 화면 전체이고, 세션 중 이동은 소켓을 닫음(`TASK-345`).
  const showMobileChrome = !showPractice && !locked;
  const history = useLoad(fetchHistory);
  const weekly = useLoad(fetchWeeklyReport);
  const course = useLoad(fetchCourse);
  const daily = useLoad(fetchDailySummary);
  const reloadCourse = course.reload;
  // ⛔ 현재 Day 로 열 때도 번호를 연 순간에 정해 둠(`TASK-315` codex 리뷰) — 비워 두면 Day 를 마친 뒤 코스를 다시
  //    읽을 때 강조 줄은 다음 Day 로 옮고 카드는 마친 Day 를 보여 둘이 어긋났음. 코스를 못 읽었으면 비움.
  const currentDay = course.status === "ready" ? course.data.current_day : undefined;

  // ⛔ 코치 세션은 문장 연습이 내려간 뒤에 엶 — 같은 틱에 열면 세션의 getUserMedia 가 연습이 마이크를
  //    놓기 전에 돌아 두 획득이 겹쳤음(codex 리뷰 HIGH). 그래서 연습이 열려 있으면 닫기만 하고, 시작할
  //    세션을 ref 에 둔 뒤 아래 effect 가 엶. 자식의 언마운트 정리(마이크 놓기·진도 저장)는 같은 커밋에서
  //    부모 effect 보다 먼저 돎.
  const pendingRef = useRef<{ entry: SessionEntry; label?: string } | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  // 아래쪽 입구(More practice · 빠른 카드 · 초점 패턴)만 지나는 길임 — 「Start speaking」은 `onOpen` 을 씀.
  const startSession = useCallback(
    (entry: SessionEntry, label?: string) => {
      revealHero(heroRef.current);
      if (!practicing) {
        onStart(entry, label);
        return;
      }
      pendingRef.current = { entry, label };
      setPracticing(false);
    },
    [onStart, practicing, setPracticing],
  );
  // Continue your path 에서 고른 Day 를 오늘의 연습 카드에서 엶 — 페이지를 옮기지 않음(`TASK-314` 사용자 지시).
  // 아래쪽 입구이므로 카드가 화면 밖이면 카드로 스크롤함(`TASK-308`).
  const pickDay = useCallback((day: number | undefined) => {
    revealHero(heroRef.current);
    setPracticeDay(day);
    setPracticing(true);
  }, [setPracticeDay, setPracticing]);
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
    if (pending) onStart(pending.entry, pending.label);
  }, [practicing, onStart, reloadCourse]);

  const doneDays = course.status === "ready" ? courseDoneCount(course.data) : 0;
  const totalDays = course.status === "ready" ? course.data.days.length : 0;
  const daysThisWeek = history.status === "ready" ? learnedInLastWeek(history.data) : null;

  return (
    <div
      className="home-dashboard text-foreground"
      data-practicing={showPractice ? "true" : "false"}
      data-extras={extrasByQuery ? "true" : undefined}
    >
      {showMobileChrome ? (
        <header className="home-mobile-header md:hidden">
          <Link href="/" aria-label="OhMyEnglish home" className="home-brand">
            <span className="home-brand-mark"><Sparkles aria-hidden="true" /></span>
            <span><strong>OhMyEnglish</strong><small>SPEAK. REMEMBER. GROW.</small></span>
          </Link>
          <Link href="/progress" aria-label="Your progress" title="Your progress" className="home-progress-button">
            <TrendingUp aria-hidden="true" />
          </Link>
        </header>
      ) : null}
      <p className={cn("home-mobile-summary md:hidden", !showMobileChrome && "hidden")}>
        {totalDays ? `${doneDays} / ${totalDays} days` : "Progress loading"} · This week {daysThisWeek?.learned ?? "—"} / {daysThisWeek?.window ?? 7}
      </p>
      {/* 날짜·인사·연속 학습 머리는 뺐음(`TASK-305` 사용자 지시). 화면 제목은 낭독기에만 남김. */}
      <h1 className="sr-only">Home</h1>

      {/* 오늘의 연습 카드는 연습에서 내용만큼의 높이이고, 대기·세션은 그 높이와 같은 `HERO_HEIGHT` 를 씀(`TASK-310`). */}
      <div className="home-primary-grid grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.85fr)]">
        <HeroCard
          heroRef={heroRef}
          course={course}
          practicing={showPractice}
          practiceDay={practiceDay}
          onOpen={() => {
            setPracticeDay(currentDay);
            setPracticing(true);
          }}
          onClose={() => setPracticing(false)}
          onDayFinished={reloadCourse}
          session={locked ? session : null}
        />
        <ProgressCard course={course} history={history} weekly={weekly} locked={locked} />
      </div>

      <div className="home-secondary-grid mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
        <PathSection
          course={course}
          locked={locked}
          selectedDay={showPractice ? (practiceDay ?? null) : null}
          onPick={pickDay}
        />
        <FocusSection
          daily={daily}
          weekly={weekly}
          onStart={startSession}
          locked={locked}
          showPractice={showFocusPractice}
        />
      </div>

      {showMorePractice ? <MorePractice onStart={startSession} locked={locked} /> : null}
    </div>
  );
}

export function ProgressDashboard() {
  const router = useRouter();
  const course = useLoad(fetchCourse);
  const history = useLoad(fetchHistory);
  const weekly = useLoad(fetchWeeklyReport);
  const daily = useLoad(fetchDailySummary);
  const pickDay = useCallback((day: number | undefined) => {
    if (day) router.push(`/?day=${day}`);
  }, [router]);

  return (
    <main className="progress-dashboard mx-auto max-w-5xl text-foreground">
      <Link href="/" className="omy-button mb-5 inline-flex min-h-11 items-center">← Home</Link>
      <h1 className="progress-title mb-6 text-3xl font-extrabold tracking-tight">Your progress</h1>
      <div className="grid gap-5">
        <ProgressCard course={course} history={history} weekly={weekly} locked={false} />
        <PathSection course={course} locked={false} selectedDay={null} onPick={pickDay} />
        <FocusSection daily={daily} weekly={weekly} onStart={() => {}} locked={false} showPractice={false} />
      </div>
    </main>
  );
}

// ── 오늘의 연습 ──

// 오늘의 연습 카드의 대기·세션 높이(`TASK-310` 사용자 지시) — 연습 상태의 카드 높이와 같게 둠.
// 연습 상태는 높이를 주지 않음 — 문장 칸(`SentencePractice.tsx`)이 상태·문장 길이와 무관한 고정 크기라
// 카드도 늘 같은 높이가 되고, 아래쪽에 빈 공간이 남지 않음. 이 값은 그 높이를 실제 화면에서 잰 것임.
// 근거는 설계서 §3 「문장 칸 고정 · 카드는 내용 높이」가 가짐. 문장 칸의 줄·여백을 바꾸면 이 값도 다시 잼.
//   1400·390 폭 모두 513.2 px → 32.1rem(513.6 px) (`TASK-326` 에서 말한 내용을 문장 글자로 키운 뒤 다시 잼 ·
//   회차 b15 `measure.mjs`).
const HERO_HEIGHT = "h-[32.1rem]";
// 문장 연습의 최저 높이 — 연습을 불러오는 첫 순간(「Loading…」)에도 카드가 대기 높이 아래로 줄지 않게 함(`TASK-319`).
// ⛔ 줄면 문서가 창보다 짧아져 스크롤이 0 에 붙음 — 1400×900 에서 Start speaking 이 창을 움직였음(회차 b16 D1).
const HERO_MIN_HEIGHT = "min-h-[32.1rem]";
// KO(문장 아래 번역)를 켜면 번역 두 줄만큼 문장 칸이 커짐(`TASK-328`). 1400 557.7 px · 390 548.7 px 이라
// 둘을 덮는 34.9rem(558.4 px)을 대기·세션 높이와 연습 최저 높이로 씀 — 두 폭 모두 대기와 연습이 같아짐(회차 b20 ko.mjs).
const HERO_HEIGHT_KO = "h-[34.9rem]";
const HERO_MIN_HEIGHT_KO = "min-h-[34.9rem]";

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
  practiceDay,
  onOpen,
  onClose,
  onDayFinished,
  session,
}: {
  heroRef: RefObject<HTMLDivElement | null>;
  course: Load<CourseOverview>;
  practicing: boolean;
  practiceDay: number | undefined;
  onOpen: () => void;
  onClose: () => void;
  onDayFinished: () => void;
  session: ReactNode;
}) {
  const inSession = session !== null;
  // KO 를 켜면 번역 줄만큼 카드가 커지므로 대기·세션 높이도 그 값을 따름(`TASK-328`).
  const [showTranslation] = useShowTranslation();
  const heroHeight = showTranslation ? HERO_HEIGHT_KO : HERO_HEIGHT;
  const heroMinHeight = showTranslation ? HERO_MIN_HEIGHT_KO : HERO_MIN_HEIGHT;
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
        className={cn(CARD, "home-hero flex flex-col", inSession ? heroHeight : heroMinHeight)}
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
          className={cn("home-hero-body flex min-h-0 flex-1 flex-col", inSession && "-mr-2 overflow-y-auto overscroll-contain pr-2")}
        >
          {inSession ? session : <HomeCoursePractice key={practiceDay ?? "current"} day={practiceDay} onDayFinished={onDayFinished} autoStart />}
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
        "home-hero flex flex-col justify-center rounded-[24px] bg-hero p-6 text-white shadow-xl shadow-hero/10 sm:justify-between sm:p-8",
        heroHeight,
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
  locked,
}: {
  course: Load<CourseOverview>;
  history: Load<HistoryPayload>;
  weekly: Load<WeeklyReportPayload>;
  locked: boolean;
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
        {/* `TASK-333` N1 — 최장 연속일은 전체 기간 값이라 아래 「Last week · …」 꼬리표 밖(진도 줄)에 둠.
            꼬리표 아래에 있을 때 지난주 값으로 읽혔음(회차 b18 N1). */}
        {history.status === "ready" && (
          <span data-testid="stat-best-streak">
            Best streak: {plural(history.data.streak.longest, "day", "days")}
          </span>
        )}
      </div>
      <WeeklyStats weekly={weekly} />
      {/* 기록·주간 리포트의 입구 — 사이드바 메뉴를 뺐으므로 여기가 그 화면들로 가는 길임(`TASK-314`). */}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <LockLink href="/history" testId="home-history" locked={locked} className="omy-button omy-button-primary">
          History →
        </LockLink>
        <LockLink href="/history/weekly" testId="home-weekly" locked={locked} className="omy-button omy-button-primary">
          Weekly report →
        </LockLink>
      </div>
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

/** 「Last week · Nov 2 – Nov 8」. 이번 주 · 지난주가 아니면 날짜만 보임. */
function periodCaption(weekStart: string, thisWeekStart: string | undefined): string {
  const name = weekName(weekRelation(weekStart, thisWeekStart));
  const range = weekRangeLabel(weekStart);
  return name ? `${name} · ${range}` : range;
}

// ⚠️ 꼬리표가 덮는 값은 Sessions · Patterns 둘뿐임 — Best streak 은 진도 줄로 옮겼음(`TASK-333` N1).
function WeeklyStats({ weekly }: { weekly: Load<WeeklyReportPayload> }) {
  const report = weekly.status === "ready" && weekly.data.analyzed ? weekly.data : null;
  const dash = weekly.status === "loading" ? "…" : "–";
  // `TASK-329` — Sessions · Patterns 는 최근 리포트(대개 지난주)의 값임. 바로 위 「This week」 줄과 섞여
  // 이번 주 값으로 읽혔으므로 그 기간을 숫자 위에 적음. 「This week」는 정말 이번 주일 때만 씀.
  const period = report?.week_start ? periodCaption(report.week_start, report.this_week_start) : null;
  return (
    <div className="mt-6 border-t border-border pt-5" data-testid="home-weekly-stats" data-state={weekly.status}>
      {period && (
        <p className="mb-2 text-center text-[11px] font-semibold text-muted-foreground" data-testid="home-weekly-period">
          {period}
        </p>
      )}
      <div className="grid grid-cols-2 gap-2 text-center">
        <Stat testId="stat-sessions" label="Sessions" value={report ? String(report.metrics.session_count ?? 0) : dash} />
        <Stat testId="stat-patterns" label="Patterns" value={report ? String(report.metrics.pattern_count ?? 0) : dash} />
      </div>
      <p className="mt-3 text-center text-[11px] text-muted-foreground">
        {weekly.status === "error" && "Can't load your weekly report."}
        {weekly.status === "ready" && !report && "No weekly report yet."}
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

function PathSection({
  course,
  locked,
  selectedDay,
  onPick,
}: {
  course: Load<CourseOverview>;
  locked: boolean;
  /** 오늘의 연습 카드가 지금 연습 중인 Day. 연습이 닫혀 있으면 `null`. */
  selectedDay: number | null;
  onPick: (day: number) => void;
}) {
  // ⛔ View all 은 다른 화면으로 가지 않고 이 목록을 모든 Day 로 펼침(`TASK-314` 사용자 결정).
  const [expanded, setExpanded] = useState(false);
  return (
    <section data-testid="home-path" data-state={course.status}>
      <SectionHead
        title="Continue your path"
        sub="Small steps, real conversations."
        action={
          <button
            type="button"
            data-testid="home-path-all"
            aria-expanded={expanded}
            onClick={() => setExpanded((open) => !open)}
            className="omy-button"
          >
            {expanded ? "Show less" : "View all"}
            <ChevronRight aria-hidden="true" className={cn("size-4", expanded && "-rotate-90")} />
          </button>
        }
      />
      {/* 줄 높이를 줄였음(`TASK-307`) — 배지 36 px · 위아래 10 px · 제목과 단원을 한 줄에 둠. */}
      {/* ⛔ 줄은 링크가 아니라 버튼임 — 고르면 그 Day 를 오늘의 연습 카드에서 엶(`TASK-314`). 예전에는 Day 화면
          (`/course/<day>`)으로 가서 영상과 옛 연습 화면이 나왔음. 세션 중에는 잠금(`TASK-301`). */}
      <div className="flex flex-col gap-2">
        {course.status === "loading" && <div className={cn(CARD, "h-[58px] animate-pulse p-4")} />}
        {course.status === "error" && (
          <div className={cn(CARD, "p-4")}>
            <Muted>Can&apos;t load the course.</Muted>
          </div>
        )}
        {course.status === "ready" &&
          (expanded ? course.data.days : pathDays(course.data)).map((day) => {
            const status = dayStatus(day, course.data.cycle);
            const selected = day.day === selectedDay;
            return (
              <button
                type="button"
                key={day.day}
                data-testid={`path-day-${day.day}`}
                data-status={status}
                data-selected={selected ? "true" : undefined}
                aria-pressed={selected}
                disabled={locked}
                title={locked ? LOCKED_TITLE : undefined}
                onClick={() => onPick(day.day)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-2xl border bg-card px-4 py-2.5 text-left shadow-sm transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50",
                  selected ? "border-brand" : "border-border",
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
              </button>
            );
          })}
      </div>
    </section>
  );
}

// ── 초점 패턴 ──

// 초점 패턴의 연습 버튼 이름 — 그 버튼으로 연 코치 세션의 제목도 이 이름임(`TASK-333` N3).
const FOCUS_PRACTICE_LABEL = "Practice a pattern";

function FocusSection({
  daily,
  weekly,
  onStart,
  locked,
  showPractice,
}: {
  daily: Load<DailySummaryPayload>;
  weekly: Load<WeeklyReportPayload>;
  onStart: (entry: SessionEntry, label?: string) => void;
  locked: boolean;
  /** Practice a pattern 을 보일지 — 기본 숨김(`TASK-338`) · `?extras=1` 이면 보임(`TASK-341`). */
  showPractice: boolean;
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
        {showPractice ? (
          <button
            type="button"
            data-testid="focus-practice"
            disabled={weakEntry === null || locked}
            onClick={() => weakEntry && onStart(weakEntry, FOCUS_PRACTICE_LABEL)}
            className="omy-button mt-3 w-full justify-center"
          >
            <Plus aria-hidden="true" className="size-4" /> {FOCUS_PRACTICE_LABEL}
          </button>
        ) : null}
      </div>
    </section>
  );
}

// ── 추가 학습 ──
// ⛔ PRD §7 — 권장량 완료와 무관하게 늘 보임. 목록의 정본은 `additionalLearning.ts` 임.

function MorePractice({
  onStart,
  locked,
}: {
  onStart: (entry: SessionEntry, label?: string) => void;
  locked: boolean;
}) {
  // ⛔ 버튼은 홈 기준 `omy-button` 임(`TASK-323` 사용자 결정 — 이동·실행 버튼 모두 같은 모양).
  // ⛔ 빠른 카드 셋과 Grammar course 는 제거했음(`TASK-323`) — 같은 학습을 여는 두 번째 입구였음.
  return (
    <section className="mt-8" data-testid="home-more-practice">
      <SectionHead title="More practice" sub="Pick any time. You don't need to finish today's practice first." />
      <div className="flex flex-wrap gap-2">
        {ADDITIONAL_LEARNING.map((item) => {
          const label = practiceLabel(item);
          const note = practiceNote(item);
          if (item.href) {
            return (
              <LockLink key={item.key} href={item.href} testId={`practice-${item.key}`} locked={locked} className="omy-button">
                {label}
              </LockLink>
            );
          }
          const entry = item.entry;
          return (
            <button
              type="button"
              key={item.key}
              data-testid={`practice-${item.key}`}
              disabled={!isAdditionalLearningEnabled(item) || locked}
              title={locked ? LOCKED_TITLE : note}
              onClick={() => entry && onStart(entry, label)}
              className="omy-button"
            >
              {label}
              {note ? <span style={{ color: "var(--foreground-muted)" }}>({note})</span> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
