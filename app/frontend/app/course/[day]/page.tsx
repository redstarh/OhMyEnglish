"use client";

// 문법 코스 — 학습 화면 (`TASK-286` · 설계서 `docs/design/2026-10-26-grammar-course-design.md` §7).
//
// 이 화면은 Day 를 읽고 영상과 문장 연습 칸을 위아래로 둠. 문장 연습의 논리·화면은
// `components/course/SentencePractice.tsx` 가 가짐(`TASK-304` — 홈의 오늘의 연습 카드도 같은 칸을 씀).
//
// ⛔ 문장 연습이 도는 동안 영상을 멈춤 — 마이크가 영상 소리를 받으면 판정이 그 소리를 전사함.
//    영상을 다시 재생하면 연습이 멈춤. 그래서 이 화면은 영상 핸들을 연습 칸에 넘기고, 영상의
//    이벤트(재생 · 끝남 · 쓸 수 없음)를 연습 칸의 핸들로 넘김.
// ⚠️ 문장은 영상·교재의 문장이 아님 — 단원의 문법 패턴으로 새로 쓴 문장임(설계서 §2).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { fetchCourseDay, type CourseDayDetail } from "@/lib/api";
import { SentencePractice, type SentencePracticeHandle } from "@/components/course/SentencePractice";
import { CoursePlayer, type CoursePlayerHandle } from "./CoursePlayer";

const PAGE_STYLE = {
  maxWidth: 640,
  margin: "0 auto",
  padding: "2rem",
} as const;

const LOAD_FAILED = "I couldn't load this Day.";

export default function CourseDayPage() {
  const params = useParams<{ day: string }>();
  const day = Number(params.day);
  const [detail, setDetail] = useState<CourseDayDetail | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  const playerRef = useRef<CoursePlayerHandle | null>(null);
  const practiceRef = useRef<SentencePracticeHandle | null>(null);

  // Day 를 읽음. 저장된 자리로 옮기는 일은 연습 칸이 첫 렌더에서 함.
  useEffect(() => {
    let cancelled = false;
    fetchCourseDay(day)
      .then((value) => {
        if (cancelled) return;
        if (!value) {
          setLoadFailed(true);
          return;
        }
        setDetail(value);
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [day]);

  const startAt = useMemo(() => detail?.progress?.position_sec ?? 0, [detail]);

  const onVideoPlaying = useCallback(() => practiceRef.current?.videoPlaying(), []);
  const onVideoEnded = useCallback(() => practiceRef.current?.videoEnded(), []);
  const onVideoUnavailable = useCallback(() => practiceRef.current?.videoUnavailable(), []);

  if (loadFailed || !Number.isInteger(day)) {
    return (
      <main style={PAGE_STYLE}>
        <Link href="/course" data-testid="course-back">
          ← Back
        </Link>
        <p style={{ marginTop: 16 }}>{LOAD_FAILED}</p>
      </main>
    );
  }

  if (!detail) {
    return (
      <main style={PAGE_STYLE}>
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main style={PAGE_STYLE}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
        <Link href="/course" data-testid="course-back" style={{ color: "var(--foreground-muted)" }}>
          ← Back
        </Link>
        <span style={{ color: "var(--foreground-muted)" }}>
          Day {detail.day} · Unit {detail.units[0].unit}–{detail.units.at(-1)?.unit}
        </span>
      </div>

      <div className="omy-course-player" style={{ marginTop: 10 }}>
        <CoursePlayer
          ref={playerRef}
          youtubeId={detail.youtube_id}
          startAt={startAt}
          onPlaying={onVideoPlaying}
          onEnded={onVideoEnded}
          onUnavailable={onVideoUnavailable}
        />
      </div>

      <SentencePractice key={detail.day} ref={practiceRef} detail={detail} day={day} player={playerRef} />
    </main>
  );
}
