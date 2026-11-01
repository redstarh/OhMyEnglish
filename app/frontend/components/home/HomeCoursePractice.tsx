"use client";

// 홈의 문장 연습 — 오늘의 연습 카드 안에서 문법 코스의 현재 Day 를 연습함(`TASK-304` · 리디자인 설계서 §3).
// ⛔ 영상을 그리지 않음(사용자 지시 2026-11-01) — 문장은 백엔드 콘텐츠의 단원 패턴 문장이고 영상에서
//    가져오는 것이 없음. 그래서 연습 칸에 영상 핸들을 넘기지 않음.
// ⚠️ 열 때마다 진도를 새로 읽음 — 홈이 마운트 때 읽은 코스 개요는 앞서 연 연습의 저장을 모름.

import { useEffect, useState } from "react";

import { SentencePractice } from "@/components/course/SentencePractice";
import { fetchCourse, fetchCourseDay, type CourseDayDetail } from "@/lib/api";

type State = { status: "loading" } | { status: "ready"; detail: CourseDayDetail } | { status: "error" };

async function loadCurrentDay(): Promise<CourseDayDetail | null> {
  const course = await fetchCourse();
  if (!course) return null;
  return fetchCourseDay(course.current_day);
}

export function HomeCoursePractice() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    loadCurrentDay().then(
      (detail) => {
        if (!cancelled) setState(detail ? { status: "ready", detail } : { status: "error" });
      },
      () => {
        if (!cancelled) setState({ status: "error" });
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <p data-testid="practice-day" data-state="loading" className="mt-5 text-sm text-muted-foreground">
        Loading…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p data-testid="practice-day" data-state="error" className="mt-5 text-sm text-muted-foreground">
        I couldn&apos;t load today&apos;s sentences.
      </p>
    );
  }

  const { detail } = state;
  return (
    <div className="mt-4">
      <p data-testid="practice-day" data-state="ready" className="text-xs font-semibold text-muted-foreground">
        Day {detail.day} · Units {detail.units[0]?.unit}–{detail.units.at(-1)?.unit}
      </p>
      <SentencePractice key={detail.day} detail={detail} day={detail.day} />
    </div>
  );
}
