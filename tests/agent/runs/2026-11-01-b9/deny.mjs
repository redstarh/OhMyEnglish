// 회차 b9 — 시나리오 6: 마이크 권한 거부 → 실패 상자 · Try again · Home 복귀. 가짜 장치 없는 Chrome(:9336)에서 돌림.
import { open, APP, saver, sleep } from "./lib.mjs";
const { note, save } = saver("DENY");
const p = await open({ port: 9336 });
const ws = [];
p.c.on((d) => { if (d.method === "Network.webSocketCreated") ws.push(d.params.url); });
await p.c.send("Network.enable");
try {
  await p.c.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "denied", origin: APP });
  await p.nav(`${APP}/`);
  note("permState", await p.ev(`navigator.permissions.query({ name: 'microphone' }).then(s => s.state)`));
  note("gumProbe", await p.ev(`navigator.mediaDevices.getUserMedia({ audio: true }).then(s => { s.getTracks().forEach(t => t.stop()); return 'granted'; }, e => e.name + ': ' + e.message)`));
  await p.click("start-session", 20000);
  await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 15000);
  const box = async () => p.ev(`(() => { const f = document.querySelector('[data-testid=session-failed]'); return f ? { reason: f.dataset.reason, text: f.innerText, inOverlay: !!f.closest('[data-testid=session-overlay]') } : null; })()`);
  note("failed1", await box());
  note("hangul1", await p.hangul());
  await p.shot("DENY-failed");
  // Try again — 같은 거부를 다시 받아야 함
  const tryBtn = `[...document.querySelectorAll('[data-testid=session-failed] button')].find(b => b.textContent.trim() === 'Try again')`;
  note("tryAgainFound", await p.ev(`!!${tryBtn}`));
  await p.ev(`(() => { window.__flips = []; const o = new MutationObserver(() => { const f = document.querySelector('[data-testid=session-failed]'); window.__flips.push([Math.round(performance.now()), !!f]); }); o.observe(document.body, { subtree: true, childList: true }); ${tryBtn}.click(); })()`);
  await sleep(1500);
  note("flipsAfterTryAgain", await p.ev("window.__flips.slice(0, 10)"));
  note("failed2", await box());
  await p.click("session-failed-home");
  await p.waitFor(`!document.querySelector('[data-testid=session-overlay]') && !!document.querySelector('[data-testid=start-session]')`, 10000);
  await sleep(1500);
  note("afterHome", { path: await p.ev("location.pathname"), overlay: await p.ev("!!document.querySelector('[data-testid=session-overlay]')"),
    navVisible: await p.ev(`[...document.querySelectorAll('[data-testid^=nav-]')].filter(e => e.getClientRects().length).length`),
    cells: await p.ev(`['home-streak','home-hero','home-course-progress','home-path','home-focus'].map(t => [t, document.querySelector('[data-testid='+t+']')?.dataset.state])`) });
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { note("webSockets", ws); note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text))); save(); p.c.close(); }
