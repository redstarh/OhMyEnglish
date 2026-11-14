// 2단계 보강 — 세션을 여는 나머지 버튼이 어떤 진입으로 소켓을 여는가. 실제 세션 상한(탭당 2개)을 지키려고
// 이 페이지 안에서만 WebSocket 을 가짜로 바꿈: 주소를 기록하고 서버에 붙지 않은 채 0.4초 뒤 닫힘을 알림.
// 그러면 화면은 connection_lost 실패 화면으로 가고, ← Home 으로 대기로 돌아옴. 백엔드에 세션이 생기지 않음.
import { APP, connect, newPage, verdicts } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`entries-${W}.json`);
const { ctx } = await connect();
const page = await newPage(ctx, W);
await page.addInitScript(() => {
  window.__ws = [];
  const Real = window.WebSocket;
  class FakeSocket {
    constructor(url, protocols) {
      if (!String(url).includes("/ws/session")) return new Real(url, protocols);
      this.url = url;
      this.readyState = 0;
      window.__ws.push(url);
      setTimeout(() => {
        this.readyState = 3;
        this.onclose?.({ code: 1006 });
      }, 400);
    }
    send() {}
    close() {
      this.readyState = 3;
    }
  }
  FakeSocket.CONNECTING = 0; FakeSocket.OPEN = 1; FakeSocket.CLOSING = 2; FakeSocket.CLOSED = 3;
  window.WebSocket = FakeSocket;
});

const CASES = [
  ["E1", "practice-free_talk", { source: "additional" }],
  ["E2", "practice-weak_patterns", { source: "additional" }],
  ["E3", "practice-five_questions", { mode: "scenario_intake", source: "additional" }],
  ["E4", "practice-pronunciation", { mode: "pronunciation", source: "additional" }],
  ["E5", "practice-shadowing", { mode: "shadowing", source: "additional" }],
  ["E6", "quick-shadowing", { mode: "shadowing", source: "additional" }],
  ["E7", "quick-weak-patterns", { source: "additional" }],
  ["E8", "focus-practice", { source: "additional" }],
];

try {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 15000 });
  await page.waitForTimeout(800);
  for (const [id, tid, want] of CASES) {
    const n0 = await page.evaluate(() => window.__ws.length);
    const btn = page.locator(`[data-testid="${tid}"]`);
    const disabled = await btn.isDisabled();
    if (disabled) {
      V.add({ id, screen: "home", action: tid, expect: `소켓 질의 ${JSON.stringify(want)}`, actual: "버튼 disabled(대기 상태에서)", verdict: "실패" });
      continue;
    }
    await btn.click();
    await page.waitForSelector('[data-testid="session-failed"]', { timeout: 10000 });
    const reason = await page.locator('[data-testid="session-failed"]').getAttribute("data-reason");
    const url = await page.evaluate((n) => window.__ws[n] ?? null, n0);
    const q = url ? Object.fromEntries(new URL(url).searchParams) : null;
    const ok = q && JSON.stringify(Object.entries(q).sort()) === JSON.stringify(Object.entries(want).sort());
    V.add({ id, screen: "home", action: tid, expect: `소켓 1개 · 질의 ${JSON.stringify(want)}`, actual: `url=${url} reason=${reason}`, verdict: ok && reason === "connection_lost" ? "통과" : "실패" });
    await page.locator('[data-testid="session-failed-home"]').click();
    await page.waitForTimeout(500);
  }
} catch (e) {
  V.add({ id: "EX", screen: "home", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
} finally {
  V.flush();
  await page.close();
  process.exit(0);
}
