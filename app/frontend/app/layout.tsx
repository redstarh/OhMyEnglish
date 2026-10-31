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
};

// 밝은 테마만 둔다(TASK-293) — 브라우저 UI 색은 `--page` 와 맞춘다.
export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f7f8fc",
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
