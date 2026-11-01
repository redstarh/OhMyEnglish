// 회차 b11 — TASK-301: 세션이 오늘의 연습 카드 안에서 도는가 · 이동이 잠기는가 · 끝·실패·복귀.
// 사용: node s301.mjs <label> <width> <height> <entry-testid> <plain|delay|deny-retry|deny-home> [scrollTo-testid]
// delay  : 첫 getUserMedia 를 12초 늦춘 뒤 진짜 가짜 장치를 줌 → 연결 중(잠김) 상태를 오래 붙잡음
// deny-* : 첫 getUserMedia 한 번만 NotAllowedError 로 거절 → 실패 상자
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const [label, W, H, tid, mode, scrollTid] = process.argv.slice(2);
const width = Number(W), height = Number(H);
const { note, save } = saver(`S301-${label}`);
const p = await open({ port: 9347, width, height });
await p.c.send("Network.enable");
const sockets = [], reqs = [];
p.c.on((d) => {
  if (d.method === "Network.webSocketCreated" && /8002/.test(d.params.url)) sockets.push({ t: Date.now(), url: d.params.url });
  if (d.method === "Network.requestWillBeSent" && /:8002/.test(d.params.request.url)) reqs.push(`${d.params.request.method} ${d.params.request.url.replace("http://localhost:8002", "")}`);
});
if (mode === "delay") await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window.__gum = 0;
  navigator.mediaDevices.getUserMedia = (c) => { window.__gum++; return window.__gum === 1 ? new Promise(r => setTimeout(r, 12000)).then(() => orig(c)) : orig(c); }; })()` });
if (mode.startsWith("deny")) await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices); window.__gum = 0;
  navigator.mediaDevices.getUserMedia = (c) => { window.__gum++; return window.__gum === 1 ? Promise.reject(new DOMException('Permission denied', 'NotAllowedError')) : orig(c); }; })()` });

const CARDS = ["home-hero", "home-progress", "home-path", "home-focus", "quick-shadowing", "quick-videos", "quick-weak-patterns", "home-more-practice", "home-streak"];
const BOXES = `Object.fromEntries(${JSON.stringify(CARDS)}.map(t => { const e = [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length); if (!e) return [t, null]; const r = e.getBoundingClientRect(); return [t, [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]]; }))`;
const STATE = `(() => { const hero = document.querySelector('[data-testid=home-hero]'); const f = document.querySelector('[data-testid=session-failed]'); const panel = document.querySelector('[data-testid=session-panel]');
  const navs = [...document.querySelectorAll('nav')].filter(n => n.getClientRects().length);
  const fixedBig = [...document.querySelectorAll('body *')].filter(e => { const cs = getComputedStyle(e); if (cs.position !== 'fixed') return false; const r = e.getBoundingClientRect(); return r.width * r.height > innerWidth * innerHeight * 0.3; }).length;
  return { path: location.pathname, heroMode: hero?.dataset.mode ?? null, panelInHero: !!(panel && hero && hero.contains(panel)), failedInHero: f ? hero?.contains(f) : null, failed: f?.dataset.reason ?? null,
    navLocked: navs.map(n => n.dataset.locked ?? null), navTitle: navs.map(n => n.title || null), overlay: !!document.querySelector('[data-testid=session-overlay]'), fixedBig,
    scrollY: Math.round(scrollY), heroTop: hero ? Math.round(hero.getBoundingClientRect().top) : null, chat: panel ? [...panel.querySelectorAll('p')].map(x => x.textContent.trim()).filter(s => /^(Coach|You)/.test(s)).length : 0 }; })()`;
const LOCKS = `(() => { const q = (s) => [...document.querySelectorAll(s)].filter(e => e.getClientRects().length);
  const links = q('nav a, aside a, header a, a[data-testid^=path-], a[data-testid=home-path-all], a[data-testid=quick-videos], a[data-testid^=practice-]').map(a => ({ tid: a.dataset.testid ?? 'logo', aria: a.getAttribute('aria-disabled'), tab: a.getAttribute('tabindex'), title: a.title || null, pe: getComputedStyle(a).pointerEvents }));
  const buttons = q('[data-testid^=quick-]:is(button), [data-testid^=practice-]:is(button), [data-testid=focus-practice], [data-testid=start-session]').map(b => ({ tid: b.dataset.testid, disabled: b.disabled }));
  return { links, buttons }; })()`;
