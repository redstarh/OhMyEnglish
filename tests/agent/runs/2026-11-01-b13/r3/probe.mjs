// 회차 b13 r3 — D1(판정 상자 낱말 줄 넘침) 수정 확인. m307.mjs 의 가로채기 부분을 그대로 씀.
// (원래 머리말) 회차 b13 r2 — TASK-307 측정. 사용: node m307.mjs <label> <width> <height>
// (a) 대기·연습·세션·실패의 home-hero 높이 · (b) 연습 중 home-hero-body 안쪽 스크롤 · (c) Start/Next/Finish Day 전후 scrollY
// (d) 이어 가기 줄·빠른 카드 높이 · (e) 세션 중 카드/본문/대화 기록 칸의 스크롤.
// 판정 응답 가로채기: CDP Fetch 로 POST …/attempts 를 200 + 판정 본문으로 채워 「You said」 상자를 띄움(백엔드에 닿지 않음 · stub 은 503).
// 긴 문장: GET /api/course/days/<n> 응답의 문장 글을 다섯 Day 통틀어 가장 긴 문장(Day 1 · 61자)으로 바꿔 끼움(합성).
import { writeFileSync } from "node:fs";
import { page, APP, API, sleep, VIS } from "../h.mjs";
import { slowSocket } from "../slow.mjs";
const [label, W, H] = process.argv.slice(2);
const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b13";
const out = { label, width: +W, height: +H, startedAt: new Date().toISOString(), m: {}, notes: [] };
const note = (k, v) => { out.m[k] = v; console.log(k, JSON.stringify(v)); };
const LONG = "She works in a big building. The building has thirty floors.";  // r3: Day 4 Unit 67 의 실제 문장을 끼워 넣음
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


const RR = `${R}/r3`;
const shot = async (name) => { const r = await p.c.send("Page.captureScreenshot", { format: "png" }); writeFileSync(`${RR}/${label}-${name}.png`, Buffer.from(r.data, "base64")); };
const G = `(() => { const q = (t) => [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length);
  const hero = q('home-hero'), body = q('home-hero-body'), de = document.documentElement; const hr = hero.getBoundingClientRect();
  const inView = (t) => { const e = q(t); if (!e) return null; const r = e.getBoundingClientRect(); const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
    const top = document.elementFromPoint(cx, cy); return { l: Math.round(r.left), r: Math.round(r.right), inside: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight, hitSelf: !!top && (top === e || e.contains(top)) }; };
  return { heroW: Math.round(hr.width * 10) / 10, heroH: Math.round(hr.height * 10) / 10, heroRight: Math.round(hr.right), bodySW: body?.scrollWidth, bodyCW: body?.clientWidth, bodySH: body?.scrollHeight, bodyCH: body?.clientHeight,
    docSW: de.scrollWidth, docCW: de.clientWidth, spoken: !!q('course-spoken'), sentence: q('course-sentence')?.innerText ?? null,
    close: inView('practice-close'), next: inView('course-next') ?? inView('course-finish'), auto: inView('course-mode-auto'), manual: inView('course-mode-manual'),
    rowText: q('course-spoken')?.querySelector('div')?.innerText?.slice(0, 80) ?? null }; })()`;
