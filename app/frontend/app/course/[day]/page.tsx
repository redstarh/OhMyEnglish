import { redirect } from "next/navigation";

// 영상과 함께 하던 옛 Day 화면은 홈으로 넘김(`TASK-323` 사용자 결정 · 회차 b16 보고서).
// ⚠️ 같은 폴더의 `CoursePlayer.tsx` 는 문장 칸(`SentencePractice.tsx`)의 영상 연동 타입만 남아 있음 —
//    그 연동은 문장 칸을 다시 짜는 `TASK-317` 에서 함께 걷어 냄.
export default function CourseDayPage() {
  redirect("/");
}
