"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type MouseEvent, type ReactNode } from "react";
import { Sparkles, Target, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type NavKey = "home";

type NavItem = {
  key: NavKey;
  label: string;
  href: string;
  Icon: LucideIcon;
};

const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", label: "Home", href: "/", Icon: Target },
];
// ⛔ 메뉴는 Home 하나임(`TASK-314` 사용자 결정) — 학습은 홈의 오늘의 연습 카드에서만 함. Practice(`/course`)·
//    Review(`/history`)·Progress(`/history/weekly`) 메뉴를 뺐음. 기록·주간 리포트는 홈 Your progress 카드에서
//    들어감. 화면 자체는 남아 있어 결과 화면 등의 이동 버튼으로 닿음.

export function activeNavKey(pathname: string): NavKey | null {
  return pathname === "/" ? "home" : null;
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
          {/* 좁은 화면은 메뉴 줄을 두지 않음 — 메뉴가 Home 하나뿐이고 로고가 Home 으로 감(`TASK-314`). */}
        </header>

        <div className="min-w-0 flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-9">{children}</div>
      </div>
    </SessionLockContext.Provider>
  );
}
