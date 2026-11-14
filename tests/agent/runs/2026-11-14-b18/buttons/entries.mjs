// 2단계 — 세션을 여는 버튼의 진입 질의. 실제 세션 상한(탭당 2개)을 지키려고 이 페이지의 /ws/session 소켓만 가짜로 바꿈:
// 주소를 기록하고 0.4초 뒤 닫힘을 알림 → connection_lost 실패 화면 → ← Home. 백엔드에 세션이 생기지 않음.
// 390 은 버튼을 맨 아래로 가져간 뒤 눌러 카드로 스크롤하는지(TASK-308)도 봄.
import { connect, newPage, verdicts, home } from "./lib.mjs";

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
  ["E6", "focus-practice", { source: "additional" }],
];
const heroTop = () => page.evaluate(() => Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().top));

try {
  await home(page);
  for (const [id, tid, want] of CASES) {
    const n0 = await page.evaluate(() => window.__ws.length);
    const btn = page.locator(`[data-testid="${tid}"]`);
    let pre = null;
    if (W < 600) {
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await btn.evaluate((e) => e.scrollIntoView({ block: "end" }));
      await page.waitForTimeout(400);
      pre = await heroTop();
    }
    await btn.click();
    await page.waitForSelector('[data-testid="session-failed"]', { timeout: 10000 });
    await page.waitForTimeout(700);
    const post = W < 600 ? await heroTop() : null;
    const reason = await page.locator('[data-testid="session-failed"]').getAttribute("data-reason");
    const url = await page.evaluate((n) => window.__ws[n] ?? null, n0);
    const q = url ? Object.fromEntries(new URL(url).searchParams) : null;
    // 소켓 주소에 실리는 질의 가운데 진입을 정하는 두 키만 견줌(다른 키가 있으면 actual 에 보임).
    const pick = q ? Object.fromEntries(Object.entries(q).filter(([k]) => k === "mode" || k === "source")) : null;
    const ok = pick && JSON.stringify(Object.entries(pick).sort()) === JSON.stringify(Object.entries(want).sort());
    const scrollOk = W >= 600 || (pre < 0 && post >= 0 && post < 844);
    V.add({ id, screen: `home@${W}`, action: tid, expect: `소켓 1개 · 질의 ${JSON.stringify(want)}${W < 600 ? " · 카드 밖에서 눌러 카드 위가 화면 안" : ""}`, actual: `url=${url} reason=${reason}${W < 600 ? ` heroTop ${pre}→${post}` : ""}`, verdict: ok && reason === "connection_lost" && scrollOk ? "통과" : "실패" });
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
