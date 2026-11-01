// 회차 b12 — 시나리오 2 본체: 홈 카드 안 문장 연습의 단계 · 토글 유지 · 자동 흐름 · 닫기 · Finish Day 와 카드 갱신.
// 사용: node s2.mjs <label> [width]
import { page, APP, sleep, api, dayProgress } from "./h.mjs";
import { saver } from "./lib.mjs";
const label = process.argv[2], width = Number(process.argv[3] ?? 1400);
const { note, save } = saver(`S2-${label}`);
const p = await page({ width });
const openPractice = async () => {
  await p.waitFor(p.hydrated("start-session"), 20000); await sleep(1500);
  await p.mouse("start-session");
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(800);
};
const IDLE_CARD = `(() => { const g = (t) => [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length); return { title: g('home-hero-title')?.innerText ?? null, day: g('home-hero-day')?.innerText ?? null,
  progress: g('home-progress')?.innerText?.replace(/\\s+/g, ' ').slice(0, 300) ?? null, path: g('home-path')?.innerText?.replace(/\\s+/g, ' ').slice(0, 300) ?? null }; })()`;
try {
  const course0 = (await api("/api/course")).body; const cd = course0.current_day;
  note("course0", { cycle: course0.cycle, current_day: cd, counts: course0.days.map((d) => [d.day, d.progress?.completed_count ?? 0]) });
  await p.nav(`${APP}/`); await openPractice();
  note("open", await p.sp());

  // 토글과 새로 고침 유지
  await p.mouse("course-mode-manual"); await sleep(300);
  note("manualClicked", { ...(await p.sp()), ls: await p.ev(`localStorage.getItem('omy.course.mode')`) });
  await p.nav(`${APP}/`); await openPractice();
  const r1 = await p.sp(); note("afterReloadManual", { auto: r1.auto, manual: r1.manual });
  await p.mouse("course-mode-auto"); await sleep(300);
  await p.nav(`${APP}/`); await openPractice();
  const r2 = await p.sp(); note("afterReloadAuto", { auto: r2.auto, manual: r2.manual });
  await p.mouse("course-mode-manual"); await sleep(300);

  // 수동 단계
  const startNum = (await p.sp()).num;
  for (const [name, tid] of [["start", "course-start"], ["again", "course-retry"], ["listen", "course-listen"], ["slow", "course-slow"]]) {
    p.reqs = [];
    await p.ev(`(() => { window.__ph = []; const f = () => { const v = document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle'; if (window.__ph.at(-1) !== v) window.__ph.push(v); }; window.__mo2?.disconnect(); window.__mo2 = new MutationObserver(f); window.__mo2.observe(document.body, { subtree: true, childList: true, attributes: true }); f(); })()`);
    const t0 = Date.now(); await p.mouse(tid);
    await p.phases(15000, (s) => s[0] === "done"); const seen = await p.ev(`window.__ph`);
    await sleep(2500); // 수동은 판정 뒤 멈춰야 함
    const s = await p.sp();
    note(name, { ms: Date.now() - t0, seen, after: { phase: s.phase, num: s.num, notice: s.notice, attempts: s.attempts, retry: s.retry, start: s.start }, stayed: s.num === startNum, attemptsPosts: p.post(/attempts/).map((r) => r.u) });
  }
  const preNav = await p.sp();
  await p.mouse("course-next"); await sleep(500); const n1 = await p.sp();
  await p.mouse("course-prev"); await sleep(500); const b1 = await p.sp();
  note("nextBack", { from: preNav.num, next: { num: n1.num, phase: n1.phase, notice: n1.notice }, back: { num: b1.num, phase: b1.phase, notice: b1.notice } });

  // 자동 한 흐름
  await p.mouse("course-mode-auto"); await sleep(300);
  p.reqs = [];
  await p.mouse("course-start");
  const autoSeen = await p.phases(22000);
  note("auto", { seen: autoSeen, attemptsPosts: p.post(/attempts/).map((r) => r.u) });
  const boxesRunning = await p.boxes(); note("boxesAutoRunning", boxesRunning);
  // 도는 중에 닫기 → 대기로 돌아오고 더 이상 시도가 나가지 않아야 함
  p.reqs = [];
  await p.mouse("practice-close"); const tc = Date.now(); await sleep(6000);
  note("closeWhileAuto", { state: await p.sp(), reqsAfterClose: p.reqs.map((r) => [r.t - tc, r.m, r.u, r.body]), boxes: await p.boxes() });

  // Finish Day: 수동으로 마지막 문장까지 → Start → done → Finish
  await openPractice();
  await p.mouse("course-mode-manual"); await sleep(300);
  let n = 0; while (n < 150 && (await p.ev(`!document.querySelector('[data-testid=course-finish]')`))) { await p.mouse("course-next"); await sleep(120); n++; }
  const last = await p.sp(); note("last", { nexts: n, unit: last.unit, num: last.num, finish: last.finish });
  await p.mouse("course-start"); const ls = await p.phases(15000, (s) => s[0] === "done");
  const ready = await p.sp(); note("lastStart", { seen: ls, finish: ready.finish });
  const before = await dayProgress(cd);
  p.reqs = [];
  await p.mouse("course-finish"); await sleep(2500);
  const fin = await p.sp(); note("finished", { state: fin, posts: p.post(/progress/).map((r) => r.body) });
  const afterFin = await dayProgress(cd); const course1 = (await api("/api/course")).body;
  note("finishApi", { before, afterFin, delta: afterFin.completed_count - before.completed_count, current_day_after: course1.current_day, counts: course1.days.map((d) => [d.day, d.progress?.completed_count ?? 0]) });
  await p.mouse("practice-close"); await sleep(1500);
  const cardNoReload = await p.ev(IDLE_CARD);
  await p.shot(`S2-${label}-after-finish-close`);
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2500);
  const cardReload = await p.ev(IDLE_CARD);
  note("cardAfterFinish", { noReload: cardNoReload, reload: cardReload, same: JSON.stringify(cardNoReload) === JSON.stringify(cardReload) });
  // 닫은 뒤 다시 열면 어느 Day 인가
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(600);
  note("reopenAfterFinish", await p.sp());
  await p.mouse("practice-close"); await sleep(800);
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text))); save(); p.c.close(); }
