import type { MetadataRoute } from "next";

// 아이폰 「홈 화면에 추가」로 열면 Safari 주소 막대·아래 막대 없이 화면 전체를 씀(`TASK-346` 사용자 결정).
// 색은 화면 바탕(`--page`)과 맞춤 — 여는 순간의 바탕과 상태 막대가 앱 바탕과 같음.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "OhMyEnglish",
    short_name: "OhMyEnglish",
    description: "Speak. Remember. Grow.",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f8fc",
    theme_color: "#f7f8fc",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
