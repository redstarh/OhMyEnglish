// 회차 b9 — 시나리오 1·2: 홈 칸과 API 대조 · 좁은 화면 배치. 사용: node home.mjs <폭> <라벨>
import { open, APP, api, saver, sleep, VIS } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), label = process.argv[3] ?? `home-${width}`;
const { note, save } = saver(label);
const p = await open({ width, height: width < 600 ? 844 : 1000 });
try {
  const apis = {};
  for (const path of ["/api/history", "/api/weekly-report", "/api/course", "/api/sessions/next-plan", "/api/daily-summary"]) apis[path] = await api(path);
  note("apiStatus", Object.fromEntries(Object.entries(apis).map(([k, v]) => [k, v.status])));
  await p.nav(`${APP}/`);
  await p.waitFor(`['home-streak','home-hero','home-course-progress','home-week-days','home-weekly-stats','home-path','home-focus'].every(t => { const e = document.querySelector('[data-testid='+t+']'); return e && e.dataset.state !== 'loading'; })`, 20000);
  await p.waitFor(`document.querySelector('[data-testid=home-date]')?.textContent.length > 0`, 5000);
  await sleep(800);
  const tids = ["home-date", "home-streak", "home-hero-reason", "home-level", "home-course-progress", "home-week-days", "stat-sessions", "stat-best-streak", "stat-patterns", "home-weekly-stats", "home-path", "home-focus"];
  const cells = {};
  for (const t of tids) cells[t] = await p.ev(`(() => { const e = document.querySelector('[data-testid=${t}]'); return e ? { state: e.dataset.state ?? null, text: e.innerText.replace(/\\s+/g, ' ').trim() } : null; })()`);
  note("cells", cells);
  note("pathDays", await p.ev(`[...document.querySelectorAll('[data-testid^=path-day-]')].map(e => ({ tid: e.dataset.testid, status: e.dataset.status, href: e.getAttribute('href'), text: e.innerText.replace(/\\s+/g,' ') }))`));
  note("barWidth", await p.ev(`(() => { const b = document.querySelector('[data-testid=home-progress] .bg-brand-bright'); return b ? b.style.width : null; })()`));
  note("quick", await p.ev(`[...document.querySelectorAll('[data-testid^=quick-],[data-testid^=practice-]')].map(e => ({ tid: e.dataset.testid, tag: e.tagName, href: e.getAttribute('href'), disabled: e.disabled ?? null, text: e.innerText.replace(/\\s+/g,' ') }))`));

  // 기대값 계산 (API 응답 → 설계서 §5 표)
  const h = apis["/api/history"].body, w = apis["/api/weekly-report"].body, c = apis["/api/course"].body, n = apis["/api/sessions/next-plan"].body, d = apis["/api/daily-summary"].body;
  const done = c.days.filter((x) => (x.progress?.completed_count ?? 0) >= c.cycle).length;
  const recent = [...h.days].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, 7);
  const exp = {
    streak: h.streak.current > 0 ? `${h.streak.current} ${h.streak.current === 1 ? "day" : "days"} in a row` : "Start a streak today",
    reason: n.reason ?? "Let's talk in English.",
    level: n.target_level ? `Speaking · Level ${n.target_level}` : "Speaking",
    course: `${done} / ${c.days.length} days`,
    bar: `${c.days.length ? Math.round((done / c.days.length) * 100) : 0}%`,
    week: `This week: ${recent.filter((x) => x.learned).length} / ${recent.length} days`,
    sessions: w.analyzed ? String(w.metrics.session_count ?? 0) : "–",
    best: String(h.streak.longest),
    patterns: w.analyzed ? String(w.metrics.pattern_count ?? 0) : "–",
    currentDay: c.current_day,
    focusEmpty: !(d.analyzed && d.patterns.length) && !((w.metrics?.top_patterns ?? []).length),
    weeklyMetrics: w.metrics,
  };
  note("expected", exp);
  const got = {
    streak: cells["home-streak"]?.text, reason: cells["home-hero-reason"]?.text, level: cells["home-level"]?.text,
    course: cells["home-course-progress"]?.text, week: cells["home-week-days"]?.text,
    sessions: cells["stat-sessions"]?.text.split(" ")[0], best: cells["stat-best-streak"]?.text.split(" ")[0], patterns: cells["stat-patterns"]?.text.split(" ")[0],
  };
  const cmp = {
    streak: got.streak === exp.streak, reason: got.reason === exp.reason, level: got.level === exp.level,
    course: got.course === exp.course, week: got.week === exp.week, sessions: got.sessions === exp.sessions, best: got.best === exp.best, patterns: got.patterns === exp.patterns,
    focus: exp.focusEmpty ? cells["home-focus"].state === "empty" : cells["home-focus"].state === "ready",
  };
  note("got", got); note("compare", cmp);
  const body = await p.ev("document.body.innerText");
  note("fakeHits", ["68%", "Alex", "+8%", "Good morning", "4/5", "4 / 5"].filter((s) => body.includes(s)));
  note("hangul", await p.hangul());
  note("overflow", await p.overflowX());
  // 배치: 칸들의 x·y
  note("layout", await p.ev(`['home-hero','home-progress','home-path','home-focus','quick-shadowing','quick-videos','quick-weak-patterns','home-more-practice'].map(t => { const r = document.querySelector('[data-testid='+t+']')?.getBoundingClientRect(); return r ? [t, Math.round(r.x), Math.round(r.y), Math.round(r.width)] : [t, null]; })`));
  note("navVisible", await p.ev(`['nav-home','nav-practice','nav-review','nav-progress'].map(t => { const all = [...document.querySelectorAll('[data-testid='+t+']')]; return [t, all.length, all.map(e => e.getClientRects().length > 0), (() => { const e = all.find(e => e.getClientRects().length > 0); if (!e) return null; const r = e.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), e.getAttribute('aria-current')]; })()]; })`).catch((e) => String(e)));
  await p.shot(label);
  await sleep(500);
  note("logs", p.logs);
} catch (e) { note("ERROR", String(e?.stack ?? e)); note("logs", p.logs); }
finally { save(); p.c.close(); }
