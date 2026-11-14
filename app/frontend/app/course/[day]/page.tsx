import { redirect } from "next/navigation";

// 영상과 함께 하던 옛 Day 화면은 홈으로 넘김(`TASK-323` 사용자 결정 · 회차 b16 보고서).
// ⚠️ 영상 플레이어(`CoursePlayer.tsx`)와 문장 칸의 영상 연동은 `TASK-317` 에서 걷어 냈음.
export default function CourseDayPage() {
  redirect("/");
}
