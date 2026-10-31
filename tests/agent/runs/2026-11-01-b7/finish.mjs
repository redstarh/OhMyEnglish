// 회차 b7 — 수동 「Day 마치기」 → 6초 머묾 → 「← 학습 목록」 → 다시 열기(되감기 확인: 첫 Unit 문장 1 · 영상 0초 cued). 사용: node finish.mjs <day> <label>
import { open, APP, api, saver, sleep, PORT } from "./lib.mjs";
import { connect } from "./cdp.mjs";
const [DAY, LABEL] = [process.argv[2], process.argv[3]];
const { note, save } = saver(`FINISH-${LABEL}`);
const p = await open();
const phaseIs = (ph) => `document.querySelector('[data-testid=course-phase]')?.dataset.phase === '${ph}'`;
const finishBtn = `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Day 마치기')`;
const nextLabel = () => p.ev(`(() => { const b = ${finishBtn} ?? ${p.btn("다음 문장 →")}; return b ? { label: b.textContent.trim(), disabled: b.disabled } : null; })()`);
async function vstate() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
  if (!f) return { iframeTarget: false };
  const fc = await connect(f.webSocketDebuggerUrl);
  const r = await Promise.race([fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player');
    return { url: location.href.slice(0, 80), t: v ? Math.round(v.currentTime * 100) / 100 : null, paused: v?.paused ?? null, state: mp?.getPlayerState?.() ?? null }; })()` }), sleep(3000).then(() => null)]);
  fc.close(); return r?.result.value ?? { evalTimeout: true };
}
try {
  await p.nav(`${APP}/course/${DAY}`, p.READY);
  if ((await p.state()).mode !== "manual") await p.click("수동");
  note("before", await p.state());
  note("nextBeforeStart", await nextLabel());
  note("apiBefore", (await api(`/api/course/days/${DAY}`)).progress);
  await p.click("시작");
  await p.waitFor(phaseIs("listen"), 20000, 10);
  note("nextDuringListen", await nextLabel());
  await p.waitFor(phaseIs("done"), 40000, 10);
  await sleep(300);
  note("atDone", await p.state());
  note("nextAtDone", await nextLabel());
  await p.ev(`${finishBtn}.click()`);
  await sleep(1500);
  note("afterFinish", await p.state());
  note("apiAfterFinish", (await api(`/api/course/days/${DAY}`)).progress);
  await sleep(6000);
  note("apiAfter6s", (await api(`/api/course/days/${DAY}`)).progress);
  await p.ev(`[...document.querySelectorAll('a')].find(a => a.getAttribute('href') === '/course').click()`);
  await p.waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-${DAY}]')`);
  await sleep(1500);
  const ov = await api("/api/course");
  note("overviewAfterLeave", { cycle: ov.cycle, current_day: ov.current_day, day: ov.days.find((d) => d.day === Number(DAY)).progress });
  note("rowAfterLeave", await p.ev(`document.querySelector('[data-testid=course-day-${DAY}]').innerText`));
  await p.ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await p.waitFor(`location.pathname === '/course/${DAY}' && !!document.querySelector('[data-testid=course-sentence]') && !!document.querySelector('[data-testid=course-player] iframe')`, 15000);
  const vs = []; const t0 = Date.now();
  for (const at of [3000, 8000]) { await sleep(Math.max(0, at - (Date.now() - t0))); vs.push({ atMs: Date.now() - t0, ...(await vstate()) }); }
  note("reopened", await p.state());
  note("reopenVideo", vs);
  note("firstSentence", (await api(`/api/course/days/${DAY}`)).units[0]);
  await p.shot(`FINISH-${LABEL}-reopen`);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { save(); p.c.close(); }