const mouse = async (t) => {
  const pt = await p.ev(`(() => { const e = ${VIS(t)}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
  if (!pt) return "없음";
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 });
  return pt;
};
const logoPt = () => p.ev(`(() => { const a = [...document.querySelectorAll('aside a[href="/"], header a[href="/"]')].find(e => e.getClientRects().length && !e.dataset.testid); if (!a) return null; const r = a.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);

try {
  await p.nav(`${APP}/`);
  await p.waitFor(p.hydrated(tid), 20000);
  await sleep(2500);
  // 상태 변화를 시간순으로 기록 (클라이언트 이동이라 window 가 남음)
  await p.ev(`(() => { window.__t0 = performance.now(); window.__mo = []; let last = ''; const f = () => { const s = ${STATE}; const k = JSON.stringify([s.path, s.heroMode, s.failed, s.navLocked, s.chat, s.overlay, s.fixedBig]);
    if (s.chat > 0) { window.__activeBoxes = [s.chat, ${BOXES}]; } if (k !== last) { last = k; window.__mo.push([Math.round(performance.now() - window.__t0), s.path, s.heroMode, s.failed, s.navLocked.join(','), s.chat, s.overlay, s.fixedBig]); } };
    new MutationObserver(f).observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true }); f(); })()`);
  if (scrollTid) await p.ev(`${VIS(scrollTid)}.scrollIntoView({ block: 'center', behavior: 'instant' })`);
  note("idleBoxes", await p.ev(BOXES));
  note("idleState", await p.ev(STATE));
  note("idleLocks", await p.ev(LOCKS));
  note("click", await mouse(tid));
  await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session' || location.pathname !== '/'`, 10000, 10);
  note("sessionBoxes", await p.ev(BOXES));
  note("sessionState", await p.ev(STATE));
  await sleep(1200);
  note("sessionStateAfterScroll", await p.ev(STATE));
  await p.shot(`S301-${label}-session`);
  const inSessionLocks = await p.ev(LOCKS); note("sessionLocks", inSessionLocks);

  if (mode === "delay" || mode.startsWith("deny")) {
    if (mode.startsWith("deny")) { await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 10000); note("failedState", await p.ev(STATE));
      note("failedText", await p.ev(`document.querySelector('[data-testid=session-failed]').innerText`)); note("failedLocks", await p.ev(LOCKS)); await p.shot(`S301-${label}-failed`); }
    // 잠긴 요소를 실제 마우스로 누름 — 이동이 없고 소켓이 새로 열리지 않아야 함
    const tries = [];
    const targets = ["nav-practice", "nav-review", "nav-progress", "nav-home", "home-path-all", "path-day-5", "path-day-6", "quick-videos", "practice-videos", "practice-course", "quick-shadowing", "quick-weak-patterns", "focus-practice", "practice-free_talk", "practice-shadowing"];
    for (const t of targets) {
      const pre = await p.ev(STATE); const nSock = sockets.length;
      const pt = await mouse(t); await sleep(400);
      const post = await p.ev(STATE);
      tries.push({ t, pt, lockedBefore: pre.navLocked.join(','), heroBefore: pre.heroMode, path: post.path, heroAfter: post.heroMode, newSockets: sockets.length - nSock });
    }
    const lp = await logoPt(); if (lp) { for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: lp[0], y: lp[1], button: "left", clickCount: 1 }); await sleep(400); tries.push({ t: "logo", pt: lp, ...(await p.ev(`({ path: location.pathname, heroAfter: document.querySelector('[data-testid=home-hero]')?.dataset.mode })`)) }); }
    // 키보드: Tab 으로 잠긴 링크에 초점이 가는가
    const focusSeen = [];
    for (let i = 0; i < 25; i++) { await p.c.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 }); await p.c.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      focusSeen.push(await p.ev(`(() => { const a = document.activeElement; return a ? (a.dataset.testid || a.tagName + ':' + (a.innerText || '').slice(0, 20)) : null; })()`)); }
    note("tabFocus", focusSeen);
    note("lockedTries", tries);
  }
  if (mode === "deny-retry") {
    const n = sockets.length;
    const ok = await p.ev(`(() => { const b = [...document.querySelectorAll('[data-testid=session-failed] button')].find(b => b.textContent.trim() === 'Try again'); if (!b) return false; b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
    for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: ok[0], y: ok[1], button: "left", clickCount: 1 });
    await p.waitFor(`location.pathname.startsWith('/results/') || (!!document.querySelector('[data-testid=session-failed]') && window.__gum > 1)`, 45000, 50);
    note("retrySockets", sockets.slice(n).map((s) => s.url));
  }
  if (mode === "deny-home") {
    await mouse("session-failed-home"); await sleep(800);
    note("afterHomeState", await p.ev(STATE)); note("afterHomeLocks", await p.ev(LOCKS)); note("afterHomeBoxes", await p.ev(BOXES));
    await mouse("nav-practice"); await sleep(1500);
    note("afterHomeNavPractice", await p.ev("location.pathname"));
  } else {
    await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 60000, 50);
    await sleep(800);
    note("end", await p.ev(STATE));
  }
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally {
  try { note("mo", await p.ev("window.__mo")); note("activeBoxes", await p.ev("window.__activeBoxes ?? null")); } catch {}
  note("sockets", sockets.map((s) => s.url)); note("reqs", [...new Set(reqs)]);
  note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React/.test(l.text)));
  save(); p.c.close();
}
