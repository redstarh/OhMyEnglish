// 회차 b9 — 시나리오 6 확장: 추가 학습(기본 쉐도잉) 진입이 마이크 거부로 실패한 뒤, 권한을 허용하고 「Try again」을
// 누르면 같은 학습(mode)으로 다시 여는지. 가짜 장치 Chrome(:9335)에서 권한만 거부→허용으로 바꿈.
// 사용: node retry.mjs <testid>
import { open, APP, saver, sleep } from "./lib.mjs";
const tid = process.argv[2] ?? "quick-shadowing";
const { note, save } = saver(`RETRY-${tid}`);
const p = await open();
const ws = [];
p.c.on((d) => { if (d.method === "Network.webSocketCreated") ws.push(d.params.url); });
await p.c.send("Network.enable");
try {
  // 가짜 UI 플래그가 권한 거부를 덮으므로(1차 실측) 첫 getUserMedia 한 번만 사용자 거부처럼 거절함
  await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window.__gumCalls = 0;
    navigator.mediaDevices.getUserMedia = (c) => { window.__gumCalls++; return window.__gumCalls === 1 ? Promise.reject(new DOMException('Permission denied', 'NotAllowedError')) : orig(c); }; })()` });
  await p.nav(`${APP}/`);
  await p.click(tid, 20000);
  await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 15000);
  note("failed", await p.ev(`document.querySelector('[data-testid=session-failed]').dataset.reason`));
  note("wsBeforeRetry", [...ws]);
  await p.ev(`[...document.querySelectorAll('[data-testid=session-failed] button')].find(b => b.textContent.trim() === 'Try again').click()`);
  await p.waitFor(`location.pathname.startsWith('/results/')`, 30000).catch((e) => note("waitResults", String(e).slice(0, 200)));
  note("gumCalls", await p.ev("window.__gumCalls"));
  note("pathAfterRetry", await p.ev("location.pathname"));
  note("wsAfterRetry", ws.filter((u) => u.includes(":8002")));
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally {
  await p.c.send("Browser.resetPermissions").catch(() => {});
  note("logs", p.logs.filter((l) => !/DevTools|HMR|Failed to load resource/.test(l.text)).map((l) => [l.kind, l.text.slice(0, 200)])); save(); p.c.close();
}
