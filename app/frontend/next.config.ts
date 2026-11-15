import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 아이폰에서 tailnet HTTPS 주소로 열 때 Next 개발 서버가 개발 자원 요청을 막지 않게 함(`TASK-325`).
  // ⚠️ 이 맥의 tailnet 이름만 허용함 — 인터넷에 공개되는 주소가 아님(`tailscale serve` · funnel 아님).
  allowedDevOrigins: ["redstarui-macbookair.tailf9cacf.ts.net"],
};

export default nextConfig;
