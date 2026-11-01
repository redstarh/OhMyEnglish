// 회차 b13 r2 — TASK-307 측정. 사용: node m307.mjs <label> <width> <height>
// (a) 대기·연습·세션·실패의 home-hero 높이 · (b) 연습 중 home-hero-body 안쪽 스크롤 · (c) Start/Next/Finish Day 전후 scrollY
// (d) 이어 가기 줄·빠른 카드 높이 · (e) 세션 중 카드/본문/대화 기록 칸의 스크롤.
// 판정 응답 가로채기: CDP Fetch 로 POST …/attempts 를 200 + 판정 본문으로 채워 「You said」 상자를 띄움(백엔드에 닿지 않음 · stub 은 503).
// 긴 문장: GET /api/course/days/<n> 응답의 문장 글을 다섯 Day 통틀어 가장 긴 문장(Day 1 · 61자)으로 바꿔 끼움(합성).
import { writeFileSync } from "node:fs";
import { page, APP, API, sleep, VIS } from "./h.mjs";
import { slowSocket } from "./slow.mjs";
const [label, W, H] = process.argv.slice(2);
const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b13";
const out = { label, width: +W, height: +H, startedAt: new Date().toISOString(), m: {}, notes: [] };
const note = (k, v) => { out.m[k] = v; console.log(k, JSON.stringify(v)); };
const LONG = "We deploy on Fridays. This week we are deploying on Thursday.";
const deny = `(() => { const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = (c) => { if (window.__deny && !window.__denied) { window.__denied = 1; return Promise.reject(new DOMException('Permission denied', 'NotAllowedError')); } return orig(c); }; })()`;
const p = await page({ width: +W, height: +H });
await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: slowSocket(900) + ";" + deny });

const M = `(() => { const q = (t) => [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length);
  const box = (e) => e ? { h: Math.round(e.getBoundingClientRect().height * 10) / 10, sh: e.scrollHeight, ch: e.clientHeight, ov: getComputedStyle(e).overflowY } : null;
  const hero = q('home-hero'), body = q('home-hero-body'), panel = q('session-panel');
  const log = panel ? [...panel.querySelectorAll('div')].find(d => getComputedStyle(d).overflowY === 'auto' && d.scrollHeight > 0 && d !== body) : null;
  return { mode: hero?.dataset.mode ?? null, scrollY: Math.round(scrollY), docH: document.documentElement.scrollHeight, hero: box(hero), body: box(body), log: box(log),
    spoken: !!q('course-spoken'), sentence: q('course-sentence')?.innerText ?? null, failed: !!q('session-failed'),
    path: [...document.querySelectorAll('[data-testid^="path-day-"]')].filter(e => e.getClientRects().length).map(e => Math.round(e.getBoundingClientRect().height * 10) / 10),
    quick: ['quick-shadowing', 'quick-videos', 'quick-weak-patterns'].map(t => q(t) ? Math.round(q(t).getBoundingClientRect().height * 10) / 10 : null),
    pathSection: q('home-path') ? Math.round(q('home-path').getBoundingClientRect().height) : null }; })()`;
const m = () => p.ev(M);
// 스크롤하지 않고 누름 — 요소가 화면 안에 있어야 함
const press = async (t) => { await p.waitFor(p.hydrated(t), 20000);
  const pt = await p.ev(`(() => { const e = ${VIS(t)}; const r = e.getBoundingClientRect(); return (r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth) ? [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)] : ['offscreen', Math.round(r.top), Math.round(r.bottom)]; })()`);
  if (pt[0] === "offscreen") throw new Error(`${t} offscreen ${pt}`);
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 }); };
const phase = `(document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle')`;
const ready = `document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`;

// 가로채기 상태
let longMode = false; let attemptMocks = 0;
p.c.on(async (d) => {
  if (d.method !== "Fetch.requestPaused") return;
  const { requestId, request, responseStatusCode } = d.params;
  try {
    if (/\/attempts$/.test(request.url) && request.method === "POST") {
      attemptMocks++;
      const sent = await p.ev(`document.querySelector('[data-testid=course-sentence]')?.innerText ?? ''`).catch(() => "");
      const words = sent.split(/\s+/).filter(Boolean).map((w, i) => ({ word: w, verdict: i % 4 === 1 ? "different" : i % 5 === 3 ? "missing" : "match" }));
      const body = Buffer.from(JSON.stringify({ transcript: sent, words, attempts: 1 })).toString("base64");
      await p.c.send("Fetch.fulfillRequest", { requestId, responseCode: 200, responseHeaders: [{ name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: "*" }], body });
    } else if (/\/api\/course\/days\/\d+$/.test(request.url) && request.method === "GET" && responseStatusCode && longMode) {
      const r = await p.c.send("Fetch.getResponseBody", { requestId });
      const j = JSON.parse(r.base64Encoded ? Buffer.from(r.body, "base64").toString() : r.body);
      for (const u of j.units) for (const s of u.sentences) s.text = LONG;
      await p.c.send("Fetch.fulfillRequest", { requestId, responseCode: 200, responseHeaders: [{ name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: "*" }], body: Buffer.from(JSON.stringify(j)).toString("base64") });
    } else await p.c.send("Fetch.continueRequest", { requestId });
  } catch (e) { out.notes.push("fetch err " + e.message); await p.c.send("Fetch.continueRequest", { requestId }).catch(() => {}); }
});
await p.c.send("Fetch.enable", { patterns: [{ urlPattern: "*/api/course/sentences/*/attempts", requestStage: "Request" }, { urlPattern: "*/api/course/days/*", requestStage: "Response" }] });

