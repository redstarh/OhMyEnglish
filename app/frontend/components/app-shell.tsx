"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type MouseEvent, type ReactNode } from "react";
import { Mic, RotateCcw, Sparkles, Target, TrendingUp, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type NavKey = "home" | "practice" | "review" | "progress";

type NavItem = {
  key: NavKey;
  label: string;
  href: string;
  Icon: LucideIcon;
};

const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", label: "Home", href: "/", Icon: Target },
  { key: "practice", label: "Practice", href: "/course", Icon: Mic },
  { key: "review", label: "Review", href: "/history", Icon: RotateCcw },
  { key: "progress", label: "Progress", href: "/history/weekly", Icon: TrendingUp },
];

// 경로 접두어 → 메뉴. 가장 긴 접두어가 이김(설계서 §3) — `/history/weekly` 가 `/history` 를 이김.
// Home 은 정확히 `/` 일 때만 활성이라 이 표에 넣지 않음.
const PREFIX_RULES: readonly (readonly [string, NavKey])[] = [
  ["/course", "practice"],
  ["/videos", "practice"],
  ["/history", "review"],
  ["/results", "review"],
  ["/history/weekly", "progress"],
];

function matchesPrefix(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function activeNavKey(pathname: string): NavKey | null {
  if (pathname === "/") return "home";
  let best: readonly [string, NavKey] | null = null;
  for (const rule of PREFIX_RULES) {
    if (matchesPrefix(pathname, rule[0]) && (best === null || rule[0].length > best[0].length)) {
      best = rule;
    }
  }
  return best ? best[1] : null;
}

// ── 세션 잠금 ──
// 세션이 도는 동안 이동 링크를 막는 잠금 (`TASK-301` · 리디자인 설계서 §3).
// ⛔ 이동하면 홈 화면이 내려가 소켓이 닫히고 세션이 끝남. 그래서 세션을 소유한 `app/page.tsx` 가
//    대기가 아닌 동안 잠그고, 대기로 돌아오거나 언마운트되면 풂.

export const LOCKED_TITLE = "End the lesson first";

// 값은 `useState` 의 설정 함수 하나 — 늘 같은 함수라 소비하는 쪽이 다시 그려지지 않음.
const SessionLockContext = createContext<(locked: boolean) => void>(() => {});

/** 잠금 상태를 화면이 정함 — 언마운트 정리가 잠금을 풂. */
export function useSessionLock(locked: boolean) {
  const setLocked = useContext(SessionLockContext);
  useEffect(() => {
    setLocked(locked);
    return () => setLocked(false);
  }, [locked, setLocked]);
}

function preventNavigation(event: MouseEvent) {
  event.preventDefault();
}

/**
 * 잠긴 링크의 속성 — 흐리게 · 누를 수 없게 · 탭 순서에서 뺌.
 * ⚠️ `onClick` 의 `preventDefault` 는 겹 방어임 — `next/link` 는 막힌 클릭을 이동하지 않음.
 */
export function lockedLinkProps(locked: boolean) {
  return locked
    ? {
        "aria-disabled": true,
        tabIndex: -1,
        title: LOCKED_TITLE,
        onClick: preventNavigation,
        lockClassName: "pointer-events-none opacity-50",
      }
    : { lockClassName: "" };
}

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid size-10 shrink-0 place-items-center rounded-[13px] bg-hero text-white shadow-lg shadow-hero/15">
        <Sparkles className="size-5" aria-hidden="true" />
      </div>
      <div>
        <p className="text-[15px] font-extrabold tracking-tight text-foreground">OhMyEnglish</p>
        <p className="whitespace-nowrap text-[10px] font-medium text-muted-foreground">SPEAK. REMEMBER. GROW.</p>
      </div>
    </div>
  );
}

function NavLink({
  href,
  locked,
  className,
  children,
  ...rest
}: {
  href: string;
  locked: boolean;
  className: string;
  children: ReactNode;
  "data-testid"?: string;
  "aria-current"?: "page";
}) {
  const { lockClassName, ...lockProps } = lockedLinkProps(locked);
  return (
    <Link href={href} {...rest} {...lockProps} className={cn(className, lockClassName)}>
      {children}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const active = activeNavKey(pathname);
  const [locked, setLocked] = useState(false);
  // ⚠️ 잠긴 링크는 `pointer-events-none` 이라 제 `title` 이 안 뜸 — 그래서 감싼 `nav` 에도 둠.
  const navLock = locked
    ? { "data-locked": "true", title: LOCKED_TITLE, className: "cursor-not-allowed" }
    : { className: "" };

  return (
    <SessionLockContext.Provider value={setLocked}>
      <div className="mx-auto flex min-h-screen max-w-[1500px] flex-col lg:flex-row">
        <aside className="hidden w-[248px] shrink-0 border-r border-border bg-white px-5 py-7 lg:flex lg:flex-col">
          <NavLink href="/" locked={locked} className="mb-12 rounded-xl px-2">
            <Logo />
          </NavLink>
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Workspace
          </p>
          <nav aria-label="Main" {...navLock} className={cn("flex flex-col gap-1", navLock.className)}>
            {NAV_ITEMS.map(({ key, label, href, Icon }) => {
              const isActive = key === active;
              return (
                <NavLink
                  key={key}
                  href={href}
                  locked={locked}
                  data-testid={`nav-${key}`}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-semibold no-underline transition-colors",
                    isActive ? "bg-brand-soft text-brand" : "text-muted-foreground hover:bg-accent",
                  )}
                >
                  <Icon className="size-[17px]" aria-hidden="true" />
                  {label}
                </NavLink>
              );
            })}
          </nav>
        </aside>

        <header className="border-b border-border bg-white px-5 pt-4 pb-2 sm:px-8 lg:hidden">
          <NavLink href="/" locked={locked} className="inline-block rounded-xl">
            <Logo />
          </NavLink>
          <nav aria-label="Main" {...navLock} className={cn("mt-3 grid grid-cols-4 gap-1", navLock.className)}>
            {NAV_ITEMS.map(({ key, label, href, Icon }) => {
              const isActive = key === active;
              return (
                <NavLink
                  key={key}
                  href={href}
                  locked={locked}
                  data-testid={`nav-${key}`}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex min-w-0 flex-col items-center gap-1 rounded-xl px-1 py-2 text-[11px] font-semibold no-underline transition-colors",
                    isActive ? "bg-brand-soft text-brand" : "text-muted-foreground hover:bg-accent",
                  )}
                >
                  <Icon className="size-[18px]" aria-hidden="true" />
                  <span className="truncate">{label}</span>
                </NavLink>
              );
            })}
          </nav>
        </header>

        <div className="min-w-0 flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-9">{children}</div>
      </div>
    </SessionLockContext.Provider>
  );
}
