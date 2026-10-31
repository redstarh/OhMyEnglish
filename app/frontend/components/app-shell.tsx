"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
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

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const active = activeNavKey(pathname);

  return (
    <div className="mx-auto flex min-h-screen max-w-[1500px] flex-col lg:flex-row">
      <aside className="hidden w-[248px] shrink-0 border-r border-border bg-white px-5 py-7 lg:flex lg:flex-col">
        <Link href="/" className="mb-12 rounded-xl px-2">
          <Logo />
        </Link>
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
          Workspace
        </p>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ key, label, href, Icon }) => {
            const isActive = key === active;
            return (
              <Link
                key={key}
                href={href}
                data-testid={`nav-${key}`}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-semibold no-underline transition-colors",
                  isActive ? "bg-brand-soft text-brand" : "text-muted-foreground hover:bg-accent",
                )}
              >
                <Icon className="size-[17px]" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <header className="border-b border-border bg-white px-5 pt-4 pb-2 sm:px-8 lg:hidden">
        <Link href="/" className="inline-block rounded-xl">
          <Logo />
        </Link>
        <nav aria-label="Main" className="mt-3 grid grid-cols-4 gap-1">
          {NAV_ITEMS.map(({ key, label, href, Icon }) => {
            const isActive = key === active;
            return (
              <Link
                key={key}
                href={href}
                data-testid={`nav-${key}`}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex min-w-0 flex-col items-center gap-1 rounded-xl px-1 py-2 text-[11px] font-semibold no-underline transition-colors",
                  isActive ? "bg-brand-soft text-brand" : "text-muted-foreground hover:bg-accent",
                )}
              >
                <Icon className="size-[18px]" aria-hidden="true" />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>
      </header>

      <div className="min-w-0 flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-9">{children}</div>
    </div>
  );
}