const g = () => p.ev(G);
const spokenDone = `${phase} === 'done' && !!document.querySelector('[data-testid=course-spoken]')`;
const REAL61 = "We deploy on Fridays. This week we are deploying on Thursday.";
try {
  await p.nav(`${APP}/`); await sleep(3000);
  note("idle", await g());
  // ① 실제 61자 문장(Day 1 · Unit 8 · 3번) — 현재 Day 가 1 임을 먼저 확인
  note("currentDay", (await (await fetch(`${API}/api/course`)).json()).current_day);
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  if ((await p.ev(`document.querySelector('[data-testid=course-mode-manual]')?.getAttribute('aria-pressed')`)) !== "true") await press("course-mode-manual");
  await sleep(300);
  const cur = () => p.ev(`document.querySelector('[data-testid=course-sentence]')?.innerText ?? ''`);
  let k = 0; while (k < 150 && (await cur()) !== REAL61 && (await p.ev(`!!document.querySelector('[data-testid=course-next]')`))) { await press("course-next"); k++; await sleep(60); }
  let b = 0; while (b < 150 && (await cur()) !== REAL61 && !(await p.ev(`document.querySelector('[data-testid=course-prev]').disabled`))) { await press("course-prev"); b++; await sleep(60); }
  note("reachedReal61", { nexts: k, backs: b, sentence: await cur() });
  await press("course-start"); await p.waitFor(spokenDone, 25000); await sleep(700);
  note("real61Spoken", await g()); await shot("real61-spoken");
  // 판정 상자가 뜬 채로 Next 를 실제로 눌러 봄 → 문장이 바뀌어야 함
  const before = await cur(); await press("course-next"); await sleep(700); const after = await cur();
  note("real61NextClick", { before, after, moved: before !== after });
  await press("course-prev"); await sleep(500); await press("course-start"); await p.waitFor(spokenDone, 25000); await sleep(700);
  // ③ 폭 검사(화면에 뜬 판정 상자 안에서 565문장 낱말 줄을 다시 그림) — 새 마크업과 옛 마크업(대조)
  const all = []; for (let d = 1; d <= 6; d++) { const j = await (await fetch(`${API}/api/course/days/${d}`)).json(); for (const u of j.units) u.sentences.forEach((s2, i) => all.push({ day: d, unit: u.unit, i: i + 1, text: s2.text })); }
  const scan = await p.ev(`(() => { const sp = document.querySelector('[data-testid=course-spoken]'); const row = sp.querySelector('div'); const saved = row.innerHTML; const savedStyle = row.getAttribute('style');
    const tmplSpan = row.querySelector('span[data-verdict]'); const legend = row.querySelector('span:not([data-verdict])');
    const hero = document.querySelector('[data-testid=home-hero]'), body = document.querySelector('[data-testid=home-hero-body]'), de = document.documentElement;
    const build = (t, old) => { row.innerHTML = ''; if (old) { row.style.overflowWrap = 'normal'; } else row.setAttribute('style', savedStyle);
      for (const w of t.split(/\\s+/).filter(Boolean)) { const s = tmplSpan.cloneNode(false); s.textContent = w; if (old) s.style.marginRight = '4px'; row.appendChild(s); if (!old) row.appendChild(document.createTextNode(' ')); }
      row.appendChild(legend.cloneNode(true)); };
    const measure = () => ({ heroW: Math.round(hero.getBoundingClientRect().width * 10) / 10, heroH: Math.round(hero.getBoundingClientRect().height), bodySW: body.scrollWidth, bodyCW: body.clientWidth, bodySH: body.scrollHeight, bodyCH: body.clientHeight, docSW: de.scrollWidth });
    const base = measure(); const texts = ${JSON.stringify(all.map((a) => a.text))};
    const res = texts.map(t => { build(t, false); return measure(); });
    build(${JSON.stringify(REAL61)}, true); const oldCtl = measure();
    row.setAttribute('style', savedStyle); row.innerHTML = saved;
    return { base, oldCtl, res }; })()`);
  const bad = scan.res.map((r, i) => ({ ...r, ...all[i] })).filter((r) => r.heroW > scan.base.heroW + 0.5 || r.bodySW > r.bodyCW || r.docSW > scan.base.docSW || r.bodySH > r.bodyCH || r.heroH !== scan.base.heroH);
  note("scan", { total: scan.res.length, base: scan.base, exceed: bad.length, maxHeroW: Math.max(...scan.res.map((r) => r.heroW)), maxBodySH_minus_CH: Math.max(...scan.res.map((r) => r.bodySH - r.bodyCH)), heroHs: [...new Set(scan.res.map((r) => r.heroH))], oldMarkupControl61: scan.oldCtl, firstBad: bad.slice(0, 3) });
  await sleep(300);
  // Close 를 실제로 눌러 봄
  await press("practice-close"); await sleep(1500); note("closeClick", { mode: await p.ev(`document.querySelector('[data-testid=home-hero]').dataset.mode`) });
  // ② Unit 67 문장(합성: Day 응답의 문장 글을 바꿔 끼움)
  longMode = true;
  await press("start-session"); await p.waitFor(ready, 15000); await sleep(1200);
  await press("course-start"); await p.waitFor(spokenDone, 25000); await sleep(700);
  note("u67Spoken", await g()); await shot("u67-spoken");
  longMode = false;
  await press("course-mode-auto"); await sleep(300); const autoPressed = await p.ev(`document.querySelector('[data-testid=course-mode-auto]').getAttribute('aria-pressed')`);
  await press("course-mode-manual"); await sleep(300);
  note("u67AutoClick", { autoPressed, manualBack: await p.ev(`document.querySelector('[data-testid=course-mode-manual]').getAttribute('aria-pressed')`) });
  await press("practice-close"); await sleep(1500); note("u67CloseClick", { mode: await p.ev(`document.querySelector('[data-testid=home-hero]').dataset.mode`) });
  note("idleAfter", await g());
  out.attemptMocks = attemptMocks; out.ok = true;
} catch (e) { out.ok = false; out.error = String(e?.stack ?? e).slice(0, 800); console.log("ERROR", out.error); out.stateAtError = await g().catch((x) => String(x)); await shot("error").catch(() => {}); }
finally { out.logs = p.logs.filter((l) => /exception|error/.test(l.kind) && !/503|Failed to load resource/.test(l.text)).slice(0, 30); writeFileSync(`${RR}/probe-${label}.json`, JSON.stringify(out, null, 1)); p.c.close(); }
