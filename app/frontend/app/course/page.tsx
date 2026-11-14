import { redirect } from "next/navigation";

// 코스 목록은 홈으로 넘김(`TASK-323` 사용자 결정 · 회차 b16 보고서) — 학습은 홈의 오늘의 연습 카드에서만 함.
// Day 를 고르는 길은 홈 Continue your path 의 Day 줄임(`TASK-314`).
export default function CoursePage() {
  redirect("/");
}