const shot = async (name) => { const r = await p.c.send("Page.captureScreenshot", { format: "png" }); writeFileSync(`${R}/evidence/r2-${label}-${name}.png`, Buffer.from(r.data, "base64")); };
try {
  await p.nav(`${APP}/`); await sleep(3000);
  note("idle", await m()); await shot("idle");
  // (c) Start speaking — 맨 위에서
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  note("practice", await m()); await shot("practice");
  await press("course-mode-manual"); await sleep(300);
  let skip = 0; while (skip < 30 && ((await p.ev(`document.querySelector('[data-testid=course-sentence]')?.innerText ?? ''`)).length > 30)) { await press(await p.ev(`!!document.querySelector('[data-testid=course-next]')`) ? "course-next" : "course-prev"); skip++; await sleep(150); }
  note("skippedLong", skip);
  const y0 = (await m()).scrollY; await press("course-start");
  await p.waitFor(`${phase} === 'done' && !!document.querySelector('[data-testid=course-spoken]')`, 25000); await sleep(600);
  note("practiceSpoken", await m()); await shot("practice-spoken");
  const y1 = (await m()).scrollY; await press("course-next"); await sleep(800);
  note("afterNext", { ...(await m()), scrollBefore: y1, scrollStartBefore: y0 });
  await press("practice-close"); await sleep(1500);
  // 창을 내려 둔 채 Start speaking (Start 단추가 화면 안에 있는 만큼만)
  await p.ev("window.scrollTo(0, 60)"); await sleep(300); const ys = (await m()).scrollY;
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  note("startScrolled", { before: ys, after: (await m()).scrollY, hero: (await m()).hero });
  await press("practice-close"); await sleep(1200); await p.ev("window.scrollTo(0, 0)"); await sleep(300);
  // (b) 긴 문장(합성)
  longMode = true;
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  note("longPractice", await m()); await shot("long");
  await press("course-start"); await p.waitFor(`${phase} === 'done' && !!document.querySelector('[data-testid=course-spoken]')`, 25000); await sleep(600);
  note("longSpoken", await m()); await shot("long-spoken");
  longMode = false;
  note("longSpokenCloseReachable", await p.ev(`(() => { const r = ${VIS("practice-close")}.getBoundingClientRect(); return { left: Math.round(r.left), right: Math.round(r.right), innerWidth }; })()`));
  if (+W < 600) { await p.nav(`${APP}/`); await sleep(2500); } else { await press("practice-close"); await sleep(1500); }
  // (c) Finish Day
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  note("modeBeforeFinishLoop", await p.ev(`[document.querySelector('[data-testid=course-mode-auto]')?.getAttribute('aria-pressed'), document.querySelector('[data-testid=course-mode-manual]')?.getAttribute('aria-pressed')]`));
  if ((await p.ev(`document.querySelector('[data-testid=course-mode-manual]')?.getAttribute('aria-pressed')`)) !== "true") await press("course-mode-manual");
  await sleep(300);
  let k = 0; while (k < 400 && (await p.ev(`!!document.querySelector('[data-testid=course-next]')`))) { await press("course-next"); k++; await sleep(50); }
  await sleep(500); await press("course-start"); await p.waitFor(`${phase} === 'done'`, 25000); await sleep(600);
  const yf = (await m()).scrollY; const dayBefore = (await (await fetch(`${API}/api/course`)).json()).current_day;
  await press("course-finish"); await sleep(1800);
  note("afterFinish", { ...(await m()), scrollBefore: yf, nexts: k, dayBefore, dayAfter: (await (await fetch(`${API}/api/course`)).json()).current_day, notice: await p.ev(`document.querySelector('[data-testid=course-notice]')?.innerText ?? null`) });
  await press("practice-close"); await sleep(2000);
  note("idleAfterFinish", await m());
  // (e) 세션 — Free talk 는 아래쪽이라 사용자처럼 스크롤해서 누름
  await p.mouse("practice-free_talk"); const t0 = Date.now(); const samples = [];
  while (Date.now() - t0 < 40000 && (await p.ev("location.pathname")) === "/") { const s = await m().catch(() => null); if (s?.mode === "session") samples.push(s); await sleep(250); }
  const sess = samples.filter((s) => s.hero);
  note("session", { n: sess.length, heroH: [...new Set(sess.map((s) => s.hero.h))], heroScrolls: sess.filter((s) => s.hero.sh > s.hero.ch).length, bodyScrolls: sess.filter((s) => s.body.sh > s.body.ch + 1).length,
    logMax: sess.reduce((a, s) => (s.log && s.log.sh - s.log.ch > (a?.sh ?? 0) - (a?.ch ?? 0) ? s.log : a), null), logScrolls: sess.filter((s) => s.log && s.log.sh > s.log.ch).length, last: sess.at(-1) });
  // 대화 기록 칸이 넘친 순간의 화면 1장은 sess 로 판정했으므로 생략
  // 실패 상자
  await p.nav(`${APP}/`); await sleep(2500); await p.ev("window.__deny = 1");
  await p.mouse("practice-free_talk"); await p.waitFor(`!!document.querySelector('[data-testid=session-failed]')`, 15000); await sleep(800);
  note("failed", await m()); await shot("failed");
  await p.mouse("session-failed-home"); await sleep(800);
  out.attemptMocks = attemptMocks; out.ok = true;
} catch (e) { out.ok = false; out.error = String(e?.stack ?? e).slice(0, 800); console.log("ERROR", out.error); out.stateAtError = await m().catch((x) => String(x)); console.log("STATE", JSON.stringify(out.stateAtError)); await shot("error").catch(() => {}); }
finally { out.logs = p.logs.filter((l) => /exception|error/.test(l.kind) && !/503|Failed to load resource/.test(l.text)).slice(0, 30); writeFileSync(`${R}/evidence/r2-m307-${label}.json`, JSON.stringify(out, null, 1)); p.c.close(); }
