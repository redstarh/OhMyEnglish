import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/app-shell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OhMyEnglish",
  description: "Speak. Remember. Grow.",
  // iOS 홈 화면 앱(`TASK-346`) — 홈 화면 아이콘으로 열면 Safari 막대 없이 전체 화면으로 엶. 아이콘은 `app/apple-icon.png`.
  // 상태 막대는 기본(밝은 바탕 · 어두운 글자) — 화면이 상태 막대 아래에서 시작하므로 겹치지 않음.
  appleWebApp: { capable: true, title: "OhMyEnglish", statusBarStyle: "default" },
};

// 밝은 테마만 둔다(TASK-293) — 브라우저 UI 색은 `--page` 와 맞춘다.
export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f7f8fc",
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="bg-page text-foreground antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
