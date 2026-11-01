// 회차 b13 — 드라이버 공용부 2: 진짜 마우스 누름 · 8002 요청 기록(본문 포함) · 문장 연습 상태 · 카드 상자 · YouTube iframe 접근.
import { open, APP, API, sleep, VIS } from "./lib.mjs";
export { APP, API, sleep, VIS };

export async function page({ width = 1400, height = 1000, port = 9365 } = {}) {
  const p = await open({ port, width, height });
  await p.c.send("Network.enable");
  p.reqs = []; p.sockets = [];
  p.c.on((d) => {
    if (d.method === "Network.requestWillBeSent" && /:8002/.test(d.params.request.url))
      p.reqs.push({ t: Date.now(), m: d.params.request.method, u: d.params.request.url.replace(API, ""), body: d.params.request.postData?.slice(0, 300) ?? null });
    if (d.method === "Network.webSocketCreated" && /8002/.test(d.params.url)) p.sockets.push({ t: Date.now(), url: d.params.url.replace("ws://localhost:8002", "") });
  });
  p.mouse = async (t) => {
    const pt = await p.ev(`(() => { const e = ${VIS(t)}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
    if (!pt) throw new Error("no element " + t);
    for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 });
    return pt;
  };
  p.sp = () => p.ev(SP);
  p.boxes = () => p.ev(BOXES);
  p.phases = async (ms, until) => { const seen = []; const st = Date.now(); while (Date.now() - st < ms) { const s = await p.ev(`(() => { const g = (t) => document.querySelector('[data-testid=' + t + ']'); return [g('course-phase')?.dataset.phase ?? 'idle', g('course-sentence-number')?.innerText ?? null, g('course-unit')?.innerText?.split(' · ')[0] ?? null]; })()`); const k = s.join('|'); if (seen.at(-1) !== k) seen.push(k); if (until && until(s)) break; await sleep(80); } return seen; };
  p.post = (re) => p.reqs.filter((r) => r.m === "POST" && re.test(r.u));
  return p;
}

export const SP = `(() => { const g = (t) => document.querySelector('[data-testid=' + t + ']'); const hero = g('home-hero');
  return { path: location.pathname, heroMode: hero?.dataset.mode ?? null, heroState: hero?.dataset.state ?? null, practiceDay: g('practice-day')?.innerText ?? null, practiceDayState: g('practice-day')?.dataset.state ?? null,
    spInHero: !!(hero && g('sentence-practice') && hero.contains(g('sentence-practice'))), sp: !!g('sentence-practice'), iframes: document.querySelectorAll('iframe').length,
    phase: g('course-phase')?.dataset.phase ?? 'idle', num: g('course-sentence-number')?.innerText ?? null, unit: g('course-unit')?.innerText ?? null, sentence: g('course-sentence')?.innerText ?? null,
    attempts: g('course-attempts')?.innerText ?? null, notice: g('course-notice')?.innerText ?? null, prevDisabled: g('course-prev')?.disabled ?? null,
    finish: g('course-finish') ? (g('course-finish').disabled ? 'disabled' : 'enabled') : 'absent', retry: !!g('course-retry'), start: !!g('course-start'),
    auto: g('course-mode-auto')?.getAttribute('aria-pressed') ?? null, manual: g('course-mode-manual')?.getAttribute('aria-pressed') ?? null, close: !!g('practice-close'),
    follow: [...document.querySelectorAll('button')].find(b => /where the video is/.test(b.textContent))?.textContent ?? null,
    heroTitle: g('home-hero-title')?.innerText ?? null, heroDay: g('home-hero-day')?.innerText ?? null, panel: !!g('session-panel'),
    navLocked: [...document.querySelectorAll('nav')].filter(n => n.getClientRects().length).map(n => n.dataset.locked ?? null) }; })()`;

const CARDS = ["home-hero", "home-progress", "home-path", "home-focus", "quick-shadowing", "quick-videos", "quick-weak-patterns", "home-more-practice", "home-streak"];
export const BOXES = `Object.fromEntries(${JSON.stringify(CARDS)}.map(t => { const e = [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length); if (!e) return [t, null]; const r = e.getBoundingClientRect(); return [t, [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]]; }))`;

export const api = async (path, init) => { const r = await fetch(`${API}${path}`, init); return { status: r.status, body: await r.json().catch(() => null) }; };
export const dayProgress = async (n) => (await api(`/api/course`)).body.days.find((d) => d.day === n)?.progress ?? null;

// YouTube iframe(별도 프로세스 대상)에 붙어 <video> 를 읽음/조작함
export async function yt(expr, port = 9365) {
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const t = list.find((x) => x.type === "iframe" && /youtube\.com\/embed/.test(x.url));
  if (!t) return { error: "no iframe target" };
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const out = await new Promise((res) => { setTimeout(() => res({ error: "yt timeout" }), 6000); ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id === 1) res(d.result?.result?.value ?? d); };
    ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { expression: expr, returnByValue: true, awaitPromise: true, userGesture: true } })); });
  ws.close();
  return out;
}
export const VID = `(() => { const v = document.querySelector('video'); const m = document.querySelector('#movie_player')?.className ?? ''; return v ? { t: Math.round(v.currentTime * 100) / 100, paused: v.paused, mode: (m.match(/(unstarted|playing|paused|ended|buffering)-mode/) || [null, null])[1] } : null; })()`;
