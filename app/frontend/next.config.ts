import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 아이폰에서 tailnet HTTPS 주소로 열 때 Next 개발 서버가 개발 자원 요청을 막지 않게 함(`TASK-325`).
  // ⚠️ 이 맥의 tailnet 이름만 허용함 — 인터넷에 공개되는 주소가 아님(`tailscale serve` · funnel 아님).
  // ⛔ `localhost` 도 넣음 — 개발 서버를 `127.0.0.1` 에만 묶었으므로(`TASK-343` · package.json `dev`) 처음 띄운 이름이
  //    `127.0.0.1` 이 되어, 그대로 두면 지금까지 쓰던 `localhost:3000` 의 개발 자원이 막힘(함정 `H-CA` 의 반대 방향).
  allowedDevOrigins: ["localhost", "redstarui-macbookair.tailf9cacf.ts.net"],
  // 화면 구석의 개발 표시(N)를 끔 — 사용자 결정(`TASK-346`). 컴파일·실행 오류 알림은 그대로 뜸.
  devIndicators: false,
};

export default nextConfig;
